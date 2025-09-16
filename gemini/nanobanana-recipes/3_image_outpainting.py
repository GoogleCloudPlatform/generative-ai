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
from utils.image_utils import save_image_to_file, create_blank_canvas, load_image_from_path
from utils.model_utils import generate_image_from_prompt, extract_image_from_response

def main():
    """
    Extends an existing image by placing it on a larger canvas and asking the model to fill in the rest.
    """

    # Load the source image
    source_image_path = "assets/3_image_outpainting/source_image.png"
    source_image = load_image_from_path(source_image_path)

    # Create a larger canvas for outpainting (e.g., 16:9)
    canvas = create_blank_canvas(aspect_ratio="16:9")

    prompt = "This is a creative outpainting task. Take the provided source image and seamlessly extend it to fill the entire blank canvas. The new areas should logically and stylistically continue the scene from the original image. Imagine what might exist just beyond the borders of the original photo and bring it to life."
    
    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text="Here is the source image:"),
                source_image,
                types.Part.from_text(text="And here is the canvas to extend it onto:"),
                canvas,
                types.Part.from_text(text=prompt)
            ]
        )
    ]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "3_outpainting.png")
    else:
        print("No image was generated.")

if __name__ == "__main__":
    main()
