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
    Restores an old or damaged photograph.
    """

    # Load the damaged photo
    damaged_photo_path = "assets/6_photo_restoration/damaged_photo.png"
    damaged_photo = load_image_from_path(damaged_photo_path)

    prompt = "Restore and recolor this old photograph as if it was taken by a modern digital camera. Your output shall solely be extracted photograph. ignore surroundings and fill all canvas by the photograph"
    
    contents = [
        types.Content(
            role="user",
            parts=[
                damaged_photo,
                types.Part.from_text(text=prompt)
            ]
        )
    ]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "6_restored_photo.png")
    else:
        print("No image was generated.")

if __name__ == "__main__":
    main()
