import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.language_models import TextGenerationModel
from os import environ

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def hello_http(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]
    print(request_json["sessionInfo"]["parameters"])

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
        print(row)
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
            print(res)
            return res

        overdraft_amount = row["amount"]
        overdraft_interest_rate = row["interest_rate"]
        overdraft_processing_fee = row["processing_fee"]
        min_interest_rate = row["min_interest_rate"]
        min_processing_fee = row["min_processing_fee"]

    vertexai.init(project=project_id, location="us-central1")
    parameters = {
        "max_output_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.8,
        "top_k": 40,
    }
    model = TextGenerationModel.from_pretrained("text-bison")

    extend_overdraft = model.predict(
        """
          you have to offer an overdraft of {0} to a user at a interest rate of {1}% with a processing fee of {2} in no more than 40 words.
          For example -> Based on our relationship, you are pre-approved of a. ₹30,000 overdraft at interest of 16% and ₹1,600. Would you like to proceed?
        """.format(
            overdraft_amount, overdraft_interest_rate, overdraft_processing_fee
        ),
        **parameters,
    )

    if request_json["sessionInfo"]["parameters"].get("number") is None:
        res = {
            "sessionInfo": {
                "parameters": {
                    "extend_overdraft": extend_overdraft.text,
                    "overdraft_interest_rate": overdraft_interest_rate,
                    "processing_fee": overdraft_processing_fee,
                    "min_processing_fee": min_processing_fee,
                    "min_interest_rate": min_interest_rate,
                }
            }
        }
        print(res)
        return res

    requested_amount = request_json["sessionInfo"]["parameters"]["number"]

    res = {
        "sessionInfo": {
            "parameters": {
                "extend_overdraft": extend_overdraft.text,
                "overdraft_amount": overdraft_amount,
                "requested_amount": requested_amount,
                "overdraft_interest_rate": overdraft_interest_rate,
                "processing_fee": overdraft_processing_fee,
                "min_processing_fee": min_processing_fee,
                "min_interest_rate": min_interest_rate,
            }
        }
    }
    print(res)
    return res
