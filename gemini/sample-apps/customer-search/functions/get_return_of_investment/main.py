from os import environ

import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.language_models import TextGenerationModel

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def hello_http(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    query_investments = f"""
        SELECT (amount_invested*six_month_return) as six_month_return,Scheme_Name from `{project_id}.DummyBankDataset.MutualFundAccountHolding`
        where account_no in (Select account_id from `{project_id}.DummyBankDataset.Account` where customer_id={customer_id})
    """

    result_investments = client.query(query_investments)

    Scheme_Name = []
    six_month_return = []
    investment_list_str = ""
    for row in result_investments:
        Scheme_Name.append(row["Scheme_Name"])
        six_month_return.append(row["six_month_return"])
        investment_list_str = (
            investment_list_str
            + f",₹ {row['six_month_return']} in {row['Scheme_Name']}"
        )

    investment_list_str = investment_list_str[1:]

    vertexai.init(project=project_id, location="us-central1")
    parameters = {
        "max_output_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.8,
        "top_k": 40,
    }
    model = TextGenerationModel.from_pretrained("text-bison")
    response = model.predict(
        """Given the return of investment list do the following:
    1. Convert amount to correct format for example ₹ 100235 to ₹ 1,00,235, ₹ 16423.3423 to ₹ 16,423.3423.
    2. Convert the list to a meaningful sentence.
    Transaction List = {0}
    Assume that a positive amount indicate profit while negative indicate loss.
    """.format(
            investment_list_str
        ),
        **parameters,
    )

    investment_list_str = response.text

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": investment_list_str}}]}
    }
    print(res)
    return res
