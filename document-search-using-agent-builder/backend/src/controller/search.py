# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""API endpoints for managing and performing document searches."""

from fastapi import APIRouter, Request, HTTPException, Response
from google.cloud import storage
from pydantic import BaseModel
from src.model.http_status import BadRequest
from src.model.search import CreateSearchRequest, SearchApplication
from src.service.engine import EngineService
from src.service.search import SearchService
from src.service.search_application import SearchApplicationService


class SignedUrlRequest(BaseModel):
    """Request model for fetching a document directly from GCS."""

    gcs_url: str


storage_client = storage.Client()

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)


@router.post("")
async def search(item: CreateSearchRequest):
    """
    Performs a search using the configured Search Application.

    Args:
        item: The search request containing the search term.

    Raises:
        BadRequest: If no Search Application is configured for the project.

    Returns:
        The search results from the SearchService.
    """
    service = SearchApplicationService()
    search_application = service.get()
    if not search_application:
        raise BadRequest(detail="No Search Application found on project")

    service = SearchService(
        search_application,
    )
    return service.search(item.term)


@router.get("/engines")
async def get_all_engines():
    """Retrieves all available Search Engines."""
    service = EngineService()
    return service.get_all()


@router.get("/application")
async def get_search_application():
    """Retrieves the currently configured Search Application."""
    service = SearchApplicationService()
    return service.get()


@router.post("/application")
async def create_search_application(search_application: SearchApplication):
    """
    Creates a new Search Application configuration.

    Args:
        search_application: The details of the Search Application to create.

    Returns:
        The created Search Application configuration.
    """
    service = SearchApplicationService()
    return service.create(search_application)


@router.put("/application/{engine_id}")
async def update_search_application(
    engine_id: str, search_application: SearchApplication
):
    """
    Updates an existing Search Application configuration.

    Args:
        engine_id: The ID of the engine associated with 
        the application to update.
        search_application: The updated details for the Search Application.

    Returns:
        The updated Search Application configuration.
    """
    service = SearchApplicationService()
    return service.update(engine_id, search_application)


@router.post("/doc")
async def get_document(request: Request, response_model=None):
    """
    Fetches a document directly from GCS and returns its content.

    Expects a JSON body with a 'gcs_url' field specifying the full GCS path
    (e.g., "gs://your-bucket-name/your-file.pdf").

    Args:
        request: The incoming FastAPI request object.

    Raises:
        HTTPException: If the GCS URL is invalid or the file cannot be fetched.

    Returns:
        A FastAPI Response object containing the raw PDF content.
    """
    try:
        req_body = await request.json()
        signed_url_request = SignedUrlRequest(**req_body)
        gcs_url = signed_url_request.gcs_url

        bucket_name = gcs_url.split("/")[2]
        object_name = "/".join(gcs_url.split("/")[3:])

        # Get a reference to the blob (PDF file)
        bucket = storage_client.bucket(bucket_name)
        blob = bucket.blob(object_name)

        # Download the blob content as bytes
        pdf_content = blob.download_as_bytes()

        # Return the PDF content with appropriate headers
        return Response(content=pdf_content, media_type="application/pdf")

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Error fetching PDF: {str(e)}"
        )
