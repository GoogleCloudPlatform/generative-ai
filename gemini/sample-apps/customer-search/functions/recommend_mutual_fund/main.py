# pylint: disable=E0401

from os import environ

import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel
import vertexai.preview.generative_models as generative_models

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def mutual_fund_recommendation(request):
    """
    Recommends mutual funds to a customer.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

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
    response = model.generate_content(
        f"""
        You are a mutual fund expert/analyst and you have to recommed the 3 best possible mutual fund based on returns among the given list in csv format
        {csv_table}

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
    """,
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    final_response = ""
    for response in response:
        final_response += response.text

    investment_list_str = final_response.text

    res = {
        "fulfillment_response": {
            "messages": [{"text": {"text": [investment_list_str]}}]
        }
    }
    return res
