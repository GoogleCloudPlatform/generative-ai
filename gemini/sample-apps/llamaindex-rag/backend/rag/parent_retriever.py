# Copyright 2024 Google, LLC. This software is provided as-is, without
# warranty or representation for any use or purpose. Your use of it is
# subject to your agreement with Google.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import logging
from typing import List

from llama_index.core import QueryBundle
from llama_index.core.retrievers import BaseRetriever, VectorIndexRetriever
from llama_index.core.schema import (
    NodeRelationship,
    NodeWithScore,
    RelatedNodeInfo,
    TextNode,
)
from llama_index.storage.docstore.firestore import FirestoreDocumentStore
import pandas as pd

# Set the desired logging level
logging.basicConfig(encoding="utf-8", level=logging.INFO)
logger = logging.getLogger(__name__)


class ParentRetriever(BaseRetriever):
    """Custom retriever which performs retrieves the source document associated with a node."""

    def __init__(
        self, vector_retriever: VectorIndexRetriever, docstore: FirestoreDocumentStore
    ) -> None:
        """
        This retriever uses a vector store to do initial node retriever and a documentstore to retrieve nodes by id
        """

        self._vector_retriever = vector_retriever
        self._docstore = docstore
        super().__init__()

    def _retrieve(self, query_bundle: QueryBundle) -> List[NodeWithScore]:
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
