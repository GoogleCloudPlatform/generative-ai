from os import environ

import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import FinishReason, GenerativeModel, Part
import vertexai.preview.generative_models as generative_models

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def account_balance(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()
    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    query_account_balance = f"""
        SELECT SUM(avg_monthly_bal) as total_account_balance FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id}
        and avg_monthly_bal is NOT NULL
        and product IN('Savings A/C ', 'Savings Salary A/C ', 'Premium Current A/C ', 'Gold Card ', 'Platinum Card ')
    """

    result_account_balance = client.query(query_account_balance)

    account_balance = 0
    for row in result_account_balance:
        account_balance = int(row["total_account_balance"])

    query_upcoming_payments = f"""
        SELECT * FROM `{project_id}.DummyBankDataset.StandingInstructions`
        where account_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id}) and EXTRACT(MONTH from Next_Payment_Date) = 10 and EXTRACT(YEAR from Next_Payment_Date) = 2023 and fund_transfer_amount IS NOT NULL
        """

    result_upcoming_payments = client.query(query_upcoming_payments)

    payment_list_str = ""
    upcoming_month_expenses_amount = 0
    for row in result_upcoming_payments:
        payment_list_str = (
            payment_list_str + f"₹{row['fund_transfer_amount']} - {row['SI_Type']} on "
            f" {row['Next_Payment_Date']}\n"
        )
        upcoming_month_expenses_amount += row["fund_transfer_amount"]

    payment_list_str_formatted = payment_list_str.split("\n")

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
        """
        Format the dates in the following information,e.g. 2024-10-01 to  Oct 1, 2024
        {0}
        Format the amount used in the following information in indian rupee format(seprated by comma in in every 2 digits) and with 2 decimal places,e.g. ₹100000 to ₹1,00,000.00
        {0}.
        The amount should be exact same as {0} just format it.
        example amount  = 10200 then ₹10,200.00 upto two decimal places
        """.format(
            payment_list_str
        ),
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    payment_list_str_formatted = ""
    for response in responses:
        payment_list_str_formatted += response.text

    responses = model.generate_content(
        f"""
            display the {account_balance} in proper format in indian currency
            example amount  = 10200 then ₹10,200.00
            amount = {account_balance}
            return a one word response
        """,
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    account_balance_formatted = ""

    for response in responses:
        account_balance_formatted += response.text

    account_balance_str = f"Your account balance is {account_balance_formatted}"

    if account_balance < upcoming_month_expenses_amount:
        if customer_id == 592783:
            res = {
                "fulfillment_response": {
                    "messages": [
                        {"text": {"text": [account_balance_str]}},
                        {
                            "text": {
                                "text": [
                                    "And, scheduled expenses for rest of month"
                                    " are:\n" + payment_list_str_formatted
                                ]
                            }
                        },
                        {
                            "text": {
                                "text": [
                                    "Your funds are on vacation, but your"
                                    " bills never take one."
                                ]
                            }
                        },
                    ]
                },
                "sessionInfo": {
                    "parameters": {
                        "transition_code": 1,
                    }
                },
            }
            return res
        else:
            res = {
                "fulfillment_response": {
                    "messages": [
                        {"text": {"text": [account_balance_str]}},
                        {
                            "text": {
                                "text": [
                                    "And, scheduled expenses for rest of month"
                                    " are:\n" + payment_list_str_formatted
                                ]
                            }
                        },
                    ]
                },
            }
            return res

    if customer_id == 235813:
        res = {
            "fulfillment_response": {
                "messages": [
                    {"text": {"text": [account_balance_str]}},
                    {
                        "text": {
                            "text": [
                                "And, scheduled expenses for rest of month"
                                " are:\n" + payment_list_str_formatted
                            ]
                        }
                    },
                ]
            },
            "sessionInfo": {
                "parameters": {
                    "transition_code": 2,
                }
            },
        }
        return res
    else:
        res = {
            "fulfillment_response": {
                "messages": [
                    {"text": {"text": [account_balance_str]}},
                    {
                        "text": {
                            "text": [
                                "And, scheduled expenses for rest of month"
                                " are:\n" + payment_list_str_formatted
                            ]
                        }
                    },
                ]
            }
        }
        return res
