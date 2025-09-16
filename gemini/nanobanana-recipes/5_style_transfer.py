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
from utils.image_utils import load_image_from_path, save_image_to_file
from utils.model_utils import extract_image_from_response, generate_image_from_prompt


def main() -> None:
    """Applies a desired style to an input image."""
    # 1. Load the content and style images
    content_image_path = "assets/5_style_transfer/content_image.png"

    content_image = load_image_from_path(content_image_path)

    # 2. Generate the final image using the content image and the style description
    print("Generating the stylized image...")
    final_prompt = "Turn this into a Vincent Van Gogh style painting."

    contents = [
        types.Content(
            role="user",
            parts=[
                types.Part.from_text(text=final_prompt),
                content_image,
            ],
        )
    ]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "5_style_transfer.png")
    else:
        print("No image was generated.")


if __name__ == "__main__":
    main()
