import time

from bs4 import BeautifulSoup
from dataProcessing import create_attributes, summarize_article
import requests

# Get news articles content


def get_articles(url, past_scrape, numPages=2):
    """Gets news articles from a given URL and returns a list of tuples containing the article URL, summary, and attributes.

    Args:
            url (str): The URL of the news website.
            past_scrape (list): A list of tuples containing the article URL, summary, and attributes of previously scraped articles.
            numPages (int, optional): The number of pages to scrape. Defaults to 2.

    Returns:
            list: A list of tuples containing the article URL, summary, and attributes.

    """
    if len(past_scrape) != 0:
        latest_link = past_scrape[0][0]
    else:
        latest_link = ""

    finish = False
    articles = []
    for page in range(1, numPages):
        print(
            "page no ------------------------------------------------------------ ",
            page,
        )
        response = requests.get(url + "/fashion?page=" + str(page))
        fashionPage = BeautifulSoup(response.content, "html.parser")

        for link in fashionPage.find_all("a", class_="SummaryItemHedLink-civMjp"):
            new_url = url + link["href"]

            if new_url == latest_link:
                print("new url is same as past")
                finish = True
                break

            res = requests.get(new_url)

            page = BeautifulSoup(res.content, "html.parser")
            article_text = ""
            for div in page.find_all("div", class_="article__body"):
                for p in div.find_all("p"):
                    article_text += p.text

            if article_text == "":
                print("Empty", new_url)
                continue

            article_summary = summarize_article(article_text)
            article_attributes = create_attributes(article_summary)
            time.sleep(1)
            articles.append((new_url, article_summary, article_attributes))
            print("article appended")

        if finish:
            break

    return articles + past_scrape
