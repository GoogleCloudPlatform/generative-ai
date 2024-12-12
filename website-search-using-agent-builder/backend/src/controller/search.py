from fastapi import APIRouter
from src.model.search import CreateSearchRequest, ResponseModel, SearchApplication

from src.service.search import SearchService

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)

@router.post("")
async def search(item: CreateSearchRequest):
    service = SearchService(
        # TODO: Try hitting agent with region="global" and engine_id="genai_1733945255176"
        SearchApplication(
            region="us",
            engine_id="investor_1733324880354"
        )
    )
    return service.search(item.term)