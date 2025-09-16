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
from utils.image_utils import save_image_to_file
from utils.model_utils import extract_image_from_response, generate_image_from_prompt


def main() -> None:
    """Generates an image that includes legible text."""
    prompt = """
    Create a Pizzeria menu with the following content:
    The Artisan Crust Pizzeria
    Crafted Pizza, Simply Delicious.
    Our Signature Pizzas
    Classic Margherita - $11 / $17
    San Marzano tomato, fresh mozzarella, basil.
    Spicy Pepperoni - $12 / $18
    Tomato sauce, mozzarella, premium pepperoni.
    Garden Veggie - $12 / $19
    Tomato sauce, mozzarella, bell peppers, onion, mushrooms, olives.
    Smoky BBQ Chicken - $13 / $19
    BBQ sauce base, grilled chicken, mozzarella, red onion.
    Beverages
    Fountain Soda - $3
    Coca-Cola, Diet Coke, Sprite, Root Beer.
    Bottled Water - $3
    Still or Sparkling.
    Order Online or Call: 555-123-4567
    """

    contents = [types.Content(role="user", parts=[types.Part.from_text(text=prompt)])]

    response = generate_image_from_prompt(contents)
    image_data = extract_image_from_response(response)

    if image_data:
        save_image_to_file(image_data, "outputs", "10_images_with_text.png")
    else:
        print("No image was generated.")


if __name__ == "__main__":
    main()
