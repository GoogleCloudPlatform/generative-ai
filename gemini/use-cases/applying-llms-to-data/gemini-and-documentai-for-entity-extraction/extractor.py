import re
from typing import Any, Optional

from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import InternalServerError, RetryError
from google.cloud import documentai, storage
from temp_file_uploader import TempFileUploader


class DocumentExtractor:
    """Abstract base class for document extraction."""

    def __init__(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        processor_version_id: Optional[str] = None,
    ):
        self.project_id = project_id
        self.location = location
        self.processor_id = processor_id
        self.processor_version_id = processor_version_id
        self.client = documentai.DocumentProcessorServiceClient(
            client_options=ClientOptions(
                api_endpoint=f"{location}-documentai.googleapis.com"
            )
        )
        self.processor_name = self._get_proccessor_name()

    def _get_proccessor_name(self) -> Any:
        if self.processor_version_id:
            return self.client.processor_version_path(
                self.project_id,
                self.location,
                self.processor_id,
                self.processor_version_id,
            )
        return self.client.processor_path(
            self.project_id, self.location, self.processor_id
        )

    def process_document(self, file_path: str, mime_type: str) -> documentai.Document:
        """abstract function for document processing"""
        raise NotImplementedError


class OnlineDocumentExtractor(DocumentExtractor):
    """
    Processes documents using the online Document AI API.
    """

    def process_document(
        self, file_path: str, mime_type: str = "application/pdf"
    ) -> documentai.Document:
        with open(file_path, "rb") as image:
            image_content = image.read()

        request = documentai.ProcessRequest(
            name=self.processor_name,
            raw_document=documentai.RawDocument(
                content=image_content, mime_type=mime_type
            ),
        )

        result = self.client.process_document(request=request)
        return result.document


class BatchDocumentExtractor(DocumentExtractor):
    """
    Processes documents using the batch Document AI API.
    """

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        gcs_output_uri: str,
        gcs_temp_uri: str,
        processor_version_id: str,
        timeout: int = 400,
    ):
        super().__init__(project_id, location, processor_id, processor_version_id)
        self.gcs_output_uri = gcs_output_uri
        self.timeout = timeout
        self.storage_client = storage.Client()
        self.temp_file_uploader = TempFileUploader(gcs_temp_uri)

    def process_document(self, file_path: str, mime_type: str) -> documentai.Document:
        gcs_input_uri = self.temp_file_uploader.upload_file(file_path)
        document = self._process_document_batch(gcs_input_uri, mime_type)
        self.temp_file_uploader.delete_file()
        return document

    # pylint: disable=too-many-locals
    def _process_document_batch(
        self, gcs_input_uri: str, mime_type: str
    ) -> documentai.Document:
        gcs_document = documentai.GcsDocument(
            gcs_uri=gcs_input_uri, mime_type=mime_type
        )
        gcs_documents = documentai.GcsDocuments(documents=[gcs_document])
        input_config = documentai.BatchDocumentsInputConfig(gcs_documents=gcs_documents)

        gcs_output_config = documentai.DocumentOutputConfig.GcsOutputConfig(
            gcs_uri=self.gcs_output_uri
        )
        output_config = documentai.DocumentOutputConfig(
            gcs_output_config=gcs_output_config
        )

        request = documentai.BatchProcessRequest(
            name=self.processor_name,
            input_documents=input_config,
            document_output_config=output_config,
        )

        operation = self.client.batch_process_documents(request)
        try:
            print(f"Waiting for operation ({operation.operation.name}) to complete...")
            operation.result(timeout=self.timeout)
        except (RetryError, InternalServerError) as e:
            print(e.message)

        metadata = documentai.BatchProcessMetadata(operation.metadata)
        if metadata.state != documentai.BatchProcessMetadata.State.SUCCEEDED:
            raise ValueError(f"Batch Process Failed: {metadata.state_message}")

        # Retrieve the processed document from GCS
        for process in list(metadata.individual_process_statuses):
            matches = re.match(r"gs://(.*?)/(.*)", process.output_gcs_destination)
            if not matches:
                print(
                    "Could not parse output GCS destination:",
                    process.output_gcs_destination,
                )
                continue

            output_bucket, output_prefix = matches.groups()
            output_blobs = self.storage_client.list_blobs(
                output_bucket, prefix=output_prefix
            )
            for blob in output_blobs:
                if blob.content_type == "application/json":
                    print(f"Fetching {blob.name}")
                    return documentai.Document.from_json(
                        blob.download_as_bytes(), ignore_unknown_fields=True
                    )

        raise FileNotFoundError("Processed document not found in GCS.")
