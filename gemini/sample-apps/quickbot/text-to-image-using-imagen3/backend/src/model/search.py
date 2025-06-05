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

from typing import Annotated, List, Literal, Optional, Union

from fastapi import Query
from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel


# Create a Literal type from the list of valid models
GenerationModelOptionalLiteral = Union[
    Literal["imagen-4.0-ultra-generate-exp-05-20"],
    Literal["imagen-3.0-generate-001"],
    Literal["imagen-3.0-fast-generate-001"],
    Literal["imagen-3.0-generate-002"],
    Literal["imagegeneration@006"],
    Literal["imagegeneration@005"],
    Literal["imagegeneration@002"],
]

AspectRatioLiteral = Union[
    Literal["1:1"],
    Literal["9:16"],
    Literal["16:9"],
    Literal["3:4"],
    Literal["4:3"],
]

ImageStyleLiteral = Union[
    Literal["Modern"],
    Literal["Realistic"],
    Literal["Vintage"],
    Literal["Monochrome"],
    Literal["Fantasy"],
    Literal["Sketch"],
]


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class CreateSearchRequest(BaseSchema):
    term: Annotated[str, Query(max_length=150)] = Field(
        description="Prompt term to be passed to the model"
    )
    generation_model: Annotated[
        Optional[GenerationModelOptionalLiteral],
        Query(description="Model used for image generation"),
    ] = Field(
        description="Model used for image generation",
    )
    aspect_ratio: Annotated[
        Optional[AspectRatioLiteral],
        Query(description="Aspect ratio of the image"),
    ] = Field(description="Aspect ratio of the image")
    number_of_images: Annotated[
        Optional[int],
        Field(ge=1, le=4, description="Number of images to generate"),
    ] = Field(description="Number of images to generate")
    image_style: Annotated[
        Optional[ImageStyleLiteral], Query(description="Style of the image")
    ] = Field(description="Style of the image")

    @field_validator("term")
    def term_must_not_be_empty(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("Term cannot be empty or whitespace only")
        return value


class CustomImageResult(BaseSchema):
    gcs_uri: Optional[str]
    mime_type: str
    encoded_image: str


class ImageGenerationResult(BaseSchema):
    enhanced_prompt: str
    rai_filtered_reason: Optional[str]
    image: CustomImageResult


class SearchResponse(BaseSchema):
    gemini_results: List[ImageGenerationResult]
    imagen_results: List[ImageGenerationResult]
