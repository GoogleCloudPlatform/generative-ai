import functions_framework
from google.cloud import bigquery
from vertexai.language_models import TextGenerationModel
import vertexai
from os import environ

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def hello_http(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()
    print(request_json)
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

    print(account_balance)

    # Getting upcoming expenses
    vertexai.init(project=project_id, location="us-central1")
    model_prompt = TextGenerationModel.from_pretrained("text-bison@001")
    parameters = {
        "max_output_tokens": 1024,
        "temperature": 0.1,
        "top_p": 0.8,
        "top_k": 40,
    }

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
        print("row = ", row["fund_transfer_amount"])
        print("payment list str = ", payment_list_str)

    print("Upcoming month expense amount = ", upcoming_month_expenses_amount)

    print("payment list debug - ", payment_list_str)

    payment_list_str_formatted = payment_list_str.split("\n")
    payment_list_str_formatted = model_prompt.predict(
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
        **parameters,
    )
    account_balance_formatted = model_prompt.predict(
        """
            display the {0} in proper format in indian currency
            example amount  = 10200 then ₹10,200.00
            amount = {0}
            return a one word response
        """.format(
            account_balance
        ),
        **parameters,
    )

    account_balance_str = f"Your account balance is {account_balance_formatted.text}"

    print("This is = ", payment_list_str_formatted.text)
    print("new = ", account_balance_formatted.text)
    print("old = ", account_balance)

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
                                    " are:\n" + payment_list_str_formatted.text
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
                # "targetPage": "projects/{project_id}/locations/us-central1/agents/de6b2b88-afd4-49fb-b118-d6457d9d6847/flows/00000000-0000-0000-0000-000000000000/pages/Home_Page"
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
                                    " are:\n" + payment_list_str_formatted.text
                                ]
                            }
                        },
                    ]
                },
                # "targetPage": "projects/{project_id}/locations/us-central1/agents/de6b2b88-afd4-49fb-b118-d6457d9d6847/flows/00000000-0000-0000-0000-000000000000/pages/Home_Page"
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
                                " are:\n" + payment_list_str_formatted.text
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
                                " are:\n" + payment_list_str_formatted.text
                            ]
                        }
                    },
                ]
            }
        }
        return res
