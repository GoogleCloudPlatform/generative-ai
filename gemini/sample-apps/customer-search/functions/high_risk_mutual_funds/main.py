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
def high_risk_mutual_funds(request):
    """
    Generates a high risk mutual fund summary for a customer.

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

    res = query_handler.run_all(
        [
            "query_fd",
            "query_total_mf",
            "query_high_risk_mf",
            "query_investment_returns",
        ]
    )

    scheme_name = []
    one_month_return = []
    ttm_return = []
    one_m = []
    ttm = []
    amount_invested = []
    fd_inv = 0
    for row in res["query_investment_returns"]:
        scheme_name.append(row["Scheme_Name"])
        one_month_return.append(row["one_month_return"])
        ttm_return.append(row["ttm_return"])
        one_m.append(row["one_M"] * 100)
        ttm.append(row["ttm"] * 100)
        amount_invested.append(row["amount_invested"])

    total_investment = 0
    total_high_risk_investment = 0

    for row in res["query_fd"]:
        if row["asset"] is not None:
            fd_inv = row["asset"]
            total_investment += row["asset"]

    for row in res["query_total_mf"]:
        if row["total_mf_investment"] is not None:
            total_investment += row["total_mf_investment"]

    for row in res["query_high_risk_mf"]:
        if row["total_high_risk_investment"] is not None:
            total_high_risk_investment += row["total_high_risk_investment"]

    model = Gemini()

    response = model.generate_response(
        f"""You are a chatbot for bank application and you are required to briefly summarize the
    key insights of given numerical values as Investment Summary in small pointers.

    Total Investment = ₹{total_investment}
    Investment in Fixed Deposits = ₹{fd_inv}
    Scheme_Name = {scheme_name}
    One_Month_Return = {one_month_return}
    One_Month_Return_Percentage = {one_m}
    ttm_return = {ttm_return}
    ttm_return_Percentage = {ttm}
    amount_invested = {amount_invested}

    Write in a professional and business-neutral tone.

    One_Month_Return and ttm_return store the amounts in Indian currency, i.e., ₹.
    do not give any amount in decimal.
    If Total Investment is greater than 0:
    the following details must be mentioned in a uniformly formatted table:
    Spacing should be proper.
    For each element in Scheme_Name:
    Mention the respective amount invested from amount_invested and one month from One_Month_Return
    and one month percentage return from One_Month_Return_Percentage and ttm returns from
    ttm_return and ttm return precentage from  ttm_return_Percentage .

    For example the summary should look like :

    **Investment Summary**

    Total Investment: ₹5,55,00,000.00
    Investment in Fixed Deposits: ₹5,00,00,000.00

    **Mutual Fund Investments**

    Scheme Name	Amount Invested	1 Month Returns	1 Month Return%  12 month Return  12 month Return%
    ICICI Prudential Bluechip Fund	₹7,00,000	₹84,000	12	₹2,52,000	35
    SBI Bluechip Fund	₹8,00,000	₹80,000	10	₹2,40,000	30
    HDFC Sensex ETF	₹17,00,000	₹2,55,000	15	₹7,65,000	45
    Nippon India Nifty 50 ETF	₹23,00,000	₹4,14,000	18	₹12,42,000	54

    """
    )

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": [response]}},
            ]
        }
    }
    return res
