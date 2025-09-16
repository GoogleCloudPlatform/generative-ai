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
    """Performs a virtual try-on, placing a garment onto a model."""
    # Load the model and garment images
    model_path = "assets/8_virtual_try_on/model.png"
    garment_path = "assets/8_virtual_try_on/garment.png"

    model_image = load_image_from_path(model_path)
    garment_image = load_image_from_path(garment_path)

    prompt = "Take the garment from the second image and realistically place it on the person in the first image. Adjust the fit, lighting, and shadows to make it look natural."

    contents = [
        types.Content(
            role="user",
            parts=[model_image, garment_image, types.Part.from_text(text=prompt)],
        )
    ]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "8_virtual_try_on.png")
    else:
        print("No image was generated.")


if __name__ == "__main__":
    main()
