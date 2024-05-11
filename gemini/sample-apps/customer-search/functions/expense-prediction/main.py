# pylint: disable=E0401

import os
from os import environ
import tempfile

import functions_framework
from google.cloud import bigquery, storage
import pandas as pd
import plotly.express as px
import plotly.io as pio

from utils.gemini import Gemini

project_id = environ.get("PROJECT_ID")
public_bucket = environ.get("PUBLIC_BUCKET")


def create_graph(amount, category, date, cust_id):
    """
    Creates a graph of the predicted expenses.

    Args:
        amount (list): The amount of each expense.
        category (list): The category of each expense.
        date (list): The date of each expense.
        cust_id (int): The customer ID.

    Returns:
        str: The public URL of the graph.
    """

    pio.templates.default = "plotly_white"

    lst = []
    for i in range(len(amount)):
        if category[i] != "Healthcare":
            lst.append(
                [
                    str(date[i].strftime("%b")) + " " + str(date[i].year),
                    category[i],
                    amount[i],
                ]
            )
    df = pd.DataFrame(lst, columns=["Date", "Category", "Amount"])
    df = df.sort_values(by="Date", ascending=False)

    fig = px.line(
        df,
        x="Date",
        y="Amount",
        color="Category",
        line_group="Category",
        width=800,
        height=600,
    )
    fig.update_yaxes(showgrid=True, gridwidth=1, zeroline=True)
    fig.update_xaxes(showgrid=False, zeroline=True)

    image_file_name = str(cust_id) + ".png"

    image_dir = os.path.join(tempfile.gettempdir(), "prediction")
    image_path = os.path.join(image_dir, image_file_name)

    if not os.path.isdir(image_dir):
        os.mkdir(image_dir)

    fig.write_image(image_path)

    client = storage.Client()
    bucket = client.bucket(public_bucket)
    cropped_image = bucket.blob(image_file_name)
    cropped_image.upload_from_filename(image_path)
    return cropped_image.public_url


def create_aggregate_transaction_table():
    """
    Creates an aggregate transaction table.
    """

    client = bigquery.Client()
    query = f"""
      SELECT ac_id, DATE_TRUNC(date, MONTH) AS month_year ,sub_category,category,sum(transaction_amount) as transaction_amount
      FROM `{project_id}.DummyBankDataset.AccountTransactions`
      WHERE debit_credit_indicator = 'Debit'
      GROUP BY ac_id,sub_category,category, month_year
    """

    job_config = bigquery.QueryJobConfig()

    # Set configuration.query.destinationTable
    destination_dataset = client.dataset("ExpensePrediction")
    destination_table = destination_dataset.table("training_data")
    job_config.destination = destination_table

    # Set configuration.query.createDisposition
    job_config.create_disposition = "CREATE_IF_NEEDED"

    # Set configuration.query.writeDisposition
    job_config.write_disposition = "WRITE_TRUNCATE"

    # Start the query
    job = client.query(query, job_config=job_config)

    # Wait for the query to finish
    job.result()


def train_model():
    """
    Trains the expense prediction model.
    """

    client = bigquery.Client()
    query_train_arima = f"""
    CREATE OR REPLACE MODEL
    `{project_id}.ExpensePrediction.expense_prediction_model` OPTIONS(MODEL_TYPE='ARIMA_PLUS',
    TIME_SERIES_TIMESTAMP_COL='month_year',
    TIME_SERIES_DATA_COL='transaction_amount',
    TIME_SERIES_ID_COL=['ac_id','category','sub_category'],
    HOLIDAY_REGION='in') AS
    SELECT
      month_year, transaction_amount, ac_id, category,sub_category
    FROM
    `{project_id}.ExpensePrediction.training_data`
    """
    job = client.query(query_train_arima)
    job.result()


def create_predicted_expense_table(customer_id):
    """
    Creates a predicted expense table for a customer.

    Args:
        customer_id (int): The customer ID.

    Returns:
        bigquery.table.RowIterator: The predicted expense table.
    """

    client = bigquery.Client()
    query = f"""
    SELECT
    ac_id, category, sub_category, forecast_timestamp as date, forecast_value as transaction_amount
    FROM
      ML.FORECAST(MODEL `{project_id}.ExpensePrediction.expense_prediction_model`,
        STRUCT(3 AS horizon))
    WHERE ac_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account` where customer_id={customer_id})
    """

    job_config = bigquery.QueryJobConfig()

    # Set configuration.query.destinationTable
    destination_dataset = client.dataset("ExpensePrediction")
    destination_table = destination_dataset.table("predicted_expenses")
    job_config.destination = destination_table

    # Set configuration.query.createDisposition
    job_config.create_disposition = "CREATE_IF_NEEDED"

    # Set configuration.query.writeDisposition
    job_config.write_disposition = "WRITE_TRUNCATE"

    # Start the query
    job = client.query(query, job_config=job_config)

    # Wait for the query to finish
    return job.result()


@functions_framework.http
def expense_prediction(request):
    """
    Predicts the expenses of a customer based on their transaction history.

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

    """
    1. Aggregate the transaction data
    2. Train the model
    3. Forecast the expenses
    4. Create a graph
    5. Return the graph as webhook response
    """

    # UNCOMMENT THE FOLLOWING TO TRAIN THE MODEL
    # create_aggregate_transaction_table()
    # train_model()
    result_predicted_expenses = create_predicted_expense_table(customer_id)

    amount = []
    category = []
    date = []
    transaction_list_str = ""
    total_expenditure_str = ""
    total_expenditure = {}
    for row in result_predicted_expenses:
        amount.append(round(row["transaction_amount"], 2))
        category.append(row["sub_category"])
        date.append(row["date"])
        transaction_list_str = (
            transaction_list_str + f"{row['sub_category']}: ₹{row['transaction_amount']} in the"
            f" month of {row['date']}\n"
        )
        if row["date"] not in total_expenditure:
            total_expenditure[row["date"]] = round(row["transaction_amount"], 2)
        else:
            total_expenditure[row["date"]] = total_expenditure[row["date"]] + round(
                row["transaction_amount"], 2
            )

    for k in total_expenditure:
        total_expenditure_str = (
            total_expenditure_str + f"Total predicted expenses in {k}: {total_expenditure[k]}"
        )

    model = Gemini()

    summarize_expense_prediction_prompt = f"""
    You are a financial analyst and you need to summarize the predicted expenses of the customer.

    Group together categories with similar trends.
    Highlight only three trends.
    Use percentages and numbers.
    The summary should only be based on the information given.
    The summary should only be 3 lines.


    Example response:
    Input:
    "Education: ₹61500.0 in the month of 2023-10-01 00:00:00+00:00
    Education: ₹61500.0 in the month of 2023-11-01 00:00:00+00:00
    Education: ₹61500.0 in the month of 2023-12-01 00:00:00+00:00
    Food and Groceries: ₹67613.65328005172 in the month of 2023-10-01 00:00:00+00:00
    Food and Groceries: ₹84694.19671890956 in the month of 2023-11-01 00:00:00+00:00
    Food and Groceries: ₹101689.74180109426 in the month of 2023-12-01 00:00:00+00:00
    Housing: ₹15104.333333333334 in the month of 2023-10-01 00:00:00+00:00
    Housing: ₹15104.333333333334 in the month of 2023-11-01 00:00:00+00:00
    Housing: ₹15104.333333333334 in the month of 2023-12-01 00:00:00+00:00
    Transportation: ₹6883.333333333333 in the month of 2023-10-01 00:00:00+00:00
    Transportation: ₹6883.333333333333 in the month of 2023-11-01 00:00:00+00:00
    Transportation: ₹6883.333333333333 in the month of 2023-12-01 00:00:00+00:00
    Entertainment: ₹15753.052113917918 in the month of 2023-10-01 00:00:00+00:00
    Entertainment: ₹19238.30696727574 in the month of 2023-11-01 00:00:00+00:00
    Entertainment: ₹19238.30696727574 in the month of 2023-12-01 00:00:00+00:00
    Miscellaneous: ₹31658.39198298211 in the month of 2023-10-01 00:00:00+00:00
    Miscellaneous: ₹22651.964064560536 in the month of 2023-11-01 00:00:00+00:00
    Miscellaneous: ₹19560.348150475478 in the month of 2023-12-01 00:00:00+00:00
    Total predicted expenses in 2023-10-01 00:00:00+00:00: ₹198512.74999999994
    Total predicted expenses in 2023-11-01 00:00:00+00:00: ₹210072.12999999998
    Total predicted expenses in 2023-12-01 00:00:00+00:00: ₹223976.05999999997


    Output:
    Education expenses to remain constant at ₹61,500 per month.
    Food and groceries expenses to increase by 50% from Oct 2023 to Dec 2023.
    Total expenses to increase by 13% from Oct 2023 to Dec 2023.

    Input:
    {transaction_list_str}
    {total_expenditure_str}

    Output:
    "
    """
    response = model.generate_response(summarize_expense_prediction_prompt)

    transaction_list_str = response
    transaction_list = transaction_list_str.split("*")
    if len(transaction_list) == 1:
        transaction_list = transaction_list_str.split("-")

    # finding upcoming payments considering last date of transaction data as
    # 2023-09-30
    query_upcoming_payments = f"""
        SELECT * FROM `{project_id}.DummyBankDataset.StandingInstructions`
        where account_id IN (SELECT account_id FROM `{project_id}.DummyBankDataset.Account`
        where customer_id={customer_id}) and Next_Payment_Date < '2023-12-31'
        and fund_transfer_amount IS NOT NULL
    """
    result_upcoming_payments = client.query(query_upcoming_payments)
    payment_list_str = ""
    for row in result_upcoming_payments:
        payment_list_str = (
            payment_list_str + f"₹{row['fund_transfer_amount']} for {row['SI_Type']} on"
            f" {row['Next_Payment_Date']}\n"
        )

    payment_list = payment_list_str.split("\n")

    format_date_prompt = f"""
    Format the dates in the following information,e.g. 2024-10-01 to  Oct 1, 2024
    {payment_list_str}


    """
    response2 = model.generate_response(format_date_prompt)

    # create a graph out of the data
    rawUrl = create_graph(amount, category, date, customer_id)

    if len(payment_list) > 1:
        custom_payload = [
            {
                "payload": {
                    "richContent": [
                        [
                            {
                                "type": "image",
                                "rawUrl": rawUrl,
                                "accessibilityText": (
                                    "Your predicted expenses bases on transaction"
                                    " history for Oct-Dec 23"
                                ),
                            }
                        ]
                    ]
                }
            },
            {"text": {"text": [response]}},
            {
                "text": {
                    "text": [
                        "Just a friendly reminder that your upcoming payments"
                        " are due soon:\n" + response2
                    ]
                }
            },
        ]
    else:
        custom_payload = [
            {
                "payload": {
                    "richContent": [
                        [
                            {
                                "type": "image",
                                "rawUrl": rawUrl,
                                "accessibilityText": (
                                    "Your predicted expenses bases on transaction"
                                    " history for Oct-Dec 23"
                                ),
                            }
                        ]
                    ]
                }
            },
            {"text": {"text": [response]}},
        ]

    res = {"fulfillment_response": {"messages": custom_payload}}

    return res
