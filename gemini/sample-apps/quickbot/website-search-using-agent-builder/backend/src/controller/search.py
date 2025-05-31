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

"""API endpoints for managing and performing website searches."""

from fastapi import APIRouter
from src.model.http_status import BadRequest
from src.model.search import CreateSearchRequest, SearchApplication

from src.service.engine import EngineService
from src.service.search import SearchService
from src.service.search_application import SearchApplicationService

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
        raise BadRequest(detail=f"No Search Application found on project")

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
