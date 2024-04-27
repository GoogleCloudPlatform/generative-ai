import json
import os

from config import config
from data_processing import generate_caption
from driver import get_top_categories

data_path = config["Data"]["current_data"]


def images_scrape(saved):
    """

    Write code here to extract/ scrape images from your data source.
    For each image, store it in your local directory (same path as this file)
    Then, for each image, call generateCaption() function written in data_processing.py which returns a dictionary
    Store the results in an array to finally get an array of dictionaries

    Dummy code for two locally stored images is given in this function definition

    Args:
                    saved (dict): The current data in dictionary format
    """

    answers = []
    image_files = os.listdir("gemini_fewshot_images")
    for image_file in image_files:
        image_path = os.path.join("gemini_fewshot_images", image_file)

        print(image_path)
        answer = generate_caption(image_path)
        answers.append(answer)

    saved["finaldata"] = {}
    saved["finaldata"]["All countries"] = {}

    for image_attr in answers:
        for cat in image_attr:
            if cat in saved["finaldata"]["All countries"]:
                saved["finaldata"]["All countries"][cat].extend(image_attr[cat].copy())
            else:
                saved["finaldata"]["All countries"][cat] = image_attr[cat].copy()

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)

    get_top_categories(saved)


if __name__ == "__main__":
    with open(data_path, "r") as f:
        saved = json.load(f)

    # the below function is called to replace the current images data
    images_scrape(saved)
