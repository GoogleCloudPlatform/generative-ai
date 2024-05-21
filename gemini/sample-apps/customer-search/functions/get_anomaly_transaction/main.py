"""This is a python utility file."""

# pylint: disable=E0401
# pylint: disable=R0801
# pylint: disable=R0914

from os import environ

import functions_framework
from google.cloud import bigquery

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def transaction_anomaly_detection(request):
    """
    Detects anomalous transactions for a customer.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    query_account_balance = f"""
CREATE OR REPLACE TABLE DummyBankDataset.RuntimeTableForAnomaly AS ( \
SELECT * FROM `{project_id}.DummyBankDataset.AccountTransactions` WHERE \
ac_id in (SELECT account_id FROM {project_id}.DummyBankDataset.Account \
where customer_id={customer_id}));

SELECT * FROM ML.DETECT_ANOMALIES(MODEL `ExpensePrediction.my_kmeans_model`,\
STRUCT(0.005 AS contamination),TABLE `{project_id}.DummyBankDataset.RuntimeTableForAnomaly`)
"""

    result_account_balance = client.query(query_account_balance)

    account_balance = 0
    for row in result_account_balance:
        account_balance = int(row["total_account_balance"])

    account_balance_str = f"Your account balance is ₹{account_balance}."

    res = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [account_balance_str]}}]
        }
    }
    return res
