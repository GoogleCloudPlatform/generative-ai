##############################################################################
# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##############################################################################
# Vertex AI RAG Comparator with Judge Model
# Developed by Ram Seshadri
# Last Updated: Feb 2025
#
# Note: This is not an officially supported Google product.
##############################################################################

import argparse
import json
import logging
import os
import re
import time
from typing import Any, Dict, List, Optional, Tuple
import warnings

from google import genai
from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine
from google.genai import types
import google.generativeai
from langchain.chains import RetrievalQA
from langchain_google_community import VertexAISearchRetriever
from langchain_google_vertexai import VertexAI
import ollama  # Added missing import
import requests
import streamlit as st

# --- Configuration Constants ---
DEBUG = False  # Set to False in production
PROMPT_FOLDER = "prompts"
SYSTEM_PROMPT_FILE = "system_instruction.txt"
REPHRASER_PROMPT_FILE = "rephraser.txt"
SUMMARIZER_PROMPT_FILE = "summarizer.txt"
DEFAULT_OLLAMA_URL = "http://localhost:11434/api/tags"
DEFAULT_OLLAMA_TIMEOUT = 10  # seconds
DEFAULT_GEMINI_API_VERSION = "v1"  # or 'v1alpha' if needed
DEFAULT_GEMINI_TEMPERATURE = 0.3
DEFAULT_GEMINI_MAX_TOKENS = 2048
DEFAULT_GEMINI_TOP_P = 0.95
DEFAULT_VERTEX_SEARCH_MODEL = "gemini-2.0-flash-001"
DEFAULT_DATA_STORE_LOCATION = "global"
DEFAULT_BRANCH_NAME = "default_branch"
DEFAULT_COLLECTION = "default_collection"
RAG_SKIP_PHRASES = ["I am not able to answer this question", "No RAG required"]
GEMINI_MODEL_PREFIXES = ["gemini-2."]
JUDGE_MODEL_NAME = "gemini-2.5-pro-001"  # Added constant

# --- Logging Setup ---
logging.basicConfig(
    level=logging.DEBUG if DEBUG else logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)

# --- Suppress Specific Warnings ---
# Filter specific warnings if necessary, but use sparingly.
warnings.filterwarnings("ignore")
with warnings.catch_warnings():
    warnings.simplefilter("ignore")


# --- Helper Functions ---
def log_debug(message: str):
    """Logs a debug message if DEBUG is True."""
    if DEBUG:
        logging.debug(message)
        # Optionally keep sidebar logging for Streamlit debugging
        st.sidebar.write(f"DEBUG: {message}")


def load_text_file(filename: str) -> Optional[str]:
    """
    Loads text content from a file.

    Args:
        filename: The path to the file.

    Returns:
        The content of the file as a string, or None if an error occurs.
    """
    log_debug(f"Attempting to load file: {filename}")
    try:
        with open(filename, "r", encoding="utf-8") as file:
            return file.read()
    except FileNotFoundError:
        logging.error(f"Error: File not found at {filename}.")
        st.error(f"Error: Prompt file not found: {filename}")
    except IOError as e:
        logging.error(f"Error: Could not read file {filename}. Reason: {e}")
        st.error(f"Error: Could not read prompt file: {os.path.basename(filename)}")
    except Exception as e:
        logging.error(f"An unexpected error occurred loading {filename}: {e}")
        st.error("An unexpected error occurred loading a required file.")
    return ""


def create_gemini_client() -> genai.Client:
    """
    Creates a Gemini client, automatically handling Vertex AI vs. API Key auth.

    Raises:
        ValueError: If required environment variables are missing.

    Returns:
        An initialized genai.Client.
    """
    if os.environ.get("GOOGLE_VERTEXAI", "").lower() == "true":
        # Vertex AI configuration
        project = os.getenv("PROJECT_ID")
        location = os.getenv("LOCATION")
        st.session_state["project_id"] = project
        st.session_state["location"] = location

        if not project or not location:
            raise ValueError(
                "Vertex AI requires GOOGLE_CLOUD_PROJECT and GOOGLE_CLOUD_LOCATION "
                "environment variables set."
            )
        log_debug(f"Creating Vertex AI client for project {project} in {location}")
        return genai.Client(
            vertexai=True,
            project=project,
            location=location,
            # http_options=types.HttpOptions(api_version=DEFAULT_GEMINI_API_VERSION) # Uncomment if specific version needed
        )
    else:
        # Gemini Developer API configuration
        api_key = os.getenv("GOOGLE_API_KEY")
        if not api_key:
            raise ValueError(
                "Gemini API requires GOOGLE_API_KEY environment variable set."
            )
        log_debug("Creating Gemini API client using API Key.")
        return google.generativeai.Client(
            api_key=api_key,
            # http_options=types.HttpOptions(api_version=DEFAULT_GEMINI_API_VERSION) # Uncomment if specific version needed
        )


def _load_prompt_template(filename: str) -> Optional[str]:
    """Loads a prompt template file from the PROMPT_FOLDER."""
    filepath = os.path.join(PROMPT_FOLDER, filename)
    return load_text_file(filepath)


def _apply_system_prompt(prompt_text: str) -> str:
    """Prepends the system prompt from session state if available."""
    system_instruction = st.session_state.get("system_prompt", "").strip()
    if system_instruction:
        return f"{system_instruction}\n\n{prompt_text}"
    return prompt_text


def get_rephraser_prompt(query: str) -> Optional[str]:
    """
    Loads and formats the rephraser prompt.

    Args:
        query: The user's original query.

    Returns:
        The formatted prompt string, or None if loading fails.
    """
    prompt_template = _load_prompt_template(REPHRASER_PROMPT_FILE)

    try:
        formatted_prompt = """Now, please rephrase the following customer query:
   
{query}
"""
        formatted_prompt = prompt_template + formatted_prompt.format(query=query)
        return _apply_system_prompt(formatted_prompt)
    except KeyError as e:
        logging.error(f"Error formatting rephraser prompt: Missing key {e}")
        st.error("Internal error: Could not format the rephrasing prompt.")
        return None


def get_summarizer_prompt(documents: List[str], query: str) -> Optional[str]:
    """
    Loads and formats the summarizer prompt with retrieved documents.

    Args:
        documents: A list of context documents.
        query: The user's query (potentially rephrased).

    Returns:
        The formatted prompt string, or None if loading fails.
    """
    prompt_template = _load_prompt_template(SUMMARIZER_PROMPT_FILE)

    document_vars = {}
    if documents:
        for i, doc in enumerate(documents):
            document_vars[f"Text_of_Document_{i + 1}"] = doc
    else:
        # Provide placeholder if no documents are found
        document_vars["Text_of_Document_1"] = "No relevant documents found."

    # Prepare format arguments - ensure all expected keys are present
    # Assuming the template expects up to 3 docs, provide placeholders
    format_args = {"query": query}
    for i in range(1, 4):  # Adjust range if template expects different number
        key = f"Text_of_Document_{i}"
        format_args[key] = document_vars.get(key, "No document provided for this slot.")

    formatted_prompt = """
Now it's your turn! Here is the query and relevant documents:
    Customer Search Query: {query}
    
    Document Texts:
    [Start of Document 1]
    {Text_of_Document_1}
    [End of Document 1]
    
    [Start of Document 2]
    {Text_of_Document_2}
    [End of Document 2]
    
    [Start of Document 3]
    {Text_of_Document_3}
    [End of Document 3]    
    """

    try:
        formatted_prompt = prompt_template + formatted_prompt.format(**format_args)
        return _apply_system_prompt(formatted_prompt)
    except KeyError as e:
        logging.error(f"Error formatting summarizer prompt: Missing key {e}")
        st.error("Internal error: Could not format the summarization prompt.")
        return None
    except Exception as e:
        logging.error(f"Unexpected error formatting summarizer prompt: {e}")
        st.error("Internal error formatting summarization prompt.")
        return None


def initialize_models() -> Tuple[List[str], List[str]]:
    """
    Initializes and lists available Gemini and Ollama models.

    Returns:
        A tuple containing two lists: (ollama_model_names, gemini_model_names).
        Returns empty lists if errors occur.
    """
    ollama_models = []
    gemini_models = []

    # Initialize Gemini client and list models
    try:
        client = create_gemini_client()
        # Increased page_size for fewer requests if many models exist
        response = client.models.list(config={"page_size": 200, "query_base": True})
        gemini_models = [
            model.name.split("/")[-1]
            for model in response.page
            if any(prefix in model.name for prefix in GEMINI_MODEL_PREFIXES)
        ]
        log_debug(f"Found Gemini models: {gemini_models}")
    except Exception as e:
        st.error(f"Failed to list Gemini models: {e}")
        logging.error(f"Gemini model initialization error: {e}")

    # Initialize Ollama models (if server is running)
    try:
        response = requests.get(DEFAULT_OLLAMA_URL, timeout=DEFAULT_OLLAMA_TIMEOUT)
        response.raise_for_status()  # Raises HTTPError for bad responses (4xx or 5xx)
        ollama_models = [model["name"] for model in response.json().get("models", [])]
        log_debug(f"Found Ollama models: {ollama_models}")
        if not ollama_models:
            st.warning(
                "Ollama server responded, but no models listed. Ensure models are available on the Ollama server."
            )
    except requests.exceptions.ConnectionError:
        st.warning("🔴 Ollama server not reachable. Is it running?")
        logging.warning("Ollama connection failed: ConnectionError.")
    except requests.exceptions.Timeout:
        st.warning("🔴 Ollama server timed out.")
        logging.warning("Ollama connection failed: Timeout.")
    except requests.exceptions.RequestException as e:
        st.error(f"Ollama connection failed: {e}")
        logging.error(f"Ollama connection failed: {e}")
    except Exception as e:
        st.error(f"Error processing Ollama response: {e}")
        logging.error(f"Error processing Ollama response: {e}")

    return ollama_models, gemini_models


def generate_gemini_response(
    prompt: str, model_config: Dict[str, Any], col: st.container
) -> str:
    """
    Generates a response using the Gemini Chat API via google-genai client.

    Args:
        prompt: The complete prompt string.
        model_config: Dictionary containing 'name' and 'temperature'.
        col: The Streamlit column container to display the response in.

    Returns:
        The generated response text.
    """
    start_time = (time.time()) * 1000.0
    model_name = model_config["name"]
    temperature = model_config.get("temperature", DEFAULT_GEMINI_TEMPERATURE)
    session_key = f"gemini_chat_client_{model_name}_{col}"  # More specific key

    log_debug(f"Calling Gemini API: model={model_name}, temp={temperature}")
    log_debug(f"Full prompt for Gemini:\n{prompt[:500]}...")  # Log truncated prompt

    full_response = ""
    system_instruction = st.session_state.get("system_prompt", "").strip()

    # Configuration for the generation request
    # Note: system_instruction placement differs for chat vs. generate_content
    chat_content_config = {
        "system_instruction": system_instruction,
        "temperature": temperature,
        "max_output_tokens": DEFAULT_GEMINI_MAX_TOKENS,
    }

    try:
        # Initialize or retrieve the client/chat object
        if session_key not in st.session_state:
            log_debug(f'Setting genai model to {model_config["name"]}')
            client = create_gemini_client()

            ### Use this if you are using a chat model. Otherwise, comment it out.
            client = client.chats.create(model=model_name, config=chat_content_config)

            st.session_state[session_key] = client  # Set the session model object

        else:  # Retrieve the model from column instead.
            client = st.session_state[session_key]

        # Generate the response using the appropriate method
        with col, st.chat_message("ai"):
            ### Use this only for a text model - not a chat model!
            # response = client.models.generate_content_stream(
            #    model = model_name,
            #    contents = prompt,
            #    config = generate_content_config,
            #    )

            #### This is a chat model ######
            response = client.send_message_stream(prompt)
            time_taken = 1000.0 * (time.time()) - start_time

            ### Both chat and text work the same way in extracting text ##
            for chunk in response:
                chunk_text = chunk.text
                full_response += chunk_text
            # Remove RAG related additional text
            st.write(
                full_response.replace("++No RAG required++", "").replace(
                    "<No RAG required>", ""
                )
            )
            st.write(f"\t\ttime taken = {time_taken:0.0f} ms")
            ### this is the input token count is the prompt token count
            st.write(
                f"\t\tinput token count = {chunk.usage_metadata.prompt_token_count}"
            )
            # Directly provides output count
            st.write(
                f"\t\toutput token count = {chunk.usage_metadata.candidates_token_count}"
            )
        # log_debug(f"Gemini Response: {full_response}") ## getting empty string
        ## if getting error, add an exception clause
        log_debug(
            f"Usage meta data: total token count = {chunk.usage_metadata.total_token_count}"
        )

    except Exception as e:
        st.error(f"Error calling Gemini API: {e}")
        logging.exception("Error during Gemini API call:")  # Log full traceback
        return f"Error generating response: {e}"

    return full_response


def generate_ollama_response(
    prompt: str, model_config: Dict[str, Any], col: st.container
) -> str:
    """
    Generates a streaming response using the Ollama Chat API.

    Args:
        prompt: The complete prompt string.
        model_config: Dictionary containing 'name'.
        col: The Streamlit column container to display the response in.

    Returns:
        The generated response text.
    """
    model_name = model_config["name"]
    log_debug(f"Calling Ollama API: model={model_name} (Streaming)")
    log_debug(f"Full prompt for Ollama:\n{prompt[:500]}...")  # Log truncated prompt

    full_response = ""

    try:
        with col, st.chat_message("ai"):
            chat_placeholder = st.empty()
            stream = ollama.chat(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
            )

            for chunk in stream:
                # Safely access message content
                message_content = chunk.get("message", {}).get("content")
                if message_content:
                    full_response += message_content
                    chat_placeholder.write(full_response + "▌")  # Indicate streaming
                # Log potential errors or empty chunks if needed
                # elif chunk.get('error'):
                #     logging.error(f"Ollama stream error: {chunk['error']}")

            chat_placeholder.write(full_response)  # Final response
            log_debug(f"Ollama Response: {full_response}")

    except Exception as e:
        st.error(f"Error calling Ollama API: {e}")
        logging.exception("Error during Ollama API call:")  # Log full traceback
        return f"Error generating response: {e}"

    return full_response


def generate_rephraser_response(
    model_config: Dict[str, Any], question: str, col: st.container
) -> str:
    """
    Orchestrates rephrased query generation using the selected model.

    Args:
        model_config: Configuration for the selected model {'type', 'name', 'temperature'}.
        question: The original user question.
        col: The Streamlit column to display the intermediate step.

    Returns:
        The rephrased query string, or the original question if errors occur.
    """
    start_time = time.time()
    rephrased_query = question  # Default to original question

    try:
        log_debug(f"Generating rephrased query with config: {model_config}")
        rephraser_prompt = get_rephraser_prompt(question)

        if not rephraser_prompt:
            st.warning("Could not load rephraser prompt. Using original question.")
            return question  # Return original if prompt loading failed

        model_type = model_config.get("type")

        # Display placeholder in the column
        with col, st.chat_message("ai"):
            st.write(
                f"*{model_config.get('name', 'Model')} is rephrasing the query...*"
            )

        # Generate response (will be displayed within the respective functions)
        if model_type == "gemini":
            rephrased_query = generate_gemini_response(
                rephraser_prompt, model_config, col
            )
        elif model_type == "3p_models":  # Change from "3p_models" to Ollama if needed
            rephrased_query = generate_ollama_response(
                rephraser_prompt, model_config, col
            )
        else:
            raise ValueError(f"Unsupported model type for rephrasing: {model_type}")

        # Clean up potential RAG skip phrases from the rephrased query itself
        for phrase in RAG_SKIP_PHRASES:
            rephrased_query = rephrased_query.replace(phrase, "").strip()

        log_debug(f"Rephrased Query: {rephrased_query}")
        elapsed_time = time.time() - start_time
        log_debug(f"Rephrasing time: {elapsed_time:.1f} seconds")

        # Optionally display the final rephrased query if needed (might be redundant)
        # with col, st.chat_message("ai"):
        #     st.write(f"**Rephrased:** {rephrased_query}")

        return rephrased_query

    except Exception as e:
        log_debug(f"Error generating rephrased response: {e}")
        st.error(f"Error during query rephrasing: {e}")
        # Fallback to original question
        return question


def generate_summarizer_response(
    model_config: Dict[str, Any],
    question: str,  # This is the potentially rephrased question
    context: List[str],  # Expecting list of strings now
    col: st.container,
) -> Dict[str, Any]:
    """
    Orchestrates final response generation using the selected model and context.

    Args:
        model_config: Configuration for the selected model.
        question: The query to answer (potentially rephrased).
        context: A list of context documents (strings). Empty list if no RAG.
        col: The Streamlit column to display the response.

    Returns:
        A dictionary containing 'text', 'time', and 'error'.
    """
    start_time = time.time()
    response_text = ""
    error_message = None

    try:
        log_debug(f"Generating summarizer response with config: {model_config}")
        # Context is now always a list, potentially empty
        summarizer_prompt = get_summarizer_prompt(context, question)

        if not summarizer_prompt:
            st.warning(
                "Could not load summarizer prompt. Cannot generate final answer."
            )
            return {"text": "", "time": 0, "error": "Prompt loading failed"}

        model_type = model_config.get("type")

        # Display placeholder - response generation happens inside called functions
        with col, st.chat_message("ai"):
            st.write(
                f"*{model_config.get('name', 'Model')} is generating the final answer...*"
            )

        if model_type == "gemini":
            response_text = generate_gemini_response(
                summarizer_prompt, model_config, col
            )
        elif model_type == "3p_models":  # Changed from "3p_models"
            response_text = generate_ollama_response(
                summarizer_prompt, model_config, col
            )
        else:
            raise ValueError(f"Unsupported model type for summarizing: {model_type}")

        log_debug(f"Final Response:\n {response_text}")

    except Exception as e:
        log_debug(f"Error generating summarizer response: {e}")
        st.error(f"Error generating final answer: {e}")
        error_message = str(e)  # Capture error message

    elapsed_time = time.time() - start_time
    log_debug(f"Summarization time: {elapsed_time:.1f} seconds")

    return {
        "text": response_text,
        "time": elapsed_time,
        "error": error_message,
    }


def model_selection(column: st.container, key_prefix: str) -> Dict[str, Any]:
    """
    Creates Streamlit widgets for selecting model type, name, and temperature.

    Args:
        column: The Streamlit column to place widgets in.
        key_prefix: A unique prefix ('left' or 'right') for widget keys.

    Returns:
        A dictionary containing the selected model configuration:
        {'type': str, 'name': str, 'temperature': float}.
    """
    with column:
        st.subheader(f"{key_prefix.capitalize()} Model Config")
        model_type = st.radio(
            "Model Provider",
            ["Gemini", "3P_Models"],  # Change "" to "Ollama" if needed
            index=(
                0 if key_prefix == "left" else 1
            ),  # Default left=Gemini, right=3P_Models
            key=f"{key_prefix}_type",
            horizontal=True,
        )

        config = {"type": model_type.lower()}  # Store type as lowercase

        if model_type == "3P_Models":
            ### let's make this for Third Party  models
            available_models = st.session_state.get("ollama_models", [])
            if not available_models:
                st.warning(
                    "No Third Party models found. Ensure 3P_Models are running and accessible."
                )
                model_name = st.text_input(
                    "Enter Third Party Model Name Manually",
                    key=f"{key_prefix}_ollama_model_manual",
                )
            else:
                model_name = st.selectbox(
                    "Select Third Party Model",
                    available_models,
                    key=f"{key_prefix}_ollama_model",
                )
            config["name"] = model_name
            # 3P_Models temperature is often handled differently or not via simple API param
            config["temperature"] = 0.0  # Set a default, but may not be used directly

        else:  # Gemini
            available_models = st.session_state.get("gemini_models", [])
            if not available_models:
                st.error("No Gemini models found. Check configuration and permissions.")
                # Provide a default or allow manual entry if list fails
                model_name = "gemini-1.5-flash-latest"  # Fallback default
            else:
                default_index = 0
                try:
                    # Try to find a reasonable default like flash
                    default_index = available_models.index("gemini-1.5-flash-latest")
                except ValueError:
                    pass  # Keep default_index 0 if not found

                model_name = st.selectbox(
                    "Select Gemini Model",
                    available_models,
                    key=f"{key_prefix}_gemini_model",
                    index=default_index,
                )

            config["name"] = model_name
            temperature = st.slider(
                "Temperature",
                min_value=0.0,
                max_value=1.0,  # Or 2.0 depending on model support
                value=DEFAULT_GEMINI_TEMPERATURE,
                step=0.1,
                key=f"{key_prefix}_temp",
            )
            config["temperature"] = temperature

    log_debug(f"{key_prefix} config selected: {config}")
    return config


def _get_discoveryengine_client_options(location: str) -> Optional[ClientOptions]:
    """Helper to create client options for Discovery Engine."""
    if location != "global":
        api_endpoint = f"{location}-discoveryengine.googleapis.com"
        log_debug(f"Using Discovery Engine endpoint: {api_endpoint}")
        return ClientOptions(api_endpoint=api_endpoint)
    log_debug("Using global Discovery Engine endpoint.")
    return None


def list_data_stores(
    project_id: str, location: str = DEFAULT_DATA_STORE_LOCATION
) -> List[str]:
    """
    Lists available Vertex AI Search data stores in a project and location.

    Args:
        project_id: Google Cloud project ID.
        location: Google Cloud location (default: 'global').

    Returns:
        A list of data store IDs (the last part of the resource name).
        Returns an empty list if an error occurs.
    """
    log_debug(f"Listing data stores for project {project_id} in {location}")
    try:
        client_options = _get_discoveryengine_client_options(location)
        client = discoveryengine.DataStoreServiceClient(client_options=client_options)
        parent_path = client.collection_path(
            project_id, location, collection=DEFAULT_COLLECTION
        )
        request = discoveryengine.ListDataStoresRequest(parent=parent_path)
        response = client.list_data_stores(request=request)

        data_store_ids = [store.name.split("/")[-1] for store in response]
        log_debug(f"Found data stores: {data_store_ids}")
        return data_store_ids

    except Exception as e:
        st.error(f"Failed to list Vertex AI Search data stores: {e}")
        logging.exception("Error listing data stores:")
        return []


def list_documents(
    project_id: str,
    location: str,
    data_store_id: str,
) -> List[discoveryengine.Document]:
    """
    Lists documents within a specific Vertex AI Search data store branch.

    Args:
        project_id: Google Cloud project ID.
        location: Google Cloud location.
        data_store_id: The ID of the data store.

    Returns:
        A list of discoveryengine.Document objects.
        Returns an empty list if an error occurs or no documents found.
    """
    log_debug(f"Listing documents in store {data_store_id} ({project_id}/{location})")
    try:
        client_options = _get_discoveryengine_client_options(location)
        client = discoveryengine.DocumentServiceClient(client_options=client_options)
        parent_path = client.branch_path(
            project=project_id,
            location=location,
            data_store=data_store_id,
            branch=DEFAULT_BRANCH_NAME,
        )
        response = client.list_documents(parent=parent_path)
        ls = []
        for i, result in enumerate(response):
            if i == 0:
                ls.append(result)
                break
        return ls

    except Exception as e:
        st.error(f"Failed to list documents in data store {data_store_id}: {e}")
        logging.exception(f"Error listing documents in {data_store_id}:")
        return None


def setup_retriever_sidebar() -> Optional[VertexAI]:
    """
    Sets up the sidebar for Vertex AI Search connection and returns the LLM.

    Returns:
        An initialized VertexAI LLM object for use with the retriever,
        or None if configuration fails.
    """
    with st.sidebar:
        st.header("📁 Vertex AI Search RAG")

        project_id = st.session_state.get("project_id", os.getenv("PROJECT_ID"))

        if not project_id:
            st.warning("Set GOOGLE_CLOUD_PROJECT env var or configure via Gemini.")
            return None

        if "datastore_ids" not in st.session_state:
            st.session_state.datastore_ids = list_data_stores(
                project_id, DEFAULT_DATA_STORE_LOCATION
            )

        if not st.session_state.datastore_ids:
            st.warning("No data stores found or accessible.")
            # Allow manual entry maybe?
            data_store_id = st.text_input(
                "Enter Data Store ID manually", key="datastore_id_manual"
            )
        else:
            data_store_id = st.selectbox(
                "Select Data Store",
                st.session_state.datastore_ids,
                key="datastore_id_select",
                index=0,
            )

        st.session_state["selected_datastore_id"] = data_store_id  # Store selection

        if st.button("Test Connection"):
            if data_store_id:
                docs = list_documents(
                    project_id, DEFAULT_DATA_STORE_LOCATION, data_store_id
                )
                if docs is not None:  # Check if list_documents returned successfully
                    st.success(f"Success! Connected to '{data_store_id}'.")
                else:
                    # Error displayed within list_documents
                    st.warning("Please select or enter a data store ID.")
            else:
                st.warning("Please select or enter a data store ID.")

        # Define the LLM for the retriever (can be different from chat models)
        try:
            llm = VertexAI(model_name=DEFAULT_VERTEX_SEARCH_MODEL, project=project_id)
        except Exception as e:
            st.error(f"Failed to initialize VertexAI LLM for retriever: {e}")
            logging.exception("VertexAI LLM init error:")
            return None

        # Create the retriever (only if a datastore is selected)
        if data_store_id:
            try:
                retriever = VertexAISearchRetriever(
                    project_id=project_id,
                    location_id=DEFAULT_DATA_STORE_LOCATION,  # Assuming global for retriever
                    data_store_id=data_store_id,
                    get_extractive_answers=False,  # Configurable?
                    max_documents=3,  # Increased context slightly
                    # max_extractive_segment_count=1, # If get_extractive_answers=True
                    # max_extractive_answer_count=1, # If get_extractive_answers=True
                )
                # Store the retriever instance in session state
                st.session_state.vector_store_retriever = retriever
                log_debug(f"Vertex AI Search Retriever created for {data_store_id}")
                return llm  # Return LLM only if retriever setup is successful
            except Exception as e:
                st.error(f"Failed to create Vertex AI Search retriever: {e}")
                logging.exception("Retriever creation error:")
                st.session_state.vector_store_retriever = (
                    None  # Ensure it's cleared on error
                )
                return None  # Don't return LLM if retriever failed
        else:
            st.info("Select a data store to enable RAG.")
            st.session_state.vector_store_retriever = (
                None  # Clear if no datastore selected
            )
            return None  # No LLM needed if no retriever


def clean_json(response_text: str):
    """Cleans potential markdown/JSON issues from a string."""
    # removing any markdown block that might appear
    response_text = response_text.replace("{{", "{").replace("}}", "}")

    pattern = r"(?:^```.*)"
    modified_text = re.sub(pattern, "", response_text, 0, re.MULTILINE)
    try:
        # print(modified_text)
        result = json.loads(modified_text)
    except json.JSONDecodeError:
        # Log warning
        logger.warning(
            f"Failed to parse cleaned JSON, returning as simple dict: {modified_text[:100]}..."
        )
        # Fallback for non-JSON input after cleaning
        result = json.loads(
            f'{"intent":modified_text, "es_intent": modified_text, "is_trouble":"No", "cot": "None"}'
        )
    return result


def process_rephraser_response(txt):
    """
    Replaced irrelevant chars before sending rephrased query to Retriever.

    Args:
        txt: The query string (potentially a JSON in string format).

    Returns:
        txt: The rephrased query string (potentially hidden in the JSON in string format).
    """
    try:
        eval_txt = clean_json(txt)
        log_debug(f"After cleaning of rephrased query: {eval_txt}")
        if "es_intent" in txt:
            return eval_txt["es_intent"]
        elif "rephrased_query" in txt:
            return eval_txt["rephrased_query"]
        else:
            return eval_txt
    except:
        log_debug(
            f"error: returning text as-is while processing rephrased query: {txt}"
        )
        return txt


def get_relevant_docs(search_query: str, llm: VertexAI) -> List[str]:
    """
    Retrieves relevant documents from Vertex AI Search using the stored retriever.

    Args:
        search_query: The query string (potentially rephrased).
        llm: The initialized Vertex AI LLM instance.

    Returns:
        A list of document contents as strings. Returns empty list if error
        or no retriever is configured.
    """
    retriever = st.session_state.get("vector_store_retriever")
    if not retriever:
        log_debug("No retriever found in session state. Skipping RAG.")
        return []
    if not search_query:
        log_debug("Empty search query received. Skipping RAG.")
        return []

    log_debug(f"Retrieving documents for query: {search_query}")
    log_debug(f"Search query is of type: {type(search_query)}")
    start_time = time.time()

    try:
        # Setup RetrievalQA chain
        retrieval_qa = RetrievalQA.from_chain_type(
            llm=llm,
            chain_type="stuff",  # Simplest chain type
            retriever=retriever,
            return_source_documents=True,
        )

        results = retrieval_qa.invoke(search_query)
        elapsed_time = time.time() - start_time
        log_debug(f"Document retrieval time: {elapsed_time:.1f} seconds")

        documents_content = []
        if results and "source_documents" in results:
            for i, doc in enumerate(results["source_documents"]):
                header = f"{'-'*20} Document {i+1} {'-'*20}\n"
                doc_content = getattr(doc, "page_content", "")
                # Maybe add metadata if useful? e.g., doc.metadata.get('source')
                documents_content.append(header + doc_content)
                # Limit logging of content length
                log_debug(f"Retrieved Doc {i+1}: {len(doc_content)} chars")
                log_debug(f"First 200 chars in doc: {doc_content[:200]}")

        log_debug(f"Retrieved {len(documents_content)} documents.")
        return documents_content

    except Exception as e:
        st.error(f"Error retrieving documents from Vertex AI Search: {e}")
        logging.exception("Error during document retrieval:")
        return []


def judge_responses(
    left_question,
    left_response,
    left_context,
    right_question,
    right_response,
    right_context,
):
    """
    Judges the responses from two models (left and right) using a hardcoded Gemini model.

    Args:

        question (str): The user's question.
        left_response (dict): The response from the left model (including text).
        right_response (dict): The response from the right model (including text).


    Returns:
        str: The judgment from the Gemini model indicating which response is better.
    """
    try:

        # Load the prompt for the judge model
        judge_prompt = f"""Given the following QUESTION and the CONTEXT which is the source of truth to use, judge each model's response:
        
        Here are two responses from different language models:

        Response from model on the left:
        QUESTION:
        {left_question}
        
        CONTEXT:
        {left_context}

        Response A (Model on the Left):
        {left_response['text']}
        
        Response from model on the right:
        QUESTION:
        {right_question}
        
        CONTEXT:
        {right_context}

        Response B (Model on the Right):
        {right_response['text']}

        Which one accurately responds to the question using the source of truth? Make sure your verdict is based on each model's strict adherence to the source of truth.
        """

        # Initialize the Gemini model for judging (from the judge model name constant above)
        client = create_gemini_client()

        ### system instruction for judge model ###
        prompt_folder = "prompts"
        filename = "judge_prompt.txt"
        filepath = os.path.join(prompt_folder, filename)
        si_text1 = load_text_file(filepath)

        generate_content_config = types.GenerateContentConfig(
            temperature=0.5,
            top_p=0.95,
            max_output_tokens=2048,
            response_modalities=["TEXT"],
            system_instruction=[types.Part.from_text(text=si_text1)],
        )

        response = client.models.generate_content_stream(
            model=JUDGE_MODEL_NAME,
            contents=judge_prompt,
            config=generate_content_config,
        )

        st.session_state.judge_name = JUDGE_MODEL_NAME
        log_debug("Judge response: %s " % response)
        return response

    except Exception as e:
        log_debug(f"Error in judge_responses: {e}")
        return f"Error during judgment: {type(e).__name__} - {e}"


##################### MAIN APP BELOW ##################################
# --- Main Application ---
def main(args: argparse.Namespace):  # <-- Pass parsed args to main
    """Runs the main Streamlit application flow."""
    st.set_page_config("Vertex RAG Compare with Dual LLMs", layout="wide")
    st.title("📊 Vertex RAG Compare with 2 LLM's")
    st.caption("Compare LLM responses using Vertex AI Search RAG")

    # --- Initialization ---
    if "app_initialized" not in st.session_state:
        st.session_state.ollama_models, st.session_state.gemini_models = (
            initialize_models()
        )
        st.session_state.chat_history = []
        # Load system prompt only once
        sys_prompt_path = os.path.join(PROMPT_FOLDER, SYSTEM_PROMPT_FILE)
        st.session_state.system_prompt = (
            load_text_file(sys_prompt_path) or ""
        )  # Ensure it's a string
        if not st.session_state.system_prompt:
            st.warning("System prompt file not loaded. Using default behavior.")
        st.session_state.app_initialized = True

    # --- Sidebar Setup ---
    retriever_llm = (
        setup_retriever_sidebar()
    )  # Sets up retriever and returns LLM if successful

    with st.sidebar:
        st.divider()
        use_rag = st.checkbox(
            "🔗 Use Vertex AI Search RAG",
            value=True,  # Default to using RAG if available
            disabled=(retriever_llm is None),  # Disable if retriever setup failed
        )
        if retriever_llm is None and use_rag:
            st.warning("RAG disabled: Vertex AI Search connection not configured.")
            use_rag = False  # Force disable if setup failed

    # --- Response Columns & Model Selection ---
    left_col, right_col = st.columns(2)
    left_config = model_selection(left_col, "left")
    right_config = model_selection(right_col, "right")

    # --- Display Chat History ---
    # Reuse logic to display history in both columns if desired
    # for message in st.session_state.chat_history:
    #     with left_col:
    #         with st.chat_message("user"):
    #             st.write(message["question"])
    #         with st.chat_message("ai"):
    #             st.write(message["left"]["text"]) # Simplified display
    #             # Add more details like time, rephrased q etc. if needed
    #     # Repeat for right_col...

    # --- User Input ---
    user_question = st.chat_input("Ask your question:")

    if user_question:
        # Display user question immediately in both columns
        with left_col, st.chat_message("user"):
            st.write(user_question)
        with right_col, st.chat_message("user"):
            st.write(user_question)

        # --- Step 1: Rephrase Query (Optional but done here) ---
        # Rephrasing is done sequentially here, could be parallelized
        # Rephrasing happens *inside* the generate_rephraser_response function columns
        left_rephrased = generate_rephraser_response(
            left_config, user_question, left_col
        )

        left_rephrased = process_rephraser_response(left_rephrased)

        right_rephrased = generate_rephraser_response(
            right_config, user_question, right_col
        )

        right_rephrased = process_rephraser_response(right_rephrased)

        # --- Step 2: Retrieve Context (Conditional RAG) ---
        left_context, right_context = [], []  # Default to empty context
        rag_active = use_rag and retriever_llm is not None

        if rag_active:
            # Check if left model response indicates RAG skip (e.g., follow-up)
            # This check might be fragile based on exact model output
            left_skip_rag = any(phrase in left_rephrased for phrase in RAG_SKIP_PHRASES)
            if left_skip_rag and st.session_state.chat_history:
                log_debug(
                    "Left model indicates RAG skip, using previous context if available."
                )
                # Decide how to handle context reuse - e.g. use previous answer?
                # left_context = [st.session_state.chat_history[-1]["left"]["text"]] # Example
                left_context = []  # Or simply skip RAG for this turn
                left_final_query = user_question  # Use original query if skipping RAG based on rephrase
            else:
                with left_col:  # Show status in the column
                    with st.spinner("Retrieving context for Left Model..."):
                        left_context = get_relevant_docs(left_rephrased, retriever_llm)
                left_final_query = left_rephrased  # Use rephrased query

            # Repeat for right model
            right_skip_rag = any(
                phrase in right_rephrased for phrase in RAG_SKIP_PHRASES
            )
            if right_skip_rag and st.session_state.chat_history:
                log_debug(
                    "Right model indicates RAG skip, using previous context if available."
                )
                # right_context = [st.session_state.chat_history[-1]["right"]["text"]] # Example
                right_context = []
                right_final_query = user_question
            else:
                with right_col:
                    with st.spinner("Retrieving context for Right Model..."):
                        right_context = get_relevant_docs(
                            right_rephrased, retriever_llm
                        )
                right_final_query = right_rephrased

            # Display retrieved context (optional, can be verbose)
            # with st.expander("Retrieved Context (Left)"):
            #      st.json(left_context if left_context else "None")
            # with st.expander("Retrieved Context (Right)"):
            #      st.json(right_context if right_context else "None")

        else:
            log_debug("RAG is disabled or not configured. Skipping document retrieval.")
            # Use original question if not rephrased, or rephrased if rephrasing always runs
            left_final_query = left_rephrased
            right_final_query = right_rephrased

        # --- Step 3: Generate Final Answer (Summarization) ---
        # Final answer generation happens *inside* generate_summarizer_response columns
        left_response_data = generate_summarizer_response(
            left_config, left_final_query, left_context, left_col
        )
        right_response_data = generate_summarizer_response(
            right_config, right_final_query, right_context, right_col
        )

        # --- Step 4: Update Chat History ---
        st.session_state.chat_history.append(
            {
                "question": user_question,
                "left_query_used": left_final_query,  # Store the query actually used
                "right_query_used": right_final_query,
                "left_context_used": bool(
                    left_context
                ),  # Store if RAG context was provided
                "right_context_used": bool(right_context),
                "left": left_response_data,
                "right": right_response_data,
                "timestamp": time.time(),
            }
        )

        # --- Step 5: Run Judge Model (Conditional) ---
        if args.judge:  # <-- Check the command-line argument flag for judge model
            ## May be wait a couple of seconds to finish streaming?
            time.sleep(1)

            # Generate the Judgment from judge model
            judgement = judge_responses(
                left_final_query,
                left_response_data,
                left_context,
                right_final_query,
                right_response_data,
                right_context,
            )  # function calls that get the judge response!

            # Display Chat history at the initialization, this part should remain before printing chat
            full_response = ""
            with st.container():
                st.subheader("Judge's Analysis")
                st.write(
                    f"*{st.session_state.judge_name} is generating the final answer...*"
                )
                # st.write(left_response)
                for chunk in judgement:
                    full_response += chunk.text
                st.write(full_response)  # add that line to print it to screen!


##################### MAIN APP COMPLETE ##################################
if __name__ == "__main__":
    # --- Argument Parsing ---
    parser = argparse.ArgumentParser(
        description="Vertex AI RAG Comparator with optional Judge Model."
    )
    parser.add_argument(
        "--judge",
        action="store_true",  # Makes it a flag: present=True, absent=False
        help="Enable the Judge Model evaluation after each response pair.",
    )
    args = parser.parse_args()  # Parse arguments from command line

    # --- Run Main App ---
    main(args)  # Pass parsed arguments to the main function
