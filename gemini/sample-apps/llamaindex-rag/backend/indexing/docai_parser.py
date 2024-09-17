import json
import logging
import time
import traceback

from google.api_core.client_options import ClientOptions
from google.cloud import documentai, storage
from google.cloud.storage import Blob
from llama_index.core import Document

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DocAIParser:
    """
    Class for interfacing with DocAIParser
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        processor_name: str,
        gcs_output_path: str,
    ):
        self.project_id = project_id
        self.location = location
        self.processor_name = processor_name
        self.gcs_output_path = gcs_output_path
        self._client = self._initialize_client()

    def _initialize_client(self):
        options = ClientOptions(
            api_endpoint=f"{self.location}-documentai.googleapis.com"
        )
        return documentai.DocumentProcessorServiceClient(client_options=options)

    def batch_parse(
        self,
        blobs: list[Blob],
        chunk_size: int = 500,
        include_ancestor_headings: bool = True,
        timeout_sec: int = 3600,
        check_in_interval_sec: int = 60,
    ) -> tuple[list[Document], list["DocAIParsingResults"]]:  # noqa: F821
        """
        Parses a list of blobs using Document AI.

        Args:
            blobs: List of GCS Blobs to parse.
            chunk_size: Chunk size for Document AI processing.
            include_ancestor_headings: Whether to include ancestor headings.
            timeout_sec: Timeout in seconds for the operation.
            check_in_interval_sec: Check-in interval in seconds.

        Returns:
            A tuple containing a list of parsed documents and a list of
            DocAIParsingResults.
        """
        try:
            operations = self._start_batch_process(
                blobs, chunk_size, include_ancestor_headings
            )
            print(f"Number of operations started: {len(operations)}")
            self._wait_for_operations(operations, timeout_sec, check_in_interval_sec)
            print("Operations completed successfully")

            for i, operation in enumerate(operations):
                print(f"Operation {i + 1} metadata: {operation.metadata}")

            results = self._get_results(operations)
            print(f"Number of results: {len(results)}")
            parsed_docs = self._parse_from_results(results)
            print(f"Number of parsed documents: {len(parsed_docs)}")
            return parsed_docs, results
        except Exception as e:
            print(f"Error in batch_parse: {str(e)}")

            traceback.print_exc()
            # Return any successfully parsed documents
            # instead of raising an exception
            return [], []

    def _start_batch_process(
        self, blobs: list[Blob], chunk_size: int, include_ancestor_headings: bool
    ):
        input_config = documentai.BatchDocumentsInputConfig(
            gcs_documents=documentai.GcsDocuments(
                documents=[
                    documentai.GcsDocument(
                        gcs_uri=blob.path,
                        mime_type=blob.mimetype or "application/pdf",
                    )
                    for blob in blobs
                ]
            )
        )

        output_config = documentai.DocumentOutputConfig(
            gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
                gcs_uri=self.gcs_output_path
            )
        )

        layout_config = documentai.ProcessOptions.LayoutConfig(
            chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                chunk_size=chunk_size,
                include_ancestor_headings=include_ancestor_headings,
            )
        )
        process_options = documentai.ProcessOptions(layout_config=layout_config)

        request = documentai.BatchProcessRequest(
            name=self.processor_name,
            input_documents=input_config,
            document_output_config=output_config,
            process_options=process_options,
            skip_human_review=True,
        )

        try:
            operation = self._client.batch_process_documents(request)
            print(f"Batch process started. Operation: {operation}")
            return [operation]
        except Exception as e:
            print(f"Error starting batch process: {str(e)}")
            raise

    def _wait_for_operations(self, operations, timeout_sec, check_in_interval_sec):
        time_elapsed = 0
        while any(not operation.done() for operation in operations):
            time.sleep(check_in_interval_sec)
            time_elapsed += check_in_interval_sec
            if time_elapsed > timeout_sec:
                raise TimeoutError("Timeout exceeded!")

        # Check for errors in completed operations
        for operation in operations:
            if operation.exception():
                raise KeyError(f"Operation failed: {operation.exception()}")

    def _get_results(self, operations) -> list["DocAIParsingResults"]:  # noqa: F821
        results = []
        for operation in operations:
            metadata = operation.metadata
            if hasattr(metadata, "individual_process_statuses"):
                for status in metadata.individual_process_statuses:
                    results.append(
                        DocAIParsingResults(
                            source_path=status.input_gcs_source,
                            parsed_path=status.output_gcs_destination,
                        )
                    )
            else:
                print(f"Warning: Unexpected metadata structure: {metadata}")
        return results

    def _parse_from_results(self, results: list["DocAIParsingResults"]):  # noqa: F821
        documents = []
        storage_client = storage.Client()

        for result in results:
            print(
                f"Processing result: source_path={result.source_path}, "
                f"parsed_path={result.parsed_path}"
            )
            if not result.parsed_path:
                print(
                    "Warning: Empty parsed_path for source "
                    f"{result.source_path}. Skipping."
                )
                continue

            try:
                bucket_name, prefix = result.parsed_path.replace("gs://", "").split(
                    "/", 1
                )
            except ValueError:
                print(
                    f"Error: Invalid parsed_path format for {result.source_path}. Skipping."
                )
                continue

            bucket = storage_client.bucket(bucket_name)
            blobs = list(bucket.list_blobs(prefix=prefix))
            print(f"Found {len(blobs)} blobs in {result.parsed_path}")

            for blob in blobs:
                if blob.name.endswith(".json"):
                    print(f"Processing JSON blob: {blob.name}")
                    try:
                        content = blob.download_as_text()
                        doc_data = json.loads(content)

                        if (
                            "chunkedDocument" in doc_data
                            and "chunks" in doc_data["chunkedDocument"]
                        ):
                            for chunk in doc_data["chunkedDocument"]["chunks"]:
                                doc = Document(
                                    text=chunk["content"],
                                    metadata={
                                        "chunk_id": chunk["chunkId"],
                                        "source": result.source_path,
                                    },
                                )
                                documents.append(doc)
                        else:
                            print(
                                "Warning: Expected 'chunkedDocument' "
                                f"structure not found in {blob.name}"
                            )
                    except Exception as e:
                        print(f"Error processing blob {blob.name}: {str(e)}")

        print(f"Total documents created: {len(documents)}")
        return documents


class DocAIParsingResults:
    """
    Document AI Parsing Results
    """

    def __init__(self, source_path: str, parsed_path: str):
        self.source_path = source_path
        self.parsed_path = parsed_path


def get_or_create_docai_processor(
    project_id: str,
    location: str,
    processor_display_name: str,
    processor_id: str | None = None,
    create_new: bool = False,
    processor_type: str = "LAYOUT_PARSER_PROCESSOR",
) -> documentai.Processor:
    client_options = ClientOptions(
        api_endpoint=f"{location}-documentai.googleapis.com",
        quota_project_id=project_id,
    )
    client = documentai.DocumentProcessorServiceClient(client_options=client_options)

    if not create_new:
        if processor_id:
            # Try to get the existing processor by ID
            name = client.processor_path(project_id, location, processor_id)
            try:
                return client.get_processor(name=name)
            except Exception as e:
                print(f"Error getting processor by ID: {e}")
                print("Falling back to searching by display name...")

        # Search for the processor by display name
        parent = client.common_location_path(project_id, location)
        processors = [
            p
            for p in client.list_processors(parent=parent)
            if p.display_name == processor_display_name
        ]

        if processors:
            return processors[0]
        elif not create_new:
            raise ValueError(
                f"No processor found with display name "
                f"'{processor_display_name}' and create_new is False"
            )

    # If we reach here, we need to create a new processor
    parent = client.common_location_path(project_id, location)
    return client.create_processor(
        parent=parent,
        processor=documentai.Processor(
            display_name=processor_display_name, type_=processor_type
        ),
    )
