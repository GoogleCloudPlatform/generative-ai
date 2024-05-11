# pylint: disable=E0401

from os import environ

import functions_framework

from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")


@functions_framework.http
def account_balance(request):
    """
    Gets the account balance of a customer.

    Args:
        request (flask.Request): The request object.
            <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """

    request_json = request.get_json(silent=True)

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    query_handler = BigQueryHandler(customer_id=customer_id)

    result_account_balance = query_handler.query("query_account_balance")

    account_balance = 0
    for row in result_account_balance:
        account_balance = int(row["total_account_balance"])

    result_upcoming_payments = query_handler.query("query_upcoming_payments")

    payment_list_str = ""
    upcoming_month_expenses_amount = 0
    for row in result_upcoming_payments:
        payment_list_str = (
            payment_list_str + f"₹{row['fund_transfer_amount']} - {row['SI_Type']} on "
            f" {row['Next_Payment_Date']}\n"
        )
        upcoming_month_expenses_amount += row["fund_transfer_amount"]

    payment_list_str_formatted = payment_list_str.split("\n")

    model = Gemini()

    payment_list_str_formatted = model.generate_response(
        """
        Format the dates in the following information,e.g. 2024-10-01 to  Oct 1, 2024
        {0}
        Format the amount used in the following information in indian rupee format
        (seprated by comma in in every 2 digits) and with 2 decimal places,
        e.g. ₹100000 to ₹1,00,000.00
        {0}.
        The amount should be exact same as {0} just format it.
        example amount  = 10200 then ₹10,200.00 upto two decimal places
        """.format(
            payment_list_str
        )
    )

    account_balance_formatted = model.generate_response(
        f"""
            display the {account_balance} in proper format in indian currency
            example amount  = 10200 then ₹10,200.00
            amount = {account_balance}
            return a one word response
        """
    )

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
                                    "Your funds are on vacation, but your bills never take one."
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
