# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Load directory from GCS Bucket"""

from typing import Callable, List, Optional

from google.cloud import storage
from langchain.docstore.document import Document
from langchain.document_loaders.base import BaseLoader
from utils.gcs_file_loader import GCSFileLoader
from utils.py_pdf_loader import PyPDFLoader


class GCSDirectoryLoader(BaseLoader):
    """Load from GCS directory."""

    def __init__(
        self,
        project_name: str,
        bucket: str,
        prefix: str = "",
        loader_func: Optional[Callable[[str], BaseLoader]] = None,
    ):
        """Initialize with bucket and key name.

        Args:
            project_name: The name of the project for the GCS bucket.
            bucket: The name of the GCS bucket.
            prefix: The prefix of the GCS bucket.
            loader_func: A loader function that instatiates a loader based on a
                file_path argument. If nothing is provided, the  GCSFileLoader
                would use its default loader.
        """
        self.project_name = project_name
        self.bucket = bucket
        self.prefix = prefix

        def default_loader_func(file_path: str) -> BaseLoader:
            return PyPDFLoader(file_path)
            # return UnstructuredFileLoader(file_path)

        self._loader_func = loader_func if loader_func else default_loader_func

    def load(self) -> List[Document]:
        """Load documents."""
        client = storage.Client(project=self.project_name)
        # docs = []
        docs: List[<type>] = []
        blob_doc = ""
        for blob in client.list_blobs(self.bucket, prefix=self.prefix):
            # we shall just skip directories since GCSFileLoader creates
            # intermediate directories on the fly
            try:
                if blob.name.endswith("/"):
                    continue
                if not blob.name.endswith(".pdf"):
                    print("Not a PDF :", self.bucket + "/" + blob.name)
                    continue
                print("Loading file :", blob.name)
                loader = GCSFileLoader(
                    self.project_name,
                    self.bucket,
                    blob.name,
                    loader_func=self._loader_func,
                )
                blob_doc = loader.load()
            except Exception as e:  # pylint: disable=W0718,W0703
                print(f"Error while loading document :{e}", blob.name)
            else:
                docs.extend(blob_doc)
                blob_doc = ""
        print("Loaded all valid documents successfully..")
        return docs
