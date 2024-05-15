"""Module for prompt to be given to Gemini for generation during data preparation."""

# pylint: disable=C0301
# pylint: disable=E0401

from config import config
from vertexai.preview.generative_models import Part

fewshot_images: list[Part] = []
num_files = len(config["fewshot_images"])
for i in range(num_files):
    filename = "image" + str(i + 1)
    fewshot_images.append(
        Part.from_uri(config["fewshot_images"][filename]), mime_type="image/jpeg"
    )


def image_attribute_prompt(user_image):
    return [
        """
                You are a fashion editor and your task is to spot fashion trends and extract outfit and fashion items from the image provided .
                List all outfit items in list of json format, with separate json for each person in the input image.
                Be as detailed as possible listing shapes, texture, material, length, design pattern, design description and brands.
                If there is no person in the image, return an empty list and only mention items that are visible in the image.
                Use fashion terminology if possible and be verbose."""
        """Input image:""",
        fewshot_images[0],
        """Output:
    [
        {
            \"hat\": \"curved brim cotton red yankees baseball cap\",
            \"sunglasses\": \"black small aviators \",
            \"jacket\": \"black bomber waist length leather jacket\",
            \"shirt\": \"white crew neck cotton t-shirt\",
            \"pants\": \"cotton chinos full length straight leg beige pants\"
        },
        {
            \"jacket\": \"cropped bomber green and white waist height  louis vuitton jacket\",
            \"shirt\": \"white cotton crop top\",
            \"skirt\": \"gabardine a-line beige mini skirt\",
            \"socks\": \"white sheer ankle crew socks\",
            \"bag\": \"green small rectangular leather top handle shoulder bag\"
        }
    ]


    Input image:""",
        fewshot_images[1],
        """Output:
[
        {
            \"top\": \"brown leopard print mid length cotton top with a square neckline and balloon sleeves and button-up front\",
            \"jeans\": \"high-waisted,  mid-rise, straight-leg style, light-wash ripped distressed denim jeans\",
            \"bag\": \"white leather rectangular tote bag\",
            \"sunglasses\": \"black cat eye style square sunglasses\",
            \"accessories\": \"choker gold necklace\"
            \"accessories\": \"choker bangle  bracelet\"
        }
]

    Input image:""",
        user_image,
        """Output:""",
    ]
