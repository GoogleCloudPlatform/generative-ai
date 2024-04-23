import base64
import json
import os
import urllib.request

import requests
import vertexai.preview.generative_models as generative_models
from config import config
from genai_prompts import qList, qList2
from helper_functions_insta import get_id
from vertexai.preview.generative_models import GenerativeModel, Part, GenerationConfig
from vertexai.preview.language_models import TextGenerationModel
from vertexai.preview.vision_models import Image, ImageQnAModel

image_qna_model = ImageQnAModel.from_pretrained("imagetext")
text_model = TextGenerationModel.from_pretrained("text-bison-32k")
gemini_model = GenerativeModel("gemini-1.0-pro-vision-001")


parameters = config["parameters"]["standard"]


directory = "gemini_fewshot_images"
files = os.listdir(directory)
sorted_files = sorted(files)  # sort by lexicographical order of the filenames
fewshot_images = []
for filename in sorted_files:
    with open(os.path.join(directory, filename), "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        fewshot_images.append(
            Part.from_data(
                data=base64.b64decode(encoded_string), mime_type="image/jpeg"
            )
        )


def generate_caption_gemini(image_path):
    """Generates a caption for an image using the Gemini model.

    Args:
                    image_path (str): The path to the image file.

    Returns:
                    dict: A dictionary containing the generated caption.
    """

    answer = {}

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        user_image = Part.from_data(
            data=base64.b64decode(encoded_string), mime_type="image/jpeg"
        )

    prompt = [
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

    response = gemini_model.generate_content(
        prompt,
        generation_config=GenerationConfig(
            max_output_tokens=2048,
            temperature=0.4,
            top_p=1,
            top_k=32,
        ),
        safety_settings={
            generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
            generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_ONLY_HIGH,
        },
        stream=False,
    ).text

    try:
        response = json.loads(response)
    except Exception as e:
        print(e)
        return {}

    for json_ob in response:
        for category in json_ob.keys():
            if category in answer:
                answer[category].append(json_ob[category])
            else:
                answer[category] = [json_ob[category]]

    return answer


def generate_caption_imageQnA(image_path):
    """Generates a caption for an image using the ImageQnA model.

    Args:
                    image_path (str): The path to the image file.

    Returns:
                    dict: A dictionary containing the generated caption.
    """

    answer = {}

    # Load the downloaded image
    user_image = Image.load_from_file(image_path)

    if (
        str(
            image_qna_model.ask_question(
                image=user_image,
                question=qList[0],
                number_of_results=1,
            )[0]
        )
        == "no"
    ):
        return answer

    items = str(
        image_qna_model.ask_question(
            image=user_image,
            question=qList[1],
            number_of_results=1,
        )[0]
    ).split(",")

    for item in items:
        res = set()
        for q in qList2:
            res.add(
                str(
                    image_qna_model.ask_question(
                        image=user_image,
                        question=q.replace("x", item),
                        number_of_results=1,
                    )[0]
                )
            )

        result = " ".join(res)

        answer[item] = [result]

    answer["Sleeves"] = [
        str(
            image_qna_model.ask_question(
                image=user_image,
                question=qList[2],
                number_of_results=1,
            )[0]
        )
    ]

    answer["Neckline"] = [
        str(
            image_qna_model.ask_question(
                image=user_image,
                question=qList[3],
                number_of_results=1,
            )[0]
        )
    ]

    answer["Jewellery"] = [
        str(
            image_qna_model.ask_question(
                image=user_image,
                question=qList[4],
                number_of_results=1,
            )[0]
        )
    ]

    return answer


def generate_caption(image_path, model):
    """Generates a caption for an image using the specified model.

    Args:
                    image_path (str): The path to the image file.
                    model (str): The model to use for generating the caption.

    Returns:
                    dict: A dictionary containing the generated caption.
    """

    if model == "Gemini":
        return generate_caption_gemini(image_path)

    elif model == "ImageQnA":
        return generate_caption_imageQnA(image_path)


def get_posts(user, previous, cnt=10, cookies={}, model="Gemini"):
    """Gets a list of posts from an Instagram user.

    Args:
                    user (str): The username of the Instagram user.
                    previous (list): A list of previous posts.
                    cnt (int): The number of posts to get.
                    cookies (dict): A dictionary of cookies.
                    model (str): The model to use for generating the captions.

    Returns:
                    list: A list of posts.
    """

    org_cnt = cnt
    userId = get_id(user, cookies)
    if userId is None:
        return previous
    params = {
        "query_id": config["postid"],  # Fixed value for posts
        "id": userId,  # User ID
        "first": 12,
    }

    if len(previous) != 0:
        latest_id = previous[0][0]
    else:
        latest_id = ""

    print("latest id: ", latest_id, "\n")
    posts = []

    flag = False
    while cnt > 0 and flag is False:
        response = requests.get(
            config["links"]["graphql"], params=params, cookies=cookies
        )

        print(response.status_code)

        if response.status_code != 200:
            print(response)
            break

        parsed_data = json.loads(response.text)

        media = parsed_data["data"]["user"]["edge_owner_to_timeline_media"]

        for i in range(len(media["edges"])):
            if media["edges"][i]["node"]["__typename"] == "GraphVideo":
                continue

            postid = media["edges"][i]["node"]["id"]
            postlink = media["edges"][i]["node"]["display_url"]
            print("post id: ", postid)

            if postid == latest_id:
                flag = True
                break

            actual_img_path = "" + user + "$.png"
            urllib.request.urlretrieve(postlink, actual_img_path)

            try:
                caption = generate_caption(actual_img_path, "Gemini")
            except Exception as e:
                print(e)
            else:
                posts = [(postid, postlink, caption)] + \
                    posts  # newest post stays first
                cnt -= 1
            finally:
                os.remove(actual_img_path)

            if cnt == 0:
                break

        params["after"] = media["page_info"]["end_cursor"]

    posts = posts + previous
    if len(posts) > org_cnt:
        posts = posts[:org_cnt]

    print("final cnt = ", cnt)
    return posts


def summarize_article(article_text: str) -> str:
    """Summarizes an article.

    Args:
                    article_text (str): The article text.

    Returns:
                    str: The summary.
    """

    response = text_model.predict(
        f"Provide a brief summary for the following article: {article_text}",
        **parameters,
    )

    return response.text


def create_attributes(article_summary):
    """Creates a dictionary of attributes from an article summary.

    Args:
                    article_summary (str): The article summary.

    Returns:
                    dict: A dictionary of attributes.
    """

    response = text_model.predict(
        """Given an article summary, I want to extract all the clothing items listed in the text. The items must be categorized by the type of item (eg. pants, jewellery, dress, etc.). The output must be a json with the keys being the name of the item and value being its description.

input: Given the following news article summary, give a json output where the key is the type of fashion item (eg. jacket, jewellery, pants etc.) and the value is the exact description - Karisma Kapoor looked stunning in a white kurta set while visiting the Taj Mahal. She paired the outfit with matching Kolhapuri sandals, black oversized sunglasses, and dainty Kundan jhumkas. Her makeup was understated yet flawless, with a clean, natural look and a pop of red on her lips. Karisma Kapoor has established herself as a fashion icon, and her love for traditional attire has provided us with a rich source of wardrobe inspiration.
output: {
\"kurta\": \"white kurta set\",
\"footwear\": \"kolhapuri sandals\",
\"accessories\": \"black oversized sunglasses\",
\"jewellery\": \"dainty kundan jhumkas\"
}

input: Given the following news article summary, give a json output where the key is the type of fashion item (eg. jacket, jewellery, pants etc.) and the value is the exact description - """
        + article_summary
        + """output:
""",
        **parameters,
    )

    try:
        output_json = json.loads(response.text)
    except Exception as e:
        print(e)
        print("not perfect json ", response.text)
        return {}

    return output_json
