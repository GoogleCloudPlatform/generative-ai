# pylint: disable=E0401

from os import environ

import functions_framework
from google.cloud import bigquery

from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def extend_overdraft(request):
    """
    Extends the overdraft limit of a customer.

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

    # verifying that the customer is valid and exists in our database or not
    query_overdraft = f"""
      SELECT * from `{project_id}.DummyBankDataset.Overdraft` where customer_id = {customer_id}
    """

    result_overdraft = client.query(query_overdraft)

    overdraft_amount = -1
    overdraft_interest_rate = -1
    overdraft_processing_fee = -1
    min_interest_rate = -1
    min_processing_fee = -1

    for row in result_overdraft:
        if (
            row.get("amount") is None
            or row.get("interest_rate") is None
            or row.get("processing_fee") is None
            or row.get("min_interest_rate") is None
            or row.get("min_processing_fee") is None
        ):
            res = {
                "fulfillment_response": {
                    "messages": [{"text": {"text": ["Some unknown Error occured"]}}]
                }
            }
            return res

        overdraft_amount = row["amount"]
        overdraft_interest_rate = row["interest_rate"]
        overdraft_processing_fee = row["processing_fee"]
        min_interest_rate = row["min_interest_rate"]
        min_processing_fee = row["min_processing_fee"]

    model = Gemini()
    response = model.generate_response(
        f"""
          You have to offer an overdraft of {overdraft_amount} to a user at a interest rate of
          {overdraft_interest_rate}% with a processing fee of {overdraft_processing_fee}
          in no more than 40 words.
          
          For example -> Based on our relationship, you are pre-approved of a.
          ₹30,000 overdraft at interest of 16% and ₹1,600. Would you like to proceed?
        """
    )

    if request_json["sessionInfo"]["parameters"].get("number") is None:
        res = {
            "sessionInfo": {
                "parameters": {
                    "extend_overdraft": response,
                    "overdraft_interest_rate": overdraft_interest_rate,
                    "processing_fee": overdraft_processing_fee,
                    "min_processing_fee": min_processing_fee,
                    "min_interest_rate": min_interest_rate,
                }
            }
        }
        return res

    requested_amount = request_json["sessionInfo"]["parameters"]["number"]

    res = {
        "sessionInfo": {
            "parameters": {
                "extend_overdraft": response,
                "overdraft_amount": overdraft_amount,
                "requested_amount": requested_amount,
                "overdraft_interest_rate": overdraft_interest_rate,
                "processing_fee": overdraft_processing_fee,
                "min_processing_fee": min_processing_fee,
                "min_interest_rate": min_interest_rate,
            }
        }
    }
    return res
