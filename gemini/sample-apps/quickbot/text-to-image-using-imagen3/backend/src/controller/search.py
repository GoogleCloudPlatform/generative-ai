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

from typing import List
from fastapi import APIRouter, HTTPException, status as Status
from pydantic import BaseModel

from src.model.search import CreateSearchRequest, ImageGenerationResult, SearchResponse
from src.service.search import ImagenSearchService

router = APIRouter(
    prefix="/api/search",
    tags=["searches"],
    responses={404: {"description": "Not found"}},
)

@router.post("")
async def search(
    item: CreateSearchRequest,
) -> SearchResponse:
    try:
        # Access parameters from CreateSearchRequest
        term = item.term
        generation_model = item.generation_model
        aspect_ratio = item.aspect_ratio
        number_of_images = item.number_of_images
        image_style = item.image_style

        service = ImagenSearchService()
        return await service.generate_images(
            term=term,
            generation_model=generation_model,
            aspect_ratio=aspect_ratio,
            number_of_images=number_of_images,
            image_style=image_style,
        )
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
