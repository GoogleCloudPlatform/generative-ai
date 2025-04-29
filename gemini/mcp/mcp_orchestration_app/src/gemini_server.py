"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import logging
import os
import sys

from google import genai
from google.api_core import exceptions as google_exceptions
import google.auth
from google.cloud import translate_v3 as translate
from google.genai import types
from mcp.server.fastmcp import FastMCP
import nest_asyncio

# Apply nest_asyncio
nest_asyncio.apply()

# Configure logging - Set default level to INFO
logging.basicConfig(
    level=logging.ERROR,
    format="%(asctime)s - %(levelname)s [%(name)s] - %(message)s",
)

# --- Suppress Verbose Google API Logs ---
# Set levels for specific noisy loggers
logging.getLogger("google.api_core").setLevel(logging.WARNING)
logging.getLogger("google.auth").setLevel(logging.WARNING)
logging.getLogger("google.generativeai").setLevel(logging.WARNING)
logging.getLogger("google.cloud").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)
logging.getLogger("httpcore").setLevel(logging.WARNING)
logging.getLogger("httpx").setLevel(logging.WARNING)

# --- Configuration ---
GOOGLE_PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
GOOGLE_LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

if not GOOGLE_PROJECT_ID or not GOOGLE_LOCATION:
    logging.error(
        "Environment variables"
        " `GOOGLE_CLOUD_PROJECT` and "
        "`GOOGLE_CLOUD_LOCATION` must be set."
    )
    sys.exit(1)


# --- Initialize Gemini Client ---
try:
    GENAI_CLIENT = genai.Client(
        vertexai=True, project=GOOGLE_PROJECT_ID, location=GOOGLE_LOCATION
    )
    logging.info(
        "Gemini Client initialized for "
        f"project `{GOOGLE_PROJECT_ID}` in "
        f"location `{GOOGLE_LOCATION}`"
    )
except google.auth.exceptions.DefaultCredentialsError as e:
    logging.error(
        "Failed to initialize Gemini Client " f"due to authentication issues: {e}"
    )
    GENAI_CLIENT = None
except google_exceptions.PermissionDenied as e:
    logging.error(
        "Failed to initialize Gemini Client" f" due to permission issues: {e}"
    )
    GENAI_CLIENT = None
except google_exceptions.GoogleAPIError as e:
    logging.error(
        "Failed to initialize Gemini Client " f"due to a Google API error: {e}"
    )
    GENAI_CLIENT = None
except RuntimeError as e:
    logging.error(f"Failed to initialize Gemini Client " f"due to a runtime error: {e}")
    GENAI_CLIENT = None

if GENAI_CLIENT:
    logging.info("GENAI_CLIENT is ready.")
else:
    logging.warning(
        "GENAI_CLIENT could not be initialized. "
        "Further operations depending on it may fail."
    )

# --- Instantiate High-Level MCP Server ---
try:
    mcp_host = FastMCP("gemini-complexity-server")
except NameError:
    logging.error("MCPHost class not available. Cannot create MCP server.")
    sys.exit(1)


# --- Common Gemini API Call Function ---
async def call_gemini_model(model_name: str, prompt: str) -> str:
    """Calls the specified Gemini model using the google-genai library.

    Args:
        model_name: The name of the Gemini model to call.
        prompt: The prompt to send to the model.

    Returns:
        The text response from the Gemini model.

    Raises:
        RuntimeError: If the Gemini client is not initialized or
        if there is an error calling the Gemini API.
    """
    if not GENAI_CLIENT:
        raise RuntimeError("Gemini client not initialized.")

    logging.debug(f"Calling model '{model_name}' for prompt: {prompt[:70]}...")
    contents = [types.Content(role="user", parts=[types.Part(text=prompt)])]

    generate_content_config = types.GenerateContentConfig(
        temperature=0.2,
        top_p=0.8,
        max_output_tokens=1024,
        response_modalities=["TEXT"],
        safety_settings=[
            types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
            types.SafetySetting(
                category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
            ),
            types.SafetySetting(
                category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
            ),
            types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
        ],
    )

    try:
        response = GENAI_CLIENT.models.generate_content(
            model=model_name, contents=contents, config=generate_content_config
        )
        if response:
            return response.text

        logging.warning(f"Model '{model_name}' response candidate has no text parts.")
        return "Error: Model returned a response structure " "without text content."

    except google_exceptions.GoogleAPIError as e:
        logging.error(f"Google API error calling model {model_name}: {e}")
        raise RuntimeError(
            "Gemini API Error " f"({e.message or type(e).__name__})"
        ) from e


def translate_text(
    project_id: str,
    location: str,
    source_language_code: str,
    target_language_code: str,
    source_text: str,
) -> str | None:
    """Translates text using the Google Cloud Translation API.

    Args:
        project_id: The ID of the Google Cloud project.
        location: The location of the project.
        source_language_code: The language code of the source text.
        target_language_code: The language code to translate to.
        source_text: The text to translate.

    Returns:
        The translated text, or None if the translation failed.
    """
    try:
        client = translate.TranslationServiceClient()
        parent = f"projects/{project_id}/locations/{location}"

        response = client.translate_text(
            request={
                "parent": parent,
                "contents": [source_text],
                "mime_type": "text/plain",
                "source_language_code": source_language_code,
                "target_language_code": target_language_code,
            }
        )
        if response.translations:
            return response.translations[0].translated_text

        logging.warning("Warning: No translations found in the response.")
        return None
    # --- More specific and common/critical exceptions first ---
    except google.auth.exceptions.DefaultCredentialsError as e:
        # This is more relevant if client instantiation is inside the try block
        logging.error(
            "Authentication failed: Could not "
            f"find default credentials. Details: {e}"
        )
        return None
    except google_exceptions.Unauthenticated as e:
        logging.error(
            f"Authentication failed for project '{project_id}'. "
            f"Check API key or service account. Details: {e}"
        )
        return None
    except (
        google_exceptions.ServiceUnavailable,
        google_exceptions.DeadlineExceeded,
        google_exceptions.ResourceExhausted,
    ) as e:
        # Grouping errors that might be transient
        # and potentially retryable
        logging.warning(
            f"Translation service temporarily unavailable or "
            f"request timed out for project '{project_id}'. "
            f"Consider retrying. Details: {type(e).__name__}: {e}"
        )
        return None

    # --- Catch-all for other Google API specific errors ---
    except google_exceptions.GoogleAPIError as e:
        # This will catch other errors from the Google API
        # that weren't listed above
        # like NotFound, AlreadyExists, InternalServerError, etc.
        logging.error(
            f"A Google API error occurred during "
            f"translation for project '{project_id}'. "
            f"Error type: {type(e).__name__}. Details: {e}"
        )
        return None


# # --- Tool Definitions using Decorator ---
@mcp_host.tool(
    name="translate_llm",
    description=(
        "Calls this translate_llm tool for requests explicitly asking "
        "for language translation or "
        "meaning clarification of non-English text. "
        "Ensure the text is not offensive or inappropriate."
    ),
)
async def call_translate(text: str, source_language: str, target_language: str) -> str:
    """Executes a prompt using the Translation API.

    Args:
        text: The text to translate.
        source_language: The source language code.
        target_language: The target language code.

    Returns:
        The translated text.
    """
    translated_result = translate_text(
        project_id=GOOGLE_PROJECT_ID,
        location=GOOGLE_LOCATION,
        source_language_code=source_language,
        target_language_code=target_language,
        source_text=text,
    )

    if translated_result:
        return translated_result

    return "\nTranslation failed."


@mcp_host.tool(
    name="gemini_flash_lite_2_0",
    description="Calls the Gemini 2.0 Flash Lite model for poetry prompts.",
)
async def call_gemini_flash_lite(prompt: str) -> str:
    """Executes a prompt using the Gemini Pro model.

    Args:
        prompt: The prompt to send to the model.

    Returns:
        The text response from the Gemini model.
    """
    model_name = "gemini-2.0-flash-lite-001"
    return await call_gemini_model(model_name, prompt)


@mcp_host.tool(
    name="gemini_flash_2_0",
    description=(
        "Calls the Gemini 2.0 Flash Thinking model " "for prompts relating to science."
    ),
)
async def call_gemini_flash(prompt: str) -> str:
    """Executes a prompt using the Gemini Pro model.

    Args:
        prompt: The prompt to send to the model.

    Returns:
        The text response from the Gemini model.
    """
    model_name = "gemini-2.0-flash"
    return await call_gemini_model(model_name, prompt)


@mcp_host.tool(
    name="gemini_pro_2_5",
    description=(
        "Calls the Gemini 2.5 Pro Thinking model for complex prompts, "
        "code prompts, math prompts where thinking is needed."
    ),
)
async def call_gemini_pro(prompt: str) -> str:
    """Executes a prompt using the Gemini 1.5 Pro model.

    Args:
        prompt: The prompt to send to the model.

    Returns:
        The text response from the Gemini model.
    """
    model_name = "gemini-2.5-pro-exp-03-25"
    return await call_gemini_model(model_name, prompt)


# --- Main Execution Function (Now Synchronous) ---
def main() -> None:
    """Sets up and runs the MCP server using the high-level host."""
    if not GENAI_CLIENT:
        logging.error("Cannot start server ")
        return
    if "mcp_host" not in globals():
        logging.error("Cannot start server: ")
        return

    logging.info(f"Starting MCP server '{mcp_host.name}' ")
    mcp_host.run()


if __name__ == "__main__":
    main()
