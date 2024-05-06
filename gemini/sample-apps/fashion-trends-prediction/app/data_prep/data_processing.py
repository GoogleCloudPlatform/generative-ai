"""
This module provides functions to
    - Get posts from Instagram.
    - Generate captions for images using the Gemini model.
    - Summarize articles using the Gemini model.
"""

# pylint: disable=E0401

import base64
import json
import os
import sys
import urllib.request

from data_prep_genai_prompts import image_attribute_prompt
import requests

sys.path.append("../")
from config import config
from helper_functions_insta import get_id
from vertexai.preview.generative_models import (
    GenerationConfig,
    GenerativeModel,
    HarmBlockThreshold,
    HarmCategory,
    Part,
)

gemini_model: GenerativeModel = GenerativeModel("gemini-1.0-pro-vision-001")
gemini_model_language: GenerativeModel = GenerativeModel("gemini-1.0-pro-002")

parameters = config["parameters"]["standard"]


def generate_caption(image_path: str) -> dict:
    """Generates a caption for an image using the Gemini model.

    Args:
                    image_path (str): The path to the image file.

    Returns:
                    dict: A dictionary containing the generated caption.
    """

    answer: dict = {}

    with open(image_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read())
        user_image = Part.from_data(
            data=base64.b64decode(encoded_string), mime_type="image/jpeg"
        )

    response = gemini_model.generate_content(
        image_attribute_prompt(user_image=user_image),
        generation_config=GenerationConfig(
            max_output_tokens=2048,
            temperature=0.4,
            top_p=1,
            top_k=32,
        ),
        safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        },
        stream=False,
    ).text

    try:
        response = json.loads(response)
    except json.decoder.JSONDecodeError as e:
        print(e)
        return {}

    for json_ob in response:
        for category in json_ob.keys():
            if category in answer:
                answer[category].append(json_ob[category])
            else:
                answer[category] = [json_ob[category]]

    return answer


def get_posts(user: str, previous: list, count: int = 10, cookies: dict = None) -> list:
    """Gets a list of posts from an Instagram user.

    Args:
                    user (str): The username of the Instagram user.
                    previous (list): A list of previous posts.
                    count (int): The number of posts to get.
                    cookies (dict): A dictionary of cookies.
                    model (str): The model to use for generating the captions.

    Returns:
                    list: A list of posts.
    """

    original_count = count
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

    posts = []

    flag = False
    while count > 0 and flag is False:
        response = requests.get(
            config["links"]["graphql"], params=params, cookies=cookies
        )

        if response.status_code != 200:
            break

        parsed_data = json.loads(response.text)

        media = parsed_data["data"]["user"]["edge_owner_to_timeline_media"]

        for i in range(len(media["edges"])):
            if media["edges"][i]["node"]["__typename"] == "GraphVideo":
                continue

            postid = media["edges"][i]["node"]["id"]
            postlink = media["edges"][i]["node"]["display_url"]

            if postid == latest_id:
                flag = True
                break

            actual_img_path = "" + user + "$.png"
            urllib.request.urlretrieve(postlink, actual_img_path)

            try:
                caption = generate_caption(actual_img_path)
            except Exception as e:
                print(e)
            else:
                posts = [(postid, postlink, caption)] + posts  # newest post stays first
                count -= 1
            finally:
                os.remove(actual_img_path)

            if count == 0:
                break

        params["after"] = media["page_info"]["end_cursor"]

    posts = posts + previous
    if len(posts) > original_count:
        posts = posts[:original_count]

    return posts


def summarize_article(article_text: str) -> str:
    """Summarizes an article.

    Args:
                    article_text (str): The article text.

    Returns:
                    str: The summary.
    """

    response = gemini_model_language.generate_content(
        [f"Provide a brief summary for the following article: {article_text}"],
        generation_config=GenerationConfig(
            max_output_tokens=2048,
            temperature=1,
            top_p=1,
        ),
        safety_settings={
            HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
            HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_ONLY_HIGH,
        },
        stream=False,
    )

    return response.text
