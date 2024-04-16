import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.language_models import TextGenerationModel
from os import environ

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
    url = (
        "https://storage.cloud.google.com/"
        + PUBLIC_BUCKET
        + "/"
        + MARKET_SUMM_DOC
    )
    print(url)

    vertexai.init(project=project_id, location="us-central1")
    parameters = {
        "max_output_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.8,
        "top_k": 40,
    }
    model = TextGenerationModel.from_pretrained("text-bison")

    debt_fund_recommendation = model.predict(
        """
            you have to recommend debt fund instead of equity funds as the account health of the user is below average in no more than 50 words.
            for example -  Given your below average account health my recommendation is to start with a low risk debt fund to build a stable corpus. Investment in equity can be started once you reach Rs.1,50,000 in a low risk debt fund. Also equity markets are very high at the moment and our research team is predicting a correction in the next 6-8 months.
          """,
        **parameters
    )

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": [debt_fund_recommendation.text]}},
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
    print(res)
    return res
