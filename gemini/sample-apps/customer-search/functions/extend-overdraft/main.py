from os import environ

import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def extend_overdraft(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    # verifying that the customer is valid and exists in our database or not
    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

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
    model = model = GenerativeModel("gemini-1.0-pro-002")
    responses = model.generate_content(
        f"""
          you have to offer an overdraft of {overdraft_amount} to a user at a interest rate of {overdraft_interest_rate}% with a processing fee of {overdraft_processing_fee} in no more than 40 words.
          For example -> Based on our relationship, you are pre-approved of a. ₹30,000 overdraft at interest of 16% and ₹1,600. Would you like to proceed?
        """,
      generation_config=generation_config,
      safety_settings=safety_settings,
      stream=True,
    )

    final_response = ""
    for response in responses:
        final_response += response.text

    if request_json["sessionInfo"]["parameters"].get("number") is None:
        res = {
            "sessionInfo": {
                "parameters": {
                    "extend_overdraft": final_response,
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
                "extend_overdraft": final_response,
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
