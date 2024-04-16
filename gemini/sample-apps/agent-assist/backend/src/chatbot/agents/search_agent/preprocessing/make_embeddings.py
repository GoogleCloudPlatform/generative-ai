from app.chunks import get_all_chunks
from langchain.embeddings import HuggingFaceEmbeddings
from langchain.vectorstores import FAISS


def make_embeddings(POLICY_NAME):
    """Creates embeddings for the given policy.

    Args:
    POLICY_NAME: The name of the policy to create embeddings for.

    Returns:
    None
    """
    EMBEDDINGS_PATH = f"data/static/embeddings/{POLICY_NAME}.rt"

    chunks, non_table_chunks = get_all_chunks(POLICY_NAME)

    embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    faiss_vectorstore = FAISS.from_documents(chunks, embedding)
    faiss_vectorstore.save_local(EMBEDDINGS_PATH)


if __name__ == "__main__":
    make_embeddings("Arogyasanjeevani")
