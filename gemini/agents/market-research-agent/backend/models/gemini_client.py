import asyncio
import json
import logging
import os
from typing import Any, Dict, List, Optional, Union

import google.generativeai as genai
from google.api_core.exceptions import GoogleAPIError
from google.generativeai.types import HarmBlockThreshold, HarmCategory

from config.settings import GEMINI_API_KEY, LLM_CONFIG

from .llm_interface import LLMInterface

logger = logging.getLogger(__name__)


class GeminiClient(LLMInterface):
    """Client for interacting with Google's Gemini model."""

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        """Initialize the Gemini client.

        Args:
            api_key: The API key for Gemini. If not provided, uses the one from settings.
            model: The model to use. If not provided, uses the one from settings.
        """
        self.api_key = api_key or GEMINI_API_KEY
        if not self.api_key:
            raise ValueError("Gemini API key is required")

        self.model_name = model or LLM_CONFIG["model"]
        self.temperature = LLM_CONFIG["temperature"]
        self.max_tokens = LLM_CONFIG["max_tokens"]
        self.top_p = LLM_CONFIG["top_p"]
        self.top_k = LLM_CONFIG["top_k"]

        # Configure the Gemini API
        genai.configure(api_key=self.api_key)

        # Set default safety settings
        self.safety_settings = {
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        }

        # Initialize the model
        try:
            self.model = genai.GenerativeModel(
                model_name=self.model_name,
                safety_settings=self.safety_settings,
                generation_config={
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "top_k": self.top_k,
                    "max_output_tokens": self.max_tokens,
                },
            )
            logger.info(f"Initialized Gemini model: {self.model_name}")
        except Exception as e:
            logger.error(f"Error initializing Gemini model: {e}")
            raise

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate text based on prompt.

        Args:
            prompt: The user prompt.
            system_prompt: Optional system prompt to guide the model's behavior.
            temperature: Optional temperature parameter for generation.
            max_tokens: Optional maximum tokens parameter for generation.

        Returns:
            Generated text response.
        """
        generation_config = {
            "temperature": temperature if temperature is not None else self.temperature,
            "max_output_tokens": (
                max_tokens if max_tokens is not None else self.max_tokens
            ),
            "top_p": self.top_p,
            "top_k": self.top_k,
        }

        try:
            # Create message content
            if system_prompt:
                messages = [
                    {"role": "user", "parts": [{"text": system_prompt}]},
                    {
                        "role": "model",
                        "parts": [{"text": "I'll follow these instructions."}],
                    },
                    {"role": "user", "parts": [{"text": prompt}]},
                ]
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    messages,
                    generation_config=generation_config,
                )
            else:
                response = await asyncio.to_thread(
                    self.model.generate_content,
                    prompt,
                    generation_config=generation_config,
                )

            # Extract the response text
            return response.text

        except GoogleAPIError as e:
            logger.error(f"Google API error during generation: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during Gemini generation: {e}")
            raise

    async def generate_with_json_output(
        self,
        prompt: str,
        json_schema: Dict[str, Any],
        system_prompt: Optional[str] = None,
        temperature: Optional[float] = None,
    ) -> Dict[str, Any]:
        """Generate structured JSON output based on prompt and schema.

        Args:
            prompt: The user prompt.
            json_schema: The JSON schema defining the expected output structure.
            system_prompt: Optional system prompt to guide the model's behavior.
            temperature: Optional temperature parameter for generation.

        Returns:
            Generated structured JSON response.
        """
        schema_str = json.dumps(json_schema, indent=2)
        structured_prompt = f"""
{prompt}

You must respond with a JSON object that conforms to the following schema:
{schema_str}

Ensure that your response is properly formatted JSON that strictly follows this schema.
"""

        try:
            response_text = await self.generate(
                prompt=structured_prompt,
                system_prompt=system_prompt,
                temperature=temperature,
            )

            # Extract JSON from response
            try:
                # Find JSON content in the response
                json_start = response_text.find("{")
                json_end = response_text.rfind("}")

                if json_start != -1 and json_end != -1:
                    json_content = response_text[json_start : json_end + 1]
                    return json.loads(json_content)

                # Try to parse the entire response as JSON
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from response: {e}")
                logger.debug(f"Response text: {response_text}")
                # Attempt to fix common JSON issues
                return self._fix_and_parse_json(response_text)

        except Exception as e:
            logger.error(f"Error in generate_with_json_output: {e}")
            raise

    async def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: Optional[float] = None,
        max_tokens: Optional[int] = None,
    ) -> str:
        """Generate a response based on a conversation history.

        Args:
            messages: List of message dictionaries with 'role' and 'content' keys.
            temperature: Optional temperature parameter for generation.
            max_tokens: Optional maximum tokens parameter for generation.

        Returns:
            Generated response text.
        """
        generation_config = {
            "temperature": temperature if temperature is not None else self.temperature,
            "max_output_tokens": (
                max_tokens if max_tokens is not None else self.max_tokens
            ),
            "top_p": self.top_p,
            "top_k": self.top_k,
        }

        try:
            # Convert messages to Gemini format
            gemini_messages = []
            for msg in messages:
                role = "user" if msg["role"] == "user" else "model"
                gemini_messages.append(
                    {"role": role, "parts": [{"text": msg["content"]}]}
                )

            # Generate response
            response = await asyncio.to_thread(
                self.model.generate_content,
                gemini_messages,
                generation_config=generation_config,
            )

            return response.text

        except GoogleAPIError as e:
            logger.error(f"Google API error during chat: {e}")
            raise
        except Exception as e:
            logger.error(f"Error during Gemini chat: {e}")
            raise

    def _fix_and_parse_json(self, text: str) -> Dict[str, Any]:
        """Attempt to fix and parse JSON from a potentially malformed string."""
        # Common JSON issues to fix
        try:
            # Try to extract JSON block with code block markers
            import re

            json_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text)
            if json_match:
                return json.loads(json_match.group(1))

            # Try to extract anything between { and } (last occurrence)
            json_start = text.find("{")
            json_end = text.rfind("}")
            if json_start != -1 and json_end != -1:
                return json.loads(text[json_start : json_end + 1])

            # If all else fails, return empty dict
            return {}
        except Exception as e:
            logger.error(f"Failed to fix and parse JSON: {e}")
            return {}
