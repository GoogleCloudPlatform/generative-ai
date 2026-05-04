# Copyright 2025 Google LLC
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#     https://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language

"""Streamlit user interface for the One-Click Refiner.

This page provides an interface to instantly upgrade a draft prompt into a
structured, production-ready instruction without managing any datasets.
"""

import json
import logging

import streamlit as st
from dotenv import load_dotenv
from src.gcp_prompt import GcpPrompt as gcp_prompt
from vertexai.generative_models import GenerationConfig, GenerativeModel
from vertexai.preview import prompts

load_dotenv("src/.env")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Prompt Templates ---
META_PROMPT_TEMPLATE = """You are an expert prompt engineer. Your goal is to improve the user's draft prompt and system instructions into highly structured, production-ready iterations.

Ensure you include and follow these directives:
{custom_directives}

Ensure tone relates to the optional requested Tone: {tone}.

CRITICAL REQUIREMENTS:
- You MUST preserve all variable placeholders exactly as they appear (e.g., `{{{{query}}}}`, `{{{{target}}}}`). Note: the draft prompt might use curly brackets like `{{variable}}`. Do NOT strip them.
- You MUST preserve any multimodal tags exactly as they appear (e.g., `@@@image/jpeg`). Do not alter or remove image attachments.

Draft System Instructions:
{draft_system_instructions}

Draft Prompt:
{draft_prompt}

You must respond in pure JSON format with exactly three keys:
1. "optimized_system_instruction": A single string containing the rewritten system instructions.
2. "optimized_prompt": A single string containing the fully rewritten structured prompt template.
3. "insights": A list of strings explaining exactly what you changed and why.
"""

SUGGEST_DIRECTIVES_PROMPT = """Analyze the following draft prompt and system instructions. Suggest 3-5 specific prompt engineering best practices that would improve it. Focus on structure, constraints, format, clarity, and safety.
Return ONLY a markdown list of suggestions suitable to be used as instructions for another LLM prompt engineer. Do not include introductory text.

Draft System Instructions:
{draft_system_instructions}

Draft Prompt:
{draft_prompt}
"""


def initialize_session_state() -> None:
    """Initializes needed session state variables."""
    if "local_prompt" not in st.session_state:
        st.session_state.local_prompt = gcp_prompt()
    if "ocr_directives" not in st.session_state:
        st.session_state.ocr_directives = "1. Add a clear Role definition.\n2. Add specific Context to constrain the generator.\n3. Clarify output format expectations."
    if "opt_sys" not in st.session_state:
        st.session_state.opt_sys = ""
    if "opt_prompt" not in st.session_state:
        st.session_state.opt_prompt = ""
    if "ocr_insights" not in st.session_state:
        st.session_state.ocr_insights = None


def _handle_load_prompt():
    """Loads the selected prompt and version into the gcp_prompt object."""
    if not st.session_state.get("selected_prompt") or not st.session_state.get(
        "selected_version"
    ):
        st.warning("Please select both a prompt and a version to load.")
        return
    prompt_name = st.session_state.selected_prompt
    prompt_id = st.session_state.local_prompt.existing_prompts[prompt_name]
    version_id = st.session_state.selected_version
    try:
        with st.spinner(f"Loading version '{version_id}' of prompt '{prompt_name}'..."):
            st.session_state.local_prompt.load_prompt(
                prompt_id, prompt_name, version_id
            )
        st.success(f"Loaded prompt '{prompt_name}' (Version: {version_id}).")

        # Clear previous optimizations
        st.session_state.opt_sys = ""
        st.session_state.opt_prompt = ""
        st.session_state.ocr_insights = None
    except Exception as e:
        logger.error("Failed to load prompt: %s", e, exc_info=True)
        st.error(f"Failed to load prompt: {e}")


def _handle_auto_suggest():
    """Calls Agent Platform to automatically suggest prompt engineering directives."""
    sys_inst = st.session_state.local_prompt.prompt_to_run.system_instruction or "None"
    prompt_data = st.session_state.local_prompt.prompt_to_run.prompt_data or "None"

    model_name = st.session_state.get("ocr_target_model", "gemini-2.5-pro")
    if not model_name:
        model_name = "gemini-2.5-pro"

    try:
        model = GenerativeModel(model_name)
        prompt_text = SUGGEST_DIRECTIVES_PROMPT.format(
            draft_system_instructions=sys_inst, draft_prompt=prompt_data
        )
        with st.spinner("Analyzing prompt and generating suggestions..."):
            response = model.generate_content(prompt_text)
            st.session_state.ocr_directives = response.text
    except Exception as e:
        logger.error("Error auto-suggesting directives: %s", e, exc_info=True)
        st.error(f"Failed to generate suggestions: {e}")


def _handle_optimize():
    """Optimizes the loaded prompt using the meta-prompt and custom directives."""
    sys_inst = st.session_state.local_prompt.prompt_to_run.system_instruction or "None"
    prompt_data = st.session_state.local_prompt.prompt_to_run.prompt_data or "None"
    directives = st.session_state.get("ocr_directives", "")
    tone = st.session_state.get("ocr_tone", "Professional")

    model_name = st.session_state.get("ocr_target_model", "gemini-2.5-pro")
    if not model_name:
        model_name = "gemini-2.5-pro"

    try:
        model = GenerativeModel(model_name)
        prompt_text = META_PROMPT_TEMPLATE.format(
            custom_directives=directives,
            tone=tone,
            draft_system_instructions=sys_inst,
            draft_prompt=prompt_data,
        )
        with st.spinner("Optimizing..."):
            response = model.generate_content(
                prompt_text,
                generation_config=GenerationConfig(
                    temperature=0.4, response_mime_type="application/json"
                ),
            )
            # Parse response
            try:
                res_obj = json.loads(response.text)
                st.session_state.opt_sys = res_obj.get(
                    "optimized_system_instruction", ""
                )
                st.session_state.opt_prompt = res_obj.get("optimized_prompt", "")
                st.session_state.ocr_insights = res_obj.get("insights", [])
                st.success("Optimization Complete!")
            except json.JSONDecodeError as e:
                st.error(f"Failed to parse optimization output as JSON: {e}")
                logger.error("Raw response: %s", response.text)
    except Exception as e:
        logger.error("Error optimizing prompt: %s", e, exc_info=True)
        st.error(f"Failed to optimize prompt: {e}")


def _handle_save_new_version():
    """Saves the optimized prompt to the backend registry as a new version."""
    prompt_obj = st.session_state.local_prompt
    if not prompt_obj.prompt_to_run.prompt_name:
        st.warning("No prompt is currently loaded to save.")
        return

    prompt_obj.prompt_to_run.prompt_data = st.session_state.opt_prompt
    prompt_obj.prompt_to_run.system_instruction = st.session_state.opt_sys

    try:
        with st.spinner("Saving as new version..."):
            prompt_obj.save_prompt(check_existing=False)
        st.success("Successfully saved new optimized version to registry!")
        prompt_obj.refresh_prompt_cache()
    except Exception as e:
        logger.error("Failed to save new version: %s", e, exc_info=True)
        st.error(f"Failed to save prompt: {e}")


def main():
    """Renders the One-Click Refiner page layout."""
    st.set_page_config(
        layout="wide", page_title="One-Click Refiner", page_icon="assets/favicon.ico"
    )
    initialize_session_state()

    st.title("One-Click Refiner")
    st.markdown(
        "Instantly upgrade a draft prompt into a structured, production-ready instruction without managing any datasets."
    )
    st.divider()

    # SECTION 1: Load Existing Prompt
    st.subheader("1. Load Prompt")

    if st.button("Refresh List"):
        with st.spinner("Refreshing..."):
            st.session_state.local_prompt.refresh_prompt_cache()
        st.toast("Prompt list refreshed.")

    col1, col2 = st.columns(2)
    with col1:
        selected_prompt_name = st.selectbox(
            "Select Existing Prompt",
            options=st.session_state.local_prompt.existing_prompts.keys(),
            placeholder="Select Prompt...",
            key="selected_prompt",
        )
    with col2:
        versions = []
        if selected_prompt_name:
            try:
                prompt_id = st.session_state.local_prompt.existing_prompts[
                    selected_prompt_name
                ]
                versions = [v.version_id for v in prompts.list_versions(prompt_id)]
            except Exception as e:
                st.error(f"Could not fetch versions: {e}")
        st.selectbox(
            "Select Version",
            options=versions,
            placeholder="Select Version...",
            key="selected_version",
        )

    st.button("Load Prompt", on_click=_handle_load_prompt, type="primary")
    st.divider()

    p_data = st.session_state.local_prompt.prompt_to_run.prompt_data
    if p_data:
        # SECTION 2: Configuration
        st.subheader("2. Configuration")
        c1, c2 = st.columns(2)
        with c1:
            current_model = st.session_state.local_prompt.prompt_to_run.model_name
            if current_model and "/" in current_model:
                current_model = current_model.split("/")[-1]
            st.text_input(
                "Target Model",
                value=current_model if current_model else "gemini-2.0-flash-001",
                key="ocr_target_model",
            )
        with c2:
            st.selectbox(
                "Tone",
                options=[
                    "Professional",
                    "Creative",
                    "Concise",
                    "Assertive",
                    "Friendly",
                    "None",
                ],
                key="ocr_tone",
            )

        st.markdown("**Optimization Directives**")
        st.text_area(
            "Modify the guidelines the optimizer should follow:",
            key="ocr_directives",
            height=120,
        )
        st.button("✨ Auto-Suggest Directives", on_click=_handle_auto_suggest)

        st.button("🚀 Optimize Now", on_click=_handle_optimize, type="primary")

        st.divider()

        # SECTION 3: Review
        st.subheader("3. Review")

        rev_c1, rev_c2 = st.columns(2)
        with rev_c1:
            st.markdown("### Original Draft")
            st.text_area(
                "System Instructions",
                value=st.session_state.local_prompt.prompt_to_run.system_instruction
                or "",
                disabled=True,
                height=200,
                key="org_sys",
            )
            st.text_area(
                "Prompt Data",
                value=p_data or "",
                disabled=True,
                height=200,
                key="org_prompt",
            )

        with rev_c2:
            st.markdown("### Optimized Result")
            st.text_area("System Instructions", key="opt_sys", height=200)
            st.text_area("Prompt Data", key="opt_prompt", height=200)

        if st.session_state.ocr_insights:
            with st.expander("💡 Why this changed (Insights)", expanded=True):
                for insight in st.session_state.ocr_insights:
                    st.markdown(f"- {insight}")

        st.divider()
        st.subheader("4. Action")
        st.button(
            "Save as New Version", on_click=_handle_save_new_version, type="primary"
        )


if __name__ == "__main__":
    main()
