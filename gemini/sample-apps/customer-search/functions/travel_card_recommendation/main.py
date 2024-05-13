# pylint: disable=E0401

from os import environ

import functions_framework
from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini
from utils.multithreading import run_all

project_id = environ.get("PROJECT_ID")


def get_ac_health_status(
    total_expenditure: int,
    asset_amount: int,
    debt_amount: int,
    total_high_risk_investment: int,
    total_investment: int,
    total_income: int,
) -> str:
    """
    Calculates the account health status based on financial details.

    Args:
        total_expenditure (int): Total expenditure of the customer.
        asset_amount (int): Total asset amount of the customer.
        debt_amount (int): Total debt amount of the customer.
        total_high_risk_investment (int): Total high-risk investment amount of the customer.
        total_investment (int): Total investment amount of the customer.
        total_income (int): Total income of the customer.

    Returns:
        str: The account health status ("Healthy", "Needs Attention", or "Concerning").
    """

    account_status = ""
    if (
        total_expenditure < 0.75 * total_income
        and asset_amount >= 0.2 * total_income
        and debt_amount < 0.3 * asset_amount
        and total_high_risk_investment < 0.3 * total_investment
    ):
        account_status = "Healthy"
    elif (
        (
            total_expenditure >= 0.75 * total_income
            and total_expenditure < 0.9 * total_income
        )
        or (asset_amount < 0.2 * total_income and asset_amount > 0.1 * total_income)
        or (debt_amount >= 0.3 * asset_amount and debt_amount < 0.75 * asset_amount)
        or (
            total_high_risk_investment >= 0.3 * total_investment
            and total_high_risk_investment < 0.8 * total_investment
        )
    ):
        account_status = "Needs Attention"
    else:
        account_status = "Concerning"

    return account_status


def get_ac_details(project_id: str, user_accounts: list) -> tuple:
    """
    Calculates the total income and total expenditure of a customer.

    Args:
        project_id (str): The project ID of the customer.
        user_accounts (list): A list of account IDs of the customer.

    Returns:
        tuple: A tuple containing the total income and total expenditure of the customer.
    """

    total_income = 0
    total_expenditure = 0
    for account in user_accounts:
        query_expenditure_details = f"""
            SELECT SUM(transaction_amount) as expenditure FROM `{project_id}.DummyBankDataset.AccountTransactions` WHERE ac_id = {account} AND debit_credit_indicator = 'Debit'
        """

        query_income = f"""
            SELECT SUM(transaction_amount) as income FROM `{project_id}.DummyBankDataset.AccountTransactions` WHERE ac_id = {account} and debit_credit_indicator = 'Credit'
        """

        res_sub = run_all(
            {
                "query_expenditure_details": query_expenditure_details,
                "query_income": query_income,
            }
        )
        for row in res_sub["query_income"]:
            if row["income"] is not None:
                total_income += row["income"]

        for row in res_sub["query_expenditure_details"]:
            if row["expenditure"] is not None:
                total_expenditure = total_expenditure + row["expenditure"]

    return total_income, total_expenditure


@functions_framework.http
def travel_card_recommendation(request):
    """
    Recommends a travel credit card to the user based on their financial profile.

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

    cust_id_exists, res = query_handler.validate_customer_id()
    if not cust_id_exists:
        return res

    result_age_on_book = query_handler.query("query_age_on_book")
    customer_age_on_book = 0
    for row in result_age_on_book:
        customer_age_on_book = row["customer_age_on_book"]

    model = Gemini()

    if customer_age_on_book < 365:
        response = model.generate_response(
            """You are a chatbot for a bank application.
        Tell the user politely that they are not eligible for the the credit card as they are new customer. Only cutomer older than 1 year with the bank are eligible for credit card.
        Ask the user to wait and ask if they want anything else like mutual funds or fixed deposit.
        Write in a professional and business-neutral tone.
        Word Limit is 60 words.
        The message comes in middle of conversation so don't greet the user with Hello/Hi.
        The user lives in India.
        The message should be in a conversation-like manner based on the Account Status.
        The message should be in second person's perespective tone.
        """
        )

        res = {
            "fulfillment_response": {"messages": [{"text": {"text": [response]}}]},
            "target_page": "projects/{project_id}/locations/asia-south1/agents/118233dd-f023-4dad-b302-3906a7365ccc/flows/00000000-0000-0000-0000-000000000000/pages/06e52d7c-536a-4cbf-baba-4fe7d686e472",
        }
        return res

    result_travel_expense = query_handler.query("query_travel_expense")

    asset_amount = 0
    debt_amount = 0
    total_investment = 0
    total_high_risk_investment = 0
    user_accounts = []
    travel_expense = 0
    account_status = ""
    credit_card = ""

    for row in result_travel_expense:
        if row["travel_expense"] is not None:
            travel_expense += int(row["travel_expense"])

    res = query_handler.run_all(
        [
            "query_assets",
            "query_debts",
            "query_account_details",
            "query_user_details",
            "query_fd",
            "query_total_mf",
            "query_high_risk_mf",
            "query_avg_monthly_balance",
            "query_average_monthly_expense",
            "query_last_month_expense",
            "query_investment_returns",
        ]
    )

    for row in res["query_assets"]:
        if row["asset"] is not None:
            asset_amount = int(row["asset"])

    for row in res["query_debts"]:
        if row["debt"] is not None:
            debt_amount = int(row["debt"])

    for row in res["query_account_details"]:
        user_accounts.append(row["account_id"])

    total_income, total_expenditure = get_ac_details(
        project_id=project_id, user_accounts=user_accounts
    )

    for row in res["query_fd"]:
        if row["asset"] is not None:
            total_investment += row["asset"]

    for row in res["query_total_mf"]:
        if row["total_mf_investment"] is not None:
            total_investment += row["total_mf_investment"]

    for row in res["query_high_risk_mf"]:
        if row["total_high_risk_investment"] is not None:
            total_high_risk_investment += row["total_high_risk_investment"]

    account_status = get_ac_health_status(
        total_income=total_income,
        total_expenditure=total_expenditure,
        asset_amount=asset_amount,
        debt_amount=debt_amount,
        total_investment=total_investment,
        total_high_risk_investment=total_high_risk_investment,
    )

    if account_status == "Healthy":
        credit_card = "Cymbal Luxury Lifestyle Card"
    elif account_status == "Needs Attention":
        credit_card = "Cymbal No-annual-fee Rewards Card"
    else:
        credit_card = "Cymbal Secured Credit Card"

    response = model.generate_response(
        f"""
        You are a chatbot for a bank application you have been given the Credit Card as {credit_card}.
        You have to recommend the given credit card to the user and explain the benefits of the credit card.
        Write in a professional and business-neutral tone.
        Word Limit is 100 words.
        The message comes in middle of conversation so don't greet the user with Hello/Hi.
        The user lives in India.
        Assume the currency that you suggest to the user to be Indian Rupees(₹).
        ONLY USE INDIAN RUPEES(₹) EVERYWHERE.
        The amount should comma seprated in indian rupees format.
        The message should be in a conversation-like manner based on the Account Status.
        The message should only be based on the information presented above.
        The message should be in second person's perespective tone.
    """
    )

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": [response]}},
                {"text": {"text": ["Would you like to apply for this card?"]}},
            ]
        },
        "sessionInfo": {
            "parameters": {
                "credit_card": credit_card,
            }
        },
    }

    return res
