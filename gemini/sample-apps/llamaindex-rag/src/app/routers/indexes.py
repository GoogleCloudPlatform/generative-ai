from fastapi import APIRouter, Depends, HTTPException
from google.api_core.exceptions import PermissionDenied
from google.api_core.client_options import ClientOptions
from google.cloud import aiplatform, firestore, firestore_admin_v1
from src.app.models import IndexUpdate
from src.app.dependencies import get_index_manager
import logging

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/list_vector_search_indexes")
async def list_vector_search_indexes(
    qa_or_base: dict, index_manager=Depends(get_index_manager)
):
    index_list = [i.display_name for i in aiplatform.MatchingEngineIndex.list()]
    if qa_or_base["qa_or_base"] == "qa":
        active_index_name = index_manager.qa_index_name
    elif qa_or_base["qa_or_base"] == "base":
        active_index_name = index_manager.base_index_name
    if active_index_name is None:
        index_list.insert(0, None)
    else:
        index_list.remove(active_index_name)
        index_list.insert(0, active_index_name)
    return index_list

@router.post("/list_vector_search_endpoints")
async def list_vector_search_endpoints(
    qa_or_base: dict, index_manager=Depends(get_index_manager)
):
    endpoint_list = aiplatform.MatchingEngineIndexEndpoint.list()
    endpoint_list = [e.display_name for e in endpoint_list]
    if qa_or_base["qa_or_base"] == "qa":
        active_endpoint_name = index_manager.qa_endpoint_name
    elif qa_or_base["qa_or_base"] == "base":
        active_endpoint_name = index_manager.base_endpoint_name
    if active_endpoint_name is None:
        endpoint_list.insert(0, None)
    else:
        endpoint_list.remove(active_endpoint_name)
        endpoint_list.insert(0, active_endpoint_name)
    return endpoint_list

@router.get("/list_firestore_databases")
async def list_firestore_databases(index_manager=Depends(get_index_manager)):
    active_db_name = index_manager.firestore_db_name
    client_options = ClientOptions(api_endpoint="firestore.googleapis.com")
    client = firestore_admin_v1.FirestoreAdminClient(client_options=client_options)
    parent = f"projects/{index_manager.project_id}"
    databases = []

    try:
        for database in client.list_databases(parent=parent).databases:
            databases.append(database.name.split("/")[-1])
        logger.info(databases)
        if active_db_name is None:
            databases.insert(0, None)
        else:
            databases.remove(active_db_name)
            databases.insert(0, active_db_name)
        return databases
    except ValueError as e:
        logger.info(f"Could not retrieve Firestore db: {e}")
        return []

@router.post("/list_firestore_collections")
async def list_firestore_collections(
    db_name: dict, index_manager=Depends(get_index_manager)
):
    def get_prefixes(string_list):
        suffixes = ["_metadata", "_data", "_ref_doc_info"]
        prefixes = []
        for s in string_list:
            for suffix in suffixes:
                if s.endswith(suffix):
                    prefixes.append(s[: -len(suffix)])
                    break
            else:
                prefixes.append(s)
        return prefixes

    if db_name["firestore_db_name"]:
        db = firestore.Client(
            project=index_manager.project_id, database=db_name["firestore_db_name"]
        )
    else:
        return []
    try:
        collections = db.collections()
        collection_info = [collection.id for collection in collections]
        collection_info = list(set(get_prefixes(collection_info)))
        active_firestore_namespace = index_manager.firestore_namespace
        if active_firestore_namespace is None:
            collection_info.insert(0, None)
        else:
            collection_info.remove(active_firestore_namespace)
            collection_info.insert(0, active_firestore_namespace)
        return collection_info
    except PermissionDenied:
        logger.error(f"Permission denied. Make sure you have the necessary permissions to access Firestore in project {index_manager.project_id}")
        return []
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return []

@router.get("/get_current_index_info")
async def get_current_index_info(index_manager=Depends(get_index_manager)):
    return index_manager.get_current_index_info()

@router.post("/update_index")
async def update_index(
    index_update: IndexUpdate, index_manager=Depends(get_index_manager)
):
    try:
        index_manager.set_current_indexes(
            index_update.base_index_name,
            index_update.base_endpoint_name,
            index_update.qa_index_name,
            index_update.qa_endpoint_name,
            index_update.firestore_db_name,
            index_update.firestore_namespace,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))