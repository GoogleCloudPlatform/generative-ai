"""Extensions to Llamaindex Base classes to allow for asynchronous execution"""

from collections.abc import Sequence
import logging

from llama_index.core.base.response.schema import RESPONSE_TYPE
from llama_index.core.callbacks import CallbackManager
from llama_index.core.indices.query.query_transform.base import BaseQueryTransform
from llama_index.core.prompts import BasePromptTemplate
from llama_index.core.prompts.default_prompts import DEFAULT_HYDE_PROMPT
from llama_index.core.prompts.mixin import PromptDictType, PromptMixinType
from llama_index.core.query_engine import BaseQueryEngine, RetrieverQueryEngine
from llama_index.core.schema import NodeWithScore, QueryBundle, QueryType
from llama_index.core.service_context_elements.llm_predictor import LLMPredictorType
from llama_index.core.settings import Settings
from pydantic import Field

logging.basicConfig(level=logging.INFO)  # Set the desired logging level
logger = logging.getLogger(__name__)


class AsyncTransformQueryEngine(BaseQueryEngine):
    """Transform query engine.

    Applies a query transform to a query bundle before passing
        it to a query engine.

    Args:
        query_engine (BaseQueryEngine): A query engine object.
        query_transform (BaseQueryTransform): A query transform object.
        transform_metadata (Optional[dict]): metadata to pass to the
            query transform.
        callback_manager (Optional[CallbackManager]): A callback manager.

    """

    callback_manager: CallbackManager = Field(
        default_factory=lambda: CallbackManager([]), exclude=True
    )

    def __init__(
        self,
        query_engine: BaseQueryEngine,
        query_transform: BaseQueryTransform,
        transform_metadata: dict | None = None,
        callback_manager: CallbackManager | None = None,
    ) -> None:
        self._query_engine = query_engine
        self._query_transform = query_transform
        self._transform_metadata = transform_metadata
        super().__init__(callback_manager)

    def _get_prompt_modules(self) -> PromptMixinType:
        """Get prompt sub-modules."""
        return {
            "query_transform": self._query_transform,
            "query_engine": self._query_engine,
        }

    async def aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        query_bundle = await self._query_transform._arun(
            query_bundle, metadata=self._transform_metadata
        )
        return await self._query_engine.aretrieve(query_bundle)

    def synthesize(
        self,
        query_bundle: QueryBundle,
        nodes: list[NodeWithScore],
        additional_source_nodes: Sequence[NodeWithScore] | None = None,
    ) -> RESPONSE_TYPE:
        query_bundle = self._query_transform.run(
            query_bundle, metadata=self._transform_metadata
        )
        return self._query_engine.synthesize(
            query_bundle=query_bundle,
            nodes=nodes,
            additional_source_nodes=additional_source_nodes,
        )

    async def arun(
        self,
        query_bundle_or_str: QueryType,
        metadata: dict | None = None,
    ) -> QueryBundle:
        """Run query transform."""
        metadata = metadata or {}
        if isinstance(query_bundle_or_str, str):
            query_bundle = QueryBundle(
                query_str=query_bundle_or_str,
                custom_embedding_strs=[query_bundle_or_str],
            )
        else:
            query_bundle = query_bundle_or_str

        return await self._query_transform._arun(query_bundle, metadata=metadata)

    async def asynthesize(
        self,
        query_bundle: QueryBundle,
        nodes: list[NodeWithScore],
        additional_source_nodes: Sequence[NodeWithScore] | None = None,
    ) -> RESPONSE_TYPE:
        query_bundle = await self._query_transform._arun(
            query_bundle, metadata=self._transform_metadata
        )
        return await self._query_engine.asynthesize(
            query_bundle=query_bundle,
            nodes=nodes,
            additional_source_nodes=additional_source_nodes,
        )

    def _query(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:
        """Answer a query."""
        query_bundle = self._query_transform.run(
            query_bundle, metadata=self._transform_metadata
        )
        return self._query_engine.query(query_bundle)

    async def _aquery(self, query_bundle: QueryBundle) -> RESPONSE_TYPE:
        """Answer a query."""
        query_bundle = await self._query_transform._arun(
            query_bundle, metadata=self._transform_metadata
        )
        return await self._query_engine.aquery(query_bundle)


class AsyncHyDEQueryTransform(BaseQueryTransform):
    """Hypothetical Document Embeddings (HyDE) query transform.

    It uses an LLM to generate hypothetical answer(s) to a given query,
    and use the resulting documents as embedding strings.

    As described in
    `[Precise Zero-Shot Dense Retrieval without Relevance Labels]
    (https://arxiv.org/abs/2212.10496)`
    """

    def __init__(
        self,
        llm: LLMPredictorType | None = None,
        hyde_prompt: BasePromptTemplate | None = None,
        include_original: bool = True,
    ) -> None:
        """Initialize HyDEQueryTransform.

        Args:
            llm_predictor (Optional[LLM]): LLM for generating
                hypothetical documents
            hyde_prompt (Optional[BasePromptTemplate]): Custom prompt for HyDE
            include_original (bool): Whether to include original query
                string as one of the embedding strings
        """
        super().__init__()

        self._llm = llm or Settings.llm
        self._hyde_prompt = hyde_prompt or DEFAULT_HYDE_PROMPT
        self._include_original = include_original

    def _get_prompts(self) -> PromptDictType:
        """Get prompts."""
        return {"hyde_prompt": self._hyde_prompt}

    def _update_prompts(self, prompts: PromptDictType) -> None:
        """Update prompts."""
        if "hyde_prompt" in prompts:
            self._hyde_prompt = prompts["hyde_prompt"]

    def _run(self, query_bundle: QueryBundle, metadata: dict) -> QueryBundle:
        """Run query transform."""
        # TODO: support generating multiple hypothetical docs
        query_str = query_bundle.query_str
        hypothetical_doc = self._llm.predict(self._hyde_prompt, context_str=query_str)
        embedding_strs = [hypothetical_doc]
        if self._include_original:
            embedding_strs.extend(query_bundle.embedding_strs)
        return QueryBundle(
            query_str=query_str,
            custom_embedding_strs=embedding_strs,
        )

    async def _arun(self, query_bundle: QueryBundle) -> QueryBundle:
        """Run query transform."""
        # TODO: support generating multiple hypothetical docs
        query_str = query_bundle.query_str
        hypothetical_doc = await self._llm.apredict(
            self._hyde_prompt, context_str=query_str
        )
        embedding_strs = [hypothetical_doc]
        if self._include_original:
            embedding_strs.extend(query_bundle.embedding_strs)
        return QueryBundle(
            query_str=query_str,
            custom_embedding_strs=embedding_strs,
        )


class AsyncRetrieverQueryEngine(RetrieverQueryEngine):
    """Async Extension of the ReterieverQueryEngine
    to allow for asynchronous post-processing"""

    async def _apply_node_postprocessors(
        self, nodes: list[NodeWithScore], query_bundle: QueryBundle
    ) -> list[NodeWithScore]:
        """Apply node postprocessors."""
        for node_postprocessor in self._node_postprocessors:
            nodes = await node_postprocessor.postprocess_nodes(
                nodes, query_bundle=query_bundle
            )
        return nodes

    async def aretrieve(self, query_bundle: QueryBundle) -> list[NodeWithScore]:
        """Retrieve nodes"""
        nodes = await self._retriever.aretrieve(query_bundle)
        num_nodes = len(nodes)
        logger.info(f"Total nodes retrieved {num_nodes}")
        return await self._apply_node_postprocessors(nodes, query_bundle=query_bundle)
