import os
from typing import Any, Dict, List, cast

import google.auth
import google.auth.transport.requests
from llama_deploy import ControlPlaneConfig, WorkflowServiceConfig, deploy_workflow
from llama_index.core import (
    Settings,
    SimpleDirectoryReader,
    StorageContext,
    VectorStoreIndex,
)
from llama_index.core.base.base_query_engine import BaseQueryEngine
from llama_index.core.indices.query.query_transform.base import (
    StepDecomposeQueryTransform,
)
from llama_index.core.llms import LLM
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.postprocessor.llm_rerank import LLMRerank
from llama_index.core.prompts import PromptTemplate
from llama_index.core.response_synthesizers import (
    ResponseMode,
    get_response_synthesizer,
)
from llama_index.core.schema import MetadataMode, NodeWithScore, QueryBundle, TextNode
from llama_index.core.workflow import (
    Context,
    Event,
    StartEvent,
    StopEvent,
    Workflow,
    step,
)
from llama_index.embeddings.vertex import VertexTextEmbedding
from llama_index.llms.vertex import Vertex
from llama_index.storage.docstore.firestore import FirestoreDocumentStore
import vertexai
from vertexai.generative_models import HarmBlockThreshold, HarmCategory, SafetySetting

# credentials will now have an API token

project_id = os.environ.get("PROJECT_ID")
location = os.environ.get("LOCATION")
vertexai.init(project=project_id, location=location)

credentials = google.auth.default(quota_project_id=project_id)[0]
request = google.auth.transport.requests.Request()
credentials.refresh(request)


safety_config = [
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_HARASSMENT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
    SafetySetting(
        category=HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT,
        threshold=HarmBlockThreshold.BLOCK_NONE,
    ),
]
embedding_model = VertexTextEmbedding("text-embedding-004", credentials=credentials)
llm = Vertex(
    model="gemini-pro",
    temperature=0.2,
    max_tokens=3000,
    safety_settings=safety_config,
    credentials=credentials,
)

Settings.embed_model = embedding_model
Settings.llm = llm


class RetrieverEvent(Event):
    """Result of running retrieval"""

    nodes: list[NodeWithScore]


class RerankEvent(Event):
    """Result of running reranking on retrieved nodes"""

    nodes: List[NodeWithScore]
    source_nodes: List[NodeWithScore]
    final_response_metadata: Dict[str, Any]


class FirestoreIndexData(Event):
    """Result of indexing documents in Firestore"""

    status: str


class QueryMultiStepEvent(Event):
    """
    Event containing results of a multi-step query process.

    Attributes:
        nodes (List[NodeWithScore]): List of nodes with their associated scores.
        source_nodes (List[NodeWithScore]): List of source nodes with their scores.
        final_response_metadata (Dict[str, Any]): Metadata associated with the final response.
    """

    nodes: List[NodeWithScore]
    source_nodes: List[NodeWithScore]
    final_response_metadata: Dict[str, Any]


class CreateCitationsEvent(Event):
    """Add citations to the nodes."""

    nodes: List[NodeWithScore]
    source_nodes: List[NodeWithScore]
    final_response_metadata: Dict[str, Any]


CITATION_QA_TEMPLATE = PromptTemplate(
    "Your task is to answer the question based on the information given in the sources listed below."
    "Use only the provided sources to answer."
    "Cite the source number(s) for any information you use in your answer (e.g., [1])."
    "Always include at least one source citation in your answer."
    "Only cite a source if you directly use information from it."
    "If the sources don't contain the information needed to answer the question, state that."
    "For example:"
    "Source 1: Apples are red, green, or yellow."
    "Source 2:  Bananas are yellow when ripe."
    "Source 3: Strawberries are red when ripe."
    "Query: Which fruits are red when ripe?"
    "Answer: Apples [1] and strawberries [3] can be red when ripe."
    "------"
    "Below are several numbered sources of information:"
    "------"
    "{context_str}"
    "------"
    "Query: {query_str}"
    "Answer: "
)

CITATION_REFINE_TEMPLATE = PromptTemplate(
    "You have an initial answer to a query."
    "Your job is to improve this answer using the information provided in the numbered sources below. Here's how:"
    " - Read the existing answer and the sources carefully."
    " - Identify any information in the sources that can improve the answer by adding details, making it more accurate, or providing better support."
    " - If the sources provide new information, incorporate it into the answer."
    " - If the sources contradict the existing answer, correct the answer."
    " - If the sources aren't helpful, keep the original answer."
    "Cite the source number(s) for any information you use in your answer (e.g., [1])."
    "We have provided an existing answer: {existing_answer}"
    "Below are several numbered sources of information. "
    "Use them to refine the existing answer. "
    "If the provided sources are not helpful, you will repeat the existing answer."
    "------"
    "{context_msg}"
    "------"
    "Query: {query_str}"
    "Answer: "
)

DEFAULT_CITATION_CHUNK_SIZE = 512
DEFAULT_CITATION_CHUNK_OVERLAP = 20


class RAGWorkflow(Workflow):
    """Defines Workflow class that architects complex Retrieval Augmented Generation (RAG) workflow using Gemini models and Firestore databases."""

    def combine_queries(
        self,
        query_bundle: QueryBundle,
        prev_reasoning: str,
        llm_inner: LLM,
    ) -> QueryBundle:
        """Combine queries using StepDecomposeQueryTransform."""
        transform_metadata = {"prev_reasoning": prev_reasoning}
        return StepDecomposeQueryTransform(llm=llm_inner)(
            query_bundle, metadata=transform_metadata
        )

    def default_stop_fn(self, stop_dict: Dict) -> bool:
        """Stop function for multi-step query combiner."""
        query_bundle = cast(QueryBundle, stop_dict.get("query_bundle"))
        if query_bundle is None:
            raise ValueError("Response must be provided to stop function.")

        return "none" in query_bundle.query_str.lower()

    def create_index(self, dirname: str | None) -> VectorStoreIndex:
        """Create Vector Store Index from documents in Firestore Database"""

        if not dirname:
            return None

        documents = SimpleDirectoryReader(dirname).load_data(show_progress=True)
        print(len(documents))
        print("Data loaded into Documents.")

        # create (or load) docstore and add nodes
        docstore = FirestoreDocumentStore.from_database(
            project=os.environ.get("PROJECT_ID"),
            database=os.environ.get("FIRESTORE_DATABASE_ID"),
        )

        docstore.add_documents(documents)
        print("Firestore document store created with documents")

        # create storage context
        storage_context = StorageContext.from_defaults(docstore=docstore)

        # setup index
        index = VectorStoreIndex.from_documents(
            documents=documents, storage_context=storage_context
        )

        print("Vector Store Index created")
        return index

    async def multi_query_inner_loop(
        self, query_engine: BaseQueryEngine, query: str, num_steps: int, cur_steps: int
    ) -> tuple[list[str], list[NodeWithScore], Dict[str, Any]] | None:
        """Helper function to execute the query loop."""

        # pylint: disable=too-many-locals
        prev_reasoning = ""
        cur_response = None
        should_stop = False

        final_response_metadata: Dict[str, Any] = {"sub_qa": []}
        text_chunks: list[str] = []
        source_nodes: list[NodeWithScore] = []
        stop_fn = self.default_stop_fn

        while not should_stop:
            if num_steps is not None and cur_steps >= num_steps:
                should_stop = True
                break

            print(llm)
            updated_query_bundle = self.combine_queries(
                QueryBundle(query_str=query),
                prev_reasoning,
                llm_inner=Settings.llm,
            )

            print(
                f"Created query for the step - {cur_steps} is: {updated_query_bundle}"
            )

            stop_dict = {"query_bundle": updated_query_bundle}
            if stop_fn(stop_dict):
                should_stop = True
                break

            cur_response = query_engine.query(updated_query_bundle)

            # append to response builder
            cur_qa_text = (
                f"\nQuestion: {updated_query_bundle.query_str}\n"
                f"Answer: {cur_response!s}"
            )
            text_chunks.append(cur_qa_text)
            for source_node in cur_response.source_nodes:
                print(source_node)
                source_nodes.append(source_node)

            # update metadata
            final_response_metadata["sub_qa"].append(
                (updated_query_bundle.query_str, cur_response)
            )

            prev_reasoning += (
                f"- {updated_query_bundle.query_str}\n" f"- {cur_response!s}\n"
            )
            cur_steps += 1

        return text_chunks, source_nodes, final_response_metadata

    @step(pass_context=True)
    async def query_multistep(
        self, ctx: Context, ev: StartEvent
    ) -> QueryMultiStepEvent | None:
        """Entry point for RAG, triggered by a StartEvent with `query`. Execute multi-step query process."""

        query = ev.get("query")
        dirname = os.environ.get("DATA_DIRECTORY")

        index = self.create_index(dirname)

        cur_steps = 0

        if not query:
            return None

        print(f"Query the database with: {query}")

        # store the query in the global context
        await ctx.set("query", query)

        # get the index from the global context
        if index is None:
            print("Index is empty, load some documents before querying!")
            return None

        num_steps = ev.get("num_steps")
        print(num_steps)
        query_engine = index.as_query_engine()

        result = await self.multi_query_inner_loop(
            query_engine, query, num_steps, cur_steps
        )
        if result is None:
            return None

        text_chunks, source_nodes, final_response_metadata = result

        nodes = [
            NodeWithScore(node=TextNode(text=text_chunk)) for text_chunk in text_chunks
        ]
        return QueryMultiStepEvent(
            nodes=nodes,
            source_nodes=source_nodes,
            final_response_metadata=final_response_metadata,
        )

    @step()
    async def rerank(self, ctx: Context, ev: QueryMultiStepEvent) -> RerankEvent:
        """Reranking the nodes based on the initial query."""

        print("Entered the rerank event")
        # Rerank the nodes
        ranker = LLMRerank(choice_batch_size=5, top_n=10, llm=Settings.llm)
        print(await ctx.get("query", default=None), flush=True)
        try:
            new_nodes = ranker.postprocess_nodes(
                ev.nodes, query_str=await ctx.get("query", default=None)
            )
        except IndexError as ex:
            print(f"IndexError occurred during reranking: {ex}")
            print("Using previous nodes instead.")
            new_nodes = ev.nodes

        print(f"Reranked nodes to {len(new_nodes)}")
        return RerankEvent(
            nodes=new_nodes,
            source_nodes=ev.source_nodes,
            final_response_metadata=ev.final_response_metadata,
        )

    @step()
    async def create_citation_nodes(self, ev: RerankEvent) -> CreateCitationsEvent:
        """
        Modify retrieved nodes to create granular sources for citations.

        Takes a list of NodeWithScore objects and splits their content
        into smaller chunks, creating new NodeWithScore objects for each chunk.
        Each new node is labeled as a numbered source, allowing for more precise
        citation in query results.

        Args:
            nodes (List[NodeWithScore]): A list of NodeWithScore objects to be processed.

        Returns:
            List[NodeWithScore]: A new list of NodeWithScore objects, where each object
            represents a smaller chunk of the original nodes, labeled as a source.
        """
        print("Entered create citation event")
        nodes = ev.nodes

        new_nodes: List[NodeWithScore] = []

        text_splitter = SentenceSplitter(
            chunk_size=DEFAULT_CITATION_CHUNK_SIZE,
            chunk_overlap=DEFAULT_CITATION_CHUNK_OVERLAP,
        )

        for node in nodes:

            print(node)

            text_chunks = text_splitter.split_text(
                node.node.get_content(metadata_mode=MetadataMode.NONE)
            )

            for text_chunk in text_chunks:
                text = f"Source {len(new_nodes)+1}:\n{text_chunk}\n"

                new_node = NodeWithScore(
                    node=TextNode.model_validate(node.node), score=node.score
                )
                new_node.node.text = text
                new_nodes.append(new_node)
        return CreateCitationsEvent(
            nodes=new_nodes,
            source_nodes=ev.source_nodes,
            final_response_metadata=ev.final_response_metadata,
        )

    @step()
    async def synthesize(self, ctx: Context, ev: CreateCitationsEvent) -> StopEvent:
        """Return a streaming response using reranked nodes."""

        print("Synthesizing final result...")

        response_synthesizer = get_response_synthesizer(
            llm=Vertex(model="gemini-1.0-pro", temperature=0.1, max_tokens=5000),
            text_qa_template=CITATION_QA_TEMPLATE,
            refine_template=CITATION_REFINE_TEMPLATE,
            response_mode=ResponseMode.COMPACT,
            use_async=True,
        )
        query = await ctx.get("query", default=None)
        response = await response_synthesizer.asynthesize(
            query, nodes=ev.nodes, additional_source_nodes=ev.source_nodes
        )
        return StopEvent(result=response)


async def main() -> None:
    """Deploys Workflow service."""

    print("starting deploy workflow creation")
    await deploy_workflow(
        workflow=RAGWorkflow(timeout=200),
        workflow_config=WorkflowServiceConfig(
            host="0.0.0.0",
            port=8002,
            service_name="my_workflow",  # This will make it accessible to all interfaces on the host
        ),
        control_plane_config=ControlPlaneConfig(),
    )
    print("Created workflow successfully")


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
