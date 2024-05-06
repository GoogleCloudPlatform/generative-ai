"""
Module for scraping Instagram data for the fashion trends prediction app.

- Gets the entire list of country names.
- Gets a list of top 50 influencers country wise.
- Logs into Instagram and returns a dictionary of cookies.
- Gets the Instagram user ID.
"""

# pylint: disable=E0401

import json
from uuid import uuid4

from bs4 import BeautifulSoup
from config import config
import requests


# Get the entire list of country names
def get_countries() -> list:
    """Gets the entire list of country names.

    Returns:
        list: A list of country names.

    """
    url = "https://hypeauditor.com/top-instagram/"
    response = requests.get(url)
    page = BeautifulSoup(response.content, "html.parser")

    divs = page.find_all("div", class_="menu")
    # category_div is not used currently as category is fixed to fashion
    _, country_div = divs[0], divs[1]
    a_tags = country_div.find_all("a")
    country_names = ["All countries"] + [a_tag.text for a_tag in a_tags]

    return country_names


# Get list of top 50 influencers country wise
def get_influencers(country: str) -> list:
    """Gets a list of top 50 influencers country wise.

    Args:
        country (str): The country name.

    Returns:
        list: A list of top 50 influencers of that country.

    """
    url = "https://hypeauditor.com/top-instagram-fashion"
    if country != "All countries":
        country = country.lower().replace(" ", "-")
        url = url + "-" + country

    response = requests.get(url)
    if response.status_code != 200:
        return []

    page = BeautifulSoup(response.content, "html.parser")

    influencers = []

    for container in page.find_all("div", class_="contributor__name-content"):
        influencers.append(container.text)

    return influencers


def insta_login() -> dict:
    """Logs into Instagram and returns a dictionary of cookies.

    Returns:
            dict: A dictionary of cookies.

    """
    # Creating a session
    # reference: https://github.com/KEAGTORB/grab-insta/blob/main/grab.py
    username = config["username"]
    password = config["password"]
    params = "iPhone8,1; iOS 14_1; en_SA@calendar=gregorian; ar-SA; scale=2.00; 750x1334; 244425769"
    headers = {
        "Host": "i.instagram.com",
        "X-Ig-Connection-Type": "WiFi",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Ig-Capabilities": "36r/Fx8=",
        "User-Agent": f"Instagram 159.0.0.28.123 ({params}) AppleWebKit/420+",
        "X-Ig-App-Locale": "en",
        "X-Mid": "Ypg64wAAAAGXLOPZjFPNikpr8nJt",
        "Content-Length": "778",
        "Accept-Encoding": "gzip, deflate",
    }
    data = {
        "username": username,
        "reg_login": "0",
        "enc_password": f"#PWD_INSTAGRAM:0:&:{password}",
        "device_id": uuid4(),
        "login_attempt_count": "0",
        "phone_id": uuid4(),
    }

    url = "https://i.instagram.com/api/v1/accounts/login/"
    r = requests.post(url=url, headers=headers, data=data)

    print(r.status_code)
    session_id = r.cookies.get("sessionid")
    cookies = {"sessionid": session_id}

    return cookies


def get_id(user: str, cookies: dict) -> str:
    """Gets the Instagram user ID.

    Args:
        user (str): The Instagram username.
        cookies (dict): A dictionary of cookies.

    Returns:
        str: The Instagram user ID.

    """
    link = f"https://www.instagram.com/web/search/topsearch/?query={user}"
    response = requests.get(link, cookies=cookies)

    if response.status_code >= 300:
        return None

    profile_data_json = response.text
    parsed_data = json.loads(profile_data_json)

    return parsed_data["users"][0]["user"]["pk"]
