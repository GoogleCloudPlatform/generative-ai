import json
import time

from config import config
from dataProcessing import getPosts
from helper_functions_insta import getInfluencers, instalogin
from helper_functions_vogue import get_articles
from prepare_data_for_retriever import prepare_data_for_retriever

parameters = config["parameters"]["standard"]
country_names = config["countryList"]
data_path = config["Data"]["current_data"]


def isRoot(word):
    if word.strip() == word and word.lower() == word:
        return True
    return False


def cmpf(item):
    return -len(item[1])


def extract_json_influencer_wise(scrape_size, first_scrape, saved):
    """Extracts data from Instagram and saves it in a JSON file.

    Args:
            scrape_size (dict): A dictionary containing the number of countries, influencers, and posts to scrape.
            first_scrape (bool): A boolean indicating whether this is the first scrape.
            saved (dict): A dictionary containing the saved data.

    """

    if first_scrape:
        temp_map = {}
        scraped_influencers = set()
    else:
        with open(data_path, "r") as f:
            temp_map = json.load(f)
        scraped_influencers = set(temp_map.keys())

    cookies = instalogin()

    for country_name in country_names[: scrape_size["num_countries"]]:
        print(country_name)

        # the top influencers of that country right now
        influencers = getInfluencers(country_name)

        for influencer in influencers[: scrape_size["num_influencers"]]:
            print(influencer)

            if (
                influencer not in scraped_influencers
            ):  # this influencer was not in the list of any other country till now
                scraped_influencers.add(influencer)
                # the influencer was there in the previous run
                if influencer in saved["global"]:
                    posts = getPosts(
                        influencer,
                        saved["global"][influencer],
                        scrape_size["num_posts"],
                        cookies,
                        model="Gemini",
                    )
                else:
                    posts = getPosts(
                        influencer,
                        [],
                        scrape_size["num_posts"],
                        cookies,
                        model="Gemini",
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


def periodic_extraction(scrape_size, first_period):
    """Extracts data from Instagram periodically and saves it in a JSON file.

    Args:
            scrape_size (dict): A dictionary containing the number of countries, influencers, and posts to scrape.
            first_period (bool): A boolean indicating whether this is the first period.

    """

    if first_period:
        saved = {}
        saved["global"] = {}
    else:
        with open(data_path, "r") as f:
            saved = json.load(f)

    # first scrape is set to True when you are running for the first time in an extraction period
    extract_json_influencer_wise(
        scrape_size=scrape_size, first_scrape=True, saved=saved
    )


def create_final_data(scrape_size):
    """Creates a final data file by combining data from Instagram and Vogue.

    Args:
            scrape_size (dict): A dictionary containing the number of countries, influencers, and posts to scrape.

    """

    with open(data_path, "r") as f:
        saved = json.load(f)

    saved["finaldata"] = {}
    for country_name in country_names[: scrape_size["num_countries"]]:
        print(country_name)
        saved["finaldata"][country_name] = {}

        # the top influencers of that country right now
        influencers = getInfluencers(country_name)

        for influencer in influencers[: scrape_size["num_influencers"]]:
            print(influencer)
            if influencer in saved["global"]:
                for element in saved["global"][influencer]:
                    image_attr = element[2]

                    for cat in image_attr:
                        if cat in saved["finaldata"][country_name]:
                            saved["finaldata"][country_name][cat].extend(
                                image_attr[cat].copy()
                            )
                        else:
                            saved["finaldata"][country_name][cat] = image_attr[
                                cat
                            ].copy()

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def merge_keys():
    """Merges keys in the final data file that have only a difference of spaces, capital letters, etc."""

    # merging the keys which only have a difference of spaces, capital letters

    with open(data_path, "r") as f:
        saved = json.load(f)

    print("merging keys")
    finaldata_new = {}
    finaldata = saved["finaldata"]
    countries = [key for key in finaldata]

    for country in countries:
        finaldata_new[country] = {}

        for key in finaldata[country]:
            if isRoot(key):
                finaldata_new[country][key] = finaldata[country][key].copy()

        for key in finaldata[country]:
            if not isRoot(key):
                newkey = (key.strip()).lower()
                if newkey in finaldata_new[country]:
                    finaldata_new[country][newkey] += finaldata[country][key].copy()
                else:
                    finaldata_new[country][newkey] = finaldata[country][key].copy()

    saved["finaldata"] = finaldata_new

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def combine_insta_and_vogue():
    """Combines data from Instagram and Vogue into a single file."""

    # Combining Instagram (India) and Vogue-India data

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


def create_news_articles_data():
    """Extracts news articles from Vogue and saves them in a JSON file."""

    with open(data_path, "r") as f:
        saved = json.load(f)

    if "articles" not in saved:
        saved["articles"] = []

    url = "https://www.vogue.in"

    past_scrape = saved["articles"]
    saved["articles"] = get_articles(url, past_scrape, numPages=10)

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def create_article_attributes():
    """Extracts attributes from news articles and saves them in a JSON file."""

    with open(data_path, "r") as f:
        saved = json.load(f)

    print("creating article attributes")
    saved["article_attributes"] = {}  # make new everytime

    for article in saved["articles"]:
        article_link = article[0]
        article_summary = article[1]
        article_attr = article[2]
        for item in article_attr:
            if (
                (article_attr[item] == "none")
                or (article_attr[item] == "None")
                or isinstance(item, str) is False
            ):
                print("invalid \n  ", item, article_attr[item])
                continue
            if item in saved["article_attributes"]:
                saved["article_attributes"][item].append(
                    [article_attr[item], article_summary, article_link]
                )
            else:
                saved["article_attributes"][item] = [
                    [article_attr[item], article_summary, article_link]
                ]

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def get_top_categories(saved):
    """Gets the top categories from the final data file.

    Args:
            saved (dict): A dictionary containing the saved data.

    """

    saved["top_categories"] = {}
    for country in saved["finaldata"]:
        allcategories = saved["finaldata"][country]

        sorted_a = sorted(allcategories.items(), key=cmpf)
        item_categories = [cat for cat, values in sorted_a[: min(15, len(sorted_a))]]

        saved["top_categories"][country] = item_categories

    with open(data_path, "w") as outfile:
        json.dump(saved, outfile)


def instaScrape():
    """Scrapes data from Instagram and saves it in a JSON file."""

    scrape_size = {"num_countries": 10, "num_influencers": 20, "num_posts": 50}

    # set first to True if this is the first time you are extracting
    periodic_extraction(scrape_size=scrape_size, first_period=True)

    with open(data_path, "r") as f:
        saved = json.load(f)

    create_final_data(scrape_size)
    # merge_keys()

    with open(data_path, "r") as f:
        saved = json.load(f)

    get_top_categories(saved)


def vogueScrape():
    """Scrapes data from Vogue and saves it in a JSON file."""

    create_news_articles_data()
    # create_article_attributes()
    prepare_data_for_retriever()


if __name__ == "__main__":
    instaScrape()
    vogueScrape()
