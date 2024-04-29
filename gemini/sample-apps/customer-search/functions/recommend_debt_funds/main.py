from os import environ

import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models

project_id = environ.get("PROJECT_ID")
client: bigquery.Client = bigquery.Client()


@functions_framework.http
def debt_fund_recommendation(request):
    request_json = request.get_json(silent=True)

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    PUBLIC_BUCKET = environ.get("PUBLIC_BUCKET")
    MARKET_SUMM_DOC = environ.get("MARKET_SUMM_DOC")
    url = "https://storage.cloud.google.com/" + PUBLIC_BUCKET + "/" + MARKET_SUMM_DOC
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

    debt_fund_recommendation = model.generate_content(
        """
            you have to recommend debt fund instead of equity funds as the account health of the user is below average in no more than 50 words.
            for example -  Given your below average account health my recommendation is to start with a low risk debt fund to build a stable corpus. Investment in equity can be started once you reach Rs.1,50,000 in a low risk debt fund. Also equity markets are very high at the moment and our research team is predicting a correction in the next 6-8 months.
          """,
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    final_response = ""
    for response in debt_fund_recommendation:
        final_response += response.text

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": [final_response.text]}},
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
