import random
import vertexai
import functions_framework

from os import environ
from datetime import date

from google.cloud import bigquery
from vertexai.language_models import TextGenerationModel

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def get_credit_card(
    request: functions_framework.HttpRequest,
) -> functions_framework.HttpResponse:
    """HTTP Cloud Function that handles user requests to upload a credit card.

    Args:
        request (HttpRequest): The request object.
            <https://cloud.google.com/functions/docs/reference/python/functions_framework#functions_framework.HttpRequest>

    Returns:
        HttpResponse: The response object.
            <https://cloud.google.com/functions/docs/reference/python/functions_framework#functions_framework.HttpResponse>
    """
    # Get the request's JSON payload
    request_json = request.get_json(silent=True)
    # Get the request's arguments

    # Create a BigQuery client
    client = bigquery.Client()

    # Get the customer ID and credit card name from the request
    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]
    credit_card = request_json["sessionInfo"]["parameters"]["credit_card"]
    print(credit_card)

    # Check if the customer ID is valid
    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    # Query BigQuery to check if the customer ID exists
    query_check_cust_id = f"""
        SELECT EXISTS(SELECT * FROM `{project_id}.DummyBankDataset.Account` where customer_id = {customer_id}) as check
    """
    result_query_check_cust_id = client.query(query_check_cust_id)
    # Iterate over the query results
    for row in result_query_check_cust_id:
        print(row["check"])
        # If the customer ID does not exist, return an error message
        if row["check"] == 0:
            res = {
                "fulfillment_response": {
                    "messages": [
                        {
                            "text": {
                                "text": [
                                    "It seems you have entered an incorrect"
                                    " Customer ID. Please try again."
                                ]
                            }
                        }
                    ]
                }
            }
            print(res)
            return res

    # Generate a random credit card number
    card_number = random.randint(100000000000, 999999999999)
    # Get the current date
    present_date = date.today()
    # Format the date as a string
    present_date_str = present_date.isoformat()
    print("present_date = ", present_date_str)
    print("Card Number = ", card_number)

    # Query BigQuery to check if the credit card already exists for the customer
    query_credit_card_count = f"""
        SELECT COUNT(*) as count FROM `{project_id}.DummyBankDataset.CreditCards`
        WHERE customer_id = {customer_id} and credit_card_name = '{credit_card}'
    """
    result_credit_card_count = client.query(query_credit_card_count)

    print(result_credit_card_count)
    # Initialize the count variable
    count = 0
    # Iterate over the query results
    for row in result_credit_card_count:
        # Set the count variable to the value of the 'count' column
        count = row["count"]
    print("count = ", count)
    # If the credit card does not exist, insert it into the database
    if count == 0:
        table_id = "{project_id}.DummyBankDataset.CreditCards"
        row = [
            {
                "customer_id": customer_id,
                "credit_card_number": card_number,
                "credit_card_expiration_month": 10,
                "credit_card_expiration_year": 2027,
                "credit_card_name": credit_card,
                "international_transaction_enabled": True,
                "credit_card_last_updated": present_date_str,
            }
        ]
        client.insert_rows_json(table_id, row)
    # If the credit card already exists, update it with the new information
    else:
        query_update_credit_card = f"""UPDATE `{project_id}.DummyBankDataset.CreditCards`
            SET credit_card_number = {card_number}, credit_card_last_updated = '{present_date_str}'
            WHERE customer_id = {customer_id} and credit_card_name = '{credit_card}'
            """
        client.query(query_update_credit_card)

    print("credit_card = ", credit_card)
    # Initialize the Vertex AI client library
    vertexai.init(project=project_id, location="us-central1")
    # Set the model parameters
    parameters = {
        "max_output_tokens": 512,
        "temperature": 0.5,
        "top_p": 0.8,
        "top_k": 40,
    }
    # Load the text generation model
    model = TextGenerationModel.from_pretrained("text-bison")
    # Generate the model response
    response = model.predict(
        """You are a chatbot for a bank application.
    Tell the user that thier response has been recorded and they will recieve the credit card in next few days.
    Thank the user for enrolling with the bank.
    Ask the user if there's anything else he wants to know.
    Write in a professional and business-neutral tone.
    Word Limit is 50 words.
    The message comes in middle of conversation so don't greet the user with Hello/Hi.
    The message should be in a conversation-like manner.
    The message should be in second person's perespective tone.
    """,
        **parameters,
    )
    # Set the response message
    res = {"fulfillment_response": {"messages": [{"text": {"text": [response.text]}}]}}

    print(res)
    # Return the response
    return res
