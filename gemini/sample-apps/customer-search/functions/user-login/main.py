# pylint: disable=E0401

from os import environ

import functions_framework
from google.cloud import bigquery

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def user_login(
    request: functions_framework.HttpRequest,
) -> functions_framework.HttpResponse:
    """HTTP Cloud Function that authenticates a user and returns their customer ID.

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

    # Check if the request method is OPTIONS
    if request.method == "OPTIONS":
        # Set the CORS headers for preflight requests
        headers = {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "GET",
            "Access-Control-Allow-Headers": "Content-Type",
            "Access-Control-Max-Age": "3600",
        }

        # Return a 204 response with the CORS headers
        return ("", 204, headers)

    # Create a BigQuery client
    client = bigquery.Client()

    # Get the user ID from the request's JSON payload
    uid = request_json["uid"]

    # Check if the user ID is present
    if uid is not None:
        print("username", uid)
    else:
        print("Please provide a uid!")
        return {"message": "Incorrect uid", "status": 400}

    # Query BigQuery to get the customer ID and first name for the user
    query_get_cust_id = f"""SELECT First_Name, customer_id FROM `{project_id}.DummyBankDataset.Customer` where firebase_uid = '{uid}'"""
    result_cust_id = client.query(query_get_cust_id)

    # Initialize the response object
    res = {}

    # Iterate over the query results
    for row in result_cust_id:
        print(row["customer_id"])
        res = {"cust_id": row["customer_id"], "name": row["First_Name"]}

    # Set the CORS headers for the response
    headers = {"Access-Control-Allow-Origin": "*"}

    # Return a 200 response with the customer ID and first name
    return (res, 200, headers)
