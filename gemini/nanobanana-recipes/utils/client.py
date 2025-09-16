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

import os

from dotenv import load_dotenv
from google import genai

load_dotenv()


def get_gemini_client():
    """Initializes and returns the GenAI client, loading project and location
    from a .env file or environment variables.
    """
    project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")

    if not project_id:
        raise ValueError(
            "The GOOGLE_CLOUD_PROJECT environment variable must be set. Please create a .env file from the .env.example."
        )

    return genai.Client(
        vertexai=True,
        project=project_id,
        location=location,
    )
