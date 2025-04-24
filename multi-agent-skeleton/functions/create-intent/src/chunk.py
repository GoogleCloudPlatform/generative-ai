from typing import List
from langchain_google_community.gcs_directory import GCSDirectoryLoader
from langchain_community.document_loaders.pdf import PDFMinerLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

CHUNKER = RecursiveCharacterTextSplitter(
    chunk_size=1000,
    chunk_overlap=200,
)

class ChunkService:

    def __init__(self, project_name:str, full_path: str):
        bucket = full_path.split("/")[2]
        prefix = full_path.replace(f"gs://{bucket}/", "")

        self.loader = GCSDirectoryLoader(
            project_name=project_name,
            bucket=bucket,
            prefix=prefix,
            loader_func=PDFMinerLoader
        )

    def generate_chunks(self) -> List[str]:
        chunks = []
        for doc in self.loader.load():
            chunks.extend([chunk.page_content for chunk in CHUNKER.split_documents([doc])])
        return chunks