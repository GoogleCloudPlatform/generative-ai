import logging

from backend.app.dependencies import get_index_manager
from backend.app.models import IndexUpdate
from fastapi import APIRouter, Depends, HTTPException
from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import PermissionDenied
from google.cloud import aiplatform, firestore, firestore_admin_v1

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/list_vector_search_indexes_and_endpoints")
async def list_vector_search_indexes_and_endpoints(
    index_manager=Depends(get_index_manager),
) -> dict:
    index_list = [i.display_name for i in aiplatform.MatchingEngineIndex.list()]
    endpoint_list = [
        e.display_name for e in aiplatform.MatchingEngineIndexEndpoint.list()
    ]

    def organize_list(items, active_item):
        if active_item is None:
            items.insert(0, None)
        else:
            items.remove(active_item)
            items.insert(0, active_item)
        return items

    return {
        "qa": {
            "indexes": organize_list(index_list.copy(), index_manager.qa_index_name),
            "endpoints": organize_list(
                endpoint_list.copy(), index_manager.qa_endpoint_name
            ),
        },
        "base": {
            "indexes": organize_list(index_list.copy(), index_manager.base_index_name),
            "endpoints": organize_list(
                endpoint_list.copy(), index_manager.base_endpoint_name
            ),
        },
    }


@router.get("/list_firestore_databases")
async def list_firestore_databases(index_manager=Depends(get_index_manager)) -> dict:
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
) -> dict:
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
        logger.error(
            f"Permission denied. Make sure you have the necessary permissions to access Firestore in project {index_manager.project_id}"
        )
        return []
    except Exception as e:
        logger.error(f"An error occurred: {e}")
        return []


@router.get("/get_current_index_info")
async def get_current_index_info(index_manager=Depends(get_index_manager)) -> dict:
    return index_manager.get_current_index_info()


@router.post("/update_index")
async def update_index(
    index_update: IndexUpdate, index_manager=Depends(get_index_manager)
) -> None:
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
