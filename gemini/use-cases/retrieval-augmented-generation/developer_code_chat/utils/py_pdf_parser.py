# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Modified Langchain PDF Wrappers"""

import os
import tempfile
from abc import ABC
from typing import Iterator, List, Optional, Union
from urllib.parse import urlparse
import requests
import pypdf

from langchain.document_loaders.base import BaseBlobParser
from langchain.document_loaders.base import BaseLoader
from langchain.document_loaders.blob_loaders import Blob
from langchain.schema import Document
from langchain.docstore.document import Document as Document_doc


class PyPDFParser(BaseBlobParser):
    """Load `PDF` using `pypdf` and chunk at character level."""

    def __init__(self, password: Optional[Union[str, bytes]] = None):
        self.password = password

    def lazy_parse(self, blob: Blob) -> Iterator[Document]:
        """Lazily parse the blob."""
        with blob.as_bytes_io() as pdf_file_obj:
            page_content_list = []
            pdf_reader = pypdf.PdfReader(pdf_file_obj, password=self.password)

            for page_number, page in enumerate(pdf_reader.pages):
                try:
                    page_content_text = page.extract_text()
                except Exception as e:  # pylint: disable=W0703
                    print(
                        "Error while reading page number :",
                        page_number,
                        "from document source :",
                        blob.source,
                    )
                    print(e)
                else:
                    page_content_list.append(
                        Document(
                            page_content=page_content_text, \
                              metadata={"source": blob.source, \
                                "page": page_number},
                        )
                    )

        yield from page_content_list


class BasePDFLoader(BaseLoader, ABC):
    """Base Loader class for `PDF` files.
    Defaults to check for local file, but if the file is a web path,
    it will download it to a temporary file, use it, then clean up
    the temporary file after completion
    """

    def __init__(self, file_path: str):
        """Initialize with a file path."""
        self.file_path = file_path
        self.web_path = None
        if "~" in self.file_path:
            self.file_path = os.path.expanduser(self.file_path)

        # If the file is a web path or S3, download it to a temporary file,
        # and use that
        if not os.path.isfile(self.file_path) and \
          self._is_valid_url(self.file_path):
            self.temp_dir = tempfile.TemporaryDirectory() #pylint:disable=R1732
            _, suffix = os.path.splitext(self.file_path)
            temp_pdf = os.path.join(self.temp_dir.name, f"tmp{suffix}")
            if self._is_s3_url(self.file_path):
                self.web_path = self.file_path
            else:
                r = requests.get(self.file_path, timeout=60)

                if r.status_code != 200:
                    raise ValueError(
                        f"Check the url of your file; returned status code \
                            {r.status_code}"
                    )

                self.web_path = self.file_path
                with open(temp_pdf, mode="wb") as f:
                    f.write(r.content)
                self.file_path = str(temp_pdf)
        elif not os.path.isfile(self.file_path):
            raise ValueError(
                f"File path {self.file_path} \
                             is not a valid file or url"
            )

    def __del__(self) -> None:
        if hasattr(self, "temp_dir"):
            self.temp_dir.cleanup()

    @staticmethod
    def _is_valid_url(url: str) -> bool:
        """Check if the url is valid."""
        parsed = urlparse(url)
        return bool(parsed.netloc) and bool(parsed.scheme)

    @staticmethod
    def _is_s3_url(url: str) -> bool:
        """check if the url is S3"""
        try:
            result = urlparse(url)
            if result.scheme == "s3" and result.netloc:
                return True
            return False
        except ValueError:
            return False

    @property
    def source(self) -> str:
        return self.web_path if self.web_path is not None else self.file_path


class PyPDFLoader(BasePDFLoader):
    """Load `PDF using `pypdf` and chunks at character level.

    Loader also stores page numbers in metadata.
    """

    def __init__(
        self, file_path: str, password: Optional[Union[str, bytes]] = None
    ) -> None:
        """Initialize with a file path."""
        self.parser = PyPDFParser(password=password)
        super().__init__(file_path)

    def load(self) -> List[Document_doc]:
        """Load given path as pages."""
        return list(self.lazy_load())

    def lazy_load(
        self,
    ) -> Iterator[Document_doc]:
        """Lazy load given path as pages."""
        blob = Blob.from_path(self.file_path)
        yield from self.parser.parse(blob)
