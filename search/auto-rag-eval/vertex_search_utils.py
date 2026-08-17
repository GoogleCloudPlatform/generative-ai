from dataclasses import dataclass  # noqa: INP001
from typing import Any

from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPIError
from google.cloud import discoveryengine_v1 as discoveryengine
from google.cloud import discoveryengine_v1alpha

MAX_NUM_CHUNKS = 5


@dataclass(frozen=True)
class DataStoreConfig:
    """Coordinates identifying a Discovery Engine data store."""

    project_id: str
    location: str
    data_store_id: str


class DataStoreError(Exception):
    """Raised when a data store operation fails."""


def list_documents_in_datastore(
    config: DataStoreConfig,
) -> list[dict[str, str]]:
    """List all documents in a Vertex AI Agent Platform data store."""
    client_options = ClientOptions(api_endpoint="discoveryengine.googleapis.com")
    client = discoveryengine.DocumentServiceClient(client_options=client_options)

    parent = client.branch_path(
        project=config.project_id,
        location=config.location,
        data_store=config.data_store_id,
        branch="default_branch",
    )

    documents = []
    try:
        response = client.list_documents(parent=parent)
        for document in response:
            doc_info = {"id": document.id, "name": document.name, "metadata": {}}
            if hasattr(document, "struct_data") and document.struct_data:
                doc_info["metadata"] = document.struct_data
            documents.append(doc_info)
    except GoogleAPIError as e:
        raise DataStoreError(f"Failed to list documents: {e}") from e
    else:
        return documents


def search_with_chunk_augmentation(
    query: str,
    config: DataStoreConfig,
    top_n: int = 5,
    num_chunks: int = 1,
) -> list[dict[str, Any]]:
    """Search the data store and return results with augmented chunks."""
    num_chunks = min(max(num_chunks, 0), MAX_NUM_CHUNKS)

    client_options = ClientOptions(api_endpoint="discoveryengine.googleapis.com")
    client = discoveryengine.SearchServiceClient(client_options=client_options)

    serving_config = client.serving_config_path(
        project=config.project_id,
        location=config.location,
        data_store=config.data_store_id,
        serving_config="default_search",
    )

    content_search_spec = discoveryengine.SearchRequest.ContentSearchSpec(
        search_result_mode=discoveryengine.SearchRequest.ContentSearchSpec.SearchResultMode.CHUNKS,
        chunk_spec=discoveryengine.SearchRequest.ContentSearchSpec.ChunkSpec(
            num_previous_chunks=num_chunks, num_next_chunks=num_chunks
        ),
    )

    request = discoveryengine.SearchRequest(
        serving_config=serving_config,
        query=query,
        page_size=top_n,
        content_search_spec=content_search_spec,
    )

    try:
        response = client.search(request)
        results = []
        for i, result in enumerate(response.results):
            result_data = {
                "rank": i + 1,
                "document_metadata": {},
                "page_span": {},
                "chunks": [],
                "augmented_content": "",
            }

            if hasattr(result, "chunk") and result.chunk:
                chunk = result.chunk
                if hasattr(chunk, "document_metadata"):
                    result_data["document_metadata"] = {
                        "uri": getattr(chunk.document_metadata, "uri", None),
                        "title": getattr(chunk.document_metadata, "title", None),
                    }
                if hasattr(chunk, "page_span"):
                    result_data["page_span"] = {
                        "start": getattr(chunk.page_span, "page_start", None),
                        "end": getattr(chunk.page_span, "page_end", None),
                    }

                all_chunk_content = []
                if hasattr(chunk.chunk_metadata, "previous_chunks"):
                    for prev_chunk in chunk.chunk_metadata.previous_chunks:
                        result_data["chunks"].append(
                            {
                                "type": "previous",
                                "id": prev_chunk.id,
                                "content": prev_chunk.content,
                            }
                        )
                        all_chunk_content.append(prev_chunk.content)

                result_data["chunks"].append(
                    {"type": "relevant", "id": chunk.id, "content": chunk.content}
                )
                all_chunk_content.append(chunk.content)

                if hasattr(chunk.chunk_metadata, "next_chunks"):
                    for next_chunk in chunk.chunk_metadata.next_chunks:
                        result_data["chunks"].append(
                            {
                                "type": "next",
                                "id": next_chunk.id,
                                "content": next_chunk.content,
                            }
                        )
                        all_chunk_content.append(next_chunk.content)

                result_data["augmented_content"] = " ".join(all_chunk_content)
            results.append(result_data)
    except GoogleAPIError as e:
        raise DataStoreError(f"Search failed: {e}") from e
    else:
        return results


def list_chunks_for_document(
    document_id: str,
    config: DataStoreConfig,
) -> list[dict[str, Any]]:
    """List all chunks for a specific document in the data store."""
    client_options = ClientOptions(api_endpoint="discoveryengine.googleapis.com")
    try:
        client = discoveryengine_v1alpha.ChunkServiceClient(
            client_options=client_options
        )

        parent = client.document_path(
            project=config.project_id,
            location=config.location,
            data_store=config.data_store_id,
            branch="default_branch",
            document=document_id,
        )

        chunks = []
        page_result = client.list_chunks(parent=parent)
        for chunk in page_result:
            chunk_data = {
                "id": chunk.id,
                "name": chunk.name,
                "content": chunk.content,
                "page_span": {
                    "start": getattr(chunk.page_span, "page_start", None)
                    if hasattr(chunk, "page_span")
                    else None,
                    "end": getattr(chunk.page_span, "page_end", None)
                    if hasattr(chunk, "page_span")
                    else None,
                },
            }
            chunks.append(chunk_data)
    except GoogleAPIError as e:
        print(f"Error listing chunks for document {document_id}: {e}")
        # Fallback to search-based approach could be implemented here if needed
        return []
    else:
        return chunks


def merge_chunks_into_bigger_chunks(
    chunks: list[dict[str, Any]], merge_count: int = 3
) -> list[dict[str, Any]]:
    """Merge consecutive chunks into bigger chunks."""
    if not chunks:
        return []

    bigger_chunks = []
    for i in range(0, len(chunks), merge_count):
        chunk_slice = chunks[i : i + merge_count]
        merged_content = " ".join([chunk["content"] for chunk in chunk_slice])

        bigger_chunk = {
            "content": merged_content,
            "chunk_ids": [chunk["id"] for chunk in chunk_slice],
            "chunk_count": len(chunk_slice),
            "start_index": i,
            "end_index": min(i + merge_count - 1, len(chunks) - 1),
        }

        if (
            "page_span" in chunk_slice[0]
            and chunk_slice[0]["page_span"]["start"] is not None
        ):
            bigger_chunk["page_span"] = {
                "start": chunk_slice[0]["page_span"]["start"],
                "end": chunk_slice[-1]["page_span"]["end"],
            }
        bigger_chunks.append(bigger_chunk)
    return bigger_chunks
