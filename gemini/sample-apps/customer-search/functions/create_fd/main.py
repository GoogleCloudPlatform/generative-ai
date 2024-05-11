# pylint: disable=E0401

import datetime
from datetime import date
from os import environ
import random
import re

import functions_framework
from google.cloud import bigquery
from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")


def get_ac_number():
    """
    Generates a random account number.

    Returns:
        A random account number as an integer.
    """

    account_number = "11000"
    for i in range(5):
        account_number += str(random.randint(0, 9))

    return int(account_number)


def check_senior_citizen(dob):
    """
    Checks whether a person is a senior citizen or not using their date of birth.

    Args:
      dob: A datetime.date object representing the person's date of birth.

    Returns:
      True if the person is a senior citizen, False otherwise.
    """

    today = datetime.date.today()
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))
    return age >= 60


def get_number_of_days(fd_tenure):
    """
    Calculates the number of days in a fixed deposit tenure.

    Args:
      fd_tenure: A string representing the fixed deposit tenure.

    Returns:
      The number of days in the fixed deposit tenure as an integer.
    """

    years = 0
    months = 0
    days = 0

    if re.search(r"(\d+) year", fd_tenure) is not None:
        years = re.search(r"(\d+) year", fd_tenure).group(1)
    if re.search(r"(\d+) month", fd_tenure) is not None:
        months = re.search(r"(\d+) month", fd_tenure).group(1)
    if re.search(r"(\d+) day", fd_tenure) is not None:
        days = re.search(r"(\d+) day", fd_tenure).group(1)

    # Convert the years, months, and days to integers.
    years = int(years)
    months = int(months)
    days = int(days)

    # Calculate the total number of days in the tenure.
    total_days = 365 * years + 30 * months + days

    return total_days


def get_interest_rate(is_sr_citizen, number_of_days):
    """
    Gets the interest rate for a fixed deposit based on the tenure and whether the customer is a senior citizen.

    Args:
      is_sr_citizen: A boolean indicating whether the customer is a senior citizen.
      number_of_days: The number of days in the fixed deposit tenure.

    Returns:
      The interest rate for the fixed deposit as a float.
    """

    client = bigquery.Client()

    roi = 3.0

    person = "rate_of_interest"
    if is_sr_citizen:
        person = "rate_of_interest_sr_citizen"

    query_interest_rate = f"""
    SELECT {person} as rate_of_interest FROM `{project_id}.DummyBankDataset.FdInterestRates`
    where bucket_start_days < {number_of_days}
    order by bucket_start_days desc limit 1
  """

    result_query_interest_rate = client.query(query_interest_rate)

    for row in result_query_interest_rate:
        if row["rate_of_interest"] is not None:
            roi = row["rate_of_interest"]

    return roi


@functions_framework.http
def create_fixed_deposit(request):
    """
    Creates a fixed deposit for a customer.

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
    fd_amount = request_json["sessionInfo"]["parameters"]["fd_amount"]
    fd_tenure = request_json["sessionInfo"]["parameters"]["fd_tenure"]
    user_name = request_json["sessionInfo"]["parameters"]["name"]

    query_handler = BigQueryHandler(customer_id=customer_id)

    # verifying that the customer is valid and exists in our database or not
    cust_id_exists, res = query_handler.validate_customer_id()
    if not cust_id_exists:
        return res

    # get the date of birth of the user
    result_dob = query_handler.query("query_dob")

    is_sr_citizen = False

    for row in result_dob:
        if row["dob"] is not None:
            dob = row["dob"]
            is_sr_citizen = check_senior_citizen(dob)

    number_of_days = get_number_of_days(fd_tenure)
    present_date = date.today()
    present_date = present_date.isoformat()
    interest_rate = get_interest_rate(is_sr_citizen, number_of_days)

    model = Gemini()

    response = model.generate_response(
        f"""Generate a confirmation message on creating a fd.
    The user name is {user_name}
    The amount is {fd_amount}
    The tenure is {fd_tenure}
    The interest rate is {interest_rate} .
    The order should be amount then tenure then interest rate and these things
    should be in bullet points.
    The bank name is Cymbal Bank.
    The amount should be in the format ₹1,20,312.15 instead of 120312.15
    Do not show maturity date and maturity amount.
    The output should be within 40 words. Use emojis.
    """
    )

    body = model.generate_response(
        f"""Generate a confirmation email on creating a fd.
    The user name is {user_name}
    The amount is {fd_amount}
    The tenure is {fd_tenure}
    The interest rate is {interest_rate} .
    The order should be amount then tenure then interest rate and these things
    should be in bullet points.
    The bank name is Cymbal Bank.
    The amount should be in the format ₹1,20,312.15 instead of 120312.15
    Do not show maturity date and maturity amount.
    Do not give subject just body

    For example:

    Dear Ayushi,

    Thank you for choosing Cymbal Bank for your fixed deposit.
    Your fixed deposit has been successfully created. Here are the details of your fixed deposit:

    - Amount: ₹30,00,000
    - Tenure: 2 years
    - Interest Rate: 6.8%

    Please note that the maturity date and maturity amount will be
    communicated to you in a separate email.

    If you have any questions or concerns, please do not hesitate to contact us.

    Thank you for banking with Cymbal Bank.

    Sincerely,
    Cymbal Bank

    """
    )

    subject = "Fixed Deposit Confirmation - Cymbal Bank"

    res = {
        "fulfillment_response": {"messages": [{"text": {"text": [response]}}]},
        "sessionInfo": {
            "parameters": {
                "fd_amount": fd_amount,
                "subject": subject,
                "body": body,
            }
        },
    }

    return res
