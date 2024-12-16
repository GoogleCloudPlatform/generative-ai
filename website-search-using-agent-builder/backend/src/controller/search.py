from fastapi import APIRouter
from src.model.http_status import BadRequest
from src.model.search import CreateSearchRequest, SearchApplication

from src.service.search import SearchService
from src.service.search_application import SearchApplicationService

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)

@router.post("")
async def search(item: CreateSearchRequest):
    service = SearchApplicationService()
    search_application = service.get()
    if not search_application: raise BadRequest(detail=f"No Search Application found on project") 

    service = SearchService(
        search_application,
    )
    return service.search(item.term)

@router.get("/application")
async def get_search_applications():
    service = SearchApplicationService()
    return service.get()

@router.post("/application")
async def create_search_application(search_application: SearchApplication):
    service = SearchApplicationService()
    return service.create(search_application)

@router.delete("/application/{engine_id}")
async def delete_search_application(engine_id: str):
    service = SearchApplicationService()
    return service.delete(engine_id)

@router.put("/application/{engine_id}")
async def update_search_application(engine_id: str, search_application: SearchApplication):
    service = SearchApplicationService()
    return service.update(engine_id, search_application)