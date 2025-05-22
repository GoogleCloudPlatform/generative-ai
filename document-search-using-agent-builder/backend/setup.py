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
Initializes the BigQuery and Vertex AI Search environment for the application.

This script performs the following actions:
1. Retrieves configuration from environment variables or uses defaults.
2. Creates the specified BigQuery dataset if it doesn't already exist.
3. Creates the 'search_applications' table within that dataset.
4. Creates a Vertex AI Search Datastore if it doesn't already exist.
5. Imports documents from a specified GCS bucket into the Datastore.
6. Creates a Vertex AI Search Engine (App) linked to the Datastore.

Usage:
    Run this script directly (e.g., `python setup.py`).
    Set environment variables to override defaults:
    - 'BIG_QUERY_DATASET'
    - 'GOOGLE_CLOUD_PROJECT'
    - 'VERTEX_AI_SEARCH_LOCATION'
    - 'VERTEX_AI_DATASTORE_ID'
    - 'VERTEX_AI_ENGINE_ID'
"""

from os import getenv
from scripts.big_query_setup import create_dataset, create_table
from src.service.search_application import SEARCH_APPLICATION_TABLE
from src.model.search import SearchApplication
from scripts.vertexai_search_setup import create_vertex_ai_datastore, create_vertex_ai_engine, import_documents_to_datastore


def main():
    # 1. BigQuery Setup
    print("--- Setting up BigQuery ---")
    BIG_QUERY_DATASET = getenv("BIG_QUERY_DATASET", "quickbot_default_bq_dataset")
    GCLOUD_PROJECT = getenv("GCLOUD_PROJECT", "my-gcloud-project")
    create_dataset(BIG_QUERY_DATASET)
    create_table(
        BIG_QUERY_DATASET, SEARCH_APPLICATION_TABLE, SearchApplication.__schema__()
    )

    # 2. Vertex AI Search Setup
    print("--- Setting up Vertex AI Search ---")
    VERTEX_AI_LOCATION = getenv("VERTEX_AI_LOCATION", "global")
    VERTEX_AI_DATASTORE_ID = getenv("VERTEX_AI_DATASTORE_ID", "quickbot_alphabet_pdfs_ds")
    VERTEX_AI_ENGINE_ID = getenv("VERTEX_AI_ENGINE_ID", "quickbot_alphabet_search_engine")
    GCS_SOURCE_URI = "gs://cloud-samples-data/gen-app-builder/search/alphabet-investor-pdfs/*.pdf"
    DATASTORE_DISPLAY_NAME_PREFIX = "Alphabet Investor Docs DS"
    ENGINE_DISPLAY_NAME_PREFIX = "Alphabet Investor Engine"

    datastore_display_name = f"{DATASTORE_DISPLAY_NAME_PREFIX} ({VERTEX_AI_DATASTORE_ID})"
    engine_display_name = f"{ENGINE_DISPLAY_NAME_PREFIX} ({VERTEX_AI_ENGINE_ID})"
    try:
        # Create/Get Datastore
        print(f"Attempting to create/get Datastore '{VERTEX_AI_DATASTORE_ID}' in project '{GCLOUD_PROJECT}' location '{VERTEX_AI_LOCATION}'...")
        datastore = create_vertex_ai_datastore(
            GCLOUD_PROJECT, VERTEX_AI_LOCATION, VERTEX_AI_DATASTORE_ID, datastore_display_name
        )
        if not datastore:
            print("Datastore creation/retrieval failed. Aborting further Vertex AI Search setup.")
            print("--- Application setup finished (with errors) ---")
            raise
        print(f"Successfully ensured Datastore exists: {datastore.name}")

        # Import documents into Datastore
        # Note: This will attempt to import documents every time the script runs.
        # For production, you might want to add a check to skip this if documents
        # are already present or if a previous import was successful.
        print(f"\nAttempting to import documents from '{GCS_SOURCE_URI}' into datastore: {datastore.name}")
        import_documents_to_datastore(
            GCLOUD_PROJECT, VERTEX_AI_LOCATION, VERTEX_AI_DATASTORE_ID, GCS_SOURCE_URI
        )
        # Note: Document import can take a long time. The script waits.
        print("Document import process initiated/completed.\n")

        # Create/Get Engine
        print(f"Attempting to create/get Engine '{VERTEX_AI_ENGINE_ID}' in project '{GCLOUD_PROJECT}' location '{VERTEX_AI_LOCATION}'...")
        # The create_vertex_ai_engine function expects a list of datastore IDs (not full resource names).
        engine = create_vertex_ai_engine(
            GCLOUD_PROJECT,
            VERTEX_AI_LOCATION,
            VERTEX_AI_ENGINE_ID,
            engine_display_name,
            [VERTEX_AI_DATASTORE_ID] # Pass the Datastore ID string
        )

        if not engine:
            print("Engine creation/retrieval failed.")
            print("--- Application setup finished (with errors) ---")
            raise
        print(f"Successfully ensured Engine exists: {engine.name}")

        print("\nVertex AI Search setup completed successfully.")

    except Exception as e:
        print(f"A critical error occurred during the setup process: {e}")
        import traceback
        print("Detailed traceback:")
        print(traceback.format_exc())
        # If running in Docker build, exiting with non-zero will fail the build
        import sys
        sys.exit(1)

    print("\n--- Application setup finished ---")
    print("\nSuccess! All resources should now be configured.\n")


if __name__ == "__main__":
    main()