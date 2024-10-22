from backend.rag.index_manager import IndexManager
from backend.rag.prompts import Prompts
from common.utils import load_config

config = load_config()

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

# Initialize State of Prompts and Indexes

prompts = Prompts()
index_manager = IndexManager(
    project_id=PROJECT_ID,
    location=LOCATION,
    base_index_name=VECTOR_INDEX_NAME,
    base_endpoint_name=INDEX_ENDPOINT_NAME,
    qa_index_name=QA_INDEX_NAME,
    qa_endpoint_name=QA_ENDPOINT_NAME,
    embeddings_model_name=EMBEDDINGS_MODEL_NAME,
    firestore_db_name=FIRESTORE_DB_NAME,
    firestore_namespace=FIRESTORE_NAMESPACE,
    vs_bucket_name=BUCKET_NAME,
)
