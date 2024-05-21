"""This is a python utility file."""

# pylint: disable=E0401
# pylint: disable=R0801
# pylint: disable=R0914

from os import environ

import functions_framework
from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def find_nearest_bike_dealer(request):
    """
    Finds the nearest bike dealer to a customer.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    query_handler = BigQueryHandler(customer_id=customer_id)

    result_asset = query_handler.query("query_assets")
    asset_amount = 0
    for row in result_asset:
        if row["asset"] is not None:
            asset_amount = int(row["asset"])

    category = ""
    if asset_amount < 6000000:
        category = "Standard"
    else:
        category = "Premium"

    result_cust_address = query_handler.query("query_cust_address")

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

    model = Gemini()

    response = model.generate_response(
        f"""You are a chatbot for Cymbal bank application.
    The user is interested in buying a new motorcycle. Given the address of the user
    as {cust_address},provide the user information about 5 motorcycle dealers of {category}
    category brands along with address of their showrooms nearest to their address {0} and
    some of the best selling models with proper spacing and indentation for clear readability.
    Also provide discount offers for the Cymbal bank's customers for each of the respective
    dealers in a professional manner. Maximum word limit is 1000.

    *DO NOT* mention the category {category} of the brands.

    The currency to be used is Indian Rupee,i.e.,₹.
    """
    )

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": [response]}}]},
        "sessionInfo": {"parameters": {"vehicle_type": "Bike", "showrooms": response}},
    }
    return res
