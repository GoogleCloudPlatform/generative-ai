"""Cloud Function code to process a pdf dropped in GCS"""

import os
from pathlib import Path
import re
import uuid

import functions_framework
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import InternalServerError, RetryError
from google.cloud import documentai  # type: ignore
from google.cloud import pubsub_v1, storage
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_alloydb_pg import AlloyDBEngine, AlloyDBVectorStore, Column
from langchain_google_vertexai import VertexAIEmbeddings


# Source: https://cloud.google.com/document-ai/docs/samples/documentai-batch-process-document#documentai_batch_process_document-python
def batch_process_documents(
    project_id: str,
    location: str,
    processor_id: str,
    gcs_output_uri: str,
    processor_version_id: str | None = None,
    gcs_input_uri: str | None = None,
    input_mime_type: str | None = None,
    gcs_input_prefix: str | None = None,
    field_mask: str | None = None,
    timeout: int = 400,
) -> list[storage.Blob]:
    """Function to batch process documents"""
    # You must set the `api_endpoint` if you use a location other than "us".
    opts = ClientOptions(api_endpoint=f"{location}-documentai.googleapis.com")

    client = documentai.DocumentProcessorServiceClient(client_options=opts)

    if gcs_input_uri:
        # Specify specific GCS URIs to process individual documents
        gcs_document = documentai.GcsDocument(
            gcs_uri=gcs_input_uri, mime_type=input_mime_type
        )
        # Load GCS Input URI into a List of document files
        gcs_documents = documentai.GcsDocuments(documents=[gcs_document])
        input_config = documentai.BatchDocumentsInputConfig(gcs_documents=gcs_documents)
    else:
        # Specify a GCS URI Prefix to process an entire directory
        gcs_prefix = documentai.GcsPrefix(gcs_uri_prefix=gcs_input_prefix)
        input_config = documentai.BatchDocumentsInputConfig(gcs_prefix=gcs_prefix)

    # Cloud Storage URI for the Output Directory
    gcs_output_config = documentai.DocumentOutputConfig.GcsOutputConfig(
        gcs_uri=gcs_output_uri, field_mask=field_mask
    )

    # Where to write results
    output_config = documentai.DocumentOutputConfig(gcs_output_config=gcs_output_config)

    if processor_version_id:
        # The full resource name of the processor version, e.g.:
        # projects/{project_id}/locations/{location}/processors/{processor_id}/processorVersions/{processor_version_id}
        name = client.processor_version_path(
            project_id, location, processor_id, processor_version_id
        )
    else:
        # The full resource name of the processor, e.g.:
        # projects/{project_id}/locations/{location}/processors/{processor_id}
        name = client.processor_path(project_id, location, processor_id)

    request = documentai.BatchProcessRequest(
        name=name,
        input_documents=input_config,
        document_output_config=output_config,
    )

    # BatchProcess returns a Long Running Operation (LRO)
    operation = client.batch_process_documents(request)

    # Continually polls the operation until it is complete.
    # This could take some time for larger files
    # Format: projects/{project_id}/locations/{location}/operations/{operation_id}
    try:
        print(f"Waiting for operation {operation.operation.name} to complete...")
        operation.result(timeout=timeout)
    # Catch exception when operation doesn't finish before timeout
    except (RetryError, InternalServerError) as e:
        print(e.message)

    # Once the operation is complete,
    # get output document information from operation metadata
    metadata = documentai.BatchProcessMetadata(operation.metadata)

    if metadata.state != documentai.BatchProcessMetadata.State.SUCCEEDED:
        raise ValueError(f"Batch Process Failed: {metadata.state_message}")

    storage_client = storage.Client()

    # One process per Input Document
    for process in list(metadata.individual_process_statuses):
        # output_gcs_destination format: gs://BUCKET/PREFIX/OPERATION_NUMBER/INPUT_FILE_NUMBER/
        # The Cloud Storage API requires the bucket name and URI prefix separately
        matches = re.match(r"gs://(.*?)/(.*)", process.output_gcs_destination)
        if not matches:
            print(
                "Could not parse output GCS destination:",
                process.output_gcs_destination,
            )
            continue

        output_bucket, output_prefix = matches.groups()

        # Get List of Document Objects from the Output Bucket
        output_blobs = storage_client.list_blobs(output_bucket, prefix=output_prefix)

    return list(output_blobs)


def split_document(_doc):
    """Splits a LangChain Document into smaller chunks."""
    # Use a recursive splitter for better semantic chunking
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=9216,
        chunk_overlap=200,  # Add overlap for context
    )

    new_docs = []
    for page in _doc:
        # Create smaller documents
        new_chunks = splitter.create_documents([page.page_content], [page.metadata])

        # Reconstruct documents with the same metadata
        for i in range(len(new_chunks)):
            new_chunks[i].metadata["page_chunk"] = i
            new_chunks[i].metadata["chunk_size"] = len(new_chunks[i].page_content)
            new_docs.append(
                Document(
                    page_content=new_chunks[i].page_content,
                    metadata=new_chunks[i].metadata,
                )
            )

    return new_docs


# Triggered by a change in a storage bucket
@functions_framework.cloud_event
def process_pdf(cloud_event):
    """Main function"""
    data = cloud_event.data

    event_id = cloud_event["id"]
    event_type = cloud_event["type"]

    bucket = data["bucket"]
    name = data["name"]
    metageneration = data["metageneration"]
    timeCreated = data["timeCreated"]
    updated = data["updated"]

    print(f"Event ID: {event_id}")
    print(f"Event type: {event_type}")
    print(f"Bucket: {bucket}")
    print(f"File: {name}")
    print(f"Metageneration: {metageneration}")
    print(f"Created: {timeCreated}")
    print(f"Updated: {updated}")

    file_name, extension = os.path.splitext(name)
    if extension != ".pdf":
        print("File is not a PDF. Please submit a PDF for processing instead.")
        return

    # Project vars
    region = os.environ["REGION"]
    project_id = os.environ["PROJECT_ID"]

    # Document AI Vars
    source_file = f"gs://{bucket}/{name}"
    gcs_output_uri = f"gs://{project_id}-doc-ai/doc-ai-output/"  # Must end with a trailing slash `/`. Format: gs://bucket/directory/subdirectory/
    location = "us"  # Format is "us" or "eu"
    processor_id = os.environ["PROCESSOR_ID"]  # Create processor before running sample

    blobs = batch_process_documents(
        project_id=project_id,
        location=location,
        processor_id=processor_id,
        gcs_output_uri=gcs_output_uri,
        gcs_input_uri=source_file,  # Format: gs://bucket/directory/file.pdf
        input_mime_type="application/pdf",
    )

    # Document AI may output multiple JSON files per source file
    lc_doc = []
    for blob in blobs:
        # Document AI should only output JSON files to GCS
        if blob.content_type != "application/json":
            print(
                f"Skipping non-supported file: {blob.name} - Mimetype: {blob.content_type}"
            )
            continue

        # Download JSON File as bytes object and convert to Document Object
        print(f"Fetching {blob.name}")
        document = documentai.Document.from_json(
            blob.download_as_bytes(), ignore_unknown_fields=True
        )

        # Create LangChain doc
        page = Document(
            page_content=document.text,
            metadata={
                "source": source_file,
                "page": document.shard_info.shard_index + 1,
                "ticker": Path(source_file).stem,
                "page_size": len(document.text),
                "doc_ai_shard_count": document.shard_info.shard_count,
                "doc_ai_shard_index": document.shard_info.shard_index,
                "doc_ai_chunk_size": blob._CHUNK_SIZE_MULTIPLE,
                "doc_ai_chunk_uri": blob.public_url,
            },
        )
        lc_doc.append(page)

    # Split docs into smaller chunks (max 3072 tokens, 9216 characters)
    lc_doc_chunks = split_document(lc_doc)

    # Setup embeddings
    embedding = VertexAIEmbeddings(
        model_name="textembedding-gecko@003", project=project_id
    )

    # AlloyDB Vars
    cluster = "alloydb-cluster"
    instance = "alloydb-instance"
    database = "ragdemos"
    table_name = "langchain_vector_store"
    user = "postgres"
    password = os.environ["ALLOYDB_PASSWORD"]
    initialize_vector_store = False
    ip_type = os.environ["IP_TYPE"]

    # Create vector store
    engine = AlloyDBEngine.from_instance(
        project_id=project_id,
        region=region,
        cluster=cluster,
        instance=instance,
        database=database,
        user=user,
        password=password,
        ip_type=ip_type,
    )

    if initialize_vector_store:
        engine.init_vectorstore_table(
            table_name=table_name,
            vector_size=768,  # Vector size for VertexAI model(textembedding-gecko@latest)
            metadata_columns=[
                Column("source", "VARCHAR", nullable=True),
                Column("page", "INTEGER", nullable=True),
                Column("ticker", "VARCHAR", nullable=True),
                Column("page_size", "INTEGER", nullable=True),
                Column("doc_ai_shard_count", "INTEGER", nullable=True),
                Column("doc_ai_shard_index", "INTEGER", nullable=True),
                Column("doc_ai_chunk_size", "INTEGER", nullable=True),
                Column("doc_ai_chunk_uri", "VARCHAR", nullable=True),
                Column("page_chunk", "INTEGER", nullable=True),
                Column("chunk_size", "INTEGER", nullable=True),
            ],
            overwrite_existing=True,
        )

    store = AlloyDBVectorStore.create_sync(
        engine=engine,
        table_name=table_name,
        embedding_service=embedding,
        metadata_columns=[
            "source",
            "page",
            "ticker",
            "page_size",
            "doc_ai_shard_count",
            "doc_ai_shard_index",
            "doc_ai_chunk_size",
            "doc_ai_chunk_uri",
            "page_chunk",
            "chunk_size",
        ],
    )

    ids = [str(uuid.uuid4()) for i in range(len(lc_doc_chunks))]
    store.add_documents(lc_doc_chunks, ids)

    print("Finished processing pdf")

    # Send message to pubsub topic to kick off next step
    ticker = Path(source_file).stem
    publisher = pubsub_v1.PublisherClient()
    topic_name = f"projects/{project_id}/topics/{project_id}-doc-ready"
    future = publisher.publish(topic_name, bytes(f"{ticker}".encode()), spam="done")
    future.result()
    print("Sent message to pubsub")
