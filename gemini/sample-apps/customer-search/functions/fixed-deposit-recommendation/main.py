# pylint: disable=E0401

import datetime
from os import environ

import functions_framework

from utils.bq_query_handler import BigQueryHandler
from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")


def round_to_nearest_thousands(number):
    """
    Rounds a number to the nearest thousand.

    Args:
        number (int): The number to round.

    Returns:
        int: The rounded number.
    """

    length = len(str(int(number)))
    if length > 0:
        length = length - 1

    length = min(length, 6)

    return number - number % pow(10, length)


def convert_days_to_proper_format(days):
    """
    Converts the number of days to a proper format, e.g. 365 days to 1 year.

    Args:
        days (int): The number of days.

    Returns:
        str: The number of days in a proper format.
    """

    years = days // 365
    days -= years * 365

    months = days // 30
    days -= months * 30

    s = ""

    if years > 1:
        s += str(years) + " years "
    elif years == 1:
        s += "1 year "

    if months > 1:
        s += str(months) + " months "
    elif months == 1:
        s += "1 month "

    if days > 1:
        s += str(days) + " days "
    elif days == 1:
        s += "1 day "

    return s[:-1]


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


@functions_framework.http
def fixed_deposit_recommendation(request):
    """
    Recommends a fixed deposit to a customer.

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
    result_upcoming_payments = query_handler.query("query_upcoming_payments")
    result_dob = query_handler.query("query_dob")
    result_best_interest_rate_row = query_handler.query("query_best_interest_rate_row")

    balance = 0
    is_sr_citizen = False
    start_day = 7
    end_day = 45
    rate_of_interest = 3.0

    for row in result_dob:
        if row["dob"] is not None:
            dob = row["dob"]
            is_sr_citizen = check_senior_citizen(dob)

    for row in result_best_interest_rate_row:
        if row["bucket_start_days"] is not None:
            start_day = row["bucket_start_days"]
            end_day = row["bucket_end_days"]
            if is_sr_citizen:
                rate_of_interest = row["rate_of_interest_sr_citizen"]
            else:
                rate_of_interest = row["rate_of_interest"]

    # for each high risk mutual fund
    for row in result_account_balance:
        # extract the name of the mutual fund and the current amount
        if row["total_account_balance"] is not None:
            balance += row["total_account_balance"]

    fd_amount = balance
    tenure_start = convert_days_to_proper_format(start_day)
    tenure_end = convert_days_to_proper_format(end_day)

    for row in result_upcoming_payments:
        if row["fund_transfer_amount"] is not None:
            fd_amount = fd_amount - row["fund_transfer_amount"]

    rounded_fd_amount = round_to_nearest_thousands(fd_amount)

    if fd_amount < 10000:
        result = "Your balance is too low for FD."
        output = {"fulfillment_response": {"messages": [{"text": {"text": [result]}}]}}
        return output

    result = "You should invest in FD"

    model = Gemini()

    response = model.generate_response(
        f"""
    You are a chatbot for a bank application.As the user have surplus amount of {fd_amount}
    after setting aside for scheduled expenses.
    Format the amount in the following way:
    e.g. amount = 100000000 to ₹10,00,00,000.00 upto two decimal places
    Mention that the surplus amount is after setting aside for scheduled expenses
    Recommend user the option to put {rounded_fd_amount} money in Fd and
    ask user whether they would like to open an fd in Cymbal Bank.
    Also tell the user that interest rates are best for time period from {tenure_start} to
    {tenure_end} and the interest rate is {rate_of_interest}%.
    Write in a professional and business-neutral tone.
    Do not say Hi Hello etc.
    Do not ask to open a fd.
    The response should not be more than 25 words.
    Write in a very polite manner.
    Make the output more conversational and user friendly.
    The response is for the user to read.
    Do not give any space between lines as shown in example.

    for example:
    You have ₹30,60,492.75 surplus after setting aside for scheduled expenses.
    Consider putting ₹30,00,000 in an FD with Cymbal Bank.
    Interest rates are best for 1-2 years at 6.8%.

    """
    )

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": [response]}},
                {"text": {"text": ["Would you like to open an FD?"]}},
            ]
        },
        "sessionInfo": {
            "parameters": {
                "fd_amount": rounded_fd_amount,
                "account_balance": balance,
                "rounded_fd_amount": rounded_fd_amount,
            }
        },
    }
    return res
