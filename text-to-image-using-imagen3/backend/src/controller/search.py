from fastapi import APIRouter

from src.model.search import CreateSearchRequest
from src.service.search import ImagenSearchService

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)


@router.post("")
async def search(item: CreateSearchRequest):
    service = ImagenSearchService()
    return service.generate_images(item.term)
