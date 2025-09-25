## Copyright 2025 Google LLC
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##     https://www.apache.org/licenses/LICENSE-2.0
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language

import json
import logging
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.cloud import storage
from src import vapo_lib

# Load environment variables
load_dotenv("src/.env")

# Configure logging to the console
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Constants ---
BASE_OPTIMIZATION_PREFIX = "optimization/"
OPTIMIZATION_JOBS_SUBDIR = "optimization_jobs/"

from google.cloud import aiplatform


def list_custom_training_jobs(project_id: str, location: str):
    """Lists all custom training jobs and their statuses in a given project and location.

    Args:
        project_id: The Google Cloud project ID.
        location: The region for the Vertex AI jobs, e.g., "us-central1".

    Returns:
        A list of dictionaries, where each dictionary contains details of a custom job.
    """
    # Initialize the Vertex AI client
    # The API endpoint is determined by the location
    client_options = {"api_endpoint": f"{location}-aiplatform.googleapis.com"}
    client = aiplatform.gapic.JobServiceClient(client_options=client_options)

    # The parent resource path format
    parent = f"projects/{project_id}/locations/{location}"

    # Make the API request to list custom jobs
    response = client.list_custom_jobs(parent=parent)

    # Process the response and format the output
    jobs_list = []
    print(f"Fetching jobs from project '{project_id}' in '{location}'...")
    for job in response:
        job_info = {
            "display_name": job.display_name,
            "name": job.name,
            "status": job.state.name,  # .name gets the string representation of the enum
        }
        jobs_list.append(job_info)

    print(f"Found {len(jobs_list)} jobs.")
    return jobs_list


# --- Example Usage ---
if __name__ == "__main__":
    # Replace with your project ID and desired location
    PROJECT_ID = os.getenv("PROJECT_ID")
    LOCATION = os.getenv("LOCATION")

    # Ensure you have authenticated with Google Cloud CLI:
    # gcloud auth application-default login

    # And have the necessary permissions (e.g., "Vertex AI User" role)

    try:
        all_jobs = list_custom_training_jobs(project_id=PROJECT_ID, location=LOCATION)

        # Print the results
        if all_jobs:
            print("\n--- Job Statuses ---")
            for job in all_jobs:
                print(f"  - Name: {job['display_name']:<40} Status: {job['status']}")
            print("--------------------\n")
        else:
            print("No custom jobs found.")

    except Exception as e:
        print(
            "\nAn error occurred. Please ensure your project ID and location are correct,"
        )
        print(f"and that you have authenticated correctly. Error: {e}")


def safe_json_loads(s):
    """Safely loads a JSON string, returning the original value on failure."""
    if not isinstance(s, str):
        return s
    try:
        return json.loads(s)
    except (json.JSONDecodeError, TypeError):
        return s


@st.cache_data(ttl=300)
def list_gcs_directories(
    bucket_name: str, prefix: str, _storage_client: storage.Client
) -> list[str]:
    """Lists 'directories' in GCS under a given prefix.
    A 'directory' is inferred from the common prefixes of objects.
    Caches the result for 5 minutes to improve performance.
    """
    if not bucket_name:
        st.warning("BUCKET environment variable is not set.")
        return []
    if not _storage_client:
        st.warning("Storage client is not initialized.")
        return []

    bucket = _storage_client.bucket(bucket_name)
    retrieved_prefixes = set()
    try:
        for page in bucket.list_blobs(prefix=prefix, delimiter="/").pages:
            retrieved_prefixes.update(page.prefixes)

        # The retrieved prefixes are the "subdirectories".
        # e.g., for prefix 'optimization/', a retrieved prefix might be 'optimization/op_id/'.
        # We want to extract just 'op_id'.
        dir_names = []
        for p in retrieved_prefixes:
            name = p.replace(prefix, "").strip("/")
            if name:
                dir_names.append(name)
        return sorted(set(dir_names))
    except Exception as e:
        st.error(
            f"Error listing GCS directories under gs://{bucket_name}/{prefix}: {e}"
        )
        logger.error(
            f"Error listing GCS directories under gs://{bucket_name}/{prefix}: {e}",
            exc_info=True,
        )
        return []


def _display_interactive_results(results_ui: vapo_lib.ResultsUI) -> None:
    """Processes results from a VAPO run and displays them in an interactive
    Streamlit UI with tabs for each prompt version.
    """
    try:
        if (
            not hasattr(results_ui, "templates")
            or not results_ui.templates
            or not hasattr(results_ui, "eval_results")
        ):
            logger.info(
                "ResultsUI object does not have 'templates' or 'eval_results', or templates list is empty. Falling back."
            )
        else:
            processed_results_for_tabs = []
            for i, template_summary_df in enumerate(results_ui.templates):
                if (
                    not isinstance(template_summary_df, pd.DataFrame)
                    or template_summary_df.empty
                ):
                    logger.warning(
                        f"Template summary data at index {i} is not a non-empty DataFrame. Skipping."
                    )
                    continue

                # Get the detailed results to perform the custom calculation
                detailed_eval_df = pd.DataFrame()
                if i < len(results_ui.eval_results) and isinstance(
                    results_ui.eval_results[i], pd.DataFrame
                ):
                    detailed_eval_df = results_ui.eval_results[i]

                # Add a custom exact_match calculation. This is more robust than simple
                # string comparison as it handles differences in JSON key order and whitespace.
                if (
                    not detailed_eval_df.empty
                    and "ground_truth" in detailed_eval_df.columns
                    and "reference" in detailed_eval_df.columns
                ):
                    # Parse the JSON strings into Python objects before comparing.
                    parsed_ground_truths = detailed_eval_df["ground_truth"].apply(
                        safe_json_loads
                    )
                    parsed_references = detailed_eval_df["reference"].apply(
                        safe_json_loads
                    )

                    # Create a boolean series for the comparison
                    is_match = parsed_ground_truths.eq(parsed_references)

                    # Map boolean to 'yes'/'no' for display in the detailed table
                    detailed_eval_df["calculated_exact_match"] = is_match.map(
                        {True: "yes", False: "no"}
                    )

                    # Calculate the mean from the boolean series for the summary metric
                    new_exact_match_mean = is_match.mean()
                    template_summary_df["metrics.calculated_exact_match/mean"] = (
                        new_exact_match_mean
                    )

                prompt_text = "Prompt text not found in template data."
                if "prompt" in template_summary_df.columns:
                    prompt_text = template_summary_df["prompt"].iloc[0]
                else:
                    logger.warning(
                        f"Column 'prompt' not found in template_summary_df at index {i}."
                    )

                # Determine the primary score and build the tab name.
                primary_score_label = "Score"
                primary_score_value = "N/A"
                if "metrics.calculated_exact_match/mean" in template_summary_df.columns:
                    primary_score_label = "Calculated Exact Match"
                    primary_score_value = template_summary_df[
                        "metrics.calculated_exact_match/mean"
                    ].iloc[0]
                else:
                    # Fallback to the first available metric
                    mean_metric_columns = [
                        col
                        for col in template_summary_df.columns
                        if col.startswith("metrics.") and "/mean" in col
                    ]
                    if mean_metric_columns:
                        first_metric_col = mean_metric_columns[0]
                        primary_score_label = (
                            first_metric_col.replace("metrics.", "")
                            .replace("/mean", "")
                            .replace("_", " ")
                            .title()
                        )
                        primary_score_value = template_summary_df[
                            first_metric_col
                        ].iloc[0]

                # Build the tab name with all available metrics for a quick overview.
                tab_name_metrics_parts = []
                mean_metric_columns = [
                    col
                    for col in template_summary_df.columns
                    if col.startswith("metrics.") and "/mean" in col
                ]
                for metric_col in mean_metric_columns:
                    metric_name_short = metric_col.replace("metrics.", "").replace(
                        "/mean", ""
                    )
                    metric_val = template_summary_df[metric_col].iloc[0]
                    if metric_name_short == "calculated_exact_match" and isinstance(
                        metric_val, float
                    ):
                        tab_name_metrics_parts.append(
                            f"{metric_name_short}: {metric_val:.1%}"
                        )
                    else:
                        tab_name_metrics_parts.append(
                            f"{metric_name_short}: {metric_val:.3f}"
                            if isinstance(metric_val, float)
                            else f"{metric_name_short}: {metric_val}"
                        )

                tab_name = f"Template {i}"
                if tab_name_metrics_parts:
                    tab_name += f" ({', '.join(tab_name_metrics_parts)})"

                current_summary_df_display = template_summary_df.copy()
                if "prompt" in current_summary_df_display.columns:
                    current_summary_df_display = current_summary_df_display.drop(
                        columns=["prompt"]
                    )

                processed_results_for_tabs.append(
                    {
                        "name": tab_name,
                        "template_text": prompt_text,
                        "primary_score_label": primary_score_label,
                        "primary_score_value": primary_score_value,
                        "summary_metrics_df": current_summary_df_display,
                        "detailed_eval_df": detailed_eval_df,
                    }
                )

            if (
                processed_results_for_tabs
            ):  # If we successfully processed data, show the new UI
                st.write("### Interactive Prompt Versions")
                tab_titles = [res["name"] for res in processed_results_for_tabs]
                tabs = st.tabs(tab_titles)

                for i, tab_content in enumerate(tabs):
                    with tab_content:
                        result_data = processed_results_for_tabs[i]

                        st.subheader("Prompt Template")
                        # Sanitize tab name for key
                        clean_key_name = "".join(
                            filter(str.isalnum, result_data["name"])
                        )
                        st.text_area(
                            "Template",
                            value=result_data["template_text"],
                            height=200,
                            disabled=True,
                            key=f"template_view_{clean_key_name}_{i}",
                        )

                        st.subheader("Primary Score")
                        score_val = result_data["primary_score_value"]
                        score_label = result_data["primary_score_label"]
                        if score_label == "Calculated Exact Match" and isinstance(
                            score_val, float
                        ):
                            st.metric(label=score_label, value=f"{score_val:.2%}")
                        else:
                            st.metric(
                                label=score_label,
                                value=f"{score_val:.4f}"
                                if isinstance(score_val, float)
                                else str(score_val),
                            )

                        if not result_data["summary_metrics_df"].empty:
                            st.subheader("Summary Metrics (from templates.json)")
                            st.dataframe(result_data["summary_metrics_df"])

                        if not result_data["detailed_eval_df"].empty:
                            st.subheader(
                                "Detailed Evaluation Results (from eval_results.json)"
                            )
                            st.dataframe(result_data["detailed_eval_df"])
                        else:
                            st.caption(
                                "No detailed evaluation results available for this template."
                            )
            else:
                st.warning("No valid results could be processed for display.")

    except Exception as e:
        st.error(f"An error occurred while trying to display results: {e}")
        logger.error(f"Error in results display section: {e}", exc_info=True)
        st.markdown(
            "For now, you can access the results directly at the GCS path shown above."
        )


def main() -> None:
    """Renders the Streamlit page for viewing Prompt Optimization Results."""
    st.set_page_config(
        layout="wide",
        page_title="Prompt Optimization Results",
        page_icon="assets/favicon.ico",
    )
    st.header("Prompt Optimization Results Browser")

    if "storage_client" not in st.session_state:
        try:
            st.session_state["storage_client"] = storage.Client()
            logger.info("Storage client initialized.")
        except Exception as e:
            st.error(f"Failed to initialize Google Cloud Storage client: {e}")
            logger.error(
                f"Failed to initialize Google Cloud Storage client: {e}", exc_info=True
            )
            st.session_state["storage_client"] = None
            return

    bucket_name = os.getenv("BUCKET")
    if not bucket_name:
        st.error("BUCKET environment variable is not set. Please configure it in .env.")
        return

    # --- Step 1: Select Operation ID ---
    op_ids = list_gcs_directories(
        bucket_name, BASE_OPTIMIZATION_PREFIX, st.session_state.storage_client
    )
    if not op_ids:
        st.info(
            f"No optimization operation IDs found under gs://{bucket_name}/{BASE_OPTIMIZATION_PREFIX}"
        )
        return

    if "op_id" in st.session_state and st.session_state.op_id:
        st.caption(
            f"Hint: The last optimization run you initiated had the ID: `{st.session_state.op_id}`."
        )

    selected_op_id = st.selectbox(
        "Select an Operation ID:", options=[None, *op_ids], key="selected_op_id_results"
    )
    if not selected_op_id:
        st.write("Please select an Operation ID to see its optimization job runs.")
        return

    st.divider()

    # --- Step 2: Select Experiment Run ---
    st.subheader(f"Optimization Job Runs for Operation ID: {selected_op_id}")
    optimization_jobs_prefix = (
        f"{BASE_OPTIMIZATION_PREFIX}{selected_op_id}/{OPTIMIZATION_JOBS_SUBDIR}"
    )
    experiment_runs = list_gcs_directories(
        bucket_name, optimization_jobs_prefix, st.session_state.storage_client
    )

    if not experiment_runs:
        st.info(
            f"No completed optimization job runs found under gs://{bucket_name}/{optimization_jobs_prefix}"
        )
        return

    selected_run = st.selectbox(
        "Select an Optimization Job Run:",
        options=[None, *experiment_runs],
        key="selected_experiment_run",
    )
    if not selected_run:
        st.write("Please select an optimization job run to view its results.")
        return

    st.divider()

    # --- Step 3: Check Job Status and Display Results ---
    st.subheader(f"Results for: {selected_run}")

    project_id = os.getenv("PROJECT_ID")
    location = os.getenv("LOCATION")

    if not project_id or not location:
        st.error("PROJECT_ID or REGION environment variables are not set.")
        return

    try:
        jobs = list_custom_training_jobs(project_id=project_id, location=location)
        job_status = "Not Found"
        for job in jobs:
            if job["display_name"] == selected_run:
                job_status = job["status"]
                break

        st.info(f"Status for job '{selected_run}': **{job_status}**")

        if job_status == "JOB_STATE_FAILED":
            st.error(
                "This optimization job has failed. Please check the logs in the Vertex AI console for more details."
            )
            return
        if job_status not in ["JOB_STATE_SUCCEEDED", "JOB_STATE_CANCELLED"]:
            st.warning(
                f"Job is currently in status: {job_status}. Results may be incomplete."
            )

    except Exception as e:
        st.error(f"Could not retrieve job status. Error: {e}")
        logger.error(
            f"Failed to retrieve job status for {selected_run}: {e}", exc_info=True
        )

    run_uri = f"gs://{bucket_name}/{optimization_jobs_prefix}{selected_run}"
    st.info(f"Loading results from: {run_uri}")
    results_ui = vapo_lib.ResultsUI(run_uri)
    _display_interactive_results(results_ui)


if __name__ == "__main__":
    main()
