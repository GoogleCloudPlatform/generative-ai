"""
This module provides functions for interacting with Vertex AI text generation
model (Gemini-Pro).

* generate_gemini():
    * Utilizes the Gemini-Pro model for flexible text generation.
    * Supports customization of generation parameters.
    * Incorporates safety settings.

* parallel_generate_search_results():
    * Employs asynchronous requests to Gemini for search result generation.
    * Handles potential errors during communication with the model.
"""

# pylint: disable=E0401

import json
import logging
import os

import aiohttp
from dotenv import load_dotenv
import vertexai
from vertexai import generative_models

load_dotenv()


PROJECT_ID = os.getenv("PROJECT_ID")
LOCATION = os.getenv("LOCATION")

vertexai.init(project=PROJECT_ID, location=LOCATION)
logging.basicConfig(format="%(levelname)s:%(message)s", level=logging.DEBUG)


def generate_gemini(text_prompt: str) -> str:
    """Generates text using the Gemini-Pro model.

    Args:
        text_prompt: The text prompt to generate from.

    Returns:
        The generated text.
    """
    model = generative_models.GenerativeModel("gemini-pro")

    safety_config = [
        generative_models.SafetySetting(
            category=generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
            threshold=generative_models.HarmBlockThreshold.BLOCK_NONE,
        ),
        generative_models.SafetySetting(
            category=generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT,
            threshold=generative_models.HarmBlockThreshold.BLOCK_NONE,
        ),
        generative_models.SafetySetting(
            category=generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
            threshold=generative_models.HarmBlockThreshold.BLOCK_NONE,
        ),
        generative_models.SafetySetting(
            category=generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH,
            threshold=generative_models.HarmBlockThreshold.BLOCK_NONE,
        ),
    ]

    generation_config = generative_models.GenerationConfig(
        max_output_tokens=8192,
        temperature=0.001,
        top_p=1,
    )

    response = model.generate_content(
        text_prompt,
        generation_config=generation_config,
        safety_settings=safety_config,
    )
    logging.debug(response.text)
    return response.text


async def parallel_generate_search_results(query: str) -> str:
    """Generates search results using the Text-Bison model in a parallel
       fashion.

    Args:
        query: The query to generate search results for.

    Returns:
        The generated search results.
    """
    data_json = json.dumps({"text_prompt": query})
    logging.debug("Text call start")
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        url = f"https://us-central1-{PROJECT_ID}.cloudfunctions.net/gemini-call"
        # Create post request to get text.
        async with session.post(
            url, data=data_json, headers=headers, verify_ssl=False
        ) as response:
            if response.status == 200:
                # If response is valid, return generated text.
                response = await response.json()
                response = response["generated_text"]
                return response
            return ""
