from fastapi import APIRouter
from src.model.search import CreateSearchRequest, ResponseModel
import requests

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)

@router.post("", response_model=ResponseModel)
async def search(item: CreateSearchRequest):
    try:
        final_response = searchViaAgent(item)
        final_response['term'] = item.term 
        print(final_response)
        return ResponseModel(**final_response) 
    except Exception as e: 
        print(f"Error during search: {e}") 
        return {"error": str(e)} 

def searchViaAgent(item):
    
    api_url = "https://discoveryengine.googleapis.com/v1alpha/projects/318457139342/locations/global/collections/default_collection/engines/robin-search-app-2_1733237288232/servingConfigs/default_search:search"
    token = get_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    data = {
        "query": item.term,
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