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


"""
A Python script to manage the RAG (Retrieval Augmented Generation) corpus for
Vertex AI Search.

This script helps in creating datastores, engines, and importing data from GCS
into Vertex AI Search for use with RAG applications.
"""

import sys
import time

from pathlib import Path

import typer
import vertexai

from google.api_core import exceptions
from google.cloud import discoveryengine_v1 as discoveryengine
from rich.console import Console
from vertexai.preview import rag

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common import get_credentials

from backend.app_settings import ApplicationSettings, get_application_settings

console = Console()
app = typer.Typer()
settings: ApplicationSettings = get_application_settings()


def _update_env_file(key: str, value: str):
    """Updates or appends a key-value pair in taskfile.env."""
    env_file = Path("taskfile.env")
    content = ""
    if env_file.exists():
        content = env_file.read_text()

    lines = [line for line in content.splitlines() if not line.startswith(f"{key}=")]
    lines.append(f"{key}={value}")

    env_file.write_text("\n".join(lines) + "\n")
    console.log(f"Updated taskfile.env with {key}={value}")


def _fetch_discovery_engine_document_service_client():
    credentials = get_credentials()
    client = discoveryengine.DocumentServiceClient(
        credentials=credentials,
    )
    return client


def _fetch_discovery_engine_client():
    credentials = get_credentials()
    client = discoveryengine.EngineServiceClient(
        credentials=credentials,
    )
    return client


def _fetch_discovery_engine_datastore_service_client():
    credentials = get_credentials()
    client = discoveryengine.DataStoreServiceClient(
        credentials=credentials,
    )
    return client


def _datastore_exists(client: discoveryengine.DataStoreServiceClient, parent: str) -> bool:
    """Check if a datastore exists."""
    datastore_path = client.data_store_path(
        project=settings.google_cloud.project_id,
        location=settings.search.datastore_settings.location,
        data_store=settings.search.datastore_settings.id,
    )
    try:
        client.get_data_store(name=datastore_path)
        console.log(f"Datastore '{settings.search.datastore_settings.id}' already exists.")
        return True
    except exceptions.NotFound:
        console.log("Datastore not found. Proceeding with creation.")
        return False


def create_vertex_ai_search_datastore(client: discoveryengine.DataStoreServiceClient, parent: str):
    if _datastore_exists(client=client, parent=parent):
        return

    data_store = discoveryengine.DataStore(
        display_name=settings.search.datastore_settings.display_name,
        industry_vertical=settings.search.datastore_settings.industry_vertical,
        solution_types=[settings.search.datastore_settings.solution_type],
        content_config=settings.search.datastore_settings.content_config,
    )
    request = discoveryengine.CreateDataStoreRequest(
        parent=parent, data_store=data_store, data_store_id=settings.search.datastore_settings.id
    )

    with console.status("[bold green]Waiting for operation to complete..."):
        operation = client.create_data_store(request=request)

    console.log(f"Operation: {operation.operation} complete.")
    response = operation.result(timeout=2700)
    console.log(f"Successfully created datastore: {response}")


def attach_gcs_source_to_datastore(client: discoveryengine.DocumentServiceClient, parent: str):
    console.log(f"Parent: {parent}")
    bucket_name = settings.google_cloud.docs_bucket_name

    # Import JSON files
    gcs_source_json = discoveryengine.GcsSource(
        input_uris=[f"gs://{bucket_name}/crawled_data/*.json"],
        data_schema="content",
    )
    console.log(f"gcs source for JSON: {gcs_source_json}")
    request_json = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=gcs_source_json,
        auto_generate_ids=False,
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    with console.status("[bold green]Waiting for JSON import operation to complete..."):
        # JSON import might fail if no files exist, so we wrap it in try-except or just let it log error
        try:
            operation_json = client.import_documents(request=request_json)
            console.log(f"JSON import operation: {operation_json.operation} complete.")
            response_json = operation_json.result(timeout=2700)
            console.log(f"Successfully imported JSON documents: {response_json}")
        except Exception as e:
            console.log(f"[yellow]JSON import skipped or failed (might be empty): {e}[/yellow]")

    # Import PDF files
    gcs_source_pdf = discoveryengine.GcsSource(
        input_uris=[f"gs://{bucket_name}/*.pdf"],
        data_schema="content",
    )
    console.log(f"gcs source for PDF: {gcs_source_pdf}")
    request_pdf = discoveryengine.ImportDocumentsRequest(
        parent=parent,
        gcs_source=gcs_source_pdf,
        reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    with console.status("[bold green]Waiting for PDF import operation to complete..."):
        operation_pdf = client.import_documents(request=request_pdf)

    console.log(f"PDF import operation: {operation_pdf.operation} complete.")
    response_pdf = operation_pdf.result(timeout=2700)
    console.log(f"Successfully imported PDF documents: {response_pdf}")


def _engine_exists(client: discoveryengine.EngineServiceClient, parent: str) -> bool:
    """Check if an engine exists."""
    engine_path = client.engine_path(
        project=settings.google_cloud.project_id,
        location=settings.search.engine_settings.location,
        collection=settings.search.engine_settings.collection_id,
        engine=settings.search.engine_settings.id,
    )
    try:
        client.get_engine(name=engine_path)
        console.log(f"Engine '{engine_path}' already exists.")
        return True
    except exceptions.NotFound:
        console.log("Engine not found. Proceeding with creation.")
        return False


def create_vertex_ai_search_engine(client: discoveryengine.EngineServiceClient, parent: str):
    """_summary_

    SOLUTION_TYPE_CHAT (3):
        Used for use cases related to the Generative AI agent.
    SOLUTION_TYPE_GENERATIVE_CHAT (4):
        Used for use cases related to the Generative Chat agent.
        It's used for Generative chat engine only, the associated
        data stores must enrolled with ``SOLUTION_TYPE_CHAT``
        solution.

    Args:
        client (discoveryengine.EngineServiceClient): _description_
        parent (str): _description_
    """
    if _engine_exists(client=client, parent=parent):
        return

    engine = discoveryengine.Engine(
        search_engine_config=settings.search.engine_settings.search_engine_config,
        name=f"projects/{settings.google_cloud.project_id}/locations/{settings.search.engine_settings.location}/collections/{settings.search.engine_settings.collection_id}/engines/{settings.search.engine_settings.id}",
        display_name=settings.search.engine_settings.display_name,
        data_store_ids=[settings.search.datastore_settings.id],
        solution_type=settings.search.engine_settings.solution_type,
    )
    request = discoveryengine.CreateEngineRequest(
        parent=parent, engine=engine, engine_id=settings.search.engine_settings.id
    )

    with console.status("[bold green]Waiting for operation to complete..."):
        operation = client.create_engine(request=request)

    console.log(f"Operation: {operation.operation} complete.")
    response = operation.result(timeout=2700)
    console.log(f"Successfully created engine: {response}")


def _initialize_vertex_ai():
    credentials = get_credentials()
    vertexai.init(
        project=settings.google_cloud.project_id,
        location=settings.search.alternative_region,
        credentials=credentials,
    )


def _corpus_exists():
    """Checks if a RAG corpus exists."""
    existing_corpora = rag.list_corpora()
    corpus_exists = False
    for existing_corpus in existing_corpora:
        if existing_corpus.display_name == settings.search.display_name:
            corpus_exists = True
            console.log(f"Found existing corpus with display name '{settings.search.display_name}'")
    return corpus_exists


def create_rag_corpus():
    _initialize_vertex_ai()
    existing_corpora = rag.list_corpora()
    for existing_corpus in existing_corpora:
        if existing_corpus.display_name == settings.search.display_name:
            console.log(f"Found existing corpus with display name '{settings.search.display_name}'")
            return existing_corpus.name

    console.log(f"Corpus '{settings.search.display_name}' not found. Proceeding with creation.")
    vertex_ai_search_engine_name = f"projects/{settings.google_cloud.project_id}/locations/{settings.search.engine_settings.location}/collections/{settings.search.engine_settings.collection_id}/engines/{settings.search.engine_settings.id}"
    vertex_ai_search_config = rag.VertexAiSearchConfig(
        serving_config=f"{vertex_ai_search_engine_name}/servingConfigs/default_search",
    )
    with console.status("[bold green]Waiting for operation to complete..."):
        corpus = rag.create_corpus(
            display_name=settings.search.display_name,
            description=settings.search.description,
            vertex_ai_search_config=vertex_ai_search_config,
        )
    return corpus.name


@app.command()
def create(
    project_id: str = typer.Option(
        default=None,
        help="Google Cloud project ID (required, e.g., 'your-google-cloud-project-id').",
    ),
    location: str = typer.Option(
        default=settings.search.datastore_settings.location,
        help="Datastore and engine ocation.",
    ),
    data_store: str = typer.Option(
        default=settings.search.datastore_settings.id,
        help="ID of the VAiS datastore.",
    ),
    branch: str = typer.Option(
        default=settings.search.datastore_settings.branch,
        help="Branch of the VAiS datastore.",
    ),
    collection: str = typer.Option(
        default=settings.search.engine_settings.collection_id,
        help="ID of the VAiS collection.",
    ),
    engine: str = typer.Option(
        default=settings.search.engine_settings.id,
        help="ID of the VAiS engine.",
    ),
):
    # Ensure global settings use the project_id provided via CLI
    if project_id:
        settings.google_cloud.project_id = project_id

    # Dynamic ID Generation
    timestamp = int(time.time())

    if not settings.search.datastore_settings.id:
        new_ds_id = f"financial-advisor-ds-{timestamp}"
        console.log(f"No Datastore ID found. Generated new ID: {new_ds_id}")
        settings.search.datastore_settings.id = new_ds_id
        _update_env_file("VAIS_RAG_SETTINGS__DATASTORE_SETTINGS__ID", new_ds_id)

    if not settings.search.engine_settings.id:
        new_engine_id = f"financial-advisor-engine-{timestamp}"
        console.log(f"No Engine ID found. Generated new ID: {new_engine_id}")
        settings.search.engine_settings.id = new_engine_id
        # We don't necessarily need to save Engine ID to env if it's derivative, but good for consistency
        _update_env_file("VAIS_RAG_SETTINGS__ENGINE_SETTINGS__ID", new_engine_id)

    document_service_client = _fetch_discovery_engine_document_service_client()
    engine_service_client = _fetch_discovery_engine_client()
    datastore_service_client = _fetch_discovery_engine_datastore_service_client()
    datastore_parent = datastore_service_client.collection_path(
        project=settings.google_cloud.project_id,
        location=settings.search.datastore_settings.location,
        collection=settings.search.datastore_settings.collection_id,
    )
    datastore_branch_parent = document_service_client.branch_path(
        project=settings.google_cloud.project_id,
        location=settings.search.datastore_settings.location,
        data_store=settings.search.datastore_settings.id,
        branch=settings.search.datastore_settings.branch,
    )
    engine_parent = engine_service_client.collection_path(
        project=settings.google_cloud.project_id,
        location=settings.search.engine_settings.location,
        collection=settings.search.engine_settings.collection_id,
    )

    create_vertex_ai_search_datastore(client=datastore_service_client, parent=datastore_parent)
    console.log("Completed creating VAiS Datastore")
    attach_gcs_source_to_datastore(client=document_service_client, parent=datastore_branch_parent)
    console.log("Completed importing GCS dataset.")
    create_vertex_ai_search_engine(client=engine_service_client, parent=engine_parent)
    console.log("Completed creating VAiS Engine")

    corpus_name = create_rag_corpus()
    if corpus_name:
        _update_env_file("VAIS_RAG_SETTINGS__RAG_CORPORA_ID", corpus_name)
    else:
        console.log("[red]Error: Failed to retrieve or create RAG Corpus ID. taskfile.env was not updated.[/red]")
        raise typer.Exit(code=1)


@app.command()
def destroy(
    project_id: str = typer.Option(
        default=None,
        help="Google Cloud project ID.",
    ),
):
    """Destroys the RAG Corpus, Vertex AI Search Engine, and Datastore."""
    if project_id:
        settings.google_cloud.project_id = project_id

    _initialize_vertex_ai()

    # 1. Delete RAG Corpus
    existing_corpora = rag.list_corpora()
    for corpus in existing_corpora:
        if corpus.display_name == settings.search.display_name:
            console.log(f"Deleting RAG Corpus: {corpus.name}")
            try:
                rag.delete_corpus(name=corpus.name)
                console.log("RAG Corpus deleted.")
            except Exception as e:
                console.log(f"[red]Failed to delete RAG Corpus: {e}[/red]")

    # 2. Delete Engine
    engine_client = _fetch_discovery_engine_client()
    engine_parent = engine_client.collection_path(
        project=settings.google_cloud.project_id,
        location=settings.search.engine_settings.location,
        collection=settings.search.engine_settings.collection_id,
    )

    engine_deleted = False
    for engine in engine_client.list_engines(parent=engine_parent):
        if engine.display_name == settings.search.engine_settings.display_name:
            console.log(f"🚀 Starting deletion for Engine: {engine.name}")
            try:
                operation = engine_client.delete_engine(name=engine.name)
                console.log(f"   ⏳ Delete Engine operation initiated: {operation.operation.name}")
                operation.result(timeout=2700)
                console.log(f"   ✅ Successfully deleted Engine: {engine.display_name}")
                engine_deleted = True
            except exceptions.NotFound:
                console.log(f"   ⚠️  Engine {engine.display_name} not found (already deleted?).")
            except Exception as e:
                console.log(f"   ❌ Error deleting Engine: {e}")

    if not engine_deleted:
        console.log(
            f"   ⚠️  No engine with display name '{settings.search.engine_settings.display_name}' found to delete."
        )

    # Optional: Short sleep to ensure backend consistency
    time.sleep(2)

    # 3. Delete Datastore
    console.log(f"\n🗑️  Starting deletion for Data Store: {settings.search.datastore_settings.id}")
    datastore_client = _fetch_discovery_engine_datastore_service_client()
    datastore_path = datastore_client.data_store_path(
        project=settings.google_cloud.project_id,
        location=settings.search.datastore_settings.location,
        data_store=settings.search.datastore_settings.id,
    )
    try:
        operation = datastore_client.delete_data_store(name=datastore_path)
        console.log(f"   ⏳ Delete Data Store operation initiated: {operation.operation.name}")
        operation.result(timeout=2700)
        console.log(f"   ✅ Successfully deleted Data Store: {settings.search.datastore_settings.id}")
    except exceptions.NotFound:
        console.log(f"   ⚠️  Data Store {settings.search.datastore_settings.id} not found.")
    except exceptions.FailedPrecondition as e:
        console.log(f"   ❌ Failed Precondition (is it still linked to an active App?): {e}")
    except Exception as e:
        console.log(f"   ❌ Error deleting Data Store: {e}")

    # 4. Clean up env file
    console.log("\n🧹 Cleaning up taskfile.env...")
    _update_env_file("VAIS_RAG_SETTINGS__DATASTORE_SETTINGS__ID", "")
    _update_env_file("VAIS_RAG_SETTINGS__ENGINE_SETTINGS__ID", "")
    _update_env_file("VAIS_RAG_SETTINGS__RAG_CORPORA_ID", "")


@app.command()
def get_id(
    project_id: str = typer.Option(
        default=None,
        help="Google Cloud project ID.",
    ),
):
    """
    Prints the RAG Corpus ID to stdout if it exists.
    Useful for command line substitution: `export ID=$(python script.py get-id)`
    """
    if project_id:
        settings.google_cloud.project_id = project_id

    _initialize_vertex_ai()

    existing_corpora = rag.list_corpora()
    for corpus in existing_corpora:
        if corpus.display_name == settings.search.display_name:
            # Print ONLY the ID to stdout so it can be captured
            print(corpus.name)
            return

    # If we are here, we didn't find it.
    # We print nothing (or a placeholder if strictness isn't required) to stdout
    # and log to stderr
    console.log(f"[yellow]No corpus found with name '{settings.search.display_name}'[/yellow]")


if __name__ == "__main__":
    app()
