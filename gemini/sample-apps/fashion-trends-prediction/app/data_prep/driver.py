"""
Module for scraping and preparing data for the fashion trends prediction app.
"""

import json
import logging
import time

from config import config
from data_processing import get_posts
from helper_functions_insta import get_influencers, insta_login
from helper_functions_vogue import get_articles
from prepare_data_for_retriever import prepare_data_for_retriever

logging.basicConfig(level=logging.INFO)

parameters = config["parameters"]["standard"]
country_names = config["countryList"]
data_path = config["Data"]["current_data"]


class Scrape:
    def __init__(self, num_countries: int, num_influencers: int, num_posts: int):
        """Initializes the scrape parameters.

        Args:
                num_countries (int): The number of countries to scrape.
                num_influencers (int): The number of influencers to scrape per country.
                num_posts (int): The number of posts to scrape per influencer.
        """
        self.num_countries = num_countries
        self.num_influencers = num_influencers
        self.num_posts = num_posts


def periodic_extraction(scrape_parameters: Scrape) -> None:
    """Extracts data from Instagram periodically and saves it in a JSON file.

    Args:
        scrape_parameters (Scrape): Object having no. of countries, influencers, posts to scrape.

    """

    saved = {}
    saved["global"] = {}

    temp_map = {}
    scraped_influencers = set()

    cookies = insta_login()

    for country_name in country_names[: scrape_parameters.num_countries]:
        logging.info(f"Scraping country {country_name}")

        # the top influencers of that country right now
        influencers = get_influencers(country_name)

        for influencer in influencers[: scrape_parameters.num_influencers]:
            logging.info(f"Scraping influencer {influencer}")

            if (
                influencer not in scraped_influencers
            ):  # this influencer was not in the list of any other country till now
                scraped_influencers.add(influencer)
                # the influencer was there in the previous run
                if influencer in saved["global"]:
                    posts = get_posts(
                        influencer,
                        saved["global"][influencer],
                        scrape_parameters.num_posts,
                        cookies,
                    )
                else:
                    posts = get_posts(
                        influencer,
                        [],
                        scrape_parameters.num_posts,
                        cookies,
                    )

                temp_map[influencer] = posts

            time.sleep(1)

            # save data after running for each influencer
            with open(data_path, "w") as outfile:
                json.dump(temp_map, outfile)

    # delete the influencers that are not in the list of any country anymore
    saved["global"] = {k: v for k, v in temp_map.items() if k in scraped_influencers}

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def create_final_data(scrape_parameters: Scrape) -> None:
    """Creates the summarized final data from the results of image captioning.

    Args:
        scrape_parameters (Scrape): Object having no. of countries, influencers, posts to scrape.

    """

    with open(data_path, "r") as f:
        saved = json.load(f)

    saved["finaldata"] = {}
    for country_name in country_names[: scrape_parameters.num_countries]:
        saved["finaldata"][country_name] = {}
        influencers = get_influencers(country_name)[
            : scrape_parameters.num_influencers
        ]  # the top influencers of that country right now

        for influencer in influencers:
            if influencer not in saved["global"]:
                continue

            for element in saved["global"][influencer]:
                image_attr = element[2]
                for cat, values in image_attr.items():
                    saved["finaldata"][country_name].setdefault(cat, []).extend(
                        values.copy()
                    )

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def merge_keys() -> None:
    """Merges keys in final data file that have a difference of spaces, capital letters, etc."""

    with open(data_path, "r") as f:
        saved = json.load(f)

    finaldata_new = {}
    finaldata = saved["finaldata"]
    countries = [key for key in finaldata]

    for country in countries:
        finaldata_new[country] = {}

        for key in finaldata[country]:
            newkey = (
                key.strip().lower()
                if not (key.strip() == key and key.lower() == key)
                else key
            )
            if newkey in finaldata_new[country]:
                finaldata_new[country][newkey] += finaldata[country][key].copy()
            else:
                finaldata_new[country][newkey] = finaldata[country][key].copy()

    saved["finaldata"] = finaldata_new

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def combine_insta_and_vogue() -> None:
    """Combines data from Instagram and Vogue into a single file."""

    with open(data_path, "r") as f:
        saved = json.load(f)

    a = saved["finaldata"]["India"]
    a_articles = saved["article_attributes"]
    combined_attributes = {}

    a2 = {}
    for key in a:
        temp = a[key]
        newlist = [[item, "", ""] for item in temp]
        a2[key] = newlist

    for key in a2:
        if key in a_articles:
            combined_attributes[key] = a2[key] + a_articles[key]
        else:
            combined_attributes[key] = a2[key]

    for key in a_articles:
        if key not in a2:
            combined_attributes[key] = a_articles[key]

    combined_attributes["jewellery"] = a_articles["jewellery"]

    saved["finaldata"]["India"] = combined_attributes

    # Make data of all countries in the format of India's data
    for country in saved["finaldata"]:
        if country != "India":
            for key in saved["finaldata"][country]:
                temp = saved["finaldata"][country][key]
                saved["finaldata"][country][key] = [[item, "", ""] for item in temp]

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def get_top_categories(saved: dict) -> None:
    """Gets the top categories from the final data file.

    Args:
            saved (dict): A dictionary containing the saved data.

    """

    saved["top_categories"] = {}
    for country in saved["finaldata"]:
        allcategories = saved["finaldata"][country]

        sorted_a = sorted(allcategories.items(), key=lambda item: -len(item[1]))
        item_categories = [cat for cat, values in sorted_a[: min(15, len(sorted_a))]]

        saved["top_categories"][country] = item_categories

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def insta_scrape() -> None:
    """Scrapes data from Instagram and saves it in a JSON file."""

    scrape_parameters = Scrape(num_countries=10, num_influencers=20, num_posts=50)

    # set first to True if this is the first time you are extracting
    periodic_extraction(scrape_parameters)

    with open(data_path, "r") as f:
        saved = json.load(f)

    create_final_data(scrape_parameters)

    with open(data_path, "r") as f:
        saved = json.load(f)

    get_top_categories(saved)


def vogue_scrape() -> None:
    """Scrapes data from Vogue and saves it in a JSON file."""

    with open(data_path, "r") as f:
        saved = json.load(f)

    if "articles" not in saved:
        saved["articles"] = []
    saved["articles"] = get_articles(
        "https://www.vogue.in", saved["articles"], num_pages=10
    )

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)

    prepare_data_for_retriever()


if __name__ == "__main__":
    insta_scrape()
    vogue_scrape()
