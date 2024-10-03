# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# pylint: disable=import-outside-toplevel, inconsistent-return-statements, missing-function-docstring
# pylint: disable=no-member, no-value-for-parameter, redefined-outer-name
# pylint: disable=too-many-arguments, singleton-comparison, too-many-locals
# pylint: disable=undefined-loop-variable,
# mypy: disable-error-code="no-untyped-def, valid-type, no-untyped-def, assignment"


"""Champion Challenger Auto Side-by-side Evaluation Vertex AI Pipelines"""

from typing import NamedTuple

from kfp import compiler, dsl
from kfp.dsl import Artifact, Dataset, Input, Output, component

PIPELINE_TEMPLATE = "champion_challenger_pipeline.yaml"


# Component to retrieve model config from GCS
@component(base_image="python:3.12", packages_to_install=["google-cloud-storage"])
def get_model_config(
    bucket_name: str,
    model_config_blob: str,
    param_file_name: str,
) -> NamedTuple(
    "params",
    [
        ("model", str),
        ("system_instruction", str),
        ("prompt_template", str),
        ("temperature", int),
        ("max_output_tokens", int),
        ("top_p", float),
    ],
):
    from collections import namedtuple
    import json

    from google.cloud import storage

    bucket = storage.Client().get_bucket(bucket_name)
    model_param_blob = bucket.blob(f"{model_config_blob}/{param_file_name}")
    if model_param_blob.exists():
        model_params = json.loads(
            bucket.blob(f"{model_config_blob}/{param_file_name}").download_as_string()
        )

        params = namedtuple(
            "params",
            [
                "model",
                "system_instruction",
                "prompt_template",
                "temperature",
                "max_output_tokens",
                "top_p",
            ],
        )
        return params(
            model_params["model"],
            model_params["system_instruction"],
            model_params["prompt_template"],
            model_params["temperature"],
            model_params["max_output_tokens"],
            model_params["top_p"],
        )
    raise RuntimeError("Missing current champion model config json")


# Component to get and store model responses in BQ
@component(
    base_image="python:3.12",
    packages_to_install=["google-cloud-aiplatform", "pandas", "pandas-gbq"],
)
def get_model_response(
    model_id: str,
    system_instruction: str,
    prompt_template: str,
    temperature: int,
    max_output_tokens: int,
    top_p: float,
    project_id: str,
    bq_dataset: str,
    bq_source_table: str,
    bq_model_response_table: str,
    model_response_summary: Output[Dataset],
):
    import pandas as pd
    from vertexai.generative_models import GenerativeModel, SafetySetting

    model_response_df = pd.read_gbq(
        f"{project_id}.{bq_dataset}.{bq_model_response_table}"
    )

    if model_response_df.empty:

        def generate(
            text,
            model_id,
            system_instruction,
            input_prompt_template,
            temperature,
            max_output_tokens,
            top_p,
        ):
            safety_settings = [
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
                SafetySetting(
                    category=SafetySetting.HarmCategory.HARM_CATEGORY_HARASSMENT,
                    threshold=SafetySetting.HarmBlockThreshold.BLOCK_ONLY_HIGH,
                ),
            ]

            generation_config = {
                "max_output_tokens": max_output_tokens,
                "temperature": temperature,
                "top_p": top_p,
            }

            prompt_template = input_prompt_template
            prompt = f"{prompt_template} \n{text}"

            model = GenerativeModel(model_id, system_instruction=[system_instruction])

            response = model.generate_content(
                [prompt],
                generation_config=generation_config,
                safety_settings=safety_settings,
            )

            return pd.Series([response.text, prompt])

        articles_df = pd.read_gbq(f"{project_id}.{bq_dataset}.{bq_source_table}")
        articles_df[["model_summary", "prompt"]] = articles_df.apply(
            lambda x: generate(
                x.article,
                model_id,
                system_instruction,
                prompt_template,
                temperature,
                max_output_tokens,
                top_p,
            ),
            axis=1,
        )
        articles_df[["id", "model_summary", "prompt"]].to_gbq(
            f"{project_id}.{bq_dataset}.{bq_model_response_table}",
            project_id=project_id,
            if_exists="replace",
        )

        model_response_summary.metadata = {
            "bq_table_id": f"{project_id}.{bq_dataset}.{bq_model_response_table}"
        }
        model_response_summary.path = (
            f"https://console.cloud.google.com/bigquery?"
            f"project={project_id}&ws=!1m5!1m4!4m3!1s"
            f"{project_id}!2s{bq_dataset}!3s{bq_model_response_table}"
        )

    else:
        model_response_summary.metadata = {
            "bq_table_id": f"{project_id}.{bq_dataset}.{bq_model_response_table}"
        }
        model_response_summary.path = (
            f"https://console.cloud.google.com/bigquery?"
            f"project={project_id}&ws=!1m5!1m4!4m3!1s"
            f"{project_id}!2s{bq_dataset}!3s{bq_model_response_table}"
        )


# Component to create champion challenger response evaluation table in BQ
@component(base_image="python:3.12", packages_to_install=["pandas", "pandas-gbq"])
def eval_dataset(
    current_model_response: Input[Dataset],
    challenger_model_response: Input[Dataset],
    bq_eval_table: str,
    bq_dataset: str,
    bq_source_table: str,
    project_id: str,
    evaluation_dataset: Output[Dataset],
):
    import pandas as pd

    input_prompt_current_df = pd.read_gbq(
        current_model_response.metadata["bq_table_id"]
    )
    input_prompt_challenger_df = pd.read_gbq(
        challenger_model_response.metadata["bq_table_id"]
    )

    input_prompt_current_df.rename(
        columns={"model_summary": "current_model_summary"}, inplace=True
    )
    input_prompt_challenger_df.rename(
        columns={"model_summary": "challenger_model_summary"}, inplace=True
    )

    merged_df = pd.merge(input_prompt_current_df, input_prompt_challenger_df, on="id")

    bq_source_df = pd.read_gbq(f"{project_id}.{bq_dataset}.{bq_source_table}")

    eval_df = pd.merge(
        bq_source_df[["id", "article"]],
        merged_df[["id", "current_model_summary", "challenger_model_summary"]],
        on="id",
    )

    eval_df.to_gbq(
        f"{project_id}.{bq_dataset}.{bq_eval_table}",
        project_id=project_id,
        if_exists="replace",
    )

    evaluation_dataset.metadata = {
        "bq_table_id": f"{project_id}.{bq_dataset}.{bq_eval_table}"
    }
    evaluation_dataset.path = (
        f"https://console.cloud.google.com/bigquery?"
        f"project={project_id}&ws=!1m5!1m4!4m3!1s"
        f"{project_id}!2s{bq_dataset}!3s{bq_eval_table}"
    )


# Component to run auto_sxs
@component(
    base_image="us-docker.pkg.dev/vertex-ai/training/tf-cpu.2-12.py310:latest",
    packages_to_install=["google-cloud-aiplatform", "pandas"],
)
def auto_sxs_eval(
    eval_dataset: Input[Dataset],
    project_id: str,
    id_column: str,
    inference_context_column: str,
    response_a_column: str,
    response_b_column: str,
    bucket_uri: str,
    region_id: str,
    judgements: Output[Dataset],
    summary_metrics: Output[Dataset],
    task: str = "summarization",
):
    import os

    from google.cloud import aiplatform
    import pandas as pd

    bq_eval_table = eval_dataset.metadata["bq_table_id"]
    parameters = {
        "evaluation_dataset": bq_eval_table,
        "id_columns": [id_column],
        "task": task,
        "autorater_prompt_parameters": {
            "inference_context": {"column": inference_context_column},
            "inference_instruction": {"template": "{{ default_instruction }}"},
        },
        "response_column_a": response_a_column,
        "response_column_b": response_b_column,
    }

    aiplatform.init(project=project_id, location=region_id, staging_bucket=bucket_uri)

    job = aiplatform.PipelineJob(
        display_name="summarisation_autosxs_eval",
        pipeline_root=os.path.join(bucket_uri, "summarisation_autosxs_eval"),
        template_path=(
            "https://us-kfp.pkg.dev/ml-pipeline/google-cloud-registry/autosxs-template/default"
        ),
        parameter_values=parameters,
    )
    job.run()

    for details in job.task_details:
        if details.task_name == "online-evaluation-pairwise":
            break

    # Judgments
    judgments_uri = details.outputs["judgments"].artifacts[0].uri
    judgments_df = pd.read_json(judgments_uri, lines=True)
    judgments_df.rename(
        columns={
            "response_a": "current_model_response_A",
            "response_b": "challenger_model_response_B",
        },
        inplace=True,
    )
    judgments_df.to_csv(judgements.path, index=False)

    for details in job.task_details:
        if details.task_name == "model-evaluation-text-generation-pairwise":
            break
    summary_metrics_df = pd.DataFrame(
        [details.outputs["autosxs_metrics"].artifacts[0].metadata]
    )
    summary_metrics_df.rename(
        columns={
            "autosxs_model_a_win_rate": "current_model_win_rate",
            "autosxs_model_b_win_rate": "challenger_model_win_rate",
        },
        inplace=True,
    )
    summary_metrics_df.to_csv(summary_metrics.path, index=False)


# Component to check if challenger win rate is greater than current champion model
@component(base_image="python:3.12", packages_to_install=["pandas"])
def challenger_model_better(summary_metrics: Input[Dataset]) -> bool:
    import pandas as pd

    summary_metrics_df = pd.read_csv(summary_metrics.path)
    challenger_winning = (
        summary_metrics_df["challenger_model_win_rate"].values
        > summary_metrics_df["current_model_win_rate"].values
    )[0]
    return bool(challenger_winning)


# Update current champion model if challenger is winning
@component(base_image="python:3.12", packages_to_install=["google-cloud-storage"])
def update_current_model_config(
    bucket_name: str,
    model_config_blob: str,
    param_file: str,
    champion_model_id: str,
    champion_system_instruction: str,
    champion_prompt_template: str,
    champion_temperature: int,
    champion_max_output_tokens: int,
    champion_top_p: float,
    champion_model_config: Output[Artifact],
):
    from datetime import datetime
    import json

    from google.cloud import storage

    params = {
        "model": champion_model_id,
        "system_instruction": champion_system_instruction,
        "prompt_template": champion_prompt_template,
        "temperature": champion_temperature,
        "max_output_tokens": champion_max_output_tokens,
        "top_p": champion_top_p,
    }

    bucket = storage.Client().get_bucket(bucket_name)
    blob = bucket.blob(f"{model_config_blob}/{param_file}")
    if blob.exists():
        now = datetime.now()
        now = now.strftime("%Y-%m-%d_%H-%M-%S")
        destination_blob_name = f"{model_config_blob}/{now}-{param_file}"
        destination_generation_match_precondition = 0

        bucket.copy_blob(
            blob,
            bucket,
            destination_blob_name,
            if_generation_match=destination_generation_match_precondition,
        )

    blob.upload_from_string(data=json.dumps(params), content_type="application/json")

    champion_model_config.path = f"gs://{bucket_name}/{model_config_blob}/{param_file}"
    champion_model_config.metadata = {"model_id": champion_model_id}


# Kubeflow Pipeline to orchestrate all the components """
@dsl.pipeline
def pipeline():
    # Expects a model config file gs://genops/model-config/summarization.json
    project_id = "YOUR_PROJECT_ID"
    region_autosxs = "us-central1"
    bucket_name = "genops"
    model_config_blob = "model-config"
    bq_dataset = "genops"
    bq_source_table = "summarizer_data"

    challenger_param_file = "challenger_summarization.json"
    challenger_model_config = get_model_config(
        bucket_name=bucket_name,
        model_config_blob=model_config_blob,
        param_file_name=challenger_param_file,
    ).set_display_name("challenger_model_config")

    bq_challenger_model_response_table = "summarizer_challenger_model"
    challenger_model_response = get_model_response(
        model_id=challenger_model_config.outputs["model"],
        system_instruction=challenger_model_config.outputs["system_instruction"],
        prompt_template=challenger_model_config.outputs["prompt_template"],
        temperature=challenger_model_config.outputs["temperature"],
        max_output_tokens=challenger_model_config.outputs["max_output_tokens"],
        top_p=challenger_model_config.outputs["top_p"],
        project_id=project_id,
        bq_dataset=bq_dataset,
        bq_source_table=bq_source_table,
        bq_model_response_table=bq_challenger_model_response_table,
    ).set_display_name("challenger_model_summary")

    current_param_file = "summarization.json"
    current_model_config = get_model_config(
        bucket_name=bucket_name,
        model_config_blob=model_config_blob,
        param_file_name=current_param_file,
    ).set_display_name("current_model_config")

    bq_current_model_response_table = "summarizer_champion_model"
    current_model_response = get_model_response(
        model_id=current_model_config.outputs["model"],
        system_instruction=current_model_config.outputs["system_instruction"],
        prompt_template=current_model_config.outputs["prompt_template"],
        temperature=current_model_config.outputs["temperature"],
        max_output_tokens=current_model_config.outputs["max_output_tokens"],
        top_p=current_model_config.outputs["top_p"],
        project_id=project_id,
        bq_dataset=bq_dataset,
        bq_source_table=bq_source_table,
        bq_model_response_table=bq_current_model_response_table,
    ).set_display_name("current_model_summary")

    bq_eval_table_name = "summarizer_champion_challenger_eval"
    eval_responses = eval_dataset(
        current_model_response=current_model_response.outputs["model_response_summary"],
        challenger_model_response=challenger_model_response.outputs[
            "model_response_summary"
        ],
        bq_dataset=bq_dataset,
        bq_eval_table=bq_eval_table_name,
        bq_source_table=bq_source_table,
        project_id=project_id,
    ).set_display_name("evaluation_data")

    pipeline_bucket_uri = "gs://genops-eval-pipelines"
    eval_results = auto_sxs_eval(
        eval_dataset=eval_responses.outputs["evaluation_dataset"],
        id_column="id",
        inference_context_column="article",
        response_a_column="current_model_summary",
        response_b_column="challenger_model_summary",
        project_id=project_id,
        region_id=region_autosxs,
        bucket_uri=pipeline_bucket_uri,
    )

    challenger_winning = challenger_model_better(
        summary_metrics=eval_results.outputs["summary_metrics"]
    )
    with dsl.If(challenger_winning.output == True):  # noqa: E712
        update_current_model_config(
            bucket_name=bucket_name,
            model_config_blob=model_config_blob,
            param_file=current_param_file,
            champion_model_id=challenger_model_config.outputs["model"],
            champion_system_instruction=challenger_model_config.outputs[
                "system_instruction"
            ],
            champion_prompt_template=challenger_model_config.outputs["prompt_template"],
            champion_temperature=challenger_model_config.outputs["temperature"],
            champion_max_output_tokens=challenger_model_config.outputs[
                "max_output_tokens"
            ],
            champion_top_p=challenger_model_config.outputs["top_p"],
        )


if __name__ == "__main__":
    compiler.Compiler().compile(pipeline_func=pipeline, package_path=PIPELINE_TEMPLATE)
