# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
import os
from typing import List

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import SKLearnVectorStore
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings

PERSIST_PATH = ".persist_vector_store"
URL = "https://services.google.com/fh/files/misc/practitioners_guide_to_mlops_whitepaper.pdf"


def load_and_split_documents(url: str) -> List[Document]:
    """Load and split documents from a given URL."""
    loader = PyPDFLoader(url)
    documents = loader.load()
    logging.info(f"# of documents loaded (pre-chunking) = {len(documents)}")

    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=200)
    doc_splits = text_splitter.split_documents(documents)
    logging.info(f"# of documents after split = {len(doc_splits)}")

    return doc_splits


def get_vector_store(
    embedding: Embeddings, persist_path: str = PERSIST_PATH, url: str = URL
) -> SKLearnVectorStore:
    """Get or create a vector store."""
    vector_store = SKLearnVectorStore(embedding=embedding, persist_path=persist_path)

    if not os.path.exists(persist_path):
        doc_splits = load_and_split_documents(url=url)
        vector_store.add_documents(documents=doc_splits)
        vector_store.persist()

    return vector_store
