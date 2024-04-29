from os import environ

import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models

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

    query_assets = f"""
        SELECT sum(avg_monthly_bal) as asset FROM `{project_id}.DummyBankDataset.Account`
        where customer_id = {customer_id} and product in ('Savings A/C ','Savings Salary A/C ', 'Premium Current A/C ', 'Fixed Deposit', 'Flexi Deposit');
    """

    result_asset = client.query(query_assets)
    asset_amount = 0
    for row in result_asset:
        if row["asset"] is not None:
            asset_amount = int(row["asset"])

    category = ""
    if asset_amount < 6000000:
        category = "Standard"
    else:
        category = "Premium"

    query_cust_address = f"""
        SELECT Address_2nd_Line, Address_3rd_Line, city, state, Plus_Code FROM `{project_id}.DummyBankDataset.Customer` where customer_id = {customer_id}
    """

    result_cust_address = client.query(query_cust_address)

    cust_address = ""
    for row in result_cust_address:
        cust_address = (
            row["Address_2nd_Line"]
            + ", "
            + row["Address_3rd_Line"]
            + ", "
            + row["city"]
            + ", "
            + row["state"]
            + " "
            + str(row["Plus_Code"])
        )
    
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
    
    responses = model.generate_content(
        f"""You are a chatbot for Cymbal bank application.
    The user is interested in buying a new motorcycle. Given the address of the user as {cust_address}, provide the user information about 5 motorcycle dealers of {category} category brands along with address of their showrooms nearest to their address {0} and some of the best selling models with proper spacing and indentation for clear readability.
    Also provide discount offers for the Cymbal bank's customers for each of the respective dealers in a professional manner. Maximum word limit is 1000.
    *DO NOT* mention the category {category} of the brands.

    The currency to be used is Indian Rupee,i.e.,₹.
    """,
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    final_response = ""
    for response in responses:
        final_response += response.text
        
    res = {
        "fulfillment_response": {"messages": [{"text": {"text": [final_response]}}]},
        "sessionInfo": {
            "parameters": {"vehicle_type": "Bike", "showrooms": final_response}
        },
    }
    return res
