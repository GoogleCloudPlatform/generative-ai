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
from utils.image_utils import save_image_to_file, load_image_from_path
from utils.model_utils import generate_image_from_prompt, extract_image_from_response

def main():
    """
    Edits an existing image based on a text prompt.
    """

    # Load the image to be edited
    image_to_edit_path = "assets/4_image_editing/image_to_edit.png"
    source_image = load_image_from_path(image_to_edit_path)

    prompt = "Please add a red bow tie and a black top hat to the person in the image. Change the background to an elegant ballroom setting with chandeliers and ornate decorations. Ensure the additions look natural and blend seamlessly with the original image."
    
    contents = [
        types.Content(
            role="user",
            parts=[
                source_image,
                types.Part.from_text(text=prompt)
            ]
        )
    ]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "4_edited_image.png")
    else:
        print("No image was generated.")

if __name__ == "__main__":
    main()
