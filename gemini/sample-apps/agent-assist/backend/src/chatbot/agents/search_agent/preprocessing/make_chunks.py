import json
import os

from langchain.document_loaders import PyMuPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


def make_chunks(DOCUMENT_PATH: str, POLICY_NAME: str) -> None:
    """
    Makes chunks of text from a PDF document.

    Args:
        DOCUMENT_PATH (str): The path to the PDF document.
        POLICY_NAME (str): The name of the policy.

    Returns:
        None

    """
    TABLES_PATH = "data/static/table_text/{POLICY_NAME}/"
    CHUNKS_PATH = f"data/static/chunks/chunks_{POLICY_NAME}.json"

    try:
        os.makedirs(TABLES_PATH)
    except Exception as e:
        print(e)
        pass

    POLICY_NAME = DOCUMENT_PATH.split("/")[-1].split(".")[0]

    loader = PyMuPDFLoader(DOCUMENT_PATH)
    data = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=500, chunk_overlap=50
    )

    chunks = text_splitter.split_documents(data)
    for chunk_id, chunk in enumerate(chunks):
        chunk.page_content = chunk.page_content.lower()
        chunk.metadata["chunk_id"] = chunk_id
        chunk.metadata["isTable"] = False

    TOTAL_DOC_CHUNKS = len(chunks)

    for folder_id in os.listdir(f"{TABLES_PATH}"):
        for file_id in os.listdir(f"{TABLES_PATH}/{folder_id}"):
            if file_id.startswith("table_string"):
                loader = TextLoader(f"{TABLES_PATH}/{folder_id}/{file_id}")
                table_chunk = loader.load()[0]
                table_chunk.metadata["isTable"] = True
                chunks.append(table_chunk)

    l = []
    for chunk in chunks:
        l.append(chunk.dict())
    chunks_dict = {}
    chunks_dict["TOTAL_DOC_CHUNKS"] = TOTAL_DOC_CHUNKS
    chunks_dict["chunks"] = l

    with open(CHUNKS_PATH, "w") as f:
        json.dump(chunks_dict, f)
