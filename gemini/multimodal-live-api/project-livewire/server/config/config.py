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

"""
Configuration for Vertex AI Gemini Multimodal Live Proxy Server
"""

import logging
import os
from typing import Optional

from dotenv import load_dotenv
from google.cloud import secretmanager

logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()


class ConfigurationError(Exception):
    """Custom exception for configuration errors."""


def get_secret(secret_id: str) -> str:
    """Get secret from Secret Manager."""
    client = secretmanager.SecretManagerServiceClient()
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")

    if not project_id:
        raise ConfigurationError("GOOGLE_CLOUD_PROJECT environment variable is not set")

    name = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    try:
        response = client.access_secret_version(request={"name": name})
        return response.payload.data.decode("UTF-8")
    except Exception:
        raise


class ApiConfig:
    """API configuration handler."""

    def __init__(self):
        # Determine if using Vertex AI
        self.use_vertex = (
            os.getenv("GOOGLE_GENAI_USE_VERTEXAI", "false").lower() == "true"
        )

        self.api_key: Optional[str] = None

        logger.info(f"Initialized API configuration with Vertex AI: {self.use_vertex}")

    async def initialize(self):
        """Initialize API credentials."""
        try:
            # Always try to get OpenWeather API key regardless of endpoint
            self.weather_api_key = get_secret("OPENWEATHER_API_KEY")
        except Exception as e:
            logger.warning(
                f"Failed to get OpenWeather API key from Secret Manager: {e}"
            )
            self.weather_api_key = os.getenv("OPENWEATHER_API_KEY")
            if not self.weather_api_key:
                raise ConfigurationError("OpenWeather API key not available")

        if not self.use_vertex:
            try:
                self.api_key = get_secret("GOOGLE_API_KEY")
            except Exception as e:
                logger.warning(f"Failed to get API key from Secret Manager: {e}")
                self.api_key = os.getenv("GOOGLE_API_KEY")
                if not self.api_key:
                    raise ConfigurationError(
                        "No API key available from Secret Manager or environment"
                    )


# Initialize API configuration
api_config = ApiConfig()

# Model configuration
if api_config.use_vertex:
    MODEL = os.getenv("MODEL_GOOGLE_GENAI_USE_VERTEXAI", "gemini-2.0-flash-exp")
    VOICE = os.getenv("VOICE_GOOGLE_GENAI_USE_VERTEXAI", "Aoede")
else:
    MODEL = os.getenv("MODEL_DEV_API", "models/gemini-2.0-flash-exp")
    VOICE = os.getenv("VOICE_DEV_API", "Puck")

# Cloud Function URLs with validation
CLOUD_FUNCTIONS = {
    "get_weather": os.getenv("WEATHER_FUNCTION_URL"),
    "get_weather_forecast": os.getenv("FORECAST_FUNCTION_URL"),
    "get_next_appointment": os.getenv("CALENDAR_FUNCTION_URL"),
    "get_past_appointments": os.getenv("PAST_APPOINTMENTS_FUNCTION_URL"),
}

# Validate Cloud Function URLs
for name, url in CLOUD_FUNCTIONS.items():
    if not url:
        logger.warning(f"Missing URL for cloud function: {name}")
    elif not url.startswith("https://"):
        logger.warning(f"Invalid URL format for {name}: {url}")

# Load system instructions
try:
    with open("config/system-instructions.txt", "r") as f:
        SYSTEM_INSTRUCTIONS = f.read()
except Exception as e:
    logger.error(f"Failed to load system instructions: {e}")
    SYSTEM_INSTRUCTIONS = ""

logger.info(f"System instructions: {SYSTEM_INSTRUCTIONS}")

# Gemini Configuration
CONFIG = {
    "generation_config": {"response_modalities": ["AUDIO"], "speech_config": VOICE},
    "tools": [
        {
            "function_declarations": [
                {
                    "name": "get_weather",
                    "description": "Get weather information for a location",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "city": {
                                "type": "string",
                                "description": "The city or location to get weather for",
                            }
                        },
                        "required": ["city"],
                    },
                },
            ]
        }
    ],
    "system_instruction": SYSTEM_INSTRUCTIONS,
}
