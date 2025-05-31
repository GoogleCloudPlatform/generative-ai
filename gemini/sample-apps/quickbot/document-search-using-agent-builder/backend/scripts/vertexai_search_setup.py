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

from google.cloud import discoveryengine_v1 as discoveryengine
from google.api_core.exceptions import AlreadyExists, NotFound

def create_vertex_ai_datastore(
    project_id: str,
    location: str,
    datastore_id: str,
    datastore_display_name: str,
):
    """Creates a Vertex AI Search Datastore if it doesn't exist."""
    client = discoveryengine.DataStoreServiceClient()
    parent = client.collection_path(project_id, location, "default_collection")
    datastore_name_full = client.data_store_path(project_id, location, datastore_id)

    try:
        ds = client.get_data_store(name=datastore_name_full)
        print(f"Datastore '{datastore_id}' already exists in location '{location}': {ds.name}")
        return ds
    except NotFound:
        print(f"Datastore '{datastore_id}' not found in location '{location}'. Attempting to create...")

    datastore = discoveryengine.DataStore(
        display_name=datastore_display_name,
        industry_vertical=discoveryengine.IndustryVertical.GENERIC,
        content_config=discoveryengine.DataStore.ContentConfig.CONTENT_REQUIRED,
    )

    try:
        operation = client.create_data_store(
            parent=parent,
            data_store=datastore,
            data_store_id=datastore_id,
        )
        print(f"Waiting for Datastore '{datastore_id}' creation (LRO: {operation.operation.name})...")
        created_datastore = operation.result(timeout=300) # 5 minutes timeout
        print(f"Successfully created Datastore: {created_datastore.name}")
        return created_datastore
    except AlreadyExists:
        print(f"Datastore '{datastore_id}' creation reported AlreadyExists. Fetching existing.")
        return client.get_data_store(name=datastore_name_full)
    except Exception as e:
        print(f"Error creating Datastore '{datastore_id}': {e}")
        raise

def import_documents_to_datastore(
    project_id: str,
    location: str,
    datastore_id: str,
    gcs_uri: str,
):
    """Imports documents from GCS into the specified Datastore."""
    client = discoveryengine.DocumentServiceClient()
    parent_branch = client.branch_path(
        project=project_id,
        location=location,
        data_store=datastore_id,
        branch="default_branch",
    )

    request = discoveryengine.ImportDocumentsRequest(
        parent=parent_branch,
        gcs_source=discoveryengine.GcsSource(input_uris=[gcs_uri], data_schema="content"),
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL
    )

    try:
        print(f"Starting document import from '{gcs_uri}' into Datastore '{datastore_id}'...")
        operation = client.import_documents(request=request)
        print(f"Waiting for document import to complete (LRO: {operation.operation.name}). This may take several minutes...")
        response = operation.result(timeout=1800) # 30 minutes timeout

        if response.error_samples and len(response.error_samples) > 0:
            print(f"Document import completed with errors. Error Config {response.error_config}")
            for i, error_sample in enumerate(response.error_samples):
                print(f"  Error sample {i+1}: {error_sample.message}")
            raise Exception("Document import failed with errors", response)
        else:
            print(f"Successfully imported documents.")
        return response
    except Exception as e:
        print(f"Error during document import for Datastore '{datastore_id}': {e}")
        raise

def create_vertex_ai_engine(
    project_id: str,
    location: str,
    engine_id: str,
    engine_display_name: str,
    datastore_ids_list: list[str],
):
    """Creates a Vertex AI Search Engine (App) if it doesn't exist."""
    client = discoveryengine.EngineServiceClient()
    parent_collection = client.collection_path(project_id, location, "default_collection")
    engine_name_full = client.engine_path(project_id, location, "default_collection", engine_id)

    try:
        eng = client.get_engine(name=engine_name_full)
        print(f"Engine '{engine_id}' already exists in location '{location}': {eng.name}")
        return eng
    except NotFound:
        print(f"Engine '{engine_id}' not found in location '{location}'. Attempting to create...")

    engine_config = discoveryengine.Engine(
        display_name=engine_display_name,
        solution_type=discoveryengine.SolutionType.SOLUTION_TYPE_SEARCH,
        data_store_ids=datastore_ids_list,
        common_config=discoveryengine.Engine.CommonConfig(company_name="QuickBot App"),
        search_engine_config=discoveryengine.Engine.SearchEngineConfig(
            search_tier="SEARCH_TIER_STANDARD",
            search_add_ons=["SEARCH_ADD_ON_LLM"]
        )
    )

    try:
        operation = client.create_engine(
            parent=parent_collection,
            engine=engine_config,
            engine_id=engine_id,
        )
        print(f"Waiting for Engine '{engine_id}' creation (LRO: {operation.operation.name})...")
        created_engine = operation.result(timeout=600) # 10 minutes timeout
        print(f"Successfully created Engine: {created_engine.name}")
        return created_engine
    except AlreadyExists:
        print(f"Engine '{engine_id}' creation reported AlreadyExists. Fetching existing.")
        return client.get_engine(name=engine_name_full)
    except Exception as e:
        print(f"Error creating Engine '{engine_id}': {e}")
        raise