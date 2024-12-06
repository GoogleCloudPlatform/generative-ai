from fastapi import APIRouter

from src.service.models import ModelService

router = APIRouter(
    prefix="/api/models",
    tags=["models"],
    responses={404: {"description": "Not found"}},
)


@router.get("")
async def get_models():
    service = ModelService()
    return service.get_all()