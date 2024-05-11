# pylint: disable=E0401

from os import environ

import functions_framework
from google.cloud import bigquery
import requests

from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")
api_key = environ.get("API_KEY")


@functions_framework.http
def find_nearest_bike_dealer(request):
    """
    Finds the nearest car dealer to a customer.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    headers = {"Content-Type": "application/json"}

    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    query_handler = BigQueryHandler(customer_id=customer_id)

    result_asset = query_handler.query("query_assets")
    asset_amount = 0
    for row in result_asset:
        if row["asset"] is not None:
            asset_amount = int(row["asset"])

    category = ""
    if asset_amount < 10000000:
        category = "Standard"
    else:
        category = "Premium"

    query_car_dealers = f"""
        SELECT brand, dealer_name, address FROM
        `{project_id}.DummyBankDataset.CarDealers` where category =
        '{category}'
    """

    result_car_dealers = client.query(query_car_dealers)

    result_cust_address = query_handler.query("query_cust_address")

    car_dealers = {}
    for row in result_car_dealers:
        if row["brand"] not in car_dealers:
            car_dealers[row["brand"]] = []
        car_dealers[row["brand"]].append((row["dealer_name"], row["address"]))

    cust_address = ""
    for row in result_cust_address:
        cust_address = (
            row["Address_2nd_Line"]
            + ", "
            + row["Address_3rd_Line"]
            + ", "
            + row["city"]
            + ", "
            + row["state"]
            + " "
            + str(row["Plus_Code"])
        )

    distances = []
    for brand in car_dealers:
        for dealer_name, dealer_address in car_dealers[brand]:
            dist_api_url = (
                f"https://maps.googleapis.com/maps/api/distancematrix/json?destinations={dealer_name},"
                f" {dealer_address}&origins={cust_address}&key={api_key}"
            )
            dist_res = requests.get(dist_api_url, headers=headers)
            dist_res_json = dist_res.json()
            distances.append(
                (
                    dist_res_json["rows"][0]["elements"][0]["distance"]["value"],
                    (dealer_name, dealer_address),
                )
            )

    distances.sort()

    model = Gemini()

    response = model.generate_response(
        f"""You are a chatbot for Cymbal bank. The user is interested in buying a new car.
    Acknowledge that the user is not interested in Fixed Deposit because they are saving
    to purchase a new car and provide them information about some partner car dealers
    near his location using the following:
    Distances = {distances}

    Provide the user information about closest 5 car dealers along with address of their showrooms
    from Distances with proper spacing and indentation for clear readability.
    Also provide some interesting offers for bank's customers for each of the dealers
    in a professional and conversation-like manner.

    The currency to be used is Indian Rupee,i.e.,₹.

    Write in a professional and business-neutral tone.
    Do not greet the user.
    The summary should be in a conversation-like manner.
    The summary should only be based on the information presented above.
    The summary should be in pointers.
    The summary for is for the user to read.
    So summary should be in second person's perespective tone.
    """
    )

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": [response]}}]},
        "sessionInfo": {
            "parameters": {"vehicle_type": "Car", "showrooms": response}
        },
    }
    return res
