# pylint: disable=E0401

from os import environ

import functions_framework

from utils.bq_query_handler import BigQueryHandler

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def debt_funds_summary(request):
    """
    Generates a debt funds summary for a customer.

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

    PUBLIC_BUCKET = environ.get("PUBLIC_BUCKET")
    MARKET_SUMM_DOC = environ.get("MARKET_SUMM_DOC")
    url = "https://storage.cloud.google.com/" + PUBLIC_BUCKET + "/" + MARKET_SUMM_DOC

    resp = (
        "Debt Funds gave a TTM return of 6%. Returns on liquid funds have been"
        " very low around 4% but in-line with the benchmark. Markets are"
        " expecting a reduction in Interest rates funds and it is better to"
        " switch to medium duration funds."
    )

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": [resp]}},
                {
                    "text": {
                        "text": [
                            "For your information: A consolidated 1-page"
                            " outlook on Indian markets from various brokers."
                        ]
                    }
                },
                {
                    "payload": {
                        "richContent": [
                            [
                                {
                                    "type": "chips",
                                    "options": [
                                        {
                                            "text": "Market Summary",
                                            "image": {
                                                "rawUrl": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/PDF_file_icon.svg/391px-PDF_file_icon.svg.png"
                                            },
                                            "anchor": {"href": url},
                                        },
                                    ],
                                }
                            ]
                        ]
                    }
                },
            ]
        }
    }
    return res
