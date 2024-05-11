# pylint: disable=E0401

from os import environ
import uuid

import functions_framework
import plotly.graph_objects as go

from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini
from utils.upload_to_gcs import upload_blob

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def category_wise_expenditure(request):
    """
    Generates a pie chart of the category-wise expenditure of a customer.

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

    result_categories = query_handler.query("query_expenditure_category")

    amount = []
    category = []
    transaction_list_str = ""
    total_expenditure = 0
    for row in result_categories:
        amount.append(round(row["amount"], 2))
        category.append(row["sub_category"])
        transaction_list_str = transaction_list_str + f"{row['sub_category']}: ₹{row['amount']}\n"
        total_expenditure = total_expenditure + row["amount"]

    model = Gemini()

    response = model.generate_response(
        f"""You are a chatbot for a bank application.
    Given the transaction list {transaction_list_str} do the following:
    1. Convert amount to correct format, for example ₹100235 to ₹1,00,235.00.
    2. Specify the Total Expenditure {total_expenditure} of the user.
    3. Convert the list to a meaningful sentence and display each sentence in a new line.
    4. Every sentence should be presented in a new line and properly formatted.
    5. Max limit should be 50 words.
    Write in a professional and business-neutral tone.
    The response should be in a conversation-like manner.
    The response is for the user to read.
    Do not say Certainly etc.
    Do not greet the user.
    Do not say - Is there anything else I can assist you with? 😊

    For example:
    Your total expenditure is ₹4,59,964.00.
    * Food and Groceries: ₹1,96,984.00.
    * Housing: ₹31,780.00.
    * Education: ₹1,23,000.00.
    * Transportation: ₹13,000.00.
    * Entertainment: ₹38,000.00.
    * Miscellaneous: ₹57,200.00.
    """
    )

    transaction_list_str = response
    transaction_list = transaction_list_str.split("*")
    if len(transaction_list) == 1:
        transaction_list = transaction_list_str.split("-")

    # Generating pie chart using plo
    labels = category
    values = amount
    fig = go.Figure(data=[go.Pie(labels=labels, values=values)])

    # Uploading pie chart to cloud bucket
    id = uuid.uuid4()
    BUCKET_NAME = environ.get("PUBLIC_BUCKET_NAME")
    SOURCE_FILE_NAME = fig.to_image(format="png")
    DESTINATION_FILE_NAME = f"pie_chart_{id}"
    url = upload_blob(BUCKET_NAME, SOURCE_FILE_NAME, DESTINATION_FILE_NAME)

    # Returning response as image
    res = {
        "fulfillment_response": {
            "messages": [
                {
                    "text": {
                        "text": [
                            " 📆 Checking... Alright, here's a breakdown of your expenditures:"
                        ]
                    }
                },
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "description",
                                    "title": "Last Month Expenditure",
                                    "text": transaction_list,
                                }
                            ],
                            [
                                {
                                    "type": "image",
                                    "rawUrl": url,
                                    "accessibilityText": "Example logo",
                                }
                            ],
                        ]
                    }
                },
            ]
        }
    }
    return res
