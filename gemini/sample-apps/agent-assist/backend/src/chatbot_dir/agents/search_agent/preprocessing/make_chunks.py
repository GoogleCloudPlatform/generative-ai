"""This is a python utility file."""

# pylint: disable=E0401

import json
import os
from typing import Any

from langchain.document_loaders import PyMuPDFLoader, TextLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter


# pylint: disable=R0914
def make_chunks(document_path: str, policy_name: str) -> None:
    """Makes chunks of text from a PDF document.

    Args:
        document_path (str): The path to the PDF document.
        policy_name (str): The name of the policy.

    Returns:
        None
    """
    tables_path = "data/static/table_text/{policy_name}/"
    chunks_path = f"data/static/chunks/chunks_{policy_name}.json"

    try:
        os.makedirs(tables_path)
    except ValueError as e:
        print(e)

    policy_name = document_path.split("/")[-1].split(".")[0]

    loader = PyMuPDFLoader(document_path)
    data = loader.load()
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)

    chunks = text_splitter.split_documents(data)
    for chunk_id, chunk in enumerate(chunks):
        chunk.page_content = chunk.page_content.lower()
        chunk.metadata["chunk_id"] = chunk_id
        chunk.metadata["isTable"] = False

    total_doc_chunks = len(chunks)

    for folder_id in os.listdir(f"{tables_path}"):
        for file_id in os.listdir(f"{tables_path}/{folder_id}"):
            if file_id.startswith("table_string"):
                loader = TextLoader(f"{tables_path}/{folder_id}/{file_id}")
                table_chunk = loader.load()[0]
                table_chunk.metadata["isTable"] = True
                chunks.append(table_chunk)

    chunk_list = []
    for chunk in chunks:
        chunk_list.append(chunk.dict())

    chunks_dict: dict[str, Any] = {}
    chunks_dict["chunks"] = []
    chunks_dict["TOTAL_DOC_CHUNKS"] = total_doc_chunks
    chunks_dict["chunks"] = chunk_list

    with open(chunks_path, "w", encoding="UTF-8") as f:
        json.dump(chunks_dict, f)
