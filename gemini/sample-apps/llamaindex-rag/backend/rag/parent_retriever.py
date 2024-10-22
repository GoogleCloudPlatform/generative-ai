"""Custom retriever which implements parent retrieval"""

import logging

from llama_index.core import QueryBundle
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever
from llama_index.core.schema import NodeRelationship, NodeWithScore, TextNode
from llama_index.storage.docstore.firestore import FirestoreDocumentStore
import pandas as pd

# Set the desired logging level
logging.basicConfig(encoding="utf-8", level=logging.INFO)
logger = logging.getLogger(__name__)


class ParentRetriever(BaseRetriever):
    """Custom retriever which performs retrieves
    the source document associated with a node."""

    def __init__(
        self, vector_retriever: VectorIndexRetriever, docstore: FirestoreDocumentStore
    ) -> None:
        """
        This retriever uses a vector store to do initial node retriever and a documentstore to retrieve nodes by id
        """

        self._vector_retriever = vector_retriever
        self._docstore = docstore
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        """Expand retrieved nodes into all their source documents"""
        initial_nodes = self._vector_retriever.retrieve(query_bundle)
        node_source_id_score_df = pd.DataFrame(
            [
                {
                    "source_id": n.node.relationships[NodeRelationship.SOURCE].node_id,
                    "score": n.score,
                }
                for n in initial_nodes
            ]
        )
        final_df = (
            node_source_id_score_df.groupby("source_id")["score"].mean().reset_index()
        )
        unique_source_doc_ids_scores = final_df.to_dict("records")

        source_docs = []
        for doc_score in unique_source_doc_ids_scores:
            source_doc = self._docstore.get_document(doc_score["source_id"])
            node = TextNode(id_=doc_score["source_id"], text=source_doc.text)
            source_docs.append(NodeWithScore(node=node, score=doc_score["score"]))

        return source_docs
