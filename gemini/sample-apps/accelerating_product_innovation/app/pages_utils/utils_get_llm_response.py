"""
This module provides functions for interacting with Vertex AI text generation model (Gemini-Pro).

* generate_gemini():
    * Utilizes the Gemini-Pro model for flexible text generation.
    * Supports customization of generation parameters.
    * Incorporates safety settings.

* parallel_generate_search_results():
    * Employs asynchronous requests to Gemini for search result generation.
    * Handles potential errors during communication with the model.
"""

import json
import logging
import os

import aiohttp
from dotenv import load_dotenv
import streamlit as st
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
    safety_setting = generative_models.HarmBlockThreshold.BLOCK_NONE
    try:
        responses = model.generate_content(
            text_prompt,
            generation_config={
                "max_output_tokens": 8192,
                "temperature": 0.001,
                "top_p": 1,
            },
            safety_settings={
                generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: safety_setting,
                generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: safety_setting,
                generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: safety_setting,
                generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: safety_setting,
            },
            stream=True,
        )
        final_response = ""
        for response in responses:
            final_response += response.text
        logging.debug(final_response)
        return final_response
    except Exception as e:
        st.error(f"An error occurred: {str(e)}")
        st.stop()


async def parallel_generate_search_results(query: str) -> str:
    """Generates search results using the Text-Bison model in a parallel fashion.

    Args:
        query: The query to generate search results for.

    Returns:
        The generated search results.
    """
    data = {"text_prompt": query}
    data_json = json.dumps(data)
    logging.debug("Text call start")
    headers = {"Content-Type": "application/json"}
    async with aiohttp.ClientSession() as session:
        url = f"https://us-central1-{PROJECT_ID}.cloudfunctions.net/gemini-call"
        async with session.post(
            url, data=data_json, headers=headers, verify_ssl=False
        ) as response:
            logging.debug("Inside IF else of session")
            if response.status == 200:
                response = await response.json()
                response = response["generated_text"]
                return response
            else:
                print(
                    "Request failed:",
                    response.status,
                    await response.text(),
                )
