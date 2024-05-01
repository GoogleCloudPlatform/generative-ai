from os import environ
import uuid

import functions_framework
from google.cloud import bigquery, storage
import plotly.graph_objects as go
import vertexai
from vertexai.generative_models import FinishReason, GenerativeModel, Part
import vertexai.preview.generative_models as generative_models

project_id = environ.get("PROJECT_ID")


def upload_blob(bucket_name, source_file_name, destination_blob_name):
    """Uploads a file to the bucket"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(source_file_name)
    return blob.public_url


@functions_framework.http
def category_wise_expenditure(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    query_expenditure_category = f"""
        SELECT SUM(transaction_amount) as amount, sub_category, EXTRACT(MONTH FROM date) AS month FROM `{project_id}.DummyBankDataset.AccountTransactions`
        where ac_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset
        Account` where customer_id={customer_id}) AND debit_credit_indicator = 'Debit' and EXTRACT(MONTH FROM date)=9 and EXTRACT(YEAR FROM date)=2023
        GROUP BY month, sub_category
    """

    result_categories = client.query(query_expenditure_category)

    amount = []
    category = []
    transaction_list_str = ""
    total_expenditure = 0
    for row in result_categories:
        amount.append(round(row["amount"], 2))
        category.append(row["sub_category"])
        transaction_list_str = (
            transaction_list_str + f"{row['sub_category']}: ₹{row['amount']}\n"
        )
        total_expenditure = total_expenditure + row["amount"]

    vertexai.init(project=project_id, location="us-central1")
    generation_config = {
        "max_output_tokens": 2048,
        "temperature": 1,
        "top_p": 1,
    }
    safety_settings = {
        generative_models.HarmCategory.HARM_CATEGORY_HATE_SPEECH: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
        generative_models.HarmCategory.HARM_CATEGORY_HARASSMENT: generative_models.HarmBlockThreshold.BLOCK_MEDIUM_AND_ABOVE,
    }
    model = GenerativeModel("gemini-1.0-pro-002")

    responses = model.generate_content(
        f"""You are a chatbot for a bank application. Given the transaction list {transaction_list_str} do the following:
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
    """,
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    final_response = ""
    for response in responses:
        final_response += response.text

    transaction_list_str = final_response
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
                            " 📆 Checking... Alright, here's a breakdown of"
                            " your expenditures:"
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
