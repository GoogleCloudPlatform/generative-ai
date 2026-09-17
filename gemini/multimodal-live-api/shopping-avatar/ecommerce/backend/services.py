# Copyright 2026 Google LLC
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
from google import genai
from auth import AuthService
from database import SpannerDatabase
from config import settings

# Initialize AuthService
auth_svc = AuthService()

# Load configurations
SPANNER_INSTANCE = settings.spanner_instance
SPANNER_DATABASE = settings.spanner_database
VERTEX_PROJECT_ID = settings.vertex_project_id or auth_svc.project_id
VERTEX_LOCATION = settings.vertex_location
GEMINI_LIVE_MODEL = settings.gemini_live_model
MULTIMODAL_EMBEDDING_MODEL = settings.multimodal_embedding_model
MULTIMODAL_EMBEDDING_LOCATION = settings.multimodal_embedding_location

# Initialize Clients
db = SpannerDatabase(SPANNER_INSTANCE, SPANNER_DATABASE, VERTEX_PROJECT_ID)

# Set standard Google GenAI SDK environment variables for Vertex AI mode
if "GOOGLE_CLOUD_PROJECT" not in os.environ and VERTEX_PROJECT_ID:
    os.environ["GOOGLE_CLOUD_PROJECT"] = VERTEX_PROJECT_ID
if "GOOGLE_CLOUD_LOCATION" not in os.environ and VERTEX_LOCATION:
    os.environ["GOOGLE_CLOUD_LOCATION"] = VERTEX_LOCATION

def get_ai_client():
    return genai.Client(vertexai=True, project=VERTEX_PROJECT_ID, location=VERTEX_LOCATION)

def get_embedding_client():
    return genai.Client(vertexai=True, project=VERTEX_PROJECT_ID, location=MULTIMODAL_EMBEDDING_LOCATION)

ai_client = get_ai_client()
