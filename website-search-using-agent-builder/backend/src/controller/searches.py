from fastapi import APIRouter, HTTPException
from src.model.search import CreateSearchRequest, ResponseModel, SearchRequest
import requests
from google.cloud import discoveryengine_v1
from typing import List

router = APIRouter(
    prefix="/api/searches",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=ResponseModel)
async def search(item: CreateSearchRequest):
    try:
        final_response = searchViaAgent(item)
        final_response['search'] = item.search 
        return ResponseModel(**final_response) 
    except Exception as e: 
        print(f"Error during search: {e}") 
        return {"error": str(e)} 

def searchViaAgent(item):
    
    api_url = "https://discoveryengine.googleapis.com/v1alpha/projects/318457139342/locations/global/collections/default_collection/engines/robin-search-app-2_1733237288232/servingConfigs/default_search:search"
    # api_url = "https://discoveryengine.googleapis.com/v1alpha/projects/318457139342/locations/global/collections/default_collection/engines/robin-docs_1733239862725_gcs_store/servingConfigs/default_search:search"

    # api_url = (
    #     f"https://discoveryengine.googleapis.com/v1alpha/projects/{item.project_id}/locations/{item.location}/"
    #     f"dataStores/{item.engine_id}/servingConfigs/{item.serving_config}:search"
    # )
    
    token = get_token()
    headers = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
    }

    data = {
        "query": item.search,
        "pageSize": 10,
        "queryExpansionSpec": {"condition": "AUTO"},
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": {"snippetSpec": {"returnSnippet": True}}
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status() 
        return response.json() 

    except requests.exceptions.RequestException as e:
        print(f"Error searching with Discovery Engine: {e}")
        raise

@router.post("/agent", response_model=ResponseModel)
async def search(item: SearchRequest):
    try:
        final_response = searchThroughAgent(item)
        final_response['search'] = item.search 
        return ResponseModel(**final_response) 
    except Exception as e: 
        print(f"Error during search: {e}") 
        return {"error": str(e)} 

def searchThroughAgent(item):
    
    # api_url = "https://discoveryengine.googleapis.com/v1alpha/projects/318457139342/locations/global/collections/default_collection/engines/robin-search-app-2_1733237288232/servingConfigs/default_search:search"
    # api_url = "https://discoveryengine.googleapis.com/v1alpha/projects/318457139342/locations/global/collections/default_collection/engines/robin-docs_1733239862725_gcs_store/servingConfigs/default_search:search"

    api_url = (
        f"https://discoveryengine.googleapis.com/v1alpha/projects/{item.project_id}/locations/{item.location}/"
        f"dataStores/{item.engine_id}/servingConfigs/{item.serving_config}:search"
    )
    
    token = get_token()
    headers = {
        'Authorization': f'Bearer {token}',
        "Content-Type": "application/json"
    }

    data = {
        "query": item.search,
        "pageSize": 10,
        "queryExpansionSpec": {"condition": "AUTO"},
        "spellCorrectionSpec": {"mode": "AUTO"},
        "contentSearchSpec": {"snippetSpec": {"returnSnippet": True}}
    }

    try:
        response = requests.post(api_url, headers=headers, json=data)
        response.raise_for_status() 
        return response.json() 

    except requests.exceptions.RequestException as e:
        print(f"Error searching with Discovery Engine: {e}")
        raise     

def get_token():
    """
    Fetches an authentication token from the metadata server.
    """
    
    metadata_server_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/token"
    headers = {
        'Metadata-Flavor': 'Google'
    }

    try:
        response = requests.get(metadata_server_url, headers=headers)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
        token_data = response.json()  # Parse the JSON response
        access_token = token_data['access_token'].strip()  # Extract the access_token
        return access_token

    except requests.exceptions.RequestException as e:
        print(f"Error fetching token: {e}")
        raise

@router.post("/{project_id}/{location}")
async def list_apps(project_id: str, location: str = "global"):
    """
    Endpoint to list applications in Vertex AI Agent Builder running on Discovery Engine.

    Args:
        project_id (str): GCP project ID (passed as a query parameter).
        location (str): Location of the Discovery Engine (default is 'global').

    Returns:
        List of applications with their details.
    """
    client = discoveryengine_v1.DataStoreServiceClient()

    # Construct the parent resource path
    parent = f"projects/{project_id}/locations/{location}"

    try:
        # Fetch DataStores
        response = client.list_data_stores(parent=parent)
        datastores = [
            {
                "datastore_id": datastore.name,
                "display_name": datastore.display_name
            }
            for datastore in response
        ]

        if not datastores:
            return {"message": "No DataStores found in the specified project/location."}

        return {"datastores": datastores}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing apps: {e}")
    

@router.post("/engines/{project_id}/{location}")
async def list_apps(project_id: str, location: str = "global"):
    """
    Endpoint to list applications in Vertex AI Agent Builder running on Discovery Engine.

    Args:
        project_id (str): GCP project ID (passed as a query parameter).
        location (str): Location of the Discovery Engine (default is 'global').

    Returns:
        List of applications with their details.
    """
    client = discoveryengine_v1.DataStoreServiceClient()
    parent = f"projects/{project_id}/locations/{location}"

    try:
        response = client.list_data_stores(parent=parent)
        engines = [
            {
                "engine_id": datastore.name.split("/")[-1],
                "full_name": datastore.name,
                "display_name": datastore.display_name,
                "create_time": datastore.create_time,
            }
            for datastore in response
        ]

        if not engines:
            return {"message": "No engines (DataStores) found."}

        return {"engines": engines}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error listing apps: {e}")    

@router.post("/services/{project_id}/{location}/{engine_id}")
def list_serving_configs(project_id: str, location: str, engine_id: str):
    """
    Lists serving configurations for a specific engine.

    Args:
        project_id (str): GCP project ID.
        location (str): Location of the Discovery Engine.
        engine_id (str): Engine ID.

    Returns:
        List of serving configuration names.
    """
    try:
        # Generate access token
        access_token = get_token()

        # Construct the API endpoint
        url = (
            f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{location}/"
            f"dataStores/{engine_id}/servingConfigs"
        )

        # Make the request
        headers = {
            "Authorization": f"Bearer {access_token}",
        }
        response = requests.get(url, headers=headers)

        if response.status_code == 200:
            serving_configs = response.json().get("servingConfigs", [])
            return {"serving_configs": serving_configs}
        else:
            raise HTTPException(
                status_code=response.status_code,
                detail=f"Error listing serving configs: {response.text}"
            )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {e}")
    