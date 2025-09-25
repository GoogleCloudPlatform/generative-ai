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

import json
import logging
import os

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from google.cloud import storage

load_dotenv("src/.env")

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def load_records_from_gcs(bucket_name: str, prefix: str) -> pd.DataFrame:
    """Loads all JSON record files from a GCS prefix and returns a DataFrame."""
    try:
        storage_client = storage.Client()
        bucket = storage_client.bucket(bucket_name)
        blobs = bucket.list_blobs(prefix=prefix)

        all_records = []
        for blob in blobs:
            if blob.name.endswith(".json"):
                logger.info(f"Loading record from {blob.name}")
                try:
                    record_data = json.loads(blob.download_as_string())
                    if isinstance(record_data, list):
                        all_records.extend(record_data)
                    else:
                        all_records.append(record_data)
                except json.JSONDecodeError:
                    logger.warning(f"Could not decode JSON from {blob.name}")
                except Exception as e:
                    logger.exception(f"Failed to process blob {blob.name}: {e}")

        if not all_records:
            st.warning(f"No JSON records found at gs://{bucket_name}/{prefix}")
            return pd.DataFrame()

        return pd.json_normalize(all_records)

    except Exception as e:
        st.error(f"Failed to load or parse records from GCS: {e}")
        logger.error("Error loading records: %s", e, exc_info=True)
        return pd.DataFrame()


def main() -> None:
    """Renders the Prompt Records Leaderboard page."""
    st.set_page_config(
        layout="wide",
        page_title="Prompt Records Leaderboard",
        page_icon="assets/favicon.ico",
    )
    st.header("Prompt Records Leaderboard")
    st.markdown(
        "This page allows you to view and compare the evaluation results of different prompt versions."
    )

    records_prefix = "records/"

    if "leaderboard_df" not in st.session_state:
        st.session_state.leaderboard_df = pd.DataFrame()

    if st.button("Load/Refresh Leaderboard"):
        with st.spinner("Loading records from GCS..."):
            st.session_state.leaderboard_df = load_records_from_gcs(
                os.getenv("BUCKET"), records_prefix
            )
        if not st.session_state.leaderboard_df.empty:
            st.success("Leaderboard loaded successfully.")
        else:
            st.info("Leaderboard is empty or could not be loaded.")

    if st.session_state.leaderboard_df.empty:
        st.info("Click the button above to load the leaderboard data.")
        return

    st.divider()

    prompt_names = st.session_state.leaderboard_df["prompt_name"].unique().tolist()
    selected_prompt = st.selectbox(
        "Select a Prompt to Compare Versions", options=[None, *prompt_names]
    )

    if selected_prompt:
        st.subheader(f"Comparison for: {selected_prompt}")

        prompt_df = st.session_state.leaderboard_df[
            st.session_state.leaderboard_df["prompt_name"] == selected_prompt
        ].copy()

        if prompt_df.empty:
            st.info("No records found for the selected prompt.")
            return

        # Extract scores into separate columns for easier analysis
        scores_df = pd.json_normalize(prompt_df["scores"])
        scores_df.columns = [f"score.{col}" for col in scores_df.columns]

        comparison_df = pd.concat([prompt_df.reset_index(drop=True), scores_df], axis=1)

        # Clean up the view
        display_columns = [
            col
            for col in comparison_df.columns
            if col not in ["scores", "evaluation_data"]
            and not (col.startswith("score.") and col[6:].isdigit())
        ]
        st.dataframe(comparison_df[display_columns])


if __name__ == "__main__":
    main()
