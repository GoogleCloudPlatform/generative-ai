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
from utils.image_utils import (
    create_blank_canvas,
    load_image_from_path,
    save_image_to_file,
)
from utils.model_utils import extract_image_from_response, generate_image_from_prompt


def main() -> None:
    """Maintains character consistency across different scenes using a two-model approach."""
    # 1. Load character reference images.
    image_file = "assets/11_character_consistency/reference.png"
    image_part = load_image_from_path(image_file)

    # 2. Craft the scene description using a text model.
    user_ideas = [
        "The character is US president signing Artificial Intelligence Act act and showing it to the camera",
        "The character is a Firefighter posing next to a fire truck in a city street.",
        "The character is a buddhist monk meditating on a mountain top during sunrise",
        "The character is a plumber posing next to a van with plumbing tools (his brand is Nemri Plumbing)",
        "The character is a pizza delivery guy (from Nemri Pizza) holding a pizza box and standing next to a red scooter in front of a house",
        "The character is a Doctor posing in a hospital corridor with a stethoscope around his neck and a white coat. He is smiling and looking confident.",
        "The character is a Police officer posing next to a police car in a city street. He is wearing a blue uniform with a badge and a hat. He is holding a walkie-talkie in one hand and giving a thumbs up with the other hand.",
        "The character is a school teacher standing in front of a classroom with a blackboard behind him. He is wearing glasses and a tie. He is holding a book in one hand and pointing to the blackboard with the other hand.",
        "The character is a soldier in a battlefield, wearing camouflage uniform and holding a rifle. The background shows a war zone with smoke and debris.",
        "The character is an astronaut posing next to a rocket on a launchpad. He is wearing a white spacesuit holding helmet in his hands. The sky is clear and blue, and the sun is shining brightly.",
        "The character is a Preacher standing in front of a church with a cross on top. He is wearing a black robe and a white collar. He is holding a bible in one hand and raising the other hand as if giving a sermon.",
    ]

    for i, user_idea in enumerate(user_ideas):
        print(f"Generating image {i + 1}/{len(user_ideas)}: {user_idea}")

        # 3. Prepare the final prompt for the image generation model
        print("Preparing the final image generation prompt...")
        canvas = create_blank_canvas(
            width=1080, height=1920
        )  # 9:16 portrait aspect ratio

        contents = [
            image_part,
            canvas,
            types.Part.from_text(
                text="Use previous reference images of the character to generate the new scene"
            ),
            types.Part.from_text(text=user_idea),
            types.Part.from_text(text="make sure to use canvas for aspect ratio"),
        ]

        # 4. Generate the final image
        response = generate_image_from_prompt(contents)
        image_data = extract_image_from_response(response)

        if image_data:
            save_image_to_file(
                image_data, "outputs", f"11_character_consistency_{i + 1}.png"
            )
        else:
            print(f"No image was generated for idea {i + 1}.")


if __name__ == "__main__":
    main()
