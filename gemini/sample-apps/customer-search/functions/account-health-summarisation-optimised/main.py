# pylint: disable=E0401

from os import environ
from typing import Dict

import functions_framework
from google.cloud import bigquery
from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini
from utils.multithreading import run_all


def get_financial_details(
    query_str: str, value_str: str, res: Dict[str, bigquery.table.RowIterator]
) -> int:
    """
    Gets a financial detail from a BigQuery query result.

    Args:
        query_str (str): The name of the query that returned the result.
        value_str (str): The name of the value to get.
        res (Dict[str, bigquery.table.RowIterator]): The dictionary of query results.

    Returns:
        The financial detail as an integer.
    """

    for row in res[query_str]:
        if row[value_str] is not None:
            return int(row[value_str])
    return 0


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
def account_health_summary(request):
    """
    Summarises the account health of a customer.

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

    project_id = environ.get("PROJECT_ID")

    query_handler = BigQueryHandler(customer_id=customer_id)

    cust_id_exists, res = query_handler.validate_customer_id()
    if not cust_id_exists:
        return res

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

    scheme_name = []
    one_month_return = []
    ttm_return = []
    for row in res["query_investment_returns"]:
        scheme_name.append(row["Scheme_Name"])
        one_month_return.append(row["one_month_return"])
        ttm_return.append(row["TTM_Return"])

    asset_amount = get_financial_details(
        query_str="query_assets", value_str="asset", res=res
    )
    debt_amount = get_financial_details(
        query_str="query_debts", value_str="debt", res=res
    )
    first_name = ""
    total_investment = 0
    total_high_risk_investment = 0
    avg_monthly_balance = get_financial_details(
        query_str="query_avg_monthly_balance", value_str="avg_monthly_balance", res=res
    )
    account_status = ""
    user_accounts = []

    for row in res["query_user_details"]:
        first_name = row["First_Name"]

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

    model = Gemini()

    gemini_prompt = f"""You are a chatbot for bank application and you are required to briefly summarize the key insights of given numerical values in small pointers.
    You are provided with name, total income, total expenditure, total asset amount, total debt amount, total investment amount, high risk investments for the user in the following lines.
    {first_name},
    {total_income},
    {total_expenditure},
    {asset_amount},
    {debt_amount},
    {total_investment},
    {total_high_risk_investment},
    {avg_monthly_balance},
    {account_status},
    {scheme_name},
    {one_month_return},
    {ttm_return},

    Write in a professional and business-neutral tone.
    The summary should be in a conversation-like manner based on the Account Status.
    The summary should only be based on the information presented above.
    Avoid giving advice to the user for improving the Account Status, just include the information in short points.
    Don't comment on spendings of the person.
    The summary should be in pointers.
    The summary should fit in the word limit of 200.
    The summary for account health is for Name to read. So summary should be in second person's perespective tone.
    For example the summary must look like :
    - Your account status is Healthy.
    - Your current balance is ₹65,00,000.00.
    - Your income is ₹1,28,35,200.00 and your expenditure is ₹28,73,104.00.
    - You have a total asset of ₹5,65,00,000.00 and a total debt of ₹0.00.
    - You have invested ₹1,00,000.00 in high risk mutual funds.

    One_Month_Return and TTM_Return store the amounts in Indian currency, i.e., ₹.
    If Total Investment is greater than 0: the following details must be mentioned in a uniformly formatted table:
    For each element in Scheme_Name: mention the respective one month from One_Month_Return in ₹ and trailing twelve month returns from TTM_Return in ₹ in the table.
    """

    response = model.generate_response(gemini_prompt)

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": [response]}}]},
        "sessionInfo": {
            "parameters": {
                "account_status": account_status,
            }
        },
    }

    return res
