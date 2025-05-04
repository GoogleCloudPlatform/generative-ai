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

"""Service layer for retrieving available AI models.

This module provides the ModelService class, which lists both standard
Google AI models (like Gemini variants) and custom models deployed
within the user's Google Cloud project via Vertex AI Platform.
"""

from google.cloud.aiplatform import Model

GOOGLE_AI_MODELS = [
    "gemini-1.5-flash",
    "gemini-1.5-flash-8b",
    "gemini-1.5-pro",
    "gemini-1.0-pro",
]


class ModelService:
    """Provides functionality to list available AI models."""

    def get_all(self):
        """Retrieves a list of available AI models, categorized by source.

        Fetches custom models deployed on Vertex AI Platform and combines them
        with a predefined list of standard Google AI models.

        Returns:
            A list of dictionaries, where each dictionary represents a model
            category ("Gemini" or "Custom") and contains a list of model names
            under the "models" key.
            Example:
            [
                {"name": "Gemini", "models": ["gemini-1.5-pro", ...]},
                {"name": "Custom", "models": ["my-custom-model-1", ...]}
            ]

        Raises:
            google.api_core.exceptions.GoogleAPICallError: If there's an issue
                communicating with the Vertex AI API to list custom models.
        """
        custom_models = Model.list()
        return [
            {
                "name": "Gemini",
                "models": GOOGLE_AI_MODELS,
            },
            {
                "name": "Custom",
                "models": [cm.display_name for cm in custom_models],
            },
        ]
