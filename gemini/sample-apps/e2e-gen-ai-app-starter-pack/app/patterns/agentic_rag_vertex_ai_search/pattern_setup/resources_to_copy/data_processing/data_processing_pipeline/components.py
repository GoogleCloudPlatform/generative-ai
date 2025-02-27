# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=C0415,R0917,R0913,R0914

from typing import Optional

from kfp.dsl import Dataset, Input, Output, component


@component(
    packages_to_install=[
        "langchain",
        "langchain-community",
        "vertexai",
        "langchain-google-vertexai",
        "pypdf",
        "pydantic==2.9.2",
    ]
)
def process_data(
    output_files: Output[Dataset],
    embedding_model: str,
    pdf_url: str,
) -> None:
    """Processes PDF document by splitting into chunks and generating embeddings."""
    import json
    import logging
    from typing import List
    import uuid

    from langchain.text_splitter import RecursiveCharacterTextSplitter
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_core.documents import Document
    from langchain_core.embeddings import Embeddings
    from langchain_google_vertexai import VertexAIEmbeddings
    import vertexai

    vertexai.init()
    embedding = VertexAIEmbeddings(model_name=embedding_model)

    def pre_process_data(url: str) -> List[Document]:
        """Load and split documents from a given URL."""
        loader = PyPDFLoader(url)
        documents = loader.load()

        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, chunk_overlap=200
        )
        doc_splits = text_splitter.split_documents(documents)
        for document in doc_splits:
            document.metadata["title"] = pdf_url
            document.metadata["id"] = str(uuid.uuid4())

        return doc_splits

    def add_embeddings(docs: List[Document], embedding: Embeddings) -> List[Document]:
        """Adds embeddings to a list of documents using the provided embedding model."""
        embeddings = embedding.embed_documents(
            [
                f"{document.metadata['title']}\n{document.page_content}"
                for document in docs
            ]
        )

        documents_with_embeddings = []

        for index, current_document in enumerate(docs):
            current_document.metadata["embedding"] = embeddings[index]
            documents_with_embeddings.append(current_document)

        return documents_with_embeddings

    def convert_docs_to_jsonl(docs: List[Document], file_path: str) -> None:
        """Converts an array of documents to a jsonl file and stores it in GCS.

        Args:
            docs: An array of documents, where each document is a dictionary.
        """
        with open(file_path, "w") as f:
            for doc in docs:
                json_data = doc.metadata
                json_data["content"] = doc.page_content
                dictionary = {
                    "id": doc.metadata["id"],
                    "json_data": json.dumps(json_data),
                }
                f.write(json.dumps(dictionary) + "\n")

    logging.info("Starting document pre-processing...")
    docs = pre_process_data(pdf_url)
    logging.info(f"Pre-processed {len(docs)} document chunks")

    logging.info("Generating embeddings...")
    docs = add_embeddings(docs, embedding)
    logging.info("Embeddings generated successfully")

    logging.info("Converting documents to JSONL format...")
    output_files.path = output_files.path + ".json"
    convert_docs_to_jsonl(docs, output_files.path)
    logging.info("JSONL conversion complete")


@component(
    packages_to_install=[
        "google-cloud-discoveryengine",
    ],
)
def ingest_data_in_datastore(
    project_id: str,
    region_vertex_ai_search: str,
    input_files: Input[Dataset],
    data_store_id: str,
    embedding_dimension: int = 768,
    embedding_column: str = "embedding",
) -> None:
    """Process and ingest documents into Vertex AI Search datastore.

    Args:
        project_id: Google Cloud project ID
        region_vertex_ai_search: Region for Vertex AI Search
        input_files: Input dataset containing documents
        data_store_id: ID of target datastore
        embedding_column: Name of embedding column in schema
    """
    import json
    import logging

    from google.api_core.client_options import ClientOptions
    from google.cloud import discoveryengine

    def update_schema_as_json(
        original_schema: str,
        embedding_dimension: int,
        field_name: Optional[str] = None,
    ) -> str:
        """Update datastore schema JSON to include embedding field.

        Args:
            original_schema: Original schema JSON string
            field_name: Name of embedding field to add

        Returns:
            Updated schema JSON string
        """
        original_schema_dict = json.loads(original_schema)

        if original_schema_dict.get("properties") is None:
            original_schema_dict["properties"] = {}

        if field_name:
            field_schema = {
                "type": "array",
                "keyPropertyMapping": "embedding_vector",
                "dimension": embedding_dimension,
                "items": {"type": "number"},
            }
            original_schema_dict["properties"][field_name] = field_schema

        return json.dumps(original_schema_dict)

    def update_data_store_schema(
        project_id: str,
        location: str,
        data_store_id: str,
        field_name: Optional[str] = None,
        client_options: Optional[ClientOptions] = None,
    ) -> None:
        """Update datastore schema to include embedding field.

        Args:
            project_id: Google Cloud project ID
            location: Google Cloud location
            data_store_id: Target datastore ID
            embedding_column: Name of embedding column
            client_options: Client options for API
        """
        schema_client = discoveryengine.SchemaServiceClient(
            client_options=client_options
        )
        collection = "default_collection"

        name = f"projects/{project_id}/locations/{location}/collections/{collection}/dataStores/{data_store_id}/schemas/default_schema"

        schema = schema_client.get_schema(
            request=discoveryengine.GetSchemaRequest(name=name)
        )
        new_schema_json = update_schema_as_json(
            original_schema=schema.json_schema,
            embedding_dimension=embedding_dimension,
            field_name=field_name,
        )
        new_schema = discoveryengine.Schema(json_schema=new_schema_json, name=name)

        operation = schema_client.update_schema(
            request=discoveryengine.UpdateSchemaRequest(
                schema=new_schema, allow_missing=True
            )
        )
        logging.info(f"Waiting for schema update operation: {operation.operation.name}")
        operation.result()

    def add_data_in_store(
        project_id: str,
        location: str,
        data_store_id: str,
        input_files_uri: str,
        client_options: Optional[ClientOptions] = None,
    ) -> None:
        """Import documents into datastore.

        Args:
            project_id: Google Cloud project ID
            location: Google Cloud location
            data_store_id: Target datastore ID
            input_files_uri: URI of input files
            client_options: Client options for API
        """
        client = discoveryengine.DocumentServiceClient(client_options=client_options)

        parent = client.branch_path(
            project=project_id,
            location=location,
            data_store=data_store_id,
            branch="default_branch",
        )

        request = discoveryengine.ImportDocumentsRequest(
            parent=parent,
            gcs_source=discoveryengine.GcsSource(
                input_uris=[input_files_uri],
                data_schema="document",
            ),
            reconciliation_mode=discoveryengine.ImportDocumentsRequest.ReconciliationMode.FULL,
        )

        operation = client.import_documents(request=request)
        logging.info(f"Waiting for import operation: {operation.operation.name}")
        operation.result()

    client_options = ClientOptions(
        api_endpoint=f"{region_vertex_ai_search}-discoveryengine.googleapis.com"
    )

    logging.info("Updating data store schema...")
    update_data_store_schema(
        project_id=project_id,
        location=region_vertex_ai_search,
        data_store_id=data_store_id,
        field_name=embedding_column,
        client_options=client_options,
    )
    logging.info("Schema updated successfully")

    logging.info("Importing data into store...")
    add_data_in_store(
        project_id=project_id,
        location=region_vertex_ai_search,
        data_store_id=data_store_id,
        client_options=client_options,
        input_files_uri=input_files.uri,
    )
    logging.info("Data import completed")
