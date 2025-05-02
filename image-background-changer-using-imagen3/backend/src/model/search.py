from typing import Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel


# Create a Literal type from the list of valid models
GenerationModelOptionalLiteral = Union[
    Literal["imagen-3.0-capability-001"], Literal["imagegeneration@006"]
]


class CreateSearchRequest(BaseModel):
    term: str = Field(description="Prompt term to be passed to the model")
    generation_model: Optional[GenerationModelOptionalLiteral] = Field(
        default="imagen-3.0-capability-001",
        description="Model used for image edition",
    )
    number_of_images: Optional[int] = Field(
        4, description="Number of images to generate"
    )
    user_image: bytes
    mask_distilation: Optional[float] = Field(
        0.005,
        description="Dilation percentage of the mask provided. Float between 0 and 1.",
    )


class BaseSchema(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True,
    )


class CustomImageResult(BaseSchema):
    gcs_uri: Optional[str]
    mime_type: str
    encoded_image: str


class ImageGenerationResult(BaseSchema):
    enhanced_prompt: Optional[str]
    rai_filtered_reason: Optional[str]
    image: CustomImageResult
