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
def mutual_fund_recommendation(request):
    """
    Recommends mutual funds to a customer.

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

    cust_id_exists, res = query_handler.validate_customer_id()
    if not cust_id_exists:
        return res

    result_mf = query_handler.query("query_mf")
    csv_table = """name,risk_category,type_of_fund,size,one_month,six_month,one_year,three_year,
    five_year,all_time,NAV,min_sip_amount,fund_size,expense_ratio,exit_load,stamp_duty\n"""

    for row in result_mf:
        csv_table = csv_table + str(row["name"]) + ","
        csv_table = csv_table + str(row["risk_category"]) + ","
        csv_table = csv_table + str(row["type_of_fund"]) + ","
        csv_table = csv_table + str(row["size"]) + ","
        csv_table = csv_table + str(row["one_month"]) + ","
        csv_table = csv_table + str(row["six_month"]) + ","
        csv_table = csv_table + str(row["one_year"]) + ","
        csv_table = csv_table + str(row["three_year"]) + ","
        csv_table = csv_table + str(row["five_year"]) + ","
        csv_table = csv_table + str(row["all_time"]) + ","
        csv_table = csv_table + str(row["min_sip_amount"]) + ","
        csv_table = csv_table + str(row["fund_size"]) + ","
        csv_table = csv_table + str(row["expense_ratio"]) + ","
        csv_table = csv_table + str(row["exit_load"]) + ","
        csv_table = csv_table + str(row["stamp_duty"])
        csv_table = csv_table + "\n"

    model = Gemini()
    response = model.generate_response(
        f"""
        You are a mutual fund expert/analyst and you have to recommed the
        3 best possible mutual fund based on returns among the given list in csv format
        {csv_table}

        Write in a professional and business-neutral tone.
        Word Limit is 40 words.
        The message comes in middle of conversation so don't greet the user with Hello/Hi.
        The currency should be Indian Rupees
        The message should be in a conversation-like manner based on the Account Status.
        The message should only be based on the information presented above.
        The message should be in second person's perespective tone.
        Start the message like "
        The top three performing mutual based on returns are these...
        the following details must be mentioned in uniformly spaced tabular format:
        For each mutual fund in the top 3 list: mention the respective one month from
        six_month return in ₹, one_year return in ₹, three_year in ₹, NAV.
        "
    """
    )

    res = {"fulfillment_response": {"messages": [{"text": {"text": [response]}}]}}
    return res
