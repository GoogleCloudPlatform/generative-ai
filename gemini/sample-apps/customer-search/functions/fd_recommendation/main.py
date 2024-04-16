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

    print(request_json["sessionInfo"]["parameters"])

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]
    # customer_id = 235813
    # 342345, 592783

    # verifying that the customer is valid and exists in our database or not
    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    query_check_cust_id = f"""
      SELECT EXISTS(SELECT * FROM `{project_id}.DummyBankDataset.Account` where customer_id = {customer_id}) as check
  """
    result_query_check_cust_id = client.query(query_check_cust_id)
    for row in result_query_check_cust_id:
        print(row["check"])
        if row["check"] == 0:
            res = {
                "fulfillment_response": {
                    "messages": [
                        {
                            "text": {
                                "text": [
                                    "It seems you have entered an incorrect"
                                    " Customer ID. Please try again."
                                ]
                            }
                        }
                    ]
                }
            }
            print(res)
            return res

    # get account balance of the user
    query_account_balance = f"""
    SELECT SUM(avg_monthly_bal) as total_account_balance FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id}
    and avg_monthly_bal is NOT NULL
    and product IN('Savings A/C ', 'Savings Salary A/C ', 'Premium Current A/C ', 'Gold Card ', 'Platinum Card ')
  """
    result_account_balance = client.query(query_account_balance)

    balance = 100

    # for each high risk mutual fund
    for row in result_account_balance:
        # extract the name of the mutual fund and the current amount
        if row["total_account_balance"] is not None:
            balance += row["total_account_balance"]

    print(balance)

    fd_amount = 0.75 * balance

    if fd_amount < 10000:
        result = "Your balance is too low for FD."

        output = {
            "fulfillment_response": {
                "messages": [{"text": {"text": [result]}}]
            }
        }
        return output

    result = "You should invest in FD"

    vertexai.init(project=project_id, location="us-central1")
    parameters = {
        "max_output_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.8,
        "top_k": 40,
    }
    model = TextGenerationModel.from_pretrained("text-bison")

    response = model.predict(
        """You are a chatbot for a bank application. Recommend user the option to put thier money {0} in Fd and
    ask user whether they would like to open an fd in CymBank.
    Show the amount as well.
    The amount should be displayed in this format e.g - ₹ 1,20,000 instead of 120000
    Write in a professional and business-neutral tone.
    Do not say Hi Hello etc.
    The response should not be more than 15 words.
    Make the output more conversational and user freindly.
    The response is for the user to read.
    """.format(
            fd_amount
        ),
        **parameters,
    )

    print("Result = ", response.text)

    res = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [response.text]}}]
        },
        "sessionInfo": {
            "parameters": {"fd_amount": fd_amount, "account_balance": balance}
        },
    }
    print(res)
    return res
