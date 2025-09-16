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
from utils.image_utils import save_image_to_file, create_blank_canvas
from utils.model_utils import generate_image_from_prompt, extract_image_from_response

def main():
    """
    Generates an image with a specific aspect ratio by providing a canvas.
    """

    # Create a 16:9 canvas
    canvas = create_blank_canvas(aspect_ratio="16:9")

    prompt = "A cinematic, wide-angle shot of a lone astronaut standing on a desolate alien planet, looking up at a swirling, colorful nebula. The planet's surface is rocky and red, and two moons are visible in the sky. Render this scene on the provided canvas to match its 16:9 aspect ratio."
    
    contents = [
        types.Content(
            role="user",
            parts=[
                canvas,
                types.Part.from_text(text=prompt)
            ]
        )
    ]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "2_aspect_ratio.png")
    else:
        print("No image was generated.")

if __name__ == "__main__":
    main()
