import vertexai
import functions_framework

from os import environ

from google.cloud import bigquery
from vertexai.language_models import TextGenerationModel

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def mutual_fund_recommendation(request):
    request_json = request.get_json(silent=True)
    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    query_mf = f"""
        SELECT * FROM `{project_id}.DummyBankDataset.MutualFund`
    """

    result_mf = client.query(query_mf)
    csv_table = "name,risk_category,type_of_fund,size,one_month,six_month,one_year,three_year,five_year,all_time,NAV,min_sip_amount,fund_size,expense_ratio,exit_load,stamp_duty\n"

    for row in result_mf:
        csv_table = csv_table + str(row["name"]) + ","
        csv_table = csv_table + str(row["risk_category"]) + ","
        csv_table = csv_table + str(row["type_of_fund"]) + ","
        csv_table = csv_table + str(row["size"]) + ","
        csv_table = csv_table + str(row["one_month"]) + ","
        csv_table = csv_table + str(row["six_month"]) + ","
        csv_table = csv_table + str(row["one_year"]) + ","
        csv_table = csv_table + str(row["three_year"]) + ","
        csv_table = csv_table + str(row["five_year"]) + ","
        csv_table = csv_table + str(row["all_time"]) + ","
        csv_table = csv_table + str(row["min_sip_amount"]) + ","
        csv_table = csv_table + str(row["fund_size"]) + ","
        csv_table = csv_table + str(row["expense_ratio"]) + ","
        csv_table = csv_table + str(row["exit_load"]) + ","
        csv_table = csv_table + str(row["stamp_duty"])
        csv_table = csv_table + "\n"

    print(csv_table)
    vertexai.init(project=project_id, location="us-central1")
    parameters = {
        "max_output_tokens": 512,
        "temperature": 0.3,
        "top_p": 0.8,
        "top_k": 40,
    }
    model = TextGenerationModel.from_pretrained("text-bison")
    response = model.predict(
        """
    You are a mutual fund expert/analyst and you have to recommed the 3 best possible mutual fund based on returns among the given list in csv format
    {0}

    Write in a professional and business-neutral tone.
    Word Limit is 40 words.
    The message comes in middle of conversation so don't greet the user with Hello/Hi.
    The currency should be Indian Rupees
    The message should be in a conversation-like manner based on the Account Status.
    The message should only be based on the information presented above.
    The message should be in second person's perespective tone.
    Start the message like "
    The top three performing mutual based on returns are these...
    the following details must be mentioned in uniformly spaced tabular format:
    For each mutual fund in the top 3 list: mention the respective one month from six_month return in ₹, one_year return in ₹, three_year in ₹, NAV.
    "
    """.format(
            csv_table
        ),
        **parameters,
    )

    investment_list_str = response.text

    res = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [investment_list_str]}}]
        }
    }
    print(res)
    return res
