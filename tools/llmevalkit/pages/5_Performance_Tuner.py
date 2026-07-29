# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Streamlit page for Performance Tuner (Prompt Optimization)."""

import json
import logging
import os
from argparse import Namespace
from datetime import datetime

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from etils import epath
from google.cloud import aiplatform, storage
from src import vapo_lib
from src.gcp_prompt import GcpPrompt as gcp_prompt
from vertexai.evaluation import MetricPromptTemplateExamples
from vertexai.preview import prompts

load_dotenv("src/.env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TARGET_MODELS = [
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-2.0-flash",
    "gemini-2.0-flash-001",
    "gemini-2.0-flash-lite",
    "gemini-2.0-flash-lite-001",
]


def initialize_session_state() -> None:
    if "op_id" not in st.session_state:
        st.session_state.op_id = vapo_lib.get_id()

    if "local_prompt" not in st.session_state:
        st.session_state.local_prompt = gcp_prompt()

    if "storage_client" not in st.session_state:
        st.session_state["storage_client"] = storage.Client()

    if "data_uris" not in st.session_state:
        st.session_state["data_uris"] = refresh_bucket()

    if "dataset" not in st.session_state:
        st.session_state["dataset"] = None

    if "cached_data_files" not in st.session_state:
        st.session_state.cached_data_files = {}
    if "last_selected_dataset_for_cache" not in st.session_state:
        st.session_state.last_selected_dataset_for_cache = None

    if "tuner_launched_job" not in st.session_state:
        st.session_state.tuner_launched_job = None

    if "tuner_run_uri" not in st.session_state:
        st.session_state.tuner_run_uri = None

    if "tuner_winning_template" not in st.session_state:
        st.session_state.tuner_winning_template = None


def refresh_bucket() -> list[str]:
    logger.info("Bucket: %s", os.getenv("BUCKET"))
    bucket = st.session_state.storage_client.bucket(os.getenv("BUCKET"))
    blobs = bucket.list_blobs()
    data_uris = []
    for i in blobs:
        if i.name.split("/")[0] == "datasets" and (
            i.name.endswith(".csv") or i.name.endswith(".jsonl")
        ):
            data_uris.append(f"gs://{i.bucket.name}/{i.name}")
    return data_uris


def get_optimization_args(
    input_optimization_data_file_uri,
    output_optimization_run_uri,
    target_model,
    selected_metrics,
    target_qps=1.0,
    optimizer_qps=1.0,
    eval_qps=1.0,
    data_limit=10,
):
    response_schema_str = st.session_state.local_prompt.prompt_meta.get(
        "response_schema", "{}"
    )
    try:
        response_schema = (
            json.loads(response_schema_str)
            if isinstance(response_schema_str, str)
            else response_schema_str
        )
    except json.JSONDecodeError:
        response_schema = {}

    response_mime_type = "application/json" if response_schema else "text/plain"
    response_schema_arg = response_schema if response_schema else ""

    has_multimodal = False
    if (
        st.session_state.dataset is not None
        and "image" in st.session_state.dataset.columns
    ):
        has_multimodal = True

    metrics = (
        selected_metrics if selected_metrics else ["question_answering_correctness"]
    )
    weights = [1.0 for _ in metrics]

    return Namespace(
        system_instruction=st.session_state.local_prompt.prompt_to_run.system_instruction,
        prompt_template=(
            f"{st.session_state.local_prompt.prompt_to_run.prompt_data}"
            "\n\tAnswer: {target}"
        ),
        target_model=target_model,
        optimization_mode="instruction",
        eval_metrics_types=metrics,
        eval_metrics_weights=weights,
        aggregation_type="weighted_sum",
        input_data_path=input_optimization_data_file_uri,
        output_path=f"gs://{output_optimization_run_uri}",
        project=os.getenv("PROJECT_ID"),
        num_steps=5,
        num_demo_set_candidates=10,
        demo_set_size=3,
        target_model_location="us-central1",
        source_model="",
        source_model_location="",
        target_model_qps=target_qps,
        optimizer_model_qps=optimizer_qps,
        eval_qps=eval_qps,
        source_model_qps="",
        response_mime_type=response_mime_type,
        response_schema=response_schema_arg,
        language="English",
        placeholder_to_content=json.loads("{}"),
        data_limit=data_limit,
        translation_source_field_name="",
        has_multimodal_inputs=has_multimodal,
    )


def check_job_status(job_name: str, project_id: str, location: str) -> str:
    client_options = {"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    client = aiplatform.gapic.JobServiceClient(client_options=client_options)
    parent = f"projects/{project_id}/locations/{location}"
    response = client.list_custom_jobs(parent=parent)
    for job in response:
        if job.display_name == job_name:
            return job.state.name
    return "NOT_FOUND"


def write_record(metrics, prompt_name, version, system_instruction):
    bucket_name = os.getenv("BUCKET")
    if not bucket_name:
        return

    record = {
        "timestamp": datetime.now().isoformat(),
        "prompt_name": prompt_name,
        "prompt_version": version,
        "system_instruction": system_instruction,
        "scores": metrics,
    }

    blob_name = f"records/{prompt_name}_{version}_{datetime.now().strftime('%Y%m%d%H%M%S')}.json"
    bucket = st.session_state.storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)
    blob.upload_from_string(json.dumps([record], indent=2))
    logger.info(f"Saved optimized record to gs://{bucket_name}/{blob_name}")


def main() -> None:
    st.set_page_config(
        layout="wide", page_title="Performance Tuner", page_icon="assets/favicon.ico"
    )
    initialize_session_state()

    st.title("Performance Tuner")
    st.markdown(
        "Optimize your prompt's System Instructions using data-driven iteration to maximize metric performance."
    )

    # 1. & 2. Data Setup & Template Definition
    st.header("1. Data & Prompt Setup")
    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Data Setup")
        data_sets = list({i.split("/")[4] for i in st.session_state.data_uris})
        st.selectbox("Select Dataset", options=[None, *data_sets], key="tuner_dataset")

        if st.session_state.tuner_dataset:
            if (
                st.session_state.tuner_dataset
                != st.session_state.last_selected_dataset_for_cache
                or st.session_state.tuner_dataset
                not in st.session_state.cached_data_files
            ):
                bucket = st.session_state.storage_client.bucket(os.getenv("BUCKET"))
                prefix = f"datasets/{st.session_state.tuner_dataset}/"
                blobs_iterator = bucket.list_blobs(prefix=prefix)
                current_dataset_files = [
                    blob.name[len(prefix) :]
                    for blob in blobs_iterator
                    if (blob.name.endswith(".csv") or blob.name.endswith(".jsonl"))
                    and not blob.name.endswith("/")
                ]
                st.session_state.cached_data_files[st.session_state.tuner_dataset] = (
                    sorted(set(current_dataset_files))
                )
                st.session_state.last_selected_dataset_for_cache = (
                    st.session_state.tuner_dataset
                )

            files = st.session_state.cached_data_files.get(
                st.session_state.tuner_dataset, []
            )
            st.selectbox(
                "Select File (.csv or .jsonl)", options=[None, *files], key="tuner_file"
            )

            if st.button("Load Dataset", key="tuner_load_data"):
                if st.session_state.tuner_file:
                    gcs_uri = f"gs://{os.getenv('BUCKET')}/datasets/{st.session_state.tuner_dataset}/{st.session_state.tuner_file}"
                    if st.session_state.tuner_file.endswith(".jsonl"):
                        st.session_state.dataset = pd.read_json(gcs_uri, lines=True)
                    else:
                        st.session_state.dataset = pd.read_csv(gcs_uri)
                    st.success(f"Loaded {len(st.session_state.dataset)} rows.")

    with col2:
        st.subheader("Template Definition")
        st.selectbox(
            "Select Prompt",
            options=st.session_state.local_prompt.existing_prompts.keys(),
            placeholder="Select Prompt...",
            key="tuner_prompt",
        )

        if st.session_state.tuner_prompt:
            st.session_state.local_prompt.prompt_meta["name"] = (
                st.session_state.tuner_prompt
            )
            versions = [
                i.version_id
                for i in prompts.list_versions(
                    st.session_state.local_prompt.existing_prompts[
                        st.session_state.tuner_prompt
                    ]
                )
            ]
            st.selectbox(
                "Select Version",
                options=versions,
                placeholder="Select Version...",
                key="tuner_version",
            )

        if st.button("Load Prompt", key="tuner_load_prompt"):
            if st.session_state.tuner_prompt and st.session_state.tuner_version:
                st.session_state.local_prompt.load_prompt(
                    st.session_state.local_prompt.existing_prompts[
                        st.session_state.tuner_prompt
                    ],
                    st.session_state.tuner_prompt,
                    st.session_state.tuner_version,
                )
                st.success("Prompt loaded successfully.")

    if st.session_state.local_prompt.prompt_to_run.system_instruction:
        with st.expander("View Loaded Prompt Details", expanded=False):
            st.text_area(
                "System Instruction",
                st.session_state.local_prompt.prompt_to_run.system_instruction,
                disabled=True,
                height=100,
            )
            st.text_area(
                "Prompt Template",
                st.session_state.local_prompt.prompt_to_run.prompt_data,
                disabled=True,
                height=100,
            )

    st.divider()

    # 3. Metric Selection
    st.header("2. Metric Selection")
    metric_names = MetricPromptTemplateExamples.list_example_metric_names()
    computation_metrics = [
        "bleu",
        "rouge_1",
        "rouge_2",
        "rouge_l",
        "rouge_l_sum",
        "exact_match",
        "question_answering_correctness",
    ]
    all_metrics = list(set(metric_names + computation_metrics))

    selected_metrics = st.multiselect(
        "Select Evaluation Metrics for Optimization",
        options=all_metrics,
        default=["question_answering_correctness"],
        key="tuner_metrics",
    )
    target_model = st.selectbox(
        "Select Target Model", options=TARGET_MODELS, key="tuner_target_model"
    )

    with st.expander("Advanced Settings"):
        st.session_state.tuner_target_qps = st.number_input(
            "Target Model QPS",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            key="tuner_target_qps_input",
        )
        st.session_state.tuner_optimizer_qps = st.number_input(
            "Optimizer Model QPS",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            key="tuner_optimizer_qps_input",
        )
        st.session_state.tuner_eval_qps = st.number_input(
            "Evaluation QPS",
            min_value=0.1,
            max_value=10.0,
            value=1.0,
            step=0.1,
            key="tuner_eval_qps_input",
        )
        st.session_state.tuner_data_limit = st.number_input(
            "Data Limit (Sample Size)",
            min_value=1,
            max_value=1000,
            value=10,
            step=1,
            key="tuner_data_limit_input",
        )

    st.divider()

    # 4. Execution
    st.header("3. Execution")
    if st.button("Start Optimization Job", type="primary"):
        if not st.session_state.dataset is not None:
            st.error("Please load a dataset first.")
            return
        if not st.session_state.local_prompt.prompt_to_run.system_instruction:
            st.error("Please load a prompt first.")
            return
        if not selected_metrics:
            st.error("Please select at least one metric.")
            return

        with st.spinner("Initializing Job..."):
            workspace_uri = (
                epath.Path(os.getenv("BUCKET"))
                / "optimization"
                / st.session_state.op_id
            )
            input_data_uri = workspace_uri / "data"
            workspace_uri.mkdir(parents=True, exist_ok=True)
            input_data_uri.mkdir(parents=True, exist_ok=True)
            output_optimization_data_uri = workspace_uri / "optimization_jobs"

            job_name = f"{st.session_state.tuner_prompt}-{st.session_state.tuner_version}-{st.session_state.tuner_dataset}-{st.session_state.op_id}"
            output_optimization_run_uri = str(output_optimization_data_uri / job_name)
            input_optimization_data_file_uri = f"gs://{input_data_uri}/{job_name}.jsonl"

            st.session_state.dataset.to_json(
                str(input_optimization_data_file_uri), orient="records", lines=True
            )

            args = get_optimization_args(
                input_optimization_data_file_uri,
                output_optimization_run_uri,
                target_model,
                selected_metrics,
                st.session_state.tuner_target_qps,
                st.session_state.tuner_optimizer_qps,
                st.session_state.tuner_eval_qps,
                st.session_state.tuner_data_limit,
            )
            args_dict = vars(args)

            config_file_uri = "gs://" + str(workspace_uri / "config" / "config.json")
            with epath.Path(config_file_uri).open("w") as config_file:
                json.dump(args_dict, config_file)

            worker_pool_specs = [
                {
                    "machine_spec": {"machine_type": "n1-standard-4"},
                    "replica_count": 1,
                    "container_spec": {
                        "image_uri": os.getenv("APD_CONTAINER_URI"),
                        "args": ["--config=" + config_file_uri],
                    },
                }
            ]

            custom_job = aiplatform.CustomJob(
                display_name=job_name,
                worker_pool_specs=worker_pool_specs,
                staging_bucket=str(workspace_uri),
            )
            custom_job.run(service_account=os.getenv("APD_SERVICE_ACCOUNT"), sync=False)

            st.session_state.tuner_launched_job = job_name
            st.session_state.tuner_run_uri = f"gs://{os.getenv('BUCKET')}/optimization/{st.session_state.op_id}/optimization_jobs/{job_name}"
            st.success(f"Started Optimization Job: {job_name}")

    if st.session_state.tuner_launched_job:
        st.info(f"Active Job Tracked: {st.session_state.tuner_launched_job}")

    st.divider()

    # 5. Results Report
    st.header("4. Results Report")
    if st.button("Load Results"):
        if not st.session_state.tuner_launched_job:
            st.warning("No optimization job has been launched in this session.")
        else:
            with st.spinner("Checking job status..."):
                status = check_job_status(
                    st.session_state.tuner_launched_job,
                    os.getenv("PROJECT_ID"),
                    os.getenv("LOCATION"),
                )
                if status in ["JOB_STATE_PENDING", "JOB_STATE_RUNNING"]:
                    st.info(
                        f"Job is still {status.replace('JOB_STATE_', '')}. Please check back later. (Hill-climbing algorithms may take a while)."
                    )
                elif status == "JOB_STATE_FAILED":
                    st.error(
                        "The optimization job failed. Check Agent Platform console logs."
                    )
                elif status == "JOB_STATE_SUCCEEDED":
                    st.success("Job Complete! Processing results...")

                    try:
                        results_ui = vapo_lib.ResultsUI(st.session_state.tuner_run_uri)
                        if getattr(results_ui, "templates", None) and getattr(
                            results_ui, "eval_results", None
                        ):
                            baseline = results_ui.templates[0]
                            winner = results_ui.templates[-1]

                            st.subheader("Score Jump")
                            mean_cols = [
                                c
                                for c in baseline.columns
                                if c.startswith("metrics.") and "/mean" in c
                            ]

                            col_metrics = st.columns(min(len(mean_cols), 4) or 1)
                            final_scores = {}
                            for idx, m_col in enumerate(mean_cols):
                                b_val = (
                                    float(baseline[m_col].iloc[0])
                                    if m_col in baseline
                                    else 0.0
                                )
                                w_val = (
                                    float(winner[m_col].iloc[0])
                                    if m_col in winner
                                    else 0.0
                                )
                                diff = w_val - b_val
                                label = (
                                    m_col.replace("metrics.", "")
                                    .replace("/mean", "")
                                    .title()
                                )
                                final_scores[label] = w_val

                                with col_metrics[idx % len(col_metrics)]:
                                    st.metric(
                                        label, f"{w_val:.3f}", delta=f"{diff:.3f}"
                                    )

                            st.subheader("Winner System Instruction")
                            winning_system_text = (
                                winner["prompt"].iloc[0]
                                if "prompt" in winner
                                else "Unable to parse winning prompt."
                            )
                            # Usually the optimizer alters the instruction which is the "prompt" field in vapo_lib output.
                            st.text_area(
                                "Optimized Instruction", winning_system_text, height=150
                            )

                            st.session_state.tuner_winning_template = (
                                winning_system_text
                            )
                            st.session_state.tuner_final_scores = final_scores
                        else:
                            st.warning("Results found but could not be parsed.")
                    except Exception as e:
                        st.error(f"Error loading results: {e}")
                else:
                    st.warning(f"Job state is currently: {status}")

    st.divider()

    # 6. Validation
    st.header("5. Validation")
    st.markdown("Test the best performing prompt on a blind test case.")
    blind_test_json = st.text_area(
        "Blind Test Case Input (JSON)",
        placeholder='{"ticket_text": "I lost my password..."}',
        height=100,
    )

    if st.button("Test Best Prompt"):
        if not st.session_state.tuner_winning_template:
            st.warning("Please load successful results first.")
        elif not blind_test_json:
            st.warning("Please provide a test case in JSON format.")
        else:
            try:
                test_input = json.loads(blind_test_json)

                # Setup temporary prompt object to run test
                prompt_obj = st.session_state.local_prompt
                prompt_obj.prompt_to_run.system_instruction = (
                    st.session_state.tuner_winning_template
                )
                # Keep original generation config/schema

                with st.spinner("Generating Response..."):
                    res = prompt_obj.generate_response(test_input)

                st.success("Evaluation complete.")
                st.text_area("Validation Response", res, height=150, disabled=True)
            except Exception as e:
                st.error(f"Failed to generate test response: {e}")

    st.divider()

    # 7. Outcome
    st.header("6. Outcome")
    if st.button("Export Final Prompt & Save Report", type="primary"):
        if not st.session_state.tuner_winning_template:
            st.error("No winning template found. Please load results first.")
        else:
            try:
                prompt_obj = st.session_state.local_prompt
                prompt_obj.prompt_to_run.system_instruction = (
                    st.session_state.tuner_winning_template
                )

                # Save as new version
                with st.spinner("Saving optimized prompt to registry..."):
                    prompt_obj.save_prompt(check_existing=False)

                new_version = prompt_obj.prompt_to_run._version_id or "latest"
                st.success(f"Successfully exported as version: {new_version}")

                # Save evaluation records
                if "tuner_final_scores" in st.session_state:
                    with st.spinner("Saving performance report..."):
                        write_record(
                            st.session_state.tuner_final_scores,
                            st.session_state.tuner_prompt,
                            new_version,
                            st.session_state.tuner_winning_template,
                        )
                    st.success("Performance report saved to GCS.")
            except Exception as e:
                st.error(f"Failed to save outcome: {e}")


if __name__ == "__main__":
    main()
