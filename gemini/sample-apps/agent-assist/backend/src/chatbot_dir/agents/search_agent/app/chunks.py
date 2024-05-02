import json

from langchain.embeddings import HuggingFaceEmbeddings
from langchain.retrievers import BM25Retriever
from langchain.schema import Document
from langchain.vectorstores import FAISS

EMBEDDINGS_PATH = "data/static/embeddings/{}.vs"

# TODO: threading, remove duplicate chunks, automerging


def get_chunks(
    policies: list[str], keywords_lexical: str, keywords_semantic: str
) -> dict[str, list[str]]:
    """
    This function takes in a list of policy names, a string of lexical keywords, and a string of semantic keywords.
    It returns a dictionary of policy names to a list of chunks of text that are relevant to the given keywords.

    Args:
        policies (list[str]): A list of policy names.
        keywords_lexical (str): A string of lexical keywords.
        keywords_semantic (str): A string of semantic keywords.

    Returns:
        dict[str, list[str]]: A dictionary of policy names to a list of chunks of text that are relevant to the given keywords.
    """
    chunks_semantic = get_chunks_semantic(policies, keywords_semantic)
    chunks_lexical = get_chunks_lexical(policies, keywords_lexical)

    chunks = {}
    for POLICY_NAME in policies:
        chunks[POLICY_NAME] = chunks_semantic[POLICY_NAME] + chunks_lexical[POLICY_NAME]

    return chunks


def get_chunks_semantic(
    policies: list[str], keywords: str
) -> dict[str, list[Document]]:
    """
    This function takes in a list of policy names and a string of semantic keywords.
    It returns a dictionary of policy names to a list of chunks of text that are relevant to the given keywords.

    Args:
        policies (list[str]): A list of policy names.
        keywords (str): A string of semantic keywords.

    Returns:
        dict[str, list[Document]]: A dictionary of policy names to a list of chunks of text that are relevant to the given keywords.
    """
    chunks_for_policy = {}
    for POLICY_NAME in policies:
        chunks, non_table_chunks = get_all_chunks(POLICY_NAME)
        embedding = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        faiss_vectorstore = FAISS.load_local(
            EMBEDDINGS_PATH.format(POLICY_NAME), embedding
        )
        faiss_retriever = faiss_vectorstore.as_retriever(search_kwards={"k": 3})
        docs = faiss_retriever.get_relevant_documents(keywords.lower())
        final_chunks = add_neighbouring_chunks(docs, chunks, non_table_chunks)
        final_chunks = [x.page_content for x in final_chunks]
        chunks_for_policy[POLICY_NAME] = final_chunks

    return chunks_for_policy


def get_chunks_lexical(policies: list[str], keywords: str) -> dict[str, list[Document]]:
    """
    This function takes in a list of policy names and a string of lexical keywords.
    It returns a dictionary of policy names to a list of chunks of text that are relevant to the given keywords.

    Args:
        policies (list[str]): A list of policy names.
        keywords (str): A string of lexical keywords.

    Returns:
        dict[str, list[Document]]: A dictionary of policy names to a list of chunks of text that are relevant to the given keywords.
    """
    chunks_for_policy = {}

    for POLICY_NAME in policies:
        chunks, non_table_chunks = get_all_chunks(POLICY_NAME)

        # lexically matching
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = 5

        docs = bm25_retriever.get_relevant_documents(keywords.lower())
        final_chunks = add_neighbouring_chunks(docs, chunks, non_table_chunks)
        final_chunks = [x.page_content for x in final_chunks]
        chunks_for_policy[POLICY_NAME] = final_chunks

    return chunks_for_policy


# k-1 and k+1 chunks


def add_neighbouring_chunks(
    relevant_chunks: list[Document], all_chunks: list[Document], non_table_chunks: int
) -> list[Document]:
    """
    This function takes in a list of relevant chunks, a list of all chunks, and the total number of chunks in the document.
    It returns a list of chunks that includes the relevant chunks and their neighboring chunks.

    Args:
        relevant_chunks (list[Document]): A list of relevant chunks.
        all_chunks (list[Document]): A list of all chunks.
        non_table_chunks (int): The total number of chunks in the document.

    Returns:
        list[Document]: A list of chunks that includes the relevant chunks and their neighboring chunks.
    """
    relevantChunkList = []
    relevantTableChunks = []
    for doc in relevant_chunks:
        if doc.metadata["isTable"]:
            relevantTableChunks.append(doc)
        else:
            relevantChunkList.append(doc.metadata["chunk_id"])

    finalListOfChunks = []
    for chunk_id in relevantChunkList:
        finalListOfChunks.append(chunk_id)
        if chunk_id == 0 or chunk_id == non_table_chunks - 1:
            continue
        if chunk_id + 1 not in relevantChunkList:
            finalListOfChunks.append(chunk_id + 1)

        if chunk_id - 1 not in relevantChunkList:
            finalListOfChunks.append(chunk_id - 1)

    finalChunks = [all_chunks[idx] for idx in finalListOfChunks]
    finalChunks += relevantTableChunks

    return finalChunks


def get_all_chunks(POLICY_NAME: str) -> tuple[list[Document], int]:
    """
    This function takes in a policy name and returns a list of all chunks in the policy and the total number of chunks in the policy.

    Args:
        POLICY_NAME (str): The name of the policy.

    Returns:
        tuple[list[Document], int]: A tuple containing a list of all chunks in the policy and the total number of chunks in the policy.
    """
    with open(f"data/static/chunks/chunks_{POLICY_NAME}.json") as f:
        chunks_dict = json.load(f)

    TOTAL_DOC_CHUNKS = chunks_dict["TOTAL_DOC_CHUNKS"]
    chunks_all = []
    chunks_all += [
        Document(**chunks_dict["chunks"][idx])
        for idx in range(len(chunks_dict["chunks"]))
    ]

    return chunks_all, TOTAL_DOC_CHUNKS
