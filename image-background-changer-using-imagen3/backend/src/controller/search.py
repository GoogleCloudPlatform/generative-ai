from typing import List
from fastapi import APIRouter, HTTPException, status as Status

from src.model.search import CreateSearchRequest, ImageGenerationResult
from src.service.search import ImagenSearchService

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)


@router.post("")
async def search(item: CreateSearchRequest) -> List[ImageGenerationResult]:
    try:
        # Access parameters from CreateSearchRequest
        term = item.term
        generation_model = item.generation_model
        aspect_ratio = item.aspect_ratio
        number_of_images = item.number_of_images
        image_style = item.image_style
        user_image=item.user_image

        service = ImagenSearchService()
        return service.generate_images(
            user_image=user_image, 
            term=term,
            generation_model=generation_model,
            aspect_ratio=aspect_ratio,
            number_of_images=number_of_images,
            image_style=image_style,
            
        )
        #return []
    except HTTPException as http_exception:
        raise http_exception
    except ValueError as value_error:
        raise HTTPException(
            status_code=Status.HTTP_400_BAD_REQUEST,
            detail=str(value_error),
        )
    except Exception as e:
        raise HTTPException(
            status_code=Status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e),
        )
