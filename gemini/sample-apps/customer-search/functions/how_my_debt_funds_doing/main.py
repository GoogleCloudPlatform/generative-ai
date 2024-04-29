from os import environ

import functions_framework
from google.cloud import bigquery

project_id = environ.get("PROJECT_ID")
client: bigquery.Client = bigquery.Client()


@functions_framework.http
def hello_http(request):
    request_json = request.get_json(silent=True)

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]
    # customer_id = 235813
    # 342345, 592783

    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

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
