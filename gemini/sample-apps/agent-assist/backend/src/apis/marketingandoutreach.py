"""This is a python utility file."""

# pylint: disable=E0401

from datetime import datetime, timedelta
import json

from flask import jsonify, request


def get_marketing_and_outreach_data() -> tuple[dict, int]:
    """
    This function gets the marketing and outreach data from a JSON
      file and returns it in a JSON format.

    Args:
        None

    Returns:
        JSON: A JSON object containing the marketing and outreach data.
    """
    file_path = "data/likes.json"
    with open(file_path, encoding="UTF-8") as json_file:
        data = json.load(json_file)

    start_date = request.args.get("start_date")
    finish_date = request.args.get("end_date")
    if start_date is None or finish_date is None:
        start_date = datetime.now() - timedelta(days=90)
        start_date = start_date.strftime("%Y-%m-%d")
        finish_date = datetime.now().strftime("%Y-%m-%d")

    (
        website_traffic,
        likes,
        comments,
        shares,
        emails_sent,
        open_rate,
        top_performing_platform,
        chart_data,
    ) = get_metrics_data(data, start_date, finish_date)

    return (
        jsonify(
            {
                "website_traffic": website_traffic,
                "likes": likes,
                "comments": comments,
                "shares": shares,
                "emails_sent": emails_sent,
                "open_rate": open_rate,
                "top_performing_platform": top_performing_platform,
                "chart_data": chart_data,
            }
        ),
        200,
    )


# pylint: disable=R0914
def get_metrics_data(
    data: list, start_date: str, end_date: str
) -> tuple[int, int, int, int, int, float, str, list]:
    """
    This function gets the metrics data from a list of dictionaries and returns it in a tuple.

    Args:
        data (list): A list of dictionaries containing the marketing and outreach data.
        start_date (str): The start date of the data to be retrieved.
        end_date (str): The end date of the data to be retrieved.

    Returns:
        tuple: A tuple containing the website traffic, likes, comments,
        shares, emails sent, open rate, top performing platform, and chart data.
    """
    website_traffic = 0
    likes = 0
    comments = 0
    shares = 0
    emails_sent = 0
    mail_opened = 0
    max_sales = 0
    top_performing_platform = ""
    sales_platforms = [
        "facebook sales",
        "newspaper sales",
        "tvads sales",
        "insta sales",
        "mail sales",
        "telephone sales",
    ]
    sum_sales = {}
    for platform in sales_platforms:
        sum_sales[platform] = 0
    for item in data:
        if (
            item["campaign_start_date"] >= start_date
            and item["campaign_start_date"] <= end_date
        ):
            website_traffic += item["website_visitors"]
            likes += item["insta_likes"] + item["facebook_likes"]
            comments += item["insta_comments"] + item["facebook_comments"]
            shares += item["facebook_shares"]
            emails_sent += item["number_of_mail_sent"]
            mail_opened += item["number_of_mail_open"]
            for platform in sales_platforms:
                sum_sales[platform] += item[platform.replace(" ", "")]

    for platform in sales_platforms:
        if sum_sales[platform] > max_sales:
            max_sales = sum_sales[platform]
            top_performing_platform = platform

    open_rate = 0.0
    if emails_sent != 0:
        open_rate = (mail_opened * 100) / emails_sent
    open_rate = round(open_rate, 2)

    chart_data = []
    for platform in sales_platforms:
        chart_data.append({"x": platform, "y1": sum_sales[platform]})
    return (
        website_traffic,
        likes,
        comments,
        shares,
        emails_sent,
        open_rate,
        top_performing_platform.split(" ", maxsplit=1)[0],
        chart_data,
    )
