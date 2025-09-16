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

from google.genai import types
from utils.client import get_gemini_client
from utils.image_utils import save_image_to_file, load_image_from_path, create_blank_canvas
from utils.model_utils import generate_image_from_prompt, extract_image_from_response
import os

def main():
    """
    Creates a new image by combining elements from multiple reference images.
    """

    # Create a 16:9 canvas
    canvas = create_blank_canvas(aspect_ratio="16:9")

    # Load the reference images
    ref_paths = os.listdir("assets/7_multiple_references")
    ref_images = [load_image_from_path(os.path.join("assets/7_multiple_references", path)) for path in ref_paths]
    
    prompt = "List all elements of the provided images, then create a new image that combines those elements into a consistent bedroom scene. Use empty bedroom as base preserving its camera angle. Render the final result on the provided blank canvas to ensure a 16:9 aspect ratio."
    
    contents = [
        types.Content(
            role="user",
            parts=[
                *ref_images,
                canvas,
                types.Part.from_text(text=prompt)
            ]
        )
    ]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "7_multiple_references.png")
    else:
        print("No image was generated.")

if __name__ == "__main__":
    main()
