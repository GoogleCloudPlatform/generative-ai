# pylint: disable=E0401

from os import environ

import functions_framework
from google.cloud import bigquery

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def detect_unusual_transactions(
    request: functions_framework.HttpRequest,
) -> functions_framework.HttpResponse:
    """HTTP Cloud Function that handles user requests to get their unusual transactions.

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

    # Get the customer ID from the request's JSON payload
    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    # Check if the customer ID is present
    # Query BigQuery to get the unusual transactions for the customer
    query_unusual_transactions = f"""SELECT
  *
FROM
  ML.DETECT_ANOMALIES(MODEL `{project_id}.ExpensePrediction.unsual_spend3`,
  STRUCT(0.02 AS contamination),
  TABLE
`{project_id}.DummyBankDataset.AccountTransactions`) WHERE debit_credit_indicator = 'Debit' and ac_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account` where customer_id = {customer_id}) and is_anomaly = True ORDER BY mean_squared_error DESC LIMIT 3
  """
    result_unusual_transactions = client.query(query_unusual_transactions)

    # Initialize the list of unusual transactions
    unusual_transactions_list = "Your unusual transactions are :" + "\n"

    # Iterate over the query results and add the unusual transactions to the list
    flag = 0
    for row in result_unusual_transactions:
        flag = flag + 1
        unusual_transactions_list = (
            unusual_transactions_list + f" ₹{row['transaction_amount']} on {row['date']} to"
            f" {row['counterparty_name']} in {row['city']},"
            f" {row['country']}." + "\n"
        )

    # If there are no unusual transactions, set the list to "You have no unusual transactions!"
    if flag == 0:
        unusual_transactions_list = "You have no unusual transactions!"

    print("result_unusual_transactions = ", unusual_transactions_list)

    # Set the response message
    res = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [unusual_transactions_list]}}]
        }
    }

    # Return the response
    return res
