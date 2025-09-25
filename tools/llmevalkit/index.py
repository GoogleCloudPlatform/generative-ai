## Copyright 2025 Google LLC
##  Licensed under the Apache License, Version 2.0 (the "License");
##  you may not use this file except in compliance with the License.
##  You may obtain a copy of the License at
##     https://www.apache.org/licenses/LICENSE-2.0
##  Unless required by applicable law or agreed to in writing, software
##  distributed under the License is distributed on an "AS IS" BASIS,
##  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
##  See the License for the specific language


"""The main landing page for the LLM EvalKit Streamlit application."""

import streamlit as st
from dotenv import load_dotenv

load_dotenv("src/.env")


def main() -> None:
    """Renders the main landing page of the application."""
    st.set_page_config(
        page_title="LLM EvalKit",
        layout="wide",
        initial_sidebar_state="expanded",
        page_icon="assets/favicon.ico",
    )

    st.title("Welcome to the LLM EvalKit")
    st.markdown(
        "A suite of tools for managing, evaluating, and optimizing LLM prompts and datasets."
    )

    st.subheader("Getting Started")
    st.markdown(
        """
        This application helps you streamline your prompt engineering workflow.
        Select a tool from the sidebar on the left to begin.

        **Available Tools:**
        *   **Prompt Management:** Create, test, and manage your prompts.
        *   **Dataset Creation:** Create evaluation datasets from CSV files.
        *   **Simple Evaluation:** Run simple evaluations on your prompts.
        *   **Evaluation Human Judge:** Manually rate model responses for evaluation.
        *   **Prompt Optimization:** Optimize your prompts for better performance.
        *   **Prompt Optimization Results:** View the results of prompt optimization runs.
        *   **Prompt Records:** View and manage your prompt records.
        """
    )
    st.caption("LLM EvalKit | Home")


if __name__ == "__main__":
    main()
