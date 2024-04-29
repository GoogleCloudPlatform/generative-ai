import datetime
from os import environ

import functions_framework
from google.cloud import bigquery
import vertexai
from vertexai.generative_models import GenerativeModel, Part, FinishReason
import vertexai.preview.generative_models as generative_models

project_id = environ.get("PROJECT_ID")


def round_to_nearest_thousands(number):
    length = len(str(int(number)))
    if length > 0:
        length = length - 1

    print(length)
    print(str(int(number)))

    print(length)
    length = min(length, 6)
    print(length)

    return number - number % pow(10, length)


def convert_days_to_proper_format(days):
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
    print("Today = ", today)
    print("age = ", age)
    return age >= 60


@functions_framework.http
def hello_http(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    print(request_json["sessionInfo"]["parameters"])

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]
    # customer_id = 235813
    # 342345, 592783

    # get account balance of the user
    query_account_balance = f"""
    SELECT SUM(avg_monthly_bal) as total_account_balance FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id}
    and avg_monthly_bal is NOT NULL
    and product IN('Savings A/C ', 'Savings Salary A/C ', 'Premium Current A/C ', 'Gold Card ', 'Platinum Card ')
  """

    query_upcoming_payments = f"""
      SELECT * FROM `{project_id}.DummyBankDataset.StandingInstructions`
      where account_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id}) and EXTRACT(MONTH from Next_Payment_Date) = 10 and EXTRACT(YEAR from Next_Payment_Date) = 2023 and fund_transfer_amount IS NOT NULL
  """

    # get the date of birth of the user
    query_dob = f"""
        SELECT date_of_birth as dob FROM `{project_id}.DummyBankDataset.Customer` where customer_id = {customer_id}
  """

    query_best_interest_rate_row = f"""
    SELECT * FROM `{project_id}.DummyBankDataset.FdInterestRates`
    ORDER BY rate_of_interest desc
    LIMIT 1
  """

    result_account_balance = client.query(query_account_balance)
    result_upcoming_payments = client.query(query_upcoming_payments)
    result_dob = client.query(query_dob)
    result_best_interest_rate_row = client.query(query_best_interest_rate_row)

    balance = 0
    is_sr_citizen = False
    start_day = 7
    end_day = 45
    rate_of_interest = 3.0

    for row in result_dob:
        if row["dob"] is not None:
            dob = row["dob"]
            is_sr_citizen = check_senior_citizen(dob)
            print(type(dob))
            print(dob)

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
            print(row["fund_transfer_amount"])

    print(balance)
    print(fd_amount)

    rounded_fd_amount = round_to_nearest_thousands(fd_amount)
    print("Rounded Fd Amount = ", rounded_fd_amount)

    # if balance < 200000:
    #   result = "This is not sufficient to cover upcoming expenses of electricity for rest of the month"
    #   output = {"fulfillment_response": {"messages": [{"text": {"text": [result]}}]}}
    #   return output

    if fd_amount < 10000:
        result = "Your balance is too low for FD."
        output = {"fulfillment_response": {"messages": [{"text": {"text": [result]}}]}}
        return output

    result = "You should invest in FD"

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
        f"""
    You are a chatbot for a bank application.As the user have surplus amount of {fd_amount} after setting aside for scheduled expenses
    Format the amount in the following way
    e.g. amount = 100000000 to ₹10,00,00,000.00 upto two decimal places
    Mention that the surplus amount is after setting aside for scheduled expenses
    Recommend user the option to put {rounded_fd_amount} money in Fd and
    ask user whether they would like to open an fd in Cymbal Bank.
    Also tell the user that interest rates are best for time period from {tenure_start} to {tenure_end} and
    the interest rate is {rate_of_interest}%.
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

    """,
        generation_config=generation_config,
        safety_settings=safety_settings,
        stream=True,
    )

    final_response = ""
    for response in responses:
        final_response += response.text 
        
    print("Result = ", final_response)

    res = {
        "fulfillment_response": {
            "messages": [
                {"text": {"text": [final_response]}},
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
    print(res)
    return res
