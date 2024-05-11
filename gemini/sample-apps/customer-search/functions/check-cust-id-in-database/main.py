# pylint: disable=E0401

from os import environ

import functions_framework

from utils.bq_query_handler import BigQueryHandler

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def check_customer_id(request):
    """
    This function checks if a customer ID exists in a database.

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

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": ["That's great! What can I help you with today?"]}}
            ]
        }
    }
    return res
