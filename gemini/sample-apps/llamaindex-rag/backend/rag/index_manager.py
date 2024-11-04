"""Main state management class for indices and prompts for
experimentation UI"""

import logging

import Stemmer
from backend.rag.async_extensions import (
    AsyncHyDEQueryTransform,
    AsyncRetrieverQueryEngine,
    AsyncTransformQueryEngine,
)
from backend.rag.claude_vertex import ClaudeVertexLLM
from backend.rag.node_reranker import CustomLLMRerank
from backend.rag.parent_retriever import ParentRetriever
from backend.rag.prompts import Prompts
from backend.rag.qa_followup_retriever import QAFollowupRetriever, QARetriever
from google.cloud import aiplatform
from llama_index.core import (
    PromptTemplate,
    Settings,
    StorageContext,
    VectorStoreIndex,
    get_response_synthesizer,
)
from llama_index.core.agent import ReActAgent
from llama_index.core.retrievers import AutoMergingRetriever, QueryFusionRetriever
from llama_index.core.tools import QueryEngineTool, ToolMetadata
from llama_index.embeddings.vertex import VertexTextEmbedding
from llama_index.llms.vertex import Vertex
from llama_index.retrievers.bm25 import BM25Retriever
from llama_index.storage.docstore.firestore import FirestoreDocumentStore
from llama_index.vector_stores.vertexaivectorsearch import VertexAIVectorStore

logging.basicConfig(level=logging.INFO)  # Set the desired logging level
logger = logging.getLogger(__name__)


class IndexManager:
    """
    This class manages state for vector indexes,
    docstores, query engines and chat engines
    across the app's lifecycle (e.g. through UI manipulations).
    The index_manager (instantiated) will be injected into all API calls
    that need to access its state or manipulate its state.
    This includes:
    - Switching out vector indices or docstores
    - Changing retrieval parameters (e.g. temperature, llm model, etc.)
    """

    def __init__(
        self,
        project_id: str,
        location: str,
        base_index_name: str,
        base_endpoint_name: str,
        qa_index_name: str | None,
        qa_endpoint_name: str | None,
        embeddings_model_name: str,
        firestore_db_name: str | None,
        firestore_namespace: str | None,
        vs_bucket_name: str,
    ):
        self.project_id = project_id
        self.location = location
        self.embeddings_model_name = embeddings_model_name
        self.base_index_name = base_index_name
        self.base_endpoint_name = base_endpoint_name
        self.qa_index_name = qa_index_name
        self.qa_endpoint_name = qa_endpoint_name
        self.firestore_db_name = firestore_db_name
        self.firestore_namespace = firestore_namespace
        self.vs_bucket_name = vs_bucket_name
        self.embed_model = VertexTextEmbedding(
            model_name=self.embeddings_model_name,
            project=self.project_id,
            location=self.location,
        )
        self.base_index = self.get_vector_index(
            index_name=self.base_index_name,
            endpoint_name=self.base_endpoint_name,
            firestore_db_name=self.firestore_db_name,
            firestore_namespace=self.firestore_namespace,
        )
        if self.qa_endpoint_name and self.qa_index_name:
            self.qa_index = self.get_vector_index(
                index_name=self.qa_index_name,
                endpoint_name=self.qa_endpoint_name,
                firestore_db_name=self.firestore_db_name,
                firestore_namespace=self.firestore_namespace,
            )
        else:
            self.qa_index = None

    def get_current_index_info(self) -> dict:
        """Return the indices currently being used"""
        return {
            "base_index_name": self.base_index_name,
            "base_endpoint_name": self.base_endpoint_name,
            "qa_index_name": self.qa_index_name,
            "qa_endpoint_name": self.qa_endpoint_name,
            "firestore_db_name": self.firestore_db_name,
            "firestore_namespace": self.firestore_namespace,
        }

    def get_vertex_llm(
        self, llm_name: str, temperature: float, system_prompt: str
    ) -> Vertex | ClaudeVertexLLM:
        """Return the LLM currently being used"""
        if "gemini" in llm_name:
            llm = Vertex(
                model=llm_name,
                max_tokens=3000,
                temperature=temperature,
                system_prompt=system_prompt,
            )
        elif "claude" in llm_name:
            llm = ClaudeVertexLLM(
                project_id=self.project_id,
                region="us-east5",
                model_name="claude-3-5-sonnet@20240620",
                max_tokens=3000,
                system_prompt=system_prompt,
            )
        Settings.llm = llm
        return llm

    def set_current_indexes(
        self,
        base_index_name,
        base_endpoint_name,
        qa_index_name: str | None,
        qa_endpoint_name: str | None,
        firestore_db_name: str | None,
        firestore_namespace: str | None,
    ) -> None:
        """Set the current indices to be used for the RAG"""
        self.base_index_name = base_index_name
        self.base_endpoint_name = base_endpoint_name
        self.qa_index_name = qa_index_name
        self.qa_endpoint_name = qa_endpoint_name
        self.firestore_db_name = firestore_db_name
        self.firestore_namespace = firestore_namespace
        self.base_index = self.get_vector_index(
            index_name=self.base_index_name,
            endpoint_name=self.base_endpoint_name,
            firestore_db_name=self.firestore_db_name,
            firestore_namespace=self.firestore_namespace,
        )
        if self.qa_endpoint_name and self.qa_index_name:
            self.qa_index = self.get_vector_index(
                index_name=self.qa_index_name,
                endpoint_name=self.qa_endpoint_name,
                firestore_db_name=self.firestore_db_name,
                firestore_namespace=self.firestore_namespace,
            )
        else:
            self.qa_index = None

    def get_vector_index(
        self,
        index_name: str,
        endpoint_name: str,
        firestore_db_name: str | None,
        firestore_namespace: str | None,
    ) -> VectorStoreIndex:
        """
        Returns a llamaindex VectorStoreIndex object which contains a storage context,
        with an accompanying local document store from Google Cloud Storage.
        """
        # Initialize Vertex AI
        aiplatform.init(project=self.project_id, location=self.location)
        # Get the Vector Search index
        indexes = aiplatform.MatchingEngineIndex.list(
            filter=f'display_name="{index_name}"'
        )
        if not indexes:
            raise ValueError(f"No index found with display name: {index_name}")
        vs_index = indexes[0]
        # Get the Vector Search endpoint
        endpoints = aiplatform.MatchingEngineIndexEndpoint.list(
            filter=f'display_name="{endpoint_name}"'
        )
        if not endpoints:
            raise ValueError(f"No endpoint found with display name: {endpoint_name}")
        vs_endpoint = endpoints[0]
        # Create the vector store
        vector_store = VertexAIVectorStore(
            project_id=self.project_id,
            region=self.location,
            index_id=vs_index.resource_name.split("/")[-1],
            endpoint_id=vs_endpoint.resource_name.split("/")[-1],
            gcs_bucket_name=self.vs_bucket_name,
        )
        if firestore_db_name and firestore_namespace:
            docstore = FirestoreDocumentStore.from_database(
                project=self.project_id,
                database=firestore_db_name,
                namespace=firestore_namespace,
            )
        else:
            docstore = None
        # Create storage context
        storage_context = StorageContext.from_defaults(
            vector_store=vector_store, docstore=docstore
        )
        # Create and return the index
        vector_store_index = VectorStoreIndex(
            nodes=[], storage_context=storage_context, embed_model=self.embed_model
        )
        return vector_store_index

    def get_query_engine(
        self,
        prompts: Prompts,
        llm_name: str = "gemini-1.5-flash",
        temperature: float = 0.0,
        similarity_top_k: int = 5,
        retrieval_strategy: str = "auto_merging",
        use_hyde: bool = True,
        use_refine: bool = True,
        use_node_rerank: bool = False,
        qa_followup: bool = True,
        hybrid_retrieval: bool = True,
    ) -> AsyncRetrieverQueryEngine:
        """
        Creates a llamaindex QueryEngine given a
        VectorStoreIndex and hyperparameters
        """
        llm = self.get_vertex_llm(
            llm_name=llm_name,
            temperature=temperature,
            system_prompt=Prompts.system_prompt,
        )
        Settings.llm = llm

        qa_prompt = PromptTemplate(prompts.qa_prompt_tmpl)
        refine_prompt = PromptTemplate(prompts.refine_prompt_tmpl)

        if use_refine:
            synth = get_response_synthesizer(
                text_qa_template=qa_prompt,
                refine_template=refine_prompt,
                response_mode="compact",
                use_async=True,
            )
        else:
            synth = get_response_synthesizer(
                text_qa_template=qa_prompt, response_mode="compact", use_async=True
            )

        base_retriever = self.base_index.as_retriever(similarity_top_k=similarity_top_k)
        if self.qa_index:
            qa_vector_retriever = self.qa_index.as_retriever(
                similarity_top_k=similarity_top_k
            )
        else:
            qa_vector_retriever = None
        query_engine = None  # Default initialization

        # Choose between retrieval strategies and configurations.
        if retrieval_strategy == "auto_merging":
            logger.info(self.base_index.storage_context.docstore)
            retriever = AutoMergingRetriever(
                base_retriever, self.base_index.storage_context, verbose=True
            )
        elif retrieval_strategy == "parent":
            retriever = ParentRetriever(
                base_retriever, docstore=self.base_index.docstore
            )
        elif retrieval_strategy == "baseline":
            retriever = base_retriever

        if qa_followup:
            qa_retriever = QARetriever(
                qa_vector_retriever=qa_vector_retriever, docstore=self.qa_index.docstore
            )
            retriever = QAFollowupRetriever(
                qa_retriever=qa_retriever, base_retriever=retriever
            )

        if hybrid_retrieval:
            bm25_retriever = BM25Retriever.from_defaults(
                docstore=self.base_index.docstore,
                similarity_top_k=similarity_top_k,
                stemmer=Stemmer.Stemmer("english"),
                language="english",
            )
            retriever = QueryFusionRetriever(
                [retriever, bm25_retriever],
                similarity_top_k=similarity_top_k,
                num_queries=1,  # set this to 1 to disable query generation
                mode="reciprocal_rerank",
                use_async=True,
                verbose=True,
                # query_gen_prompt="...",  # we could override the
                # query generation prompt here
            )

        if use_node_rerank:
            reranker_llm = Vertex(
                model="gemini-1.5-flash",
                max_tokens=8192,
                temperature=temperature,
                system_prompt=prompts.system_prompt,
            )
            choice_select_prompt = PromptTemplate(prompts.choice_select_prompt_tmpl)
            llm_reranker = CustomLLMRerank(
                choice_batch_size=10,
                top_n=5,
                choice_select_prompt=choice_select_prompt,
                llm=reranker_llm,
            )
        else:
            llm_reranker = None

        query_engine = AsyncRetrieverQueryEngine.from_args(
            retriever,
            response_synthesizer=synth,
            node_postprocessors=[llm_reranker] if llm_reranker else None,
        )

        if use_hyde:
            hyde_prompt = PromptTemplate(prompts.hyde_prompt_tmpl)
            hyde = AsyncHyDEQueryTransform(
                include_original=True, hyde_prompt=hyde_prompt
            )
            query_engine = AsyncTransformQueryEngine(
                query_engine=query_engine, query_transform=hyde
            )

        self.query_engine = query_engine
        return query_engine

    def get_react_agent(
        self,
        prompts: Prompts,
        llm_name: str = "gemini-1.5-flash",
        temperature: float = 0.2,
    ) -> ReActAgent:
        """
        Creates a ReAct agent from a given QueryEngine
        """
        query_engine_tools = [
            QueryEngineTool(
                query_engine=self.query_engine,
                metadata=ToolMetadata(
                    name="google_financials",
                    description=(
                        "Provides information about Google financials. "
                        "Use a detailed plain text question as input to the tool."
                    ),
                ),
            )
        ]
        llm = self.get_vertex_llm(
            llm_name=llm_name,
            temperature=temperature,
            system_prompt=prompts.system_prompt,
        )
        Settings.llm = llm
        agent = ReActAgent.from_tools(
            query_engine_tools, llm=llm, verbose=True, context=prompts.system_prompt
        )
        return agent
