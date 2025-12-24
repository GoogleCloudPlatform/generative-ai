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


import vertexai
from vertexai.preview import rag

from backend.app_logging import get_logger

from backend.app_settings import ApplicationSettings, get_application_settings

settings: ApplicationSettings = get_application_settings()
logger = get_logger(__name__)


def _initialize_vertex_ai():
    """Initializes Vertex AI with ADC."""
    if not settings.google_cloud.project_id:
        logger.error("Cannot initialize Vertex AI: Project ID is None.")
        return

    vertexai.init(
        project=settings.google_cloud.project_id,
        location=settings.search.alternative_region,
    )


def _corpus_exists():
    """Checks if a RAG corpus exists and returns its resource name."""
    _initialize_vertex_ai()

    if not settings.google_cloud.project_id:
        logger.error("Cannot check RAG corpus existence: Project ID is None.")
        return None

    try:
        # Use the display name from settings
        expected_display_name = settings.search.display_name
        logger.info(f"Listing RAG corpora to find '{expected_display_name}'...")
        for corpus in rag.list_corpora():
            if corpus.display_name == expected_display_name:
                logger.info(f"Found existing RAG Corpus: {corpus.name}")
                return corpus.name
        logger.warning(f"RAG Corpus with display name '{expected_display_name}' not found.")
        return None
    except Exception as e:
        logger.error(f"Error listing RAG corpora: {e}", exc_info=True)
        return None
