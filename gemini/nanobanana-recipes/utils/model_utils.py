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

from google.genai import client, types

from .client import get_gemini_client

client = get_gemini_client()

model = "gemini-2.5-flash-image-preview"

generate_content_config = types.GenerateContentConfig(
    temperature=1,
    top_p=0.95,
    max_output_tokens=32768,
    response_modalities=["TEXT", "IMAGE"],
    safety_settings=[
        types.SafetySetting(category="HARM_CATEGORY_HATE_SPEECH", threshold="OFF"),
        types.SafetySetting(
            category="HARM_CATEGORY_DANGEROUS_CONTENT", threshold="OFF"
        ),
        types.SafetySetting(
            category="HARM_CATEGORY_SEXUALLY_EXPLICIT", threshold="OFF"
        ),
        types.SafetySetting(category="HARM_CATEGORY_HARASSMENT", threshold="OFF"),
    ],
)


def generate_text(
    model: str,
    contents: list,
) -> types.GenerateContentResponse:
    """Makes a generate_content call to the model.

    Args:
        model: The generative model client.
        contents: A list of contents for the prompt.
        config: The generation configuration.

    Returns:
        The response from the model.
    """
    return client.models.generate_content(
        model=model,
        contents=contents,
    )


def generate_image_from_prompt(
    contents: list,
) -> types.GenerateContentResponse:
    """Makes a generate_content call to the model.

    Args:
        model: The generative model client.
        contents: A list of contents for the prompt.
        config: The generation configuration.

    Returns:
        The response from the model.
    """
    return client.models.generate_content(
        model=model, contents=contents, config=generate_content_config
    )


def extract_image_from_response(
    response: types.GenerateContentResponse,
) -> bytes | None:
    """Safely extracts the image data from a model's response.

    Args:
        response: The response from the model.

    Returns:
        The raw image data as bytes, or None if no image is found.
    """
    image_part = next(
        (
            part
            for part in response.candidates[0].content.parts
            if hasattr(part, "inline_data") and hasattr(part.inline_data, "data")
        ),
        None,
    )
    if image_part:
        return image_part.inline_data.data
    return None
