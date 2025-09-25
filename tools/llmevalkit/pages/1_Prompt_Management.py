# Copyright 2025 Google LLC
#  Licensed under the Apache License, Version 2.0 (the "License");
#  you may not use this file except in compliance with the License.
#  You may obtain a copy of the License at
#     https://www.apache.org/licenses/LICENSE-2.0
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language

"""Streamlit user interface for managing prompts in the LLM EvalKit.

This page provides a comprehensive interface for prompt engineering, allowing users
to create, load, edit, and test prompts that are stored and versioned in a
backend service (e.g., Google Cloud's Vertex AI Prompt Management).

The page is divided into two main sections:
1.  **Create New Prompt**: A form to define a new prompt from scratch, including
    its name, text, model, system instructions, and other metadata. Users can
    test the prompt with sample input before saving it.
2.  **Load & Edit Prompt**: A section to load existing prompts and their specific
    versions. Users can modify the loaded prompt's details and save the changes
    as a new version, facilitating iterative development and A/B testing.

Helper functions handle JSON parsing, data type conversions, and interactions
with the `gcp_prompt` object, which abstracts the backend communication.
"""

import json
import logging
from typing import Any

import streamlit as st
from dotenv import load_dotenv
from src.gcp_prompt import GcpPrompt as gcp_prompt
from vertexai.preview import prompts

# --- Initial Configuration ---
load_dotenv("src/.env")
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# --- Constants ---
AVAILABLE_PROMPT_TASKS = [
    "Classification",
    "Summarization",
    "Translation",
    "Creative Writing",
    "Q&A",
]


# --- Helper Functions ---
def _parse_json_input(json_string: str, field_name: str) -> dict[str, Any] | None:
    """Safely parses a JSON string from a text area.

    Cleans the input string to handle common copy-paste errors and displays
    an error in the Streamlit UI if parsing fails.

    Args:
        json_string: The raw string from a Streamlit text_area.
        field_name: The user-facing name of the field for error messages.

    Returns:
        A dictionary if parsing is successful, otherwise None.
    """
    if not json_string:
        return None
    try:
        # Clean up common copy-paste issues like smart quotes and newlines
        json_string_cleaned = (
            json_string.replace("’", "'")
            .replace("\n", " ")
            .replace("\t", " ")
            .replace("\r", "")
        )
        return json.loads(json_string_cleaned)
    except json.JSONDecodeError as e:
        st.error(f"Invalid JSON format for {field_name}: {e}")
        return None


def _apply_generation_config_typing(config: dict[str, Any]) -> dict[str, Any]:
    """Applies correct data types to generation config parameters.

    Streamlit text inputs return strings, but the underlying API requires
    specific types (e.g., float for temperature). This function converts
    common configuration values to their expected types.

    Args:
        config: The generation configuration dictionary with string values.

    Returns:
        The configuration dictionary with values cast to the correct types.
    """
    if "temperature" in config:
        config["temperature"] = float(config["temperature"])
    if "top_p" in config:
        config["top_p"] = float(config["top_p"])
    if "max_output_tokens" in config:
        config["max_output_tokens"] = int(config["max_output_tokens"])
    return config


# --- Handlers for "Create New Prompt" Tab ---
def _handle_save_new_prompt() -> None:
    """Validates inputs and saves a new prompt.

    Retrieves all necessary data from the Streamlit session state for the
    "Create New Prompt" tab, validates that required fields are filled,
    constructs the prompt object, and calls the backend service to save it.
    Displays success or error messages in the UI.
    """
    required_fields = {
        "new_prompt_name": "Prompt Name",
        "new_prompt_data": "Prompt Text",
        "new_model_name": "Model Name",
        "new_system_instructions": "System Instructions",
    }
    for key, name in required_fields.items():
        if not st.session_state.get(key):
            st.warning(f"Please enter a value for {name}.")
            return

    prompt_obj = st.session_state.local_prompt
    prompt_obj.prompt_to_run.prompt_name = st.session_state.new_prompt_name
    prompt_obj.prompt_to_run.prompt_data = st.session_state.new_prompt_data
    prompt_obj.prompt_to_run.model_name = st.session_state.new_model_name.strip()
    prompt_obj.prompt_to_run.system_instruction = (
        st.session_state.new_system_instructions
    )

    response_schema = _parse_json_input(
        st.session_state.new_response_schema, "Response Schema"
    )
    generation_config = _parse_json_input(
        st.session_state.new_generation_config, "Generation Config"
    )

    if generation_config:
        generation_config = _apply_generation_config_typing(generation_config)
        if response_schema:
            generation_config["response_schema"] = response_schema
        prompt_obj.prompt_meta["generation_config"] = generation_config

    if response_schema:
        prompt_obj.prompt_meta["response_schema"] = response_schema
    prompt_obj.prompt_meta["meta_tags"] = st.session_state.new_meta_tags

    try:
        logger.info("Saving new prompt...")
        prompt_meta_info = prompt_obj.save_prompt(check_existing=True)
        logger.info("Prompt saved successfully: %s", prompt_meta_info)
        st.success("Prompt saved successfully!")
    except Exception as e:
        logger.error("Failed to save prompt: %s", e, exc_info=True)
        st.error(f"Failed to save prompt: {e}")


def _handle_generate_test_for_new() -> None:
    """Generates a test response for the new prompt form.

    Takes the user-provided sample input and the current prompt configuration
    from the "Create" tab, sends it to the model for a response, and displays
    the output in the UI. This allows for quick testing before saving.
    """
    user_input_str = st.session_state.new_sample_user_input
    if not user_input_str:
        st.warning("Please provide sample user input to generate a response.")
        return

    sample_user_input = _parse_json_input(user_input_str, "User Input")
    if sample_user_input is None:
        return

    try:
        prompt_obj = st.session_state.local_prompt
        prompt_obj.prompt_to_run.prompt_data = st.session_state.new_prompt_data
        prompt_obj.prompt_to_run.model_name = st.session_state.new_model_name.strip()
        prompt_obj.prompt_to_run.system_instruction = (
            st.session_state.new_system_instructions
        )
        prompt_obj.prompt_meta["sample_user_input"] = sample_user_input

        with st.spinner("Generating response..."):
            response = prompt_obj.generate_response(sample_user_input)
        st.session_state.new_sample_output = response
        st.success("Prompt response generated!")
    except Exception as e:
        logger.error("Error during test generation: %s", e, exc_info=True)
        st.error(f"An error occurred during generation: {e}")


# --- Handlers for "Load & Edit Prompt" Tab ---
def _populate_ui_from_prompt() -> None:
    """Populates session state for UI widgets from the loaded prompt object.

    After a prompt is loaded from the backend, this function takes the data
    from the `gcp_prompt` object and sets the corresponding values in the
    Streamlit session state. This updates the "Load & Edit" tab's input
    widgets to display the loaded prompt's information.
    """
    prompt_obj = st.session_state.local_prompt
    st.session_state.edit_prompt_name = prompt_obj.prompt_to_run.prompt_name
    st.session_state.edit_prompt_data = prompt_obj.prompt_to_run.prompt_data
    st.session_state.edit_model_name = prompt_obj.prompt_to_run.model_name.split("/")[
        -1
    ]
    st.session_state.edit_system_instructions = (
        prompt_obj.prompt_to_run.system_instruction
    )
    st.session_state.edit_response_schema = json.dumps(
        prompt_obj.prompt_meta.get("response_schema", {}), indent=2
    )
    st.session_state.edit_generation_config = json.dumps(
        prompt_obj.prompt_meta.get("generation_config", {}), indent=2
    )
    st.session_state.edit_meta_tags = prompt_obj.prompt_meta.get("meta_tags", [])
    st.session_state.edit_sample_user_input = json.dumps(
        prompt_obj.prompt_meta.get("sample_user_input", {}), indent=2
    )
    st.session_state.edit_sample_output = ""  # Clear previous output


def _handle_load_prompt() -> None:
    """Loads the selected prompt and version and populates the UI.

    Triggered by the 'Load Prompt' button. It retrieves the selected prompt
    name and version from the UI, calls the backend to fetch the data,
    and then uses `_populate_ui_from_prompt` to display it.
    """
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
        logger.info(
            "Successfully loaded prompt '%s' version '%s'.", prompt_name, version_id
        )
        _populate_ui_from_prompt()
        st.success(f"Loaded prompt '{prompt_name}' (Version: {version_id}).")
    except Exception as e:
        logger.error("Failed to load prompt: %s", e, exc_info=True)
        st.error(f"Failed to load prompt: {e}")


def _handle_save_edited_prompt() -> None:
    """Validates inputs and saves the current prompt config as a new version.

    Similar to saving a new prompt, but it takes the data from the "Edit" tab's
    widgets. It saves the current configuration as a new version of the
    already existing prompt.
    """
    if not st.session_state.get("edit_prompt_name"):
        st.warning("Cannot save. Please load a prompt first.")
        return

    required_fields = {
        "edit_prompt_data": "Prompt Text",
        "edit_model_name": "Model Name",
        "edit_system_instructions": "System Instructions",
    }
    for key, name in required_fields.items():
        if not st.session_state.get(key):
            st.warning(f"Please ensure '{name}' is not empty.")
            return

    prompt_obj = st.session_state.local_prompt
    prompt_obj.prompt_to_run.prompt_name = st.session_state.edit_prompt_name
    prompt_obj.prompt_to_run.prompt_data = st.session_state.edit_prompt_data
    prompt_obj.prompt_to_run.model_name = st.session_state.edit_model_name.strip()
    prompt_obj.prompt_to_run.system_instruction = (
        st.session_state.edit_system_instructions
    )

    response_schema = _parse_json_input(
        st.session_state.edit_response_schema, "Response Schema"
    )
    generation_config = _parse_json_input(
        st.session_state.edit_generation_config, "Generation Config"
    )

    if generation_config:
        generation_config = _apply_generation_config_typing(generation_config)
        if response_schema:
            generation_config["response_schema"] = response_schema
        prompt_obj.prompt_meta["generation_config"] = generation_config

    if response_schema:
        prompt_obj.prompt_meta["response_schema"] = response_schema
    prompt_obj.prompt_meta["meta_tags"] = st.session_state.edit_meta_tags

    try:
        with st.spinner("Saving as new version..."):
            prompt_meta_info = prompt_obj.save_prompt(check_existing=False)
        logger.info("Prompt saved successfully: %s", prompt_meta_info)
        st.success("Saved as a new version successfully!")
        st.session_state.local_prompt.refresh_prompt_cache()
    except Exception as e:
        logger.error("Failed to save prompt: %s", e, exc_info=True)
        st.error(f"Failed to save prompt: {e}")


def _handle_generate_test_for_edit() -> None:
    """Generates a test response for the edited prompt.

    Allows users to test changes made in the "Edit" tab before saving them
    as a new version. It uses the current values in the UI fields to generate
    a response from the model.
    """
    if not st.session_state.get("edit_prompt_name"):
        st.warning("Please load a prompt before generating a response.")
        return

    user_input_str = st.session_state.get("edit_sample_user_input", "")
    if not user_input_str:
        st.warning("Please provide sample user input to generate a response.")
        return

    sample_user_input = _parse_json_input(user_input_str, "Sample User Input")
    if sample_user_input is None:
        return

    try:
        prompt_obj = st.session_state.local_prompt
        prompt_obj.prompt_to_run.prompt_data = st.session_state.edit_prompt_data
        prompt_obj.prompt_to_run.system_instruction = (
            st.session_state.edit_system_instructions
        )
        prompt_obj.prompt_meta["sample_user_input"] = sample_user_input

        with st.spinner("Generating response..."):
            response = prompt_obj.generate_response(sample_user_input)
        st.session_state.edit_sample_output = response
        st.success("Prompt response generated!")
    except Exception as e:
        logger.error("Error during test generation: %s", e, exc_info=True)
        st.error(f"An error occurred during generation: {e}")


# --- UI Rendering Functions ---
def render_create_tab() -> None:
    """Renders the UI components for the 'Create New Prompt' tab.

    This function defines and lays out all the Streamlit widgets (text inputs,
    buttons, etc.) for the prompt creation workflow.
    """
    st.subheader("1. Define Prompt Details")
    st.text_input(
        "**Prompt Name**",
        key="new_prompt_name",
        placeholder="e.g., customer_sentiment_classifier_v1",
        help="A unique name to identify your prompt.",
    )
    st.text_area(
        "**Prompt Text**",
        key="new_prompt_data",
        height=150,
        placeholder="e.g., Classify the sentiment of the following text: {customer_review}",
        help="The core text of your prompt. Use curly braces `{}` for variables.",
    )
    st.text_input(
        "**Model Name**",
        key="new_model_name",
        placeholder="gemini-2.5-pro-001",
        help="The specific model version to use (e.g., gemini-2.5-pro).",
    )
    st.text_area(
        "**System Instructions**",
        key="new_system_instructions",
        height=300,
        placeholder="e.g., You are an expert in sentiment analysis...",
        help="Optional instructions to guide the model's behavior.",
    )
    st.multiselect(
        "**Prompt Task**",
        options=AVAILABLE_PROMPT_TASKS,
        key="new_meta_tags",
        help="Select the most appropriate task type for this prompt.",
    )
    st.text_area(
        "**Response Schema (JSON)**",
        key="new_response_schema",
        height=150,
        placeholder='{\n  "type": "object", ... \n}',
        help="Define the desired JSON structure for the model's output.",
    )
    st.text_area(
        "**Generation Config (JSON)**",
        key="new_generation_config",
        height=150,
        placeholder='{\n  "temperature": 0.2, ... \n}',
        help="A dictionary of generation parameters.",
    )

    if st.button(
        "Save Prompt", type="primary", use_container_width=True, key="save_new"
    ):
        _handle_save_new_prompt()

    st.divider()

    st.subheader("2. Test Your Prompt")
    st.markdown("You can test your prompt here before saving.")
    st.text_area(
        "**Sample User Input (JSON)**",
        key="new_sample_user_input",
        height=150,
        placeholder='{\n  "customer_review": "The product was amazing!"\n}',
        help="A JSON object where keys match the variables in your prompt text.",
    )

    if st.button("Generate Test Response", use_container_width=True, key="test_new"):
        _handle_generate_test_for_new()

    st.text_area(
        "**Test Output**",
        key="new_sample_output",
        height=150,
        placeholder="The model's response will be displayed here.",
        disabled=True,
    )


def render_edit_tab() -> None:
    """Renders the UI components for the 'Load & Edit Prompt' tab.

    This function defines and lays out all the Streamlit widgets for loading,
    editing, and versioning existing prompts.
    """
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
            help="Choose the prompt you want to load.",
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
            help="Choose the specific version to load.",
        )

    st.button(
        "Load Prompt",
        on_click=_handle_load_prompt,
        use_container_width=True,
        type="primary",
    )

    st.divider()

    st.subheader("2. Edit Prompt Details")
    st.text_input("Prompt Name", key="edit_prompt_name", disabled=True)
    st.text_area("Prompt Text", key="edit_prompt_data", height=150)
    st.text_input("Model Name", key="edit_model_name")
    st.text_area("System Instructions", key="edit_system_instructions", height=300)
    st.multiselect("Prompt Task", options=AVAILABLE_PROMPT_TASKS, key="edit_meta_tags")

    col_schema, col_config = st.columns(2)
    with col_schema:
        st.text_area("Response Schema (JSON)", key="edit_response_schema", height=200)
    with col_config:
        st.text_area(
            "Generation Config (JSON)", key="edit_generation_config", height=200
        )

    if st.button(
        "Save as New Version", type="primary", use_container_width=True, key="save_edit"
    ):
        _handle_save_edited_prompt()

    st.divider()

    st.subheader("3. Test Your Prompt")
    st.text_area("Sample User Input (JSON)", key="edit_sample_user_input", height=150)

    if st.button("Generate Test Response", use_container_width=True, key="test_edit"):
        _handle_generate_test_for_edit()

    st.text_area(
        "Test Output",
        key="edit_sample_output",
        height=150,
        placeholder="The model's response will be displayed here.",
        disabled=True,
    )


# --- Main Application ---
def main() -> None:
    """Renders the main Prompt Management page.

    Sets the page configuration, initializes the session state (including the
    `gcp_prompt` object and UI field defaults), and renders the main title
    and tabbed layout for creating and editing prompts.
    """
    st.set_page_config(
        layout="wide",
        page_title="Prompt Management",
        page_icon="assets/favicon.ico",
    )

    # Initialize session state object and UI fields
    if "local_prompt" not in st.session_state:
        st.session_state.local_prompt = gcp_prompt()

    ui_fields = {
        "new_prompt_name": "",
        "new_prompt_data": "",
        "new_model_name": "",
        "new_system_instructions": "",
        "new_response_schema": "",
        "new_generation_config": "",
        "new_meta_tags": [],
        "new_sample_user_input": "",
        "new_sample_output": "",
        "edit_prompt_name": "",
        "edit_prompt_data": "",
        "edit_model_name": "",
        "edit_system_instructions": "",
        "edit_response_schema": "",
        "edit_generation_config": "",
        "edit_meta_tags": [],
        "edit_sample_user_input": "",
        "edit_sample_output": "",
    }
    for field, default_val in ui_fields.items():
        if field not in st.session_state:
            st.session_state[field] = default_val

    st.title("Prompt Management")
    st.markdown(
        "Create new prompts or load, edit, and test existing ones from the Prompt Management service."
    )
    st.divider()

    # Use st.radio to create stateful tabs that persist across reruns.
    # This prevents the UI from resetting to the first tab on every interaction.
    selected_tab = st.radio(
        "Select Action",
        ["Create New Prompt", "Load & Edit Prompt"],
        key="prompt_management_tab",
        horizontal=True,
        label_visibility="collapsed",
    )

    if selected_tab == "Create New Prompt":
        render_create_tab()
    elif selected_tab == "Load & Edit Prompt":
        render_edit_tab()

    st.caption("LLM EvalKit | Prompt Management")


if __name__ == "__main__":
    main()
