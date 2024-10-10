"""Master script for parsing, embedding
and indexing data living in a GCS bucket"""

import asyncio
import logging
import os

from backend.indexing.docai_parser import DocAIParser
from backend.indexing.prompts import QA_EXTRACTION_PROMPT, QA_PARSER_PROMPT
from backend.indexing.vector_search_utils import (
    get_or_create_existing_index,
)  # noqa: E501
from common.utils import (
    create_pdf_blob_list,
    download_bucket_with_transfer_manager,
    link_nodes,
)
from google.cloud import aiplatform
from llama_index.core import Document, Settings, StorageContext, VectorStoreIndex
from llama_index.core.extractors import QuestionsAnsweredExtractor
from llama_index.core.node_parser import HierarchicalNodeParser, SentenceSplitter
from llama_index.core.program import LLMTextCompletionProgram
from llama_index.core.schema import NodeRelationship, RelatedNodeInfo, TextNode
from llama_index.embeddings.vertex import VertexTextEmbedding
from llama_index.llms.vertex import Vertex
from llama_index.storage.docstore.firestore import FirestoreDocumentStore
from llama_index.vector_stores.vertexaivectorsearch import VertexAIVectorStore
from pydantic import BaseModel
from tqdm.asyncio import tqdm_asyncio
import yaml

logging.basicConfig(level=logging.INFO)  # Set the desired logging level
logger = logging.getLogger(__name__)


# Load configuration from config.yaml
def load_config():
    config_path = os.path.join(
        os.path.dirname(__file__), "..", "..", "common", "config.yaml"
    )
    with open(config_path) as config_file:
        return yaml.safe_load(config_file)


# Load configuration
config = load_config()

# Initialize parameters
PROJECT_ID = config["project_id"]
LOCATION = config["location"]
INPUT_BUCKET_NAME = config["input_bucket_name"]
DOCSTORE_BUCKET_NAME = config["docstore_bucket_name"]
INDEX_ID = config["index_id"]
VECTOR_INDEX_NAME = config["vector_index_name"]
INDEX_ENDPOINT_NAME = config["index_endpoint_name"]
INDEXING_METHOD = config["indexing_method"]
CHUNK_SIZES = config["chunk_sizes"]
EMBEDDINGS_MODEL_NAME = config["embeddings_model_name"]
APPROXIMATE_NEIGHBORS_COUNT = config["approximate_neighbors_count"]
BUCKET_PREFIX = config["bucket_prefix"]
VECTOR_DATA_PREFIX = config["vector_data_prefix"]
CHUNK_SIZE = config.get("chunk_size", 512)
CHUNK_OVERLAP = config.get("chunk_overlap", 50)
DOCAI_LOCATION = config["docai_location"]
DOCAI_PROCESSOR_DISPLAY_NAME = config["document_ai_processor_display_name"]
DOCAI_PROCESSOR_ID = config.get("docai_processor_id")
CREATE_DOCAI_PROCESSOR = config.get("create_docai_processor", False)
FIRESTORE_DB_NAME = config.get("firestore_db_name")
FIRESTORE_NAMESPACE = config.get("firestore_namespace")
QA_INDEX_NAME = config.get("qa_index_name")
QA_ENDPOINT_NAME = config.get("qa_endpoint_name")


class QuesionsAnswered(BaseModel):
    """List of Questions Answered by Document"""

    questions_list: list[str]


def create_qa_index(li_docs, docstore, embed_model, llm):
    """creates index of hypothetical questions"""
    qa_index, qa_endpoint = get_or_create_existing_index(
        QA_INDEX_NAME, QA_ENDPOINT_NAME, APPROXIMATE_NEIGHBORS_COUNT
    )
    qa_vector_store = VertexAIVectorStore(
        project_id=PROJECT_ID,
        region=LOCATION,
        index_id=qa_index.name,  # Use .name instead of .resource_name
        endpoint_id=qa_endpoint.name,
        gcs_bucket_name=DOCSTORE_BUCKET_NAME,
    )
    qa_extractor = QuestionsAnsweredExtractor(
        llm, questions=5, prompt_template=QA_EXTRACTION_PROMPT
    )

    async def extract_batch(li_docs):
        return await tqdm_asyncio.gather(
            *[qa_extractor._aextract_questions_from_node(doc) for doc in li_docs]
        )

    loop = asyncio.get_event_loop()
    metadata_list = loop.run_until_complete(extract_batch(li_docs))

    program = LLMTextCompletionProgram.from_defaults(
        output_cls=QuesionsAnswered,
        prompt_template_str=QA_PARSER_PROMPT,
        verbose=True,
    )

    async def parse_batch(metadata_list):
        return await asyncio.gather(
            *[program.acall(questions_list=x) for x in metadata_list],
            return_exceptions=True,
        )

    parsed_questions = loop.run_until_complete(parse_batch(metadata_list))

    loop.close()

    q_docs = []
    for doc, questions in zip(li_docs, parsed_questions):
        if isinstance(questions, Exception):
            logger.info(f"Unparsable questions exception {questions}")
            continue
        else:
            for q in questions.questions_list:
                logger.info(f"Question extracted: {q}")
                q_doc = Document(text=q)
                q_doc.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
                    node_id=doc.doc_id
                )
                q_docs.append(q_doc)
    docstore.add_documents(li_docs)
    storage_context = StorageContext.from_defaults(
        docstore=docstore, vector_store=qa_vector_store
    )
    VectorStoreIndex(
        nodes=q_docs,
        storage_context=storage_context,
        embed_model=embed_model,
        llm=llm,
    )


def create_hierarchical_index(li_docs, docstore, vector_store, embed_model, llm):
    # Let hierarchical node parser take care of granular chunking
    node_parser = HierarchicalNodeParser.from_defaults(chunk_sizes=CHUNK_SIZES)
    nodes = node_parser.get_nodes_from_documents(li_docs)

    leaf_nodes = node_parser.get_leaf_nodes(nodes)
    num_leaf_nodes = len(leaf_nodes)
    num_nodes = len(nodes)
    logger.info(f"There are {num_leaf_nodes} leaf_nodes and {num_nodes} total nodes")
    docstore.add_documents(nodes)
    storage_context = StorageContext.from_defaults(
        docstore=docstore, vector_store=vector_store
    )
    VectorStoreIndex(
        nodes=leaf_nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        llm=llm,
    )


def create_flat_index(li_docs, docstore, vector_store, embed_model, llm):
    sentence_splitter = SentenceSplitter(chunk_size=CHUNK_OVERLAP)
    # Chunk into granular chunks manually
    node_chunk_list = []
    for doc in li_docs:
        doc_dict = doc.to_dict()
        metadata = doc_dict.pop("metadata")
        doc_dict.update(metadata)
        chunks = sentence_splitter.get_nodes_from_documents([doc])

        # Create nodes with relationships and flatten
        nodes = []
        for chunk in chunks:
            text = chunk.pop("text")
            doc_source_id = doc.doc_id
            node = TextNode(text=text, metadata=chunk)
            node.relationships[NodeRelationship.SOURCE] = RelatedNodeInfo(
                node_id=doc_source_id
            )
            nodes.append(node)

        nodes = link_nodes(nodes)
        node_chunk_list.extend(nodes)

    nodes = node_chunk_list
    logger.info("embedding...")
    docstore.add_documents(li_docs)
    storage_context = StorageContext.from_defaults(
        docstore=docstore, vector_store=vector_store
    )

    for node in nodes:
        node.metadata.pop("excluded_embed_metadata_keys", None)
        node.metadata.pop("excluded_llm_metadata_keys", None)

    # Creating an index automatically embeds and creates the
    # vector db collection
    VectorStoreIndex(
        nodes=nodes,
        storage_context=storage_context,
        embed_model=embed_model,
        llm=llm,
    )


def main():
    """Main parsing, embedding and indexing logic for data living in GCS"""
    # Initialize Vertex AI and create index and endpoint
    aiplatform.init(project=PROJECT_ID, location=LOCATION)

    # Creating Vector Search Index
    vs_index, vs_endpoint = get_or_create_existing_index(
        VECTOR_INDEX_NAME, INDEX_ENDPOINT_NAME, APPROXIMATE_NEIGHBORS_COUNT
    )

    # Vertex AI Vector Search Vector DB and Firestore Docstore
    vector_store = VertexAIVectorStore(
        project_id=PROJECT_ID,
        region=LOCATION,
        index_id=vs_index.name,  # Use .name instead of .resource_name
        endpoint_id=vs_endpoint.name,  # Use .name instead of .resource_name
        gcs_bucket_name=DOCSTORE_BUCKET_NAME,
    )

    docstore = FirestoreDocumentStore.from_database(
        project=PROJECT_ID, database=FIRESTORE_DB_NAME, namespace=FIRESTORE_NAMESPACE
    )

    # Setup embedding model and LLM
    embed_model = VertexTextEmbedding(
        model_name=EMBEDDINGS_MODEL_NAME, project=PROJECT_ID, location=LOCATION
    )
    llm = Vertex(model="gemini-1.5-flash", temperature=0.0)
    Settings.llm = llm
    Settings.embed_model = embed_model

    # Initialize Document AI parser
    GCS_OUTPUT_PATH = f"gs://{DOCSTORE_BUCKET_NAME}/{VECTOR_DATA_PREFIX}/docai_output/"

    parser = DocAIParser(
        project_id=PROJECT_ID,
        location=DOCAI_LOCATION,
        processor_name=f"projects/{PROJECT_ID}/locations/{DOCAI_LOCATION}/processors/{DOCAI_PROCESSOR_ID}",  # noqa: E501
        gcs_output_path=GCS_OUTPUT_PATH,
    )

    # Download data from specified bucket and parse
    local_data_path = os.path.join("/tmp", BUCKET_PREFIX)
    os.makedirs(local_data_path, exist_ok=True)
    blobs = create_pdf_blob_list(INPUT_BUCKET_NAME, BUCKET_PREFIX)
    logger.info("downloading data")
    download_bucket_with_transfer_manager(
        INPUT_BUCKET_NAME, prefix=BUCKET_PREFIX, destination_directory=local_data_path
    )

    # Parse documents using Document AI
    try:
        parsed_docs, raw_results = parser.batch_parse(
            blobs, chunk_size=CHUNK_SIZE, include_ancestor_headings=True
        )
        print(f"Number of documents parsed by Document AI: {len(parsed_docs)}")
        if parsed_docs:
            print(
                f"First parsed document text (first 100 chars): {parsed_docs[0].text[:100]}..."  # noqa: E501
            )
        else:
            print("No documents were parsed by Document AI.")

        # Print raw results for debugging
        print("Raw results:")
        for result in raw_results:
            print(f"  Source: {result.source_path}")
            print(f"  Parsed: {result.parsed_path}")
    except Exception as e:
        print(f"Error processing single document: {str(e)}")
        parsed_docs = []
        raw_results = []

    # Turn each parsed document into a llamaindex Document
    li_docs = [Document(text=doc.text, metadata=doc.metadata) for doc in parsed_docs]

    if QA_INDEX_NAME or QA_ENDPOINT_NAME:
        create_qa_index(li_docs, docstore, embed_model, llm)

    if INDEXING_METHOD == "hierarchical":
        create_hierarchical_index(li_docs, docstore, vector_store, embed_model, llm)

    elif INDEXING_METHOD == "flat":
        create_flat_index(li_docs, docstore, vector_store, embed_model, llm)


if __name__ == "__main__":
    main()
