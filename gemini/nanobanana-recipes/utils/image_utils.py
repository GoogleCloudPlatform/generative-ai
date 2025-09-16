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

import os
from PIL import Image
from google.genai import types

def load_image_from_path(path: str) -> types.Part:
    """Loads an image from a file path and returns it as a types.Part."""
    image_data = types.Image.from_file(location=path).image_bytes
    mime_type = "image/png" if path.endswith(".png") else "image/jpeg"
    return types.Part.from_bytes(data=image_data, mime_type=mime_type)

def save_image_to_file(image_data: bytes, folder: str, filename: str):
    """Saves raw image data to a file."""
    if not os.path.exists(folder):
        os.makedirs(folder)
    with open(os.path.join(folder, filename), "wb") as f:
        f.write(image_data)
    print(f"Image saved to {os.path.join(folder, filename)}")

def create_blank_canvas(
    aspect_ratio: str = "1:1",
    width: int = None,
    height: int = None,
    color: str = "white",
) -> types.Part:
    """
    Creates a blank image canvas based on an aspect ratio string or custom dimensions.

    Args:
        aspect_ratio (str): The desired aspect ratio. Supported values are "1:1",
                            "3:4", "4:3", "9:16", "16:9", and "custom".
                            Defaults to "1:1".
        width (int): The width for the custom aspect ratio. Required if
                     aspect_ratio is "custom".
        height (int): The height for the custom aspect ratio. Required if
                      aspect_ratio is "custom".
        color (str): The color of the canvas. Defaults to "white".

    Returns:
        A types.Part object containing the blank canvas image.
    """
    import io

    aspect_ratios = {
        "1:1": (1024, 1024),
        "3:4": (768, 1024),
        "4:3": (1024, 768),
        "9:16": (720, 1280),
        "16:9": (1280, 720),
    }

    if aspect_ratio == "custom":
        if not width or not height:
            raise ValueError("Width and height must be provided for custom aspect ratio.")
        final_width, final_height = width, height
    elif aspect_ratio in aspect_ratios:
        final_width, final_height = aspect_ratios[aspect_ratio]
    else:
        raise ValueError(f"Unsupported aspect ratio: {aspect_ratio}. Supported values are {list(aspect_ratios.keys())} and 'custom'.")

    image = Image.new("RGB", (final_width, final_height), color)
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    image_data = buffer.getvalue()
    return types.Part.from_bytes(data=image_data, mime_type="image/png")
