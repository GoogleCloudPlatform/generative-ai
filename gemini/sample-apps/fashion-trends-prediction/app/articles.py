"""
Module for retrieving articles related to a given outfit using the ensemble retriever.
"""

# pylint: disable=E0401

from config import config
from gcs import read_file_from_gcs_link
from genai_prompts import ARTICLES_PROMPT
from langchain.docstore.document import Document
from langchain.retrievers import BM25Retriever, EnsembleRetriever
from langchain.vectorstores import VectorStore
from sentence_transformers import SentenceTransformer
import vertexai
from vertexai.generative_models import GenerationConfig, GenerativeModel

PROJECT_ID = config["PROJECT_ID"]  # @param {type:"string"}
LOCATION = config["LOCATION"]  # @param {type:"string"}
MODE = config["mode"]


class Articles:
    def __init__(self, data: dict):
        """Initializes the Articles class.

        Args:
            data (dict): A dictionary of articles.
        """
        self.data = data
        self.embedder = SentenceTransformer("all-MiniLM-L6-v2")

        if MODE == 0:
            chunks = read_file_from_gcs_link(config["Data"]["chunks_local"])
        else:
            chunks = read_file_from_gcs_link(config["Data"]["chunks_prod"])

        chunks = [Document(**chunk) for chunk in chunks]
        bm25_retriever = BM25Retriever.from_documents(chunks)
        bm25_retriever.k = 3

        if MODE == 0:
            global vectorstore
            local_vectorstore: VectorStore = read_file_from_gcs_link(
                config["Data"]["vectorstore_local"]
            )
        else:
            global vectorstore
            local_vectorstore: VectorStore = read_file_from_gcs_link(
                config["Data"]["vectorstore_prod"]
            )

        faiss_retriever = local_vectorstore.as_retriever(search_kwargs={"k": 3})

        # initialize the ensemble retriever
        p = 0.6
        self.ensemble_retriever = EnsembleRetriever(
            retrievers=[bm25_retriever, faiss_retriever], weights=[p, 1 - p]
        )

        vertexai.init(project=PROJECT_ID, location=LOCATION)

        self.model = GenerativeModel("gemini-1.0-pro-002")

    def get_articles(self, outfit: str) -> list:
        """Gets articles related to a given outfit.

        Args:
            outfit (str): The outfit to search for.

        Returns:
            list: A list of articles related to the outfit.
        """
        docs = self.ensemble_retriever.get_relevant_documents(outfit)

        answers = []
        included = set()
        for doc in docs:
            id = doc.metadata["id"]
            if id not in included:
                included.add(id)
                article_s = self.data[id][1]
                if len(self.data[id][1]) > 8000:
                    article_s = self.data[id][1][:8000]

                try:
                    response = self.model.generate_content(
                        [ARTICLES_PROMPT.format(outfit=outfit, article=article_s)],
                        generation_config=GenerationConfig(
                            max_output_tokens=2048,
                            temperature=1,
                            top_p=1,
                        ),
                        stream=False,
                    )
                    if response.text.split()[0][0] == "Y":
                        # [summary, link]
                        answers.append([self.data[id][1], self.data[id][0]])
                except Exception as e:
                    print(e)

                    # [summary, link]
                    answers.append([self.data[id][1], self.data[id][0]])

        return answers
