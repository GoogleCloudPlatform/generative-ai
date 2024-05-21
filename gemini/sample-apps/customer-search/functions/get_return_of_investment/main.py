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
def return_of_investment(request):
    """
    Calculates the return of investment for a customer.

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

    result_investments = query_handler.query("query_investments_six_month_return")

    scheme_name = []
    six_month_return = []
    investment_list_str = ""
    for row in result_investments:
        scheme_name.append(row["Scheme_Name"])
        six_month_return.append(row["six_month_return"])
        investment_list_str = (
            investment_list_str
            + f",₹ {row['six_month_return']} in {row['Scheme_Name']}"
        )

    investment_list_str = investment_list_str[1:]

    model = Gemini()

    response = model.generate_response(
        """Given the return of investment list do the following:
    1. Convert amount to correct format for example ₹ 100235 to ₹ 1,00,235,
    ₹ 16423.3423 to ₹ 16,423.3423.
    2. Convert the list to a meaningful sentence.
    Transaction List = {investment_list_str}
    Assume that a positive amount indicate profit while negative indicate loss.
    """
    )

    res = {"fulfillment_response": {"messages": [{"text": {"text": response}}]}}
    return res
