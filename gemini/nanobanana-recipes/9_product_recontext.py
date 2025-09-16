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
    Places a product image into a new, realistic context.
    """

    # Load the product image
    product_path = "assets/9_product_recontext/product.png"
    product_image = load_image_from_path(product_path)

    prompt = "Take the product in this image and place it in a professionally styled kitchen setting, on a marble countertop next to a window with soft, natural light. The final image should look like a high-end advertisement."
    
    contents = [
        types.Content(
            role="user",
            parts=[
                product_image,
                types.Part.from_text(text=prompt)
            ]
        )
    ]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "9_product_recontext.png")
    else:
        print("No image was generated.")

if __name__ == "__main__":
    main()
