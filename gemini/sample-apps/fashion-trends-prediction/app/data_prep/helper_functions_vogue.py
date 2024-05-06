"""
Module for scraping news articles from Vogue for the fashion trends prediction app.
"""

# pylint: disable=E0401

import logging
import time

from bs4 import BeautifulSoup
from data_processing import summarize_article
import requests

logging.basicConfig(level=logging.INFO)


# Get news articles content
def get_articles(url: str, past_scrape: list, num_pages: int = 2) -> list:
    """Gets news articles from a given URL and returns a list of tuples containing the article URL,
    summary, and attributes.

    Args:
            url (str): The URL of the news website.
            past_scrape (list): A list of tuples containing the article URL,
                                summary, and attributes of previously scraped articles.
            num_pages (int, optional): The number of pages to scrape. Defaults to 2.

    Returns:
            list: A list of tuples containing the article URL, summary, and attributes.

    """

    if len(past_scrape) != 0:
        latest_link = past_scrape[0][0]
    else:
        latest_link = ""

    articles = []
    for page in range(1, num_pages):
        logging.info("Scraping page number %s", str(page))
        fashion_page = BeautifulSoup(
            requests.get(url + "/fashion?page=" + str(page)).content, "html.parser"
        )

        for link in fashion_page.find_all("a", class_="SummaryItemHedLink-civMjp"):
            new_url = url + link["href"]

            if new_url == latest_link:
                return articles + past_scrape

            article_text = ""
            for div in BeautifulSoup(
                requests.get(new_url).content, "html.parser"
            ).find_all("div", class_="article__body"):
                article_text += "".join(p.text for p in div.find_all("p"))

            if article_text == "":
                continue

            article_summary = summarize_article(article_text)
            time.sleep(1)
            articles.append((new_url, article_summary))

    return articles + past_scrape
