"""Handles document loading from GCS and splitting into text chunks using LangChain."""
from typing import List
from langchain_google_community.gcs_directory import GCSDirectoryLoader
from langchain_community.document_loaders.pdf import PDFMinerLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNKER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)


class ChunkService:
    """
    Handles loading documents from Google Cloud Storage and splitting them into text chunks.
    """

    def __init__(self, project_name: str, full_path: str):
        """
        Initializes the ChunkService.

        Args:
            project_id: The Google Cloud project ID.
            bucket_name: The name of the GCS bucket containing the source documents.
        """
        bucket = full_path.split("/")[2]
        prefix = full_path.replace(f"gs://{bucket}/", "")

        self.loader = GCSDirectoryLoader(
            project_name=project_name,
            bucket=bucket,
            prefix=prefix,
            loader_func=PDFMinerLoader,
        )

    def generate_chunks(self) -> List[str]:
        """
        Loads documents from the configured GCS bucket and splits them into text chunks.

        Returns:
            A list of strings, where each string is a text chunk.
            Returns an empty list if no documents are found or an 
            error occurs during loading/splitting.
        """
        chunks = []
        for doc in self.loader.load():
            chunks.extend(
                [chunk.page_content for chunk in CHUNKER.split_documents([doc])]
            )
        return chunks
