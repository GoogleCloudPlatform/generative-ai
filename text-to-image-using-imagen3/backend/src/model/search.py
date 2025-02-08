from typing import Optional

import google.auth
from pydantic import BaseModel, ConfigDict
from pydantic.alias_generators import to_camel

_, PROJECT_ID = google.auth.default()


class CreateSearchRequest(BaseModel):
    term: str


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
    enhanced_prompt: str
    rai_filtered_reason: Optional[str]
    image: CustomImageResult
