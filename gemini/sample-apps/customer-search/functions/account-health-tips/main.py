# pylint: disable=E0401

from os import environ

import functions_framework
from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def account_health_tips(request):
    """
    Provides tips to improve account health.

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

    result_categories = query_handler.query("query_transaction_category")
    result_average_monthly_expense = query_handler.query(
        "query_average_monthly_expense"
    )

    # modification starts

    rc = query_handler.query("query_expenditure_category")

    lm_amount = 0
    category = []
    transaction_list_str = ""
    total_expenditure = 0
    for row in rc:
        lm_amount += round(row["amount"], 2)
        category.append(row["sub_category"])
        transaction_list_str = (
            transaction_list_str + f"{row['sub_category']}: ₹{row['amount']}\n"
        )
        total_expenditure = total_expenditure + row["amount"]

    # modification ends

    average_monthly_expense = 0
    amount = []
    category = []
    transaction_list = ""
    for row in result_categories:
        amount.append(row["amount"])
        category.append(row["category"])
        transaction_list = transaction_list + f",₹{row['amount']} {row['category']}"

    for row in result_average_monthly_expense:
        if row["average_monthly_expense"] is not None:
            average_monthly_expense = int(row["average_monthly_expense"])

    transaction_list = transaction_list[1:]

    model = Gemini()
    response = model.generate_response(
        f"""You are a bank chatbot.
    Tell the user whether the Last Month Expense = ₹{lm_amount} is less than or greater than the
    Average monthly expense = ₹{average_monthly_expense}.
    You have been give list of categories and amount spend.
    Transaction List  = {transaction_list_str}.
    Depending on the data get some insights on how the spending and if any what to do for better
    account health, explain exaclty where is is not good and why.
    Write in a professional and business-neutral tone in very brief in about
    60 words in a very readable form.
    Do not say that largest expense category is housing as housing is a necessity.
    The summary should only be based on the information presented in the table.
    Aslo provide 3-4 tips to reduce the spent in largest spent categories.
    The summary is to be read in a chat response.
    The amount should be comma seprated in indian rupee format and upto 2 decimal places.
    Convert amount to correct format for example ₹ 100235 to ₹ 1,00,235.00.
    For example the output should look like : The last month's expense of ₹24,07,764.00 is
    greater than the average monthly expense of ₹13,09,025.00.
    The largest expense category is xyz, followed by abc. You may want to consider reducing your
    spending in these areas to improve your account health.
    """
    )

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": [response]}}]},
        "sessionInfo": {"parameters": {"vehicle_type": "Bike"}},
    }
    return res
