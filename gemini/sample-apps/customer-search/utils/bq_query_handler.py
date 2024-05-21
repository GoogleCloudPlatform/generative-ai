"""This is a python utility file."""

# pylint: disable=E0401

from concurrent.futures import ThreadPoolExecutor
from os import environ
from typing import Dict

from google.cloud import bigquery


class BigQueryHandler:
    """
    A class to interact with BigQuery.
    """

    def __init__(
        self,
        customer_id: str,
    ):
        """
        Initializes the class.

        Args:
            model (str): The name of the model to use.
        """

        self.project_id = environ.get("PROJECT_ID")
        self.location = "us-central1"
        self.customer_id = customer_id
        self.client = bigquery.Client()
        self.queries = {}

        self.queries[
            "query_check_cust_id"
        ] = f"""
SELECT EXISTS(SELECT * FROM `{self.project_id}.DummyBankDataset.Account` \
where customer_id = {self.customer_id}) as check
"""

        self.queries[
            "query_assets"
        ] = f"""
SELECT sum(avg_monthly_bal) as asset FROM `{self.project_id}.DummyBankDataset.Account` \
where customer_id = {self.customer_id} and product in ('Savings A/C ', \
'Savings Salary A/C ', 'Premium Current A/C ', 'Fixed Deposit', 'Flexi Deposit');
"""

        self.queries[
            "query_avg_monthly_balance"
        ] = f"""
SELECT sum(avg_monthly_bal) as avg_monthly_balance FROM \
`{self.project_id}.DummyBankDataset.Account` where customer_id = {self.customer_id} \
and product in ('Savings A/C ', 'Savings Salary A/C ', 'Premium Current A/C ');
"""

        self.queries[
            "query_fd"
        ] = f"""
SELECT sum(avg_monthly_bal) as asset FROM `{self.project_id}.DummyBankDataset.Account` \
where customer_id = {self.customer_id} and product = 'Fixed Deposit';
"""

        self.queries[
            "query_total_mf"
        ] = f"""
SELECT SUM(amount_invested) as total_mf_investment FROM \
`DummyBankDataset.MutualFundAccountHolding` where account_no in (\
select account_id from `DummyBankDataset.Account` where customer_id \
= {self.customer_id});
"""

        self.queries[
            "query_high_risk_mf"
        ] = f"""
select SUM(amount_invested) as total_high_risk_investment from \
`DummyBankDataset.MutualFundAccountHolding` where risk_category > 4 \
and account_no in (select account_id from `DummyBankDataset.Account` where customer_id \
= {self.customer_id})
"""

        self.queries[
            "query_debts"
        ] = f"""
SELECT sum(avg_monthly_bal) as debt FROM `{self.project_id}.DummyBankDataset.Account` \
where customer_id = {self.customer_id} and product in ('Gold Card',\
'Medical Insurance','Premium Travel Card','Platinum Card','Personal Loan',\
'Vehicle Loan','Consumer Durables Loan','Broking A/C');
"""

        self.queries[
            "query_account_details"
        ] = f"""
SELECT * FROM `{self.project_id}.DummyBankDataset.Account` WHERE customer_id = {self.customer_id}
"""

        self.queries[
            "query_user_details"
        ] = f"""
SELECT * FROM `{self.project_id}.DummyBankDataset.Customer` WHERE customer_id = {self.customer_id}
"""

        self.queries[
            "query_average_monthly_expense"
        ] = f"""SELECT AVG(total_amount) \
as average_monthly_expense from (SELECT EXTRACT(MONTH FROM 	date) AS month, \
SUM(transaction_amount) AS total_amount FROM \
`{self.project_id}.DummyBankDataset.AccountTransactions` WHERE ac_id IN \
(SELECT account_id FROM `{self.project_id}.DummyBankDataset.Account` \
where customer_id = {self.customer_id}) GROUP BY month ORDER BY month)
"""

        self.queries[
            "query_last_month_expense"
        ] = f"""SELECT EXTRACT(MONTH FROM date) AS month, \
SUM(transaction_amount) AS last_month_expense FROM \
`{self.project_id}.DummyBankDataset.AccountTransactions` WHERE ac_id IN (SELECT account_id \
FROM `{self.project_id}.DummyBankDataset.Account` where customer_id={self.customer_id}) \
and EXTRACT(MONTH FROM date)=9 GROUP BY month ORDER BY month;
"""

        self.queries[
            "query_investment_returns"
        ] = f"""
SELECT (amount_invested*one_month_return) as one_month_return, (amount_invested*TTM_Return) as \
TTM_Return,Scheme_Name from `{self.project_id}.DummyBankDataset.MutualFundAccountHolding` where \
account_no in (Select account_id from `{self.project_id}.DummyBankDataset.Account` \
where customer_id={self.customer_id})
"""

        self.queries[
            "query_transaction_category"
        ] = f"""
SELECT SUM(transaction_amount) as amount, sub_category as category,FROM \
`{self.project_id}.DummyBankDataset.AccountTransactions` where ac_id IN \
(SELECT account_id FROM `{self.project_id}.DummyBankDataset.Account` where \
customer_id={self.customer_id}) AND debit_credit_indicator = 'Debit' and category \
in('Wants', 'Miscellaneous') GROUP BY sub_category
"""

        self.queries[
            "query_average_monthly_expense"
        ] = f"""SELECT AVG(total_amount) as average_monthly_expense from (\
SELECT EXTRACT(MONTH FROM 	date) AS month, SUM(transaction_amount) AS total_amount FROM \
`{self.project_id}.DummyBankDataset.AccountTransactions` WHERE ac_id IN \
(SELECT account_id FROM `{self.project_id}.DummyBankDataset.Account` where \
customer_id = {self.customer_id} and debit_credit_indicator = 'Debit') \
GROUP BY month ORDER BY month)
"""

        self.queries[
            "query_last_month_expense"
        ] = f"""SELECT EXTRACT(MONTH FROM date) AS month, SUM(transaction_amount) \
AS last_month_expense FROM `{self.project_id}.DummyBankDataset.AccountTransactions` \
WHERE ac_id IN (SELECT account_id FROM `{self.project_id}.DummyBankDataset.Account` where \
customer_id={self.customer_id} and debit_credit_indicator = 'Debit') and \
EXTRACT(MONTH FROM date)=9 GROUP BY month ORDER BY month;
"""

        self.queries[
            "query_expenditure_category"
        ] = f"""
SELECT SUM(transaction_amount) as amount, sub_category, EXTRACT(MONTH FROM date) AS \
month FROM `{self.project_id}.DummyBankDataset.AccountTransactions` where ac_id IN \
(SELECT account_id FROM `{self.project_id}.DummyBankDataset.Account` where \
customer_id={self.customer_id}) AND debit_credit_indicator = 'Debit' and \
EXTRACT(MONTH FROM date)=9 and EXTRACT(YEAR FROM date)=2023 \
GROUP BY month, sub_category
"""

        self.queries[
            "query_dob"
        ] = f"""
SELECT date_of_birth as dob FROM `{self.project_id}.DummyBankDataset.Customer` \
where customer_id = {self.customer_id}
"""

        self.queries[
            "query_user_affinities"
        ] = f"""
SELECT Affinities FROM `{self.project_id}.DummyBankDataset.Customer` \
WHERE customer_id = {self.customer_id}
"""

        self.queries["query_event_details"] = (
            f"""SELECT * FROM `{self.project_id}.DummyBankDataset.CustomerEvents`"""
        )

        self.queries[
            "query_cust_address"
        ] = f"""
SELECT Address_2nd_Line, Address_3rd_Line, city, state, Plus_Code FROM \
`{self.project_id}.DummyBankDataset.Customer` where customer_id = {self.customer_id}
"""

        self.queries[
            "query_account_balance"
        ] = f"""
SELECT SUM(avg_monthly_bal) as total_account_balance FROM \
`{self.project_id}.DummyBankDataset.Account` where customer_id={self.customer_id} \
and avg_monthly_bal is NOT NULL and product IN('Savings A/C ', 'Savings Salary A/C ', \
'Premium Current A/C ', 'Gold Card ', 'Platinum Card ')
"""

        self.queries[
            "query_upcoming_payments"
        ] = f"""
SELECT * FROM `{self.project_id}.DummyBankDataset.StandingInstructions` where account_id \
IN (SELECT account_id FROM `{self.project_id}.DummyBankDataset.Account` where \
customer_id={self.customer_id}) and EXTRACT(MONTH from Next_Payment_Date) = 10 and \
EXTRACT(YEAR from Next_Payment_Date) = 2023 and fund_transfer_amount IS NOT NULL
"""

        self.queries[
            "query_best_interest_rate_row"
        ] = f"""
SELECT * FROM `{self.project_id}.DummyBankDataset.FdInterestRates` \
ORDER BY rate_of_interest desc LIMIT 1
"""

        self.queries[
            "query_investments_six_month_return"
        ] = f"""
SELECT (amount_invested*six_month_return) as six_month_return,Scheme_Name from \
`{self.project_id}.DummyBankDataset.MutualFundAccountHolding` where account_no in \
(Select account_id from `{self.project_id}.DummyBankDataset.Account` \
where customer_id={self.customer_id})
"""

        self.queries["query_mf"] = (
            f"""SELECT * FROM `{self.project_id}.DummyBankDataset.MutualFund`"""
        )

        self.queries[
            "query_age_on_book"
        ] = f"""
SELECT age_on_book as customer_age_on_book FROM \
`{self.project_id}.DummyBankDataset.Customer` where customer_id = {self.customer_id}
"""

        self.queries[
            "query_travel_expense"
        ] = f"""
SELECT SUM(transaction_amount) as travel_expense from \
`{self.project_id}.DummyBankDataset.AccountTransactions` \
WHERE debit_credit_indicator = 'Debit' and ac_id IN (SELECT account_id FROM \
`{self.project_id}.DummyBankDataset.Account` where customer_id = {self.customer_id}) \
and sub_category = 'Travel'
"""

    def validate_customer_id(
        self,
    ) -> tuple[bool, dict[str, dict[str, list[dict[str, dict[str, list[str]]]]]]]:
        """
        Validates the customer ID.

        Returns:
            A tuple containing a boolean value and a dictionary.
        """

        result_query_check_cust_id = self.query("query_check_cust_id")
        for row in result_query_check_cust_id:
            if row["check"] == 0:
                res = {
                    "fulfillment_response": {
                        "messages": [
                            {
                                "text": {
                                    "text": [
                                        "It seems you have entered an incorrect"
                                        " Customer ID. Please try again."
                                    ]
                                }
                            }
                        ]
                    }
                }
                return False, res
        return True, {}

    def query(self, query_name: str) -> bigquery.QueryJob:
        """
        Runs a BigQuery query and returns the query job.

        Args:
            query_name (str): The name of the query.

        Returns:
            A BigQuery query job.
        """

        return self.client.query(self.queries[query_name])

    def run(self, name: str) -> tuple[str, bigquery.table.RowIterator]:
        """
        Runs a BigQuery query and returns the name of the query and the result iterator.

        Args:
            name (str): The name of the query.

        Returns:
            A tuple containing the name of the query and the result iterator.
        """

        return name, self.query(name).result()  # blocks the thread

    def run_all(self, queries: list[str]) -> Dict[str, bigquery.table.RowIterator]:
        """
        Runs a list of BigQuery queries and returns a dictionary of query names
        and result iterators.

        Args:
            queries (list[str]): A list of BigQuery query statements.

        Returns:
            A dictionary of query names and result iterators.
        """

        with ThreadPoolExecutor() as executor:
            jobs = []
            for name in queries:
                jobs.append(executor.submit(self.run, name))
            result = dict([job.result() for job in jobs])
        return result
