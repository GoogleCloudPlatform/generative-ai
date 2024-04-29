from os import environ

import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import FinishReason, GenerativeModel, Part
import vertexai.preview.generative_models as generative_models

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def account_health_tips(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    query_transaction_category = f"""
        SELECT SUM(transaction_amount) as amount, sub_category as category,FROM `{project_id}.DummyBankDataset.AccountTransactions`
        where ac_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id}) AND debit_credit_indicator = 'Debit' and category in('Wants', 'Miscellaneous')
        GROUP BY sub_category
    """

    query_average_monthly_expense = f"""SELECT AVG(total_amount) as average_monthly_expense from (
        SELECT EXTRACT(MONTH FROM 	date) AS month,
        SUM(transaction_amount) AS total_amount FROM `{project_id}.DummyBankDataset.AccountTransactions` WHERE ac_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account` where customer_id = {customer_id} and debit_credit_indicator = 'Debit')
        GROUP BY month
        ORDER BY month)
    """
    query_last_month_expense = f"""SELECT EXTRACT(MONTH FROM date) AS month,
        SUM(transaction_amount) AS last_month_expense FROM `{project_id}.DummyBankDataset.AccountTransactions` WHERE ac_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id} and debit_credit_indicator = 'Debit') and EXTRACT(MONTH FROM date)=9
        GROUP BY month
        ORDER BY month;
    """

    result_categories = client.query(query_transaction_category)
    result_average_monthly_expense = client.query(query_average_monthly_expense)
    result_last_month_expense = client.query(query_last_month_expense)

    # modification starts

    query_expenditure_category = f"""
        SELECT SUM(transaction_amount) as amount, sub_category, EXTRACT(MONTH FROM date) AS month FROM `{project_id}.DummyBankDataset.AccountTransactions`
        where ac_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id}) AND debit_credit_indicator = 'Debit' and EXTRACT(MONTH FROM date)=9 and EXTRACT(YEAR FROM date)=2023
        GROUP BY month, sub_category
    """

    rc = client.query(query_expenditure_category)

    lm_amount = 0
    category = []
    transaction_list_str = ""
    total_expenditure = 0
    for row in rc:
        lm_amount += round(row["amount"], 2)
        category.append(row["sub_category"])
        transaction_list_str = (
            transaction_list_str + f"{row['sub_category']}: ₹{row['amount']}\n"
        )
        total_expenditure = total_expenditure + row["amount"]

    # modification ends

    average_monthly_expense = 0
    last_month_expense = 0
    amount = []
    category = []
    transaction_list = ""
    for row in result_categories:
        amount.append(row["amount"])
        category.append(row["category"])
        transaction_list = transaction_list + f",₹{row['amount']} {row['category']}"

    for row in result_average_monthly_expense:
        if row["average_monthly_expense"] is not None:
            average_monthly_expense = int(row["average_monthly_expense"])

    for row in result_last_month_expense:
        if row["last_month_expense"] is not None:
            last_month_expense = int(row["last_month_expense"])

    transaction_list = transaction_list[1:]

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
        f"""You are a bank chatbot.
    Tell the user whether the Last Month Expense = ₹{lm_amount} is less than or greater than the Average monthly expense = ₹{average_monthly_expense}.
    You have been give list of categories and amount spend.
    Transaction List  = {transaction_list_str}.
    Depending on the data get some insights on how the spending and if any what to do for better account health, explain exaclty where is is not good and why.
    Write in a professional and business-neutral tone in very brief in about 60 words in a very readable form.
    do not say that largest expense category is housing as housing is a necessity.
    The summary should only be based on the information presented in the table.
    Aslo provide 3-4 tips to reduce the spent in largest spent categories.
    The summary is to be read in a chat response.
    The amount should be comma seprated in indian rupee format and upto 2 decimal places. Convert amount to correct format for example ₹ 100235 to ₹ 1,00,235.00.
    For example the output should look like : The last month's expense of ₹24,07,764.00 is greater than the average monthly expense of ₹13,09,025.00. The largest expense category is xyz, followed by abc. You may want to consider reducing your spending in these areas to improve your account health.
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
        "sessionInfo": {"parameters": {"vehicle_type": "Bike"}},
    }
    return res
