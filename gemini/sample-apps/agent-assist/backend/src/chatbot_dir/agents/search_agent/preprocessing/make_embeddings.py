"""This is a python utility file."""

# pylint: disable=E0401

from app.chunks import get_all_chunks
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS


def make_embeddings(policy_name):
    """Creates embeddings for the given policy.

    Args:
    policy_name: The name of the policy to create embeddings for.

    Returns:
    None
    """
    embeddings_path = f"data/static/embeddings/{policy_name}.rt"

    chunks, _ = get_all_chunks(policy_name)

    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    faiss_vectorstore = FAISS.from_documents(chunks, embedding)
    faiss_vectorstore.save_local(embeddings_path)


if __name__ == "__main__":
    make_embeddings("Arogyasanjeevani")
