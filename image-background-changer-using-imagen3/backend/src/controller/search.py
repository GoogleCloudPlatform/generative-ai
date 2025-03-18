from typing import Annotated, Optional
from fastapi import APIRouter, HTTPException, status as Status

from src.model.search import (
    CreateSearchRequest,
    GenerationModelOptionalLiteral,
    ImageStyleLiteral,
)
from src.service.search import ImagenSearchService
from fastapi import Form, File, UploadFile

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)

ALLOWED_IMAGE_TYPES = ["image/jpg", "image/jpeg", "image/png", "image/webp"]


@router.post("")
async def search(
    userImage: Annotated[UploadFile, File()],
    term: Annotated[Optional[str], Form(min_length=10, max_length=200)],
    generationModel: Annotated[
        Optional[GenerationModelOptionalLiteral],
        Form(description="Model used for image edition"),
    ],
    numberOfImages: Annotated[
        Optional[int], Form(ge=1, le=4, description="Number of images to generate")
    ],
    imageStyle: Annotated[
        Optional[ImageStyleLiteral], Form(description="Style of the image")
    ],
    maskDistilation: Annotated[
        Optional[float], Form(ge=0, le=1, description="Dilation percentage of the mask provided. Float between 0 and 1.")
    ],
):
    try:
        if userImage.content_type not in ALLOWED_IMAGE_TYPES:
            raise HTTPException(
                status_code=Status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid image type. Allowed types are: {', '.join(ALLOWED_IMAGE_TYPES)}",
            )
        createSearchRequest = CreateSearchRequest.model_validate(
            {
                "term": term,
                "generation_model": generationModel,
                "number_of_images": numberOfImages,
                "image_style": imageStyle,
                "user_image": userImage.file.read(),
                "mask_distilation": maskDistilation
            }
        )

        service = ImagenSearchService()
        return service.generate_images(createSearchRequest)
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
