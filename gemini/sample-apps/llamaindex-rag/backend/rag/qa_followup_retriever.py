"""Custom retriever which implements
retrieval based on hypothetical questions"""

import logging

from llama_index.core import QueryBundle
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever
from llama_index.core.schema import NodeRelationship, NodeWithScore
from llama_index.storage.docstore.firestore import FirestoreDocumentStore

# Set the desired logging level
logging.basicConfig(encoding="utf-8", level=logging.INFO)
logger = logging.getLogger(__name__)


class QARetriever(BaseRetriever):
    """Retrieves nodes based on questions answered by nodes. First identifies
    document ids based on vector search and then does lookup in document store."""

    def __init__(
        self,
        qa_vector_retriever: VectorIndexRetriever,
        docstore: FirestoreDocumentStore,
    ) -> None:
        """
        This retriever uses a vector store to do
        initial node retriever and a documentstore to retrieve nodes by id
        """

        self._qa_vector_retriever = qa_vector_retriever
        self._docstore = docstore
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        qa_nodes = self._qa_vector_retriever.retrieve(query_bundle)
        og_docs = []
        for nodewscore in qa_nodes:
            logger.info(nodewscore.node.text)
            source_doc_id = nodewscore.node.relationships[
                NodeRelationship.SOURCE
            ].node_id
            og_docs.append(
                NodeWithScore(
                    node=self._docstore.get_document(source_doc_id),
                    score=nodewscore.score,
                )
            )

        return og_docs

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        qa_nodes = await self._qa_vector_retriever.aretrieve(query_bundle)
        og_docs = []
        for nodewscore in qa_nodes:
            logger.info(f"Matched Question: {nodewscore.node.text}")
            source_doc_id = nodewscore.node.relationships[
                NodeRelationship.SOURCE
            ].node_id
            og_docs.append(
                NodeWithScore(
                    node=self._docstore.get_document(source_doc_id),
                    score=nodewscore.score,
                )
            )
        return og_docs


class QAFollowupRetriever(BaseRetriever):
    """Custom retriever which automerging retrieval and then follows that up
    with another vector-based retrieval
    into an index storing questions answered per docs"""

    def __init__(
        self, qa_retriever: QARetriever, base_retriever: BaseRetriever
    ) -> None:
        """
        This retriever uses a vector store to do initial node retriever
        and a documentstore to retrieve nodes by id
        """

        self._qa_retriever = qa_retriever
        self._base_retriever = base_retriever
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        am_nodes = self._base_retriever.retrieve(query_bundle)
        qa_nodes = self._qa_retriever.retrieve(query_bundle)

        am_ids = {n.node.node_id for n in am_nodes}
        qa_ids = {n.node.node_id for n in qa_nodes}
        num_qa_ids = len(qa_ids)
        num_am_ids = len(am_ids)
        logger.info(f"number of nodes found with question matching {num_qa_ids}")
        logger.info(f"number of nodes found with base retriever: {num_am_ids}")
        combined_dict = {n.node.node_id: n for n in am_nodes}
        combined_dict.update({n.node.node_id: n for n in qa_nodes})
        retrieve_ids = am_ids.union(qa_ids)
        retrieve_nodes = [combined_dict[rid] for rid in retrieve_ids]
        return retrieve_nodes

    async def _aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        am_nodes = await self._base_retriever.aretrieve(query_bundle)
        qa_nodes = await self._qa_retriever.aretrieve(query_bundle)

        am_ids = {n.node.node_id for n in am_nodes}
        qa_ids = {n.node.node_id for n in qa_nodes}
        num_qa_ids = len(qa_ids)
        num_am_ids = len(am_ids)
        logger.info(f"number of nodes found with question matching {num_qa_ids}")
        logger.info(f"number of nodes found with base retriever: {num_am_ids}")
        combined_dict = {n.node.node_id: n for n in am_nodes}
        combined_dict.update({n.node.node_id: n for n in qa_nodes})
        retrieve_ids = am_ids.union(qa_ids)
        retrieve_nodes = [combined_dict[rid] for rid in retrieve_ids]
        return retrieve_nodes
