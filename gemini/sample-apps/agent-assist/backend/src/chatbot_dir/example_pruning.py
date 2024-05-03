"""This is a python utility file."""

# pylint: disable=E0401

import json
import os

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.schema import Document
from langchain.vectorstores import FAISS

EXAMPLES_PATH = "data/static/oe_examples/examples.json"
VS_QUERY_PATH = "data/static/oe_examples/vs_query"
VS_HISTORY_PATH = "data/static/oe_examples/vs_history"
embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")


def main():
    """
    This function loads the examples from a JSON file
      and creates two FAISS vectorstores, one for the query and one for the chat history.
    """

    try:
        os.makedirs(EXAMPLES_PATH)
    except ValueError as e:
        print(e)

    with open(EXAMPLES_PATH, encoding="UTF-8") as f:
        examples_list = json.load(f)

    examples = []
    for example in examples_list:
        tmp = {
            "page_content": example["query"],
            "metadata": {"example": example["example"]},
        }
        examples.append(Document(**tmp))

    faiss_vectorstore = FAISS.from_documents(examples, embedding)
    faiss_vectorstore.save_local(VS_QUERY_PATH)

    examples = []
    for example in examples_list:
        tmp = {
            "page_content": example["chat_history"],
            "metadata": {"example": example["example"]},
        }
        examples.append(Document(**tmp))

    faiss_vectorstore = FAISS.from_documents(examples, embedding)
    faiss_vectorstore.save_local(VS_HISTORY_PATH)


def get_similar_examples(query: str, chat_history: str) -> str:
    """
    This function takes a query and a chat history as input and returns a list of similar examples.

    Args:
        query (str): The query string.
        chat_history (str): The chat history string.

    Returns:
        str: A string containing the similar examples.
    """

    queries = get_similar_examples_query(query) + get_similar_examples_history(
        chat_history
    )

    examples = "\n\n-------------------------------\n\n".join(queries)

    return examples


def get_similar_examples_query(query: str) -> list:
    """
    This function takes a query as input and
    returns a list of similar examples from the query vectorstore.

    Args:
        query (str): The query string.

    Returns:
        list: A list of similar examples.
    """
    vectorstore = FAISS.load_local(VS_QUERY_PATH, embedding)
    examples = vectorstore.similarity_search(query)
    examples = [example.metadata["example"] for example in examples]
    return examples


def get_similar_examples_history(chat_history: str) -> list:
    """
    This function takes a chat history as input and returns
      a list of similar examples from the history vectorstore.

    Args:
        chat_history (str): The chat history string.

    Returns:
        list: A list of similar examples.
    """

    vectorstore = FAISS.load_local(VS_HISTORY_PATH, embedding)
    examples = vectorstore.similarity_search(chat_history)
    examples = [example.metadata["example"] for example in examples]
    return examples


if __name__ == "__main__":
    main()
