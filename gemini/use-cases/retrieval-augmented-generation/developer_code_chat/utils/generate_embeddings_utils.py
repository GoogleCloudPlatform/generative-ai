# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Embedding Utils"""


import time
from typing import List

from langchain.embeddings import VertexAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter


def split_documents(documents, split_document_flag="PAGES"):
    """Split documents either by Pages or by the chunks"""

    # by default documents are split by pages using PyPDFLoader
    # in GCSDirectoryLoader_modified class
    doc_splits = documents

    if split_document_flag == "CHUNKS":
        # split the documents into chunks
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=50,
            separators=["\n\n", "\n", ".", "!", "?", ",", " ", ""],
        )
        doc_splits = text_splitter.split_documents(documents)

    # Add chunk number to metadata
    for idx, split in enumerate(doc_splits):
        split.metadata["chunk"] = idx

    return doc_splits


def rate_limit(max_per_minute):
    """Utility functions for Embeddings API with rate limiting"""

    period = 60 / max_per_minute
    # print("Waiting")
    while True:
        before = time.time()
        yield
        after = time.time()
        elapsed = after - before
        sleep_time = max(0, period - elapsed)
        if sleep_time > 0:
            print(".", end="")
            time.sleep(sleep_time)


class CustomVertexAIEmbeddings(VertexAIEmbeddings):
    """Custom Vertex AI Embeddings"""
    # embedding_model_name: str
    # location: str
    requests_per_minute: int
    num_instances_per_batch: int

#     def __init__(self, embedding_model_name: str, location: str, requests_per_minute: int, num_instances_per_batch: int):
#         print("## debug: initialising parameters to :", embedding_model_name, location, requests_per_minute, num_instances_per_batch)
#         super().__init__(model_name=embedding_model_name, location=location)
#         self.requests_per_minute = requests_per_minute
#         self.num_instances_per_batch = num_instances_per_batch

    def embed_documents(self, texts: List[str]):
        """Overriding embed_documents method"""

        limiter = rate_limit(self.requests_per_minute)
        results = []
        docs = list(texts)

        while docs:
            # Working in batches because the API accepts maximum 5
            # documents per request to get embeddings
            head, docs = (
                docs[: self.num_instances_per_batch],
                docs[self.num_instances_per_batch :],
            )
            chunk = self.client.get_embeddings(head)
            results.extend(chunk)
            next(limiter)

        return [r.values for r in results]


def check_if_doc_needs_fix(documents):
    """Check if doument needs fix if page content is empty"""

    for doc_index, doc in enumerate(documents):
        if doc.page_content == "" or len(doc.page_content) == 0:
            return doc_index
    return -1
