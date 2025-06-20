# pylint: disable=broad-exception-caught,broad-exception-raised,invalid-name
"""
This module demonstrates the usage of the Gemini API in Vertex AI within a Streamlit application.
"""

import os

import streamlit as st
from gitingest import ingest
from google import genai
from google.genai.types import GenerateContentConfig, ThinkingConfig

MODELS = {
    "gemini-2.5-flash": "Gemini 2.5 Flash",
    "gemini-2.5-pro": "Gemini 2.5 Pro",
    "gemini-2.5-flash-lite-preview-06-17": "Gemini 2.5 Flash-Lite",
}

THINKING_BUDGET_MODELS = {
    "gemini-2.5-pro",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite-preview-06-17",
}

GENAI_REPOS = {
    "Python": "https://github.com/googleapis/python-genai",
    "Java": "https://github.com/googleapis/java-genai",
    "Go": "https://github.com/googleapis/go-genai",
    "JavaScript": "https://github.com/googleapis/js-genai",
}


def get_model_name(name: str | None) -> str:
    """Get the formatted model name."""
    if not name:
        return "Gemini"
    return MODELS.get(name, "Gemini")


st.link_button(
    "View on GitHub",
    "https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/sample-apps/gemini-streamlit-cloudrun",
)

cloud_run_service = os.environ.get("K_SERVICE")
if cloud_run_service:
    st.link_button(
        "Open in Cloud Run",
        f"https://console.cloud.google.com/run/detail/us-central1/{cloud_run_service}/source",
    )


st.text("Provide an API Key or a Google Cloud Project ID")

api_key = st.text_input(
    "Gemini API Key",
    type="password",
    key="gemini_api_key",
)
project_id = st.text_input(
    "Google Cloud Project ID",
    key="project_id",
)

st.header(":sparkles: Write Code for the Google Gen AI SDK", divider="rainbow")

selected_model = st.selectbox(
    "Select Model:",
    MODELS.keys(),
    format_func=get_model_name,
    key="selected_model",
)

selected_language = st.selectbox(
    "Select Language:",
    GENAI_REPOS.keys(),
    key="selected_language",
)

thinking_budget = None
if selected_model in THINKING_BUDGET_MODELS:
    thinking_budget_mode = st.selectbox(
        "Thinking budget",
        ("Auto", "Manual", "Off"),
        key="thinking_budget_mode_selectbox",
    )

    if thinking_budget_mode == "Manual":
        thinking_budget = st.slider(
            "Thinking budget token limit",
            min_value=0,
            max_value=24576,
            step=1,
            key="thinking_budget_manual_slider",
        )
    elif thinking_budget_mode == "Off":
        thinking_budget = 0

thinking_config = (
    ThinkingConfig(thinking_budget=thinking_budget)
    if thinking_budget is not None
    else None
)

temperature = st.slider(
    "Select the temperature (Model Randomness):",
    min_value=0.0,
    max_value=2.0,
    value=1.0,
    step=0.05,
    key="temperature",
)

max_output_tokens = st.slider(
    "Maximum Number of Tokens to Generate:",
    min_value=1,
    max_value=65535,
    value=8192,
    step=1,
    key="max_output_tokens",
)

top_p = st.slider(
    "Select the Top P",
    min_value=0.0,
    max_value=1.0,
    value=0.95,
    step=0.05,
    key="top_p",
)

prompt = st.text_area(
    "Enter your prompt here...",
    key="prompt",
    height=200,
)

config = GenerateContentConfig(
    temperature=temperature,
    max_output_tokens=max_output_tokens,
    top_p=top_p,
    thinking_config=thinking_config,
)

generate_freeform = st.button("Generate", key="generate_freeform")


if generate_freeform and prompt:
    if not api_key and not project_id:
        st.error(
            "🚨 Configuration Error: Please set either `GOOGLE_API_KEY` or `PROJECT_ID`."
        )

    location = "global" if project_id else None
    client = genai.Client(
        vertexai=bool(project_id),
        project=project_id,
        location=location,
        api_key=api_key,
    )

    with st.spinner(f"Generating response using {get_model_name(selected_model)} ..."):
        repo_url = GENAI_REPOS.get(selected_language)
        _, tree, content = ingest(
            source=repo_url,
            exclude_patterns={
                "google/genai/tests/",
                "docs/",
                ".github/",
                "test/",
                "web/",
                "api-report/",
                "node/",
                "scripts/",
                "src/test/",
                "internal/changefinder/",
                "*_test.*",
                "testdata/",
            },
        )
        config.system_instruction = f"""You are an expert software engineer, proficient in {selected_language}. Your task is to write code using the Google Gen AI SDK based on the user's request. Don't suggest using Gemini 1.0 or 1.5. Do not suggest using the library google.generativeai"""
        contents = [
            "The Google Gen AI SDK repository is provided here",
            tree,
            content,
            "This is the user's request:",
            prompt,
        ]
        response = client.models.generate_content(
            model=selected_model,
            contents=contents,
            config=config,
        )
        if response:
            st.markdown(response.text)
            if (
                response.usage_metadata
                and response.usage_metadata.total_token_count is not None
            ):
                st.text(f"Total tokens: {response.usage_metadata.total_token_count}")
