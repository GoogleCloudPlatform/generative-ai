import os

from backend.rag.index_manager import IndexManager
import yaml

# Load configuration from config.yaml
config_path = os.path.join(
    os.path.dirname(__file__), "..", "..", "common", "config.yaml"
)
with open(config_path) as config_file:
    config = yaml.safe_load(config_file)

PROJECT_ID = config["project_id"]
LOCATION = config["location"]
DOCSTORE_BUCKET_NAME = config["docstore_bucket_name"]
VECTOR_INDEX_NAME = config["vector_index_name"]
INDEX_ENDPOINT_NAME = config["index_endpoint_name"]
EMBEDDINGS_MODEL_NAME = config["embeddings_model_name"]
VECTOR_DATA_PREFIX = config["vector_data_prefix"]
FIRESTORE_DB_NAME = config["firestore_db_name"]
FIRESTORE_NAMESPACE = config["firestore_namespace"]
QA_INDEX_NAME = config.get("qa_index_name")
QA_ENDPOINT_NAME = config.get("qa_endpoint_name")
FIRESTORE_DB_NAME = config.get("firestore_db_name")
FIRESTORE_NAMESPACE = config.get("firestore_namespace")
BUCKET_NAME = config.get("docstore_bucket_name")


def test_no_docstore():
    index_manager = IndexManager(
        project_id=PROJECT_ID,
        location=LOCATION,
        embeddings_model_name=EMBEDDINGS_MODEL_NAME,
        base_index_name=VECTOR_INDEX_NAME,
        base_endpoint_name=INDEX_ENDPOINT_NAME,
        qa_index_name=QA_INDEX_NAME,
        qa_endpoint_name=QA_ENDPOINT_NAME,
        firestore_db_name=None,
        firestore_namespace=None,
        vs_bucket_name=BUCKET_NAME,
    )
    assert index_manager.firestore_db_name == None
    assert index_manager.firestore_namespace == None


def test_no_qa_vector_store():
    index_manager = IndexManager(
        project_id=PROJECT_ID,
        location=LOCATION,
        embeddings_model_name=EMBEDDINGS_MODEL_NAME,
        base_index_name=VECTOR_INDEX_NAME,
        base_endpoint_name=INDEX_ENDPOINT_NAME,
        qa_index_name=None,
        qa_endpoint_name=None,
        firestore_db_name=FIRESTORE_DB_NAME,
        firestore_namespace=FIRESTORE_NAMESPACE,
        vs_bucket_name=BUCKET_NAME,
    )
    assert index_manager.qa_index == None
    assert index_manager.qa_endpoint_name == None
    assert index_manager.qa_index_name == None
