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

import datetime
import json
import logging
import os
import re

import pandas as pd
import streamlit as st
import vertexai
from dotenv import load_dotenv
from google.cloud import storage
from src.gcp_prompt import GcpPrompt as gcp_prompt
from vertexai.evaluation import (
    EvalTask,
    MetricPromptTemplateExamples,
    PairwiseMetricPromptTemplate,
    PointwiseMetricPromptTemplate,
)
from vertexai.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
)
from vertexai.preview import prompts

load_dotenv("src/.env")


logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def get_metric_object_by_name(metric_name: str):
    """Retrieves a metric template object from its string name."""
    try:
        return MetricPromptTemplateExamples._PROMPT_TEMPLATE_MAP[metric_name]
    except Exception as e:
        logger.exception(f"Failed to get metric object for {metric_name}: {e}")
        raise


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


def get_autorater_pairwise_response(metric_prompt: str, model: str) -> dict:
    """Gets a response from the autorater model for pairwise evaluation.

    Args:
        metric_prompt: The prompt to send to the autorater model.
        model: The name of the evaluation model to use.

    Returns:
        A dictionary containing the autorater's response.
    """
    metric_response_schema = {
        "type": "OBJECT",
        "properties": {
            "pairwise_choice": {"type": "STRING"},
            "explanation": {"type": "STRING"},
        },
        "required": ["pairwise_choice", "explanation"],
    }

    autorater = GenerativeModel(
        model,
        generation_config=GenerationConfig(
            response_mime_type="application/json",
            response_schema=metric_response_schema,
        ),
        safety_settings={
            HarmCategory.HARM_CATEGORY_UNSPECIFIED: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
        },
    )

    response = autorater.generate_content(metric_prompt)
    response_json = {}

    if response.candidates and len(response.candidates) > 0:
        candidate = response.candidates[0]
        if (
            candidate.content
            and candidate.content.parts
            and len(candidate.content.parts) > 0
        ):
            part = candidate.content.parts[0]
            if part.text:
                response_json = json.loads(part.text)

    return response_json


def main() -> None:
    """Initializes and runs the Streamlit evaluation application.

    This function sets up the Streamlit page configuration, initializes session state
    variables, and orchestrates the user interface for the evaluation workflow.
    It handles dataset and prompt selection, response generation or loading,
    human-in-the-loop rating, and the launching of automated evaluations.
    """
    st.set_page_config(
        layout="wide",
        page_title="Prompt Engineering App",
        page_icon="assets/favicon.ico",
    )

    st.header("Evaluation Set-Up")

    if "storage_client" not in st.session_state:
        st.session_state["storage_client"] = storage.Client()

    if "data_uris" not in st.session_state:
        st.session_state["data_uris"] = refresh_bucket()

    if "current_index" not in st.session_state:
        st.session_state.current_index = 0

    if "eval_result" not in st.session_state:
        st.session_state.eval_result = None

    if "custom_eval_result" not in st.session_state:
        st.session_state.custom_eval_result = None

    if "df_data" not in st.session_state:
        st.session_state.df_data = None

    if "df_dataset_eval" not in st.session_state:
        st.session_state.df_dataset_eval = None

    if "all_metrics_eval" not in st.session_state:
        st.session_state.all_metrics_eval = None

    if "metrics" not in st.session_state:
        st.session_state.metrics = None

    if "local_prompt" not in st.session_state:
        st.session_state.local_prompt = gcp_prompt()

    if "cached_data_files" not in st.session_state:
        st.session_state.cached_data_files = {}
    if "last_selected_dataset_for_cache" not in st.session_state:
        st.session_state.last_selected_dataset_for_cache = None

    if "cached_prompt_versions" not in st.session_state:
        st.session_state.cached_prompt_versions = {}

    if "last_selected_prompt_for_versions_cache" not in st.session_state:
        st.session_state.last_selected_prompt_for_versions_cache = None

    if "human_rated_dict" not in st.session_state:
        st.session_state.human_rated_dict = {}

    if "metric_preview_index" not in st.session_state:
        st.session_state.metric_preview_index = 0

    if "vertex_session_init" not in st.session_state:
        vertexai.init(
            project=os.getenv("PROJECT_ID"),
            location=os.getenv("LOCATION"),
            staging_bucket=os.getenv("BUCKET"),
            experiment=os.getenv("EXPERIMENT_NAME"),
        )
        st.session_state.vertex_session_init = True

    data_sets = list({i.split("/")[4] for i in st.session_state.data_uris})
    logger.info(f"Data Sets: {data_sets}")
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

    st.text_input("Number of Samples", key="n_samples")

    st.text_input(
        "Ground Truth Column Name",
        key="ground_truth_column_name",
        value="target",
        help="The name of the column in your dataset that contains the ground truth or target response.",
    )

    st.selectbox(
        "Select Existing Prompt",
        options=[None, *list(st.session_state.local_prompt.existing_prompts.keys())],
        placeholder="Select Prompt...",
        key="selected_prompt",
    )

    versions_to_display_in_selectbox = []
    if st.session_state.selected_prompt:
        st.session_state.local_prompt.prompt_meta["name"] = (
            st.session_state.selected_prompt
        )

        selected_prompt_obj = st.session_state.local_prompt.existing_prompts[
            st.session_state.selected_prompt
        ]
        prompt_resource_name_for_cache = str(selected_prompt_obj)

        if (
            st.session_state.selected_prompt
            != st.session_state.last_selected_prompt_for_versions_cache
            or prompt_resource_name_for_cache
            not in st.session_state.cached_prompt_versions
        ):
            logger.info(
                "Cache miss or prompt changed for versions. Fetching for: %s",
                st.session_state.selected_prompt,
            )
            fetched_versions = [
                v.version_id for v in prompts.list_versions(selected_prompt_obj)
            ]

            st.session_state.cached_prompt_versions[prompt_resource_name_for_cache] = (
                fetched_versions
            )
            st.session_state.last_selected_prompt_for_versions_cache = (
                st.session_state.selected_prompt
            )
            logger.info(
                "Cached versions for %s: %s",
                st.session_state.selected_prompt,
                fetched_versions,
            )

            if "selected_version" in st.session_state:
                st.session_state.selected_version = None
                logger.info("Reset selected_version due to prompt change.")
        versions_to_display_in_selectbox = st.session_state.cached_prompt_versions.get(
            prompt_resource_name_for_cache, []
        )

        st.selectbox(
            "Select Version",
            options=versions_to_display_in_selectbox,
            placeholder="Select Version...",
            key="selected_version",
        )

    st.button("Load Prompt", key="load_prompt_button")
    if st.session_state.load_prompt_button:
        logger.info(
            f"Selected Prompt ID: {st.session_state.local_prompt.existing_prompts[st.session_state.selected_prompt]}"
        )
        logger.info(f"Version: {st.session_state.selected_version}")
        st.session_state.local_prompt.load_prompt(
            st.session_state.local_prompt.existing_prompts[
                st.session_state.selected_prompt
            ],
            st.session_state.selected_prompt,
            st.session_state.selected_version,
        )
        logger.info(f"Local Prompt Meta: {st.session_state.local_prompt.prompt_meta}")
        logger.info(
            f"Local Prompt Meta Dict Keys: {st.session_state.local_prompt.prompt_meta.keys()}"
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

    st.button("Upload Data and Get Responses", key="upload_data_get_responses_button")

    if (
        st.session_state.upload_data_get_responses_button
        and st.session_state.n_samples
        and st.session_state.selected_dataset
    ):
        if not st.session_state.n_samples:
            st.warning("Please enter the Number of Samples.")
            return
        if not st.session_state.selected_dataset:
            st.warning("Please select an Existing Dataset.")
            return
        if not st.session_state.selected_file_from_dataset:
            st.warning("Please select a file from the dataset.")
            return

        try:
            num_samples = int(st.session_state.n_samples)
            if num_samples <= 0:
                st.warning("Number of Samples must be a positive integer.")
                return
        except ValueError:
            st.warning("Number of Samples must be a valid integer.")
            return

        gcs_path = f"gs://{os.getenv('BUCKET')}/datasets/{st.session_state.selected_dataset}/{st.session_state.selected_file_from_dataset}"
        st.session_state["input_data_uri"] = gcs_path
        try:
            if gcs_path.endswith(".csv"):
                df_full = pd.read_csv(gcs_path)
            elif gcs_path.endswith(".jsonl"):
                df_full = pd.read_json(gcs_path, lines=True)
            else:
                st.error(f"Unsupported file type: {gcs_path.split('.')[-1]}")
                return
        except Exception as e:
            st.error(f"Error reading data from {gcs_path}: {e}")
            return

        df = df_full.iloc[:num_samples]
        if df.empty:
            st.warning(
                "No data found for the first %s samples in %s, or the file is smaller than requested.",
                num_samples,
                st.session_state.selected_file_from_dataset,
            )
            st.session_state.human_rated_dict = {}
            st.session_state.ratings = []
            st.session_state.include_in_evaluations = []
            st.session_state.current_index = 0
            return

        user_input_list = []
        expected_result_list = []
        assistant_response_list = []
        baseline_model_response_list = []

        generate = False
        ground_truth_col = st.session_state.ground_truth_column_name
        required_cols_for_loading_existing = [
            "user_input",
            ground_truth_col,
            "assistant_response",
        ]

        if "assistant_response" in df.columns:
            missing_loading_cols = [
                col
                for col in required_cols_for_loading_existing
                if col not in df.columns
            ]
            if not missing_loading_cols:
                logger.info("Sufficient columns found to load existing responses.")
                generate = False
            else:
                st.error(
                    f"The file has 'assistant_response' column, but is missing other essential columns for loading: {missing_loading_cols}. Required for loading: {required_cols_for_loading_existing}. Found columns: {df.columns.tolist()}",
                )
                st.session_state.human_rated_dict = {}
                st.session_state.ratings = []
                st.session_state.include_in_evaluations = []
                st.session_state.current_index = 0
                return
        else:
            if not st.session_state.get("prompt_data"):
                st.error(
                    "To generate new responses, please load a prompt first using the 'Load Prompt' button."
                )
                st.session_state.human_rated_dict = {}
                st.session_state.ratings = []
                st.session_state.include_in_evaluations = []
                st.session_state.current_index = 0
                return

            template_vars = re.findall(r"{(\w+)}", st.session_state.prompt_data)
            required_cols_for_generating_new = list(set(template_vars))

            all_required_cols = [*required_cols_for_generating_new, ground_truth_col]
            missing_generating_cols = [
                col for col in all_required_cols if col not in df.columns
            ]

            if not missing_generating_cols:
                logger.info(
                    "'assistant_response' column not found. Required columns for generating new responses are present. Will generate."
                )
                generate = True
            else:
                st.error(
                    f"The file does not have 'assistant_response' column, and is also missing columns required for generating new responses based on the loaded prompt: {missing_generating_cols}. Required for generation: {all_required_cols}. Found columns: {df.columns.tolist()}",
                )
                st.session_state.human_rated_dict = {}
                st.session_state.ratings = []
                st.session_state.include_in_evaluations = []
                st.session_state.current_index = 0
                return

        logger.info("Generate flag set to: %s for %s samples.", generate, len(df))

        if generate:
            logger.info("Proceeding with generating new assistant responses.")
            if (
                not st.session_state.selected_prompt
                or not st.session_state.selected_version
            ):
                st.error(
                    "A prompt and version must be loaded to generate new responses. Please use the 'Load Prompt' button."
                )
                st.session_state.human_rated_dict = {}
                st.session_state.ratings = []
                st.session_state.include_in_evaluations = []
                st.session_state.current_index = 0
                return
            if not st.session_state.local_prompt.prompt_to_run.prompt_data:
                st.error(
                    "Prompt data is missing from the loaded prompt. Cannot generate. Please re-load the prompt using 'Load Prompt'."
                )
                st.session_state.human_rated_dict = {}
                st.session_state.ratings = []
                st.session_state.include_in_evaluations = []
                st.session_state.current_index = 0
                return

            if len(df) > 0:
                st.session_state.generation_progress_bar = st.progress(
                    0, text="Starting response generation..."
                )

            template_vars = re.findall(r"{(\w+)}", st.session_state.prompt_data)
            required_cols_for_generating_new = list(set(template_vars))
            for idx, r in df.iterrows():
                current_user_input_item = {
                    col: r[col] for col in required_cols_for_generating_new
                }
                try:
                    generated_text = st.session_state.local_prompt.generate_response(
                        current_user_input_item
                    )
                    user_input_list.append(current_user_input_item)
                    expected_result_list.append(
                        r[st.session_state.ground_truth_column_name]
                    )
                    assistant_response_list.append(generated_text)
                    if "generation_progress_bar" in st.session_state:
                        progress_text = f"Generating response {idx + 1} of {len(df)}..."
                        st.session_state.generation_progress_bar.progress(
                            (idx + 1) / len(df), text=progress_text
                        )
                except Exception as e:
                    logger.exception(
                        "Error generating response for row index %s (data: %s): %s",
                        idx,
                        current_user_input_item,
                        e,
                    )
                    st.warning(
                        f"Skipped generating response for one item (row index {idx}) due to error: {e}"
                    )
                    if "generation_progress_bar" in st.session_state:
                        progress_text = f"Generating response {idx + 1} of {len(df)}... (Error, skipped)"
                        st.session_state.generation_progress_bar.progress(
                            (idx + 1) / len(df), text=progress_text
                        )
                    continue
            if "generation_progress_bar" in st.session_state:
                st.session_state.generation_progress_bar.empty()
                del st.session_state.generation_progress_bar

            if len(user_input_list) < len(df):
                st.info(
                    "Successfully generated responses for %s out of %s requested samples due to errors during generation.",
                    len(user_input_list),
                    len(df),
                )
        else:
            logger.info(
                "Proceeding with loading existing assistant responses from file."
            )
            parsed_user_inputs_temp = []
            for item_str in df["user_input"].astype(str).tolist():
                try:
                    parsed_user_inputs_temp.append(json.loads(item_str))
                except json.JSONDecodeError:
                    logger.debug(
                        "User input item is not valid JSON, using as raw string: %s",
                        item_str[:100],
                    )
                    parsed_user_inputs_temp.append(item_str)
            user_input_list = parsed_user_inputs_temp
            expected_result_list = df[
                st.session_state.ground_truth_column_name
            ].tolist()
            assistant_response_list = df.assistant_response.tolist()
            baseline_model_response_list = []
            if "baseline_model_response" in df.columns:
                baseline_model_response_list = df.baseline_model_response.tolist()

        st.session_state.human_rated_dict = {
            "user_input": user_input_list,
            "ground_truth": expected_result_list,
            "assistant_response": assistant_response_list,
        }
        if baseline_model_response_list:
            st.session_state.human_rated_dict["baseline_model_response"] = (
                baseline_model_response_list
            )
        num_processed_items = len(user_input_list)

        if num_processed_items > 0:
            st.session_state.include_in_evaluations = [True] * num_processed_items
            st.session_state.current_index = 0
            st.success(f"Successfully processed {num_processed_items} samples.")
        else:
            st.warning(
                "No data items were processed successfully. Check logs for errors or review file structure."
            )
            st.session_state.human_rated_dict = {}
            st.session_state.include_in_evaluations = []
            st.session_state.current_index = 0

    st.divider()

    if st.session_state.human_rated_dict:
        st.title("Review Responses")

        col1, col2, col3 = st.columns(3)

        with col1:
            st.subheader("User Input")
            st.text_area(
                label="User's original query/text",
                value=st.session_state.human_rated_dict["user_input"][
                    st.session_state.current_index
                ],
                height=200,
                key="user_input_text",
                disabled=True,
            )

        with col2:
            st.subheader("Ground Truth")
            st.text_area(
                label="The ideal/target response",
                value=st.session_state.human_rated_dict["ground_truth"][
                    st.session_state.current_index
                ],
                height=200,
                key="ground_truth_text",
                disabled=True,
            )

        with col3:
            st.subheader("Assistant Response")
            st.text_area(
                label="The assistant's generated response",
                value=st.session_state.human_rated_dict["assistant_response"][
                    st.session_state.current_index
                ],
                height=200,
                key="assistant_response_text",
                disabled=True,
            )

        eval_include = st.checkbox(
            "Include in Evaluation",
            value=st.session_state.include_in_evaluations[
                st.session_state.current_index
            ],
            key="evaluation_checkbox",
        )

        if (
            st.session_state.include_in_evaluations
            and eval_include
            != st.session_state.include_in_evaluations[st.session_state.current_index]
        ):
            st.session_state.include_in_evaluations[st.session_state.current_index] = (
                eval_include
            )

        st.markdown("---")
        col_prev, col_spacer, col_next = st.columns([1, 3, 1])

        with col_prev:
            if st.button("Previous", disabled=(st.session_state.current_index == 0)):
                st.session_state.current_index -= 1
                st.rerun()

        with col_next:
            if st.button(
                "Next",
                disabled=(
                    st.session_state.current_index
                    == len(st.session_state.human_rated_dict["user_input"]) - 1
                ),
            ):
                st.session_state.current_index += 1
                st.rerun()

        st.markdown(
            f"<p style='text-align: center; font-size: 1.2em;'>Case {st.session_state.current_index + 1} of {len(st.session_state.human_rated_dict['user_input'])}</p>",
            unsafe_allow_html=True,
        )

        st.markdown("---")
        st.subheader("Launch Eval")

        st.subheader("Metrics Selection")

        col1, col2 = st.columns(2)

        with col1:
            st.write("**Model-Based**")
            metric_names = MetricPromptTemplateExamples.list_example_metric_names()
            selected_model_based_metrics = st.multiselect(
                "Select from model-based metrics",
                metric_names,
                key="selected_model_based_metrics",
                label_visibility="collapsed",
            )
            if selected_model_based_metrics:
                num_metrics = len(selected_model_based_metrics)
                if st.session_state.metric_preview_index >= num_metrics:
                    st.session_state.metric_preview_index = 0

                current_metric_name = selected_model_based_metrics[
                    st.session_state.metric_preview_index
                ]

                st.markdown(
                    f"**Previewing Template: {current_metric_name} ({st.session_state.metric_preview_index + 1}/{num_metrics})**"
                )

                try:
                    metric_object = get_metric_object_by_name(current_metric_name)
                    if isinstance(
                        metric_object,
                        PointwiseMetricPromptTemplate | PairwiseMetricPromptTemplate,
                    ):
                        st.text_area(
                            "Template Preview",
                            metric_object.metric_prompt_template,
                            height=200,
                        )
                except Exception as e:
                    st.error(
                        f"Could not retrieve template for {current_metric_name}: {e}"
                    )

                if num_metrics > 1:
                    prev_col, next_col = st.columns(2)
                    with prev_col:
                        if st.button(
                            "Previous Template",
                            disabled=st.session_state.metric_preview_index <= 0,
                        ):
                            st.session_state.metric_preview_index -= 1
                            st.rerun()
                    with next_col:
                        if st.button(
                            "Next Template",
                            disabled=st.session_state.metric_preview_index
                            >= num_metrics - 1,
                        ):
                            st.session_state.metric_preview_index += 1
                            st.rerun()

        with col2:
            st.write("**Computation-Based Pointwise**")
            computation_based_pointwise = [
                "bleu",
                "rouge_1",
                "rouge_2",
                "rouge_l",
                "rouge_l_sum",
                "exact_match",
            ]
            st.multiselect(
                "Select from computation-based pointwise metrics",
                computation_based_pointwise,
                key="selected_cbp",
                label_visibility="collapsed",
            )

        st.selectbox(
            "Select Evaluation Model",
            options=[
                "gemini-2.0-flash-lite",
                "gemini-2.5-flash",
                "gemini-2.5-pro",
            ],
            key="selected_evaluation_model",
        )

        st.button("Launch Eval", key="launch_eval_button")

        if st.session_state.launch_eval_button:
            selected_mbp_names = st.session_state.get(
                "selected_model_based_metrics", []
            )
            selected_cbp_metrics = st.session_state.get("selected_cbp", [])

            all_metrics = selected_mbp_names + selected_cbp_metrics

            if not all_metrics:
                st.warning("Please select at least one evaluation metric.")
                return

            evaluation_data_list = []
            for idx, include_item in enumerate(st.session_state.include_in_evaluations):
                if include_item:
                    user_input_values = st.session_state.human_rated_dict["user_input"][
                        idx
                    ]
                    prompt_template = (
                        st.session_state.local_prompt.prompt_to_run.prompt_data
                    )
                    logger.info(f"Prompt template: {prompt_template}")
                    system_instruction = (
                        st.session_state.local_prompt.prompt_to_run.system_instruction
                    )
                    prediction = str(
                        st.session_state.human_rated_dict["assistant_response"][idx]
                    )

                    # Process reference value like in the old code
                    reference_val = st.session_state.human_rated_dict["ground_truth"][
                        idx
                    ]
                    final_reference_str = ""
                    if isinstance(reference_val, int | float | bool):
                        final_reference_str = json.dumps({"value": reference_val})
                    elif isinstance(reference_val, str):
                        try:
                            parsed_json = json.loads(reference_val)
                            if isinstance(parsed_json, int | float | bool):
                                final_reference_str = json.dumps({"value": parsed_json})
                            else:
                                final_reference_str = reference_val
                        except json.JSONDecodeError:
                            final_reference_str = reference_val
                    elif isinstance(reference_val, dict | list):
                        final_reference_str = json.dumps(reference_val)
                    else:
                        final_reference_str = str(reference_val)

                    instruction = (
                        prompt_template.format(**user_input_values)
                        if isinstance(user_input_values, dict)
                        else prompt_template
                    )
                    context = system_instruction if system_instruction else ""
                    prompt_str = (
                        json.dumps(user_input_values)
                        if isinstance(user_input_values, dict)
                        else str(user_input_values)
                    )

                    eval_item = {
                        "context": context,
                        "instruction": instruction,
                        "prompt": prompt_str,
                        "prediction": prediction,
                        "reference": final_reference_str,
                    }
                    evaluation_data_list.append(eval_item)

            if not evaluation_data_list:
                st.warning(
                    "No items were selected for evaluation. Please check the 'Include in Evaluation' checkboxes."
                )
                return

            df_dataset = pd.DataFrame(evaluation_data_list)
            st.session_state.df_dataset_eval = df_dataset
            st.session_state.all_metrics_eval = all_metrics
            logger.info(f"Evaluation DataFrame columns: {df_dataset.columns.tolist()}")
            logger.info(f"Evaluation DataFrame head:\n{df_dataset.head()}")

            task = EvalTask(
                dataset=df_dataset,
                metrics=all_metrics,
                experiment=os.getenv("EXPERIMENT_NAME"),
            )
            st.session_state.eval_result = task.evaluate(
                response_column_name="prediction",
                baseline_model_response_column_name="reference",
            )

        st.markdown("---")
        st.subheader("View Eval")

        st.button("View Evaluation Results", key="eval_results_button")

        if st.session_state.eval_result and st.session_state.eval_results_button:
            print(st.session_state.eval_result.metrics_table)
            st.dataframe(st.session_state.eval_result.metrics_table)
        if st.session_state.eval_result:
            st.markdown("---")
            st.subheader("Summary Scores")

            mean_scores = {}
            if (
                st.session_state.eval_result
                and hasattr(st.session_state.eval_result, "metrics_table")
                and not st.session_state.eval_result.metrics_table.empty
            ):
                for col in st.session_state.eval_result.metrics_table.columns:
                    if col.endswith("/score"):
                        scores = pd.to_numeric(
                            st.session_state.eval_result.metrics_table[col],
                            errors="coerce",
                        )
                        if not scores.dropna().empty:
                            mean_scores[col] = scores.dropna().mean()
            if mean_scores:
                for metric, score in mean_scores.items():
                    st.metric(label=f"Mean {metric}", value=f"{score:.2f}")
            else:
                st.metric(
                    label="Mean Automated Score",
                    value="N/A",
                )

            st.markdown("---")
            st.subheader("Save to Prompt Records")
            save_to_records = st.checkbox(
                "I want to save the results of this evaluation to the prompt records.",
                key="save_to_records_checkbox",
            )
            if st.button("Save to Prompt Records", key="save_to_records_button"):
                if save_to_records:
                    prompt_name = st.session_state.selected_prompt
                    prompt_version = st.session_state.selected_version
                    data_file = st.session_state.input_data_uri

                    if "df_dataset_eval" in st.session_state:
                        data = st.session_state.df_dataset_eval.to_dict(
                            orient="records"
                        )
                    else:
                        st.error(
                            "Evaluation data not found in session state. Please re-run evaluation."
                        )
                        return

                    if "all_metrics_eval" in st.session_state:
                        metrics = st.session_state.all_metrics_eval
                    else:
                        st.error(
                            "Metrics not found in session state. Please re-run evaluation."
                        )
                        return

                    scores_df = st.session_state.eval_result.metrics_table
                    scores = scores_df.to_dict(orient="records")

                    mean_scores_to_save = {}
                    for col in scores_df.columns:
                        if col.endswith("/score"):
                            s = pd.to_numeric(scores_df[col], errors="coerce")
                            if not s.dropna().empty:
                                mean_scores_to_save[col] = s.dropna().mean()

                    record_data = {
                        "prompt_name": prompt_name,
                        "prompt_version": prompt_version,
                        "data_file": data_file,
                        "metrics": metrics,
                        "mean_scores": mean_scores_to_save,
                        "scores": scores,
                        "evaluation_data": data,
                        "timestamp": datetime.datetime.now().isoformat(),
                    }

                    try:
                        filename = f"record_{prompt_name}_v{prompt_version}_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.json"
                        bucket = st.session_state.storage_client.bucket(
                            os.getenv("BUCKET")
                        )
                        blob = bucket.blob(f"records/{filename}")

                        json_data = json.dumps(record_data, indent=4)
                        blob.upload_from_string(
                            json_data, content_type="application/json"
                        )

                        gcs_path = f"gs://{os.getenv('BUCKET')}/records/{filename}"

                        st.success(
                            f"Successfully saved to prompt records at: {gcs_path}"
                        )
                        st.json(json_data)
                    except Exception as e:
                        st.error(f"Failed to save to GCS: {e}")
                else:
                    st.warning(
                        "Please check the box to confirm you want to save to prompt records."
                    )


if __name__ == "__main__":
    main()
