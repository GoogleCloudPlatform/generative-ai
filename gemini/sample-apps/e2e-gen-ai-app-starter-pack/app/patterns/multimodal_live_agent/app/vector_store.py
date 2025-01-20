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

from langchain.schema import Document
from langchain.text_splitter import CharacterTextSplitter
from langchain_community.document_loaders import WebBaseLoader
from langchain_community.vectorstores import SKLearnVectorStore
from langchain_core.embeddings import Embeddings

PERSIST_PATH = ".persist_vector_store"


def load_and_split_documents(urls: List[str]) -> List[Document]:
    """Load and split documents from a list of URLs."""
    docs = [WebBaseLoader(url).load() for url in urls]
    docs_list = [item for sublist in docs for item in sublist]
    logging.info(f"# of documents loaded (pre-chunking) = {len(docs_list)}")

    text_splitter = CharacterTextSplitter(chunk_size=2000, chunk_overlap=50)
    doc_splits = text_splitter.split_documents(docs_list)
    logging.info(f"# of documents after split = {len(doc_splits)}")

    return doc_splits


def get_vector_store(
    embedding: Embeddings, urls: List[str], persist_path: str = PERSIST_PATH
) -> SKLearnVectorStore:
    """Get or create a vector store."""

    if os.path.exists(persist_path):
        vector_store = SKLearnVectorStore(
            embedding=embedding, persist_path=persist_path
        )
    else:
        doc_splits = load_and_split_documents(urls=urls)
        vector_store = SKLearnVectorStore.from_documents(
            documents=doc_splits, embedding=embedding, persist_path=persist_path
        )
        vector_store.persist()
    return vector_store
