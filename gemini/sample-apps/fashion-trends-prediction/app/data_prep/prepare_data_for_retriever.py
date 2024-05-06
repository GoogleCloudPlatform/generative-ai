"""
Module for preparing data for the retriever in the fashion trends prediction app.
"""

# pylint: disable=E0401

import json
import pickle

from config import config
from langchain.docstore.document import Document
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain.vectorstores import FAISS

DATA_PATH = config["Data"]["current_data"]


def prepare_data_for_retriever() -> None:
    """Prepares data for the retriever.

    This function loads the saved data, converts articles to lowercase,
    creates Document objects for each article, splits the documents into chunks, and
    saves the chunks and vectorstore to disk.

    """

    with open(DATA_PATH, "r", encoding="utf-8") as f:
        saved = json.load(f)

    articles = [item[1].lower() for item in saved["articles"]]
    article_docs = []

    for article in articles:
        doc = Document(page_content=article)
        article_docs.append(doc)

    text_splitter = RecursiveCharacterTextSplitter(
        # Set a really small chunk size, just to show.
        chunk_size=200,
        chunk_overlap=20,
        length_function=len,
        is_separator_regex=False,
    )

    all_chunks = []
    for i, doc in enumerate(article_docs):
        chunks = text_splitter.split_documents([doc])
        for chunk in chunks:
            chunk.metadata["id"] = i
        all_chunks += chunks

    chunks_list = []
    for chunk in all_chunks:
        chunks_list.append(chunk.dict())

    # either create a data directory and run the below code to store the files locally
    # and correspondingly change the code in articles.py to read from local
    # or store these files in gcs and change path in config.py of relevant keys of config['Data']
    with open("../data/chunks_final.json", "w", encoding="utf-8") as outfile:
        json.dump(chunks_list, outfile)

    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    faiss_vectorstore = FAISS.from_documents(all_chunks, embedding)

    with open("../data/vectorstore_final.pkl", "wb") as outfile:
        pickle.dump(faiss_vectorstore, outfile)
