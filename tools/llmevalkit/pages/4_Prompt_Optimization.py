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


"""Streamlit page for running Vertex AI Prompt Optimization.

This script provides a user interface for:
- Loading existing prompts from Vertex AI Prompt Registry.
- Loading datasets from a Google Cloud Storage bucket.
- Generating baseline responses and evaluating them against a ground truth.
- Configuring and launching a Vertex AI CustomJob for prompt optimization.
- Displaying baseline evaluation results.

File Source:
https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/prompts/prompt_optimizer/vapo_lib.py
"""

import json
import logging
import os
from argparse import Namespace

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from etils import epath
from google.cloud import aiplatform, storage
from src import vapo_lib
from src.gcp_prompt import GcpPrompt as gcp_prompt
from vertexai.preview import prompts

load_dotenv("src/.env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

TARGET_MODELS = ["gemini-2.0-flash-001", "gemini-2.0-flash-lite-001"]


def initialize_session_state() -> None:
    """Initializes the session state variables."""
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


def refresh_bucket() -> list[str]:
    """Refreshes the list of available dataset URIs from the GCS bucket.

    This function lists all blobs in the configured GCS bucket, filters for
    CSV and JSONL files located within the 'datasets/' prefix, and constructs a list
    of their full gs:// URI paths.

    Returns:
        A list of strings, where each string is a GCS URI to a dataset file.
    """
    logger.info("Bucket: %s", os.getenv("BUCKET"))
    bucket = st.session_state.storage_client.bucket(os.getenv("BUCKET"))
    blobs = bucket.list_blobs()
    data_uris = []
    for i in blobs:
        if i.name.split("/")[0] == "datasets" and (
            i.name.endswith(".csv") or i.name.endswith(".jsonl")
        ):
            data_uris.append(f"gs://{i.bucket.name}/{i.name}")
    logger.info("Data URIs: %s", data_uris)
    return data_uris


def prompt_selection() -> None:
    """Handles the prompt selection and loading."""
    st.selectbox(
        "Select Existing Prompt",
        options=st.session_state.local_prompt.existing_prompts.keys(),
        placeholder="Select Prompt...",
        key="selected_prompt",
    )
    if st.session_state.selected_prompt:
        logger.info("Prompt Meta: %s", st.session_state.local_prompt.prompt_meta)
        st.session_state.local_prompt.prompt_meta["name"] = (
            st.session_state.selected_prompt
        )
        versions = [
            i.version_id
            for i in prompts.list_versions(
                st.session_state.local_prompt.existing_prompts[
                    st.session_state.selected_prompt
                ]
            )
        ]

        st.selectbox(
            "Select Version",
            options=versions,
            placeholder="Select Version...",
            key="selected_version",
        )

    st.button("Load Prompt", key="load_existing_prompt_button")
    if st.session_state.load_existing_prompt_button:
        logger.info(
            "Selected Prompt ID: %s",
            st.session_state.local_prompt.existing_prompts[
                st.session_state.selected_prompt
            ],
        )
        logger.info("Version: %s", st.session_state.selected_version)
        st.session_state.local_prompt.load_prompt(
            st.session_state.local_prompt.existing_prompts[
                st.session_state.selected_prompt
            ],
            st.session_state.selected_prompt,
            st.session_state.selected_version,
        )
        logger.info("Local Prompt Meta: %s", st.session_state.local_prompt.prompt_meta)
        logger.info(
            "Local Prompt Meta Dict Keys: %s",
            st.session_state.local_prompt.prompt_meta.keys(),
        )

        st.session_state.prompt_name = (
            st.session_state.local_prompt.prompt_to_run.prompt_name
        )
        st.session_state.prompt_data = (
            st.session_state.local_prompt.prompt_to_run.prompt_data
        )
        st.session_state.model_name = (
            st.session_state.local_prompt.prompt_to_run.model_name.split("/")[-1]
        )
        st.session_state.system_instructions = (
            st.session_state.local_prompt.prompt_to_run.system_instruction
        )
        st.session_state.response_schema = json.dumps(
            st.session_state.local_prompt.prompt_meta.get("response_schema", {})
        )
        st.session_state.generation_config = json.dumps(
            st.session_state.local_prompt.prompt_meta.get("generation_config", {})
        )
        st.session_state.meta_tags = st.session_state.local_prompt.prompt_meta[
            "meta_tags"
        ]


def dataset_selection() -> None:
    """Handles the dataset selection and loading."""
    data_sets = list({i.split("/")[4] for i in st.session_state.data_uris})
    logger.info("Data Sets: %s", data_sets)
    st.selectbox(
        "Select an Existing Dataset", options=[None, *data_sets], key="selected_dataset"
    )

    files_to_display_in_selectbox = []
    if st.session_state.selected_dataset:
        if (
            st.session_state.selected_dataset
            != st.session_state.last_selected_dataset_for_cache
            or st.session_state.selected_dataset
            not in st.session_state.cached_data_files
        ):
            logger.info(
                "Cache miss or dataset changed for files. Fetching for: %s",
                st.session_state.selected_dataset,
            )
            bucket = st.session_state.storage_client.bucket(os.getenv("BUCKET"))
            prefix = f"datasets/{st.session_state.selected_dataset}/"
            blobs_iterator = bucket.list_blobs(prefix=prefix)

            current_dataset_files = []
            for blob in blobs_iterator:
                if (
                    blob.name.endswith(".csv") or blob.name.endswith(".jsonl")
                ) and not blob.name.endswith("/"):
                    filename = blob.name[len(prefix) :]
                    if filename:
                        current_dataset_files.append(filename)

            st.session_state.cached_data_files[st.session_state.selected_dataset] = (
                sorted(set(current_dataset_files))
            )
            st.session_state.last_selected_dataset_for_cache = (
                st.session_state.selected_dataset
            )
            logger.info(
                "Cached files for %s: %s",
                st.session_state.selected_dataset,
                st.session_state.cached_data_files[st.session_state.selected_dataset],
            )

            if "selected_file_from_dataset" in st.session_state:
                st.session_state.selected_file_from_dataset = None
                logger.info("Reset selected_file_from_dataset due to dataset change.")

        files_to_display_in_selectbox = st.session_state.cached_data_files.get(
            st.session_state.selected_dataset, []
        )

        st.selectbox(
            "Select a file from this dataset:",
            options=[None, *files_to_display_in_selectbox],
            key="selected_file_from_dataset",
        )

    st.button("Load Dataset", key="load_existing_dataset_button")
    if st.session_state.load_existing_dataset_button:
        gcs_uri = f"gs://{os.getenv('BUCKET')}/datasets/{st.session_state.selected_dataset}/{st.session_state.selected_file_from_dataset}"
        logger.info("Loading file: %s", gcs_uri)
        if st.session_state.selected_file_from_dataset.endswith(".jsonl"):
            st.session_state.dataset = pd.read_json(gcs_uri, lines=True)
        else:
            st.session_state.dataset = pd.read_csv(gcs_uri)

    if st.session_state.dataset is not None:
        st.dataframe(st.session_state.dataset)


def get_optimization_args(
    input_optimization_data_file_uri, output_optimization_run_uri
):
    """Gets the arguments for the optimization job."""
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

    if response_schema and response_schema != {}:
        response_mime_type = "application/json"
        response_schema_arg = response_schema
    else:
        response_mime_type = "text/plain"
        response_schema_arg = ""

    has_multimodal = False
    if (
        st.session_state.dataset is not None
        and "image" in st.session_state.dataset.columns
    ):
        has_multimodal = True

    return Namespace(
        system_instruction=st.session_state.local_prompt.prompt_to_run.system_instruction,
        prompt_template=(
            f"{st.session_state.local_prompt.prompt_to_run.prompt_data}"
            "\n\tAnswer: {target}"
        ),
        target_model="gemini-2.0-flash-001",
        optimization_mode="instruction",
        eval_metrics_types=[
            "question_answering_correctness",
        ],
        eval_metrics_weights=[
            1.0,
        ],
        aggregation_type="weighted_sum",
        input_data_path=input_optimization_data_file_uri,
        output_path=f"gs://{output_optimization_run_uri}",
        project=os.getenv("PROJECT_ID"),
        num_steps=10,
        num_demo_set_candidates=10,
        demo_set_size=3,
        target_model_location="us-central1",
        source_model="",
        source_model_location="",
        target_model_qps=1,
        optimizer_model_qps=1,
        eval_qps=1,
        source_model_qps="",
        response_mime_type=response_mime_type,
        response_schema=response_schema_arg,
        language="English",
        placeholder_to_content=json.loads("{}"),
        data_limit=10,
        translation_source_field_name="",
        has_multimodal_inputs=has_multimodal,
    )


def start_optimization() -> None:
    """Starts the optimization job."""
    st.divider()

    st.subheader("Run Optimization")
    st.button("Start Optimization", key="start_optimization_button")

    if st.session_state.start_optimization_button:
        workspace_uri = (
            epath.Path(os.getenv("BUCKET")) / "optimization" / st.session_state.op_id
        )
        logger.info("Workspace URI: %s", workspace_uri)

        input_data_uri = epath.Path(workspace_uri) / "data"
        logger.info("Input Data URI: %s", input_data_uri)

        workspace_uri.mkdir(parents=True, exist_ok=True)
        input_data_uri.mkdir(parents=True, exist_ok=True)

        output_optimization_data_uri = epath.Path(workspace_uri) / "optimization_jobs"
        logger.info("Output Data URI: %s", output_optimization_data_uri)

        prompt_optimization_job = (
            f"{st.session_state.selected_prompt}-"
            f"{st.session_state.selected_version}-"
            f"{st.session_state.selected_dataset}-"
            f"{st.session_state.op_id}"
        )
        output_optimization_run_uri = str(
            output_optimization_data_uri / prompt_optimization_job
        )
        input_optimization_data_file_uri = (
            f"gs://{input_data_uri}/{prompt_optimization_job}.jsonl"
        )
        logger.info("Input Optimization Data URI: %s", input_optimization_data_file_uri)
        if st.session_state.dataset is not None:
            st.session_state.dataset.to_json(
                str(input_optimization_data_file_uri), orient="records", lines=True
            )
        else:
            st.error("Please load a dataset first.")
            return

        args = get_optimization_args(
            input_optimization_data_file_uri, output_optimization_run_uri
        )

        with st.expander("Prompt Optimization Config"):
            st.json(vars(args))

        args = vars(args)

        config_file_uri = "gs://" + str(workspace_uri / "config" / "config.json")

        with epath.Path(config_file_uri).open("w") as config_file:
            json.dump(args, config_file)
        config_file.close()
        st.success(f"Successfully wrote config file to {config_file_uri}")

        worker_pool_specs = [
            {
                "machine_spec": {
                    "machine_type": "n1-standard-4",
                },
                "replica_count": 1,
                "container_spec": {
                    "image_uri": os.getenv("APD_CONTAINER_URI"),
                    "args": ["--config=" + config_file_uri],
                },
            }
        ]

        custom_job = aiplatform.CustomJob(
            display_name=prompt_optimization_job,
            worker_pool_specs=worker_pool_specs,
            staging_bucket=str(workspace_uri),
        )

        custom_job.run(service_account=os.getenv("APD_SERVICE_ACCOUNT"), sync=False)

        st.success("Successfully Started Job!!")


def main() -> None:
    """Streamlit page for Prompt Optimization."""
    st.set_page_config(
        layout="wide", page_title="Prompt Optimization", page_icon="assets/favicon.ico"
    )

    initialize_session_state()

    st.header("Prompt Optimization")

    st.selectbox(
        "Select Target Model for Optimization:",
        options=TARGET_MODELS,
        key="target_model_optimization",
    )

    prompt_selection()
    dataset_selection()
    start_optimization()


if __name__ == "__main__":
    main()
