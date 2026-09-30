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
import logging
from pydantic import BaseModel

logger = logging.getLogger("config")

def load_dotenv(dotenv_path: str = ".env"):
    script_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths = [
        os.path.join(script_dir, dotenv_path),
        os.path.join(script_dir, "DataGenerator", dotenv_path),
        dotenv_path
    ]
    for path in possible_paths:
        if os.path.exists(path):
            logger.info(f"Loading environment configuration from: {path}")
            with open(path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line and not line.startswith("#"):
                        parts = line.split("=", 1)
                        if len(parts) == 2:
                            os.environ[parts[0].strip()] = parts[1].strip().strip('"').strip("'")
            break

# Pre-load dot-env values to populate os.environ before instantiating settings
load_dotenv()

class Settings(BaseModel):
    google_genai_use_vertexai: bool = True
    vertex_project_id: str = os.getenv("VERTEX_PROJECT_ID", "")
    vertex_location: str = os.getenv("VERTEX_LOCATION", "global")
    google_cloud_project: str = os.getenv("GOOGLE_CLOUD_PROJECT", "")
    google_cloud_location: str = os.getenv("GOOGLE_CLOUD_LOCATION", "global")
    spanner_instance: str = os.getenv("SPANNER_INSTANCE", "ecommerce-instance")
    spanner_database: str = os.getenv("SPANNER_DATABASE", "catalog-db")
    gemini_live_model: str = os.getenv("GEMINI_LIVE_MODEL", "gemini-3.5-live-preview")
    multimodal_embedding_model: str = os.getenv("MULTIMODAL_EMBEDDING_MODEL", "gemini-embedding-2")
    multimodal_embedding_location: str = os.getenv("MULTIMODAL_EMBEDDING_LOCATION", "global")
    gcs_bucket_name: str = os.getenv("GCS_BUCKET_NAME", "gen-ai-4all-live-retail-images")
    image_generation_model: str = os.getenv("IMAGE_GENERATION_MODEL", "gemini-2.5-flash-image")
    vqa_model: str = os.getenv("VQA_MODEL", "gemini-2.5-flash")
    spanner_location: str = os.getenv("SPANNER_LOCATION", "us-central1")
    retailer: str = os.getenv("RETAILER", "Retail")

settings = Settings()
