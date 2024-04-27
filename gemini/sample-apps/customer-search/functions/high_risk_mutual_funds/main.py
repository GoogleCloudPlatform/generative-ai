from concurrent.futures import ThreadPoolExecutor
from typing import Dict

import functions_framework
from google.cloud import bigquery, storage
import vertexai
from vertexai.language_models import TextGenerationModel

client: bigquery.Client = bigquery.Client()


def run(name: str, statement: str) -> tuple[str, bigquery.table.RowIterator]:
    return name, client.query(statement).result()  # blocks the thread


def run_all(statements: Dict[str, str]) -> Dict[str, bigquery.table.RowIterator]:
    with ThreadPoolExecutor() as executor:
        jobs = []
        for name, statement in statements.items():
            jobs.append(executor.submit(run, name, statement))
        result = dict([job.result() for job in jobs])
    return result


def upload_blob(
    bucket_name: str, source_file_name: str, destination_blob_name: str
) -> str:
    """Uploads a file to the bucket"""
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)

    blob = bucket.blob(destination_blob_name)
    blob.upload_from_string(source_file_name)
    print(f"File {source_file_name} uploaded to {destination_blob_name}.")
    return blob.public_url


@functions_framework.http
def high_risk_mutual_funds(request):
    request_json = request.get_json(silent=True)

    client = bigquery.Client()

    customer_id = request_json["sessionInfo"]["parameters"]["cust_id"]

    if customer_id is not None:
        print("Customer ID ", customer_id)
    else:
        print("Customer ID not defined")

    query_check_cust_id = f"""
        SELECT EXISTS(SELECT * FROM `fintech-app-gcp.DummyBankDataset.Account` where customer_id = {customer_id}) as check
    """
    result_query_check_cust_id = client.query(query_check_cust_id)
    for row in result_query_check_cust_id:
        print(row["check"])
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
            print(res)
            return res

    query_fd = f"""
        SELECT sum(avg_monthly_bal) as asset FROM `fintech-app-gcp.DummyBankDataset.Account`
        where customer_id = {customer_id} and product = 'Fixed Deposit';
    """

    query_total_mf = f"""
        SELECT SUM(amount_invested) as total_mf_investment FROM `DummyBankDataset.MutualFundAccountHolding` where account_no in (
            select account_id from `DummyBankDataset.Account` where customer_id = {customer_id}
        );
    """

    query_high_risk_mf = f"""
        select SUM(amount_invested) as total_high_risk_investment from `DummyBankDataset.MutualFundAccountHolding` where risk_category > 4 and account_no in (
            select account_id from `DummyBankDataset.Account` where customer_id = {customer_id}
        )
    """

    query_investment_returns = f"""
        SELECT (amount_invested*one_month_return) as one_month_return, amount_invested as amount_invested, one_month_return as one_M, (amount_invested*TTM_Return) as TTM_Return,TTM_Return as TTM,Scheme_Name from `fintech-app-gcp.DummyBankDataset.MutualFundAccountHolding`
        where account_no in (Select account_id from `fintech-app-gcp.DummyBankDataset.Account` where customer_id={customer_id})
    """

    res = run_all(
        {
            "query_fd": query_fd,
            "query_total_mf": query_total_mf,
            "query_high_risk_mf": query_high_risk_mf,
            "query_investment_returns": query_investment_returns,
        }
    )

    scheme_name = []
    one_month_return = []
    ttm_return = []
    one_m = []
    TTM = []
    amount_invested = []
    fd_inv = 0
    for row in res["query_investment_returns"]:
        scheme_name.append(row["Scheme_Name"])
        one_month_return.append(row["one_month_return"])
        ttm_return.append(row["TTM_Return"])
        one_m.append(row["one_M"] * 100)
        TTM.append(row["TTM"] * 100)
        amount_invested.append(row["amount_invested"])

    total_investment = 0
    total_high_risk_investment = 0

    for row in res["query_fd"]:
        if row["asset"] is not None:
            fd_inv = row["asset"]
            total_investment += row["asset"]

    for row in res["query_total_mf"]:
        if row["total_mf_investment"] is not None:
            total_investment += row["total_mf_investment"]

    for row in res["query_high_risk_mf"]:
        if row["total_high_risk_investment"] is not None:
            total_high_risk_investment += row["total_high_risk_investment"]

    vertexai.init(project="fintech-app-gcp", location="us-central1")
    parameters = {
        "max_output_tokens": 512,
        "temperature": 0.2,
        "top_p": 0.8,
        "top_k": 40,
    }
    model = TextGenerationModel.from_pretrained("text-bison")
    response = model.predict(
        """You are a chatbot for bank application and you are required to briefly summarize the key insights of given numerical values as Investment Summary in small pointers.

    Total Investment = ₹{0}
    Investment in Fixed Deposits = ₹{4}
    Scheme_Name = {1}
    One_Month_Return = {2}
    One_Month_Return_Percentage = {5}
    TTM_Return = {3}
    TTM_Return_Percentage = {6}
    amount_invested = {7}

    Write in a professional and business-neutral tone.

    One_Month_Return and TTM_Return store the amounts in Indian currency, i.e., ₹.
    do not give any amount in decimal.
    If Total Investment is greater than 0: the following details must be mentioned in a uniformly formatted table:
    Spacing should be proper.
    For each element in Scheme_Name:
    Mention the respective amount invested from amount_invested and one month from One_Month_Return and one month percentage return from One_Month_Return_Percentage and TTM returns from TTM_Return and TTM return precentage from  TTM_Return_Percentage .

    For example the summary should look like :

    **Investment Summary**

    Total Investment: ₹5,55,00,000.00
    Investment in Fixed Deposits: ₹5,00,00,000.00

    **Mutual Fund Investments**

    Scheme Name	Amount Invested	1 Month Returns	1 Month Return %	12 month Return	12 month Return %
    ICICI Prudential Bluechip Fund	₹7,00,000	₹84,000	12	₹2,52,000	35
    SBI Bluechip Fund	₹8,00,000	₹80,000	10	₹2,40,000	30
    HDFC Sensex ETF	₹17,00,000	₹2,55,000	15	₹7,65,000	45
    Nippon India Nifty 50 ETF	₹23,00,000	₹4,14,000	18	₹12,42,000	54

    """.format(
            total_investment,
            scheme_name,
            one_month_return,
            ttm_return,
            fd_inv,
            one_m,
            TTM,
            amount_invested,
        ),
        **parameters,
    )

    print("One month return -> ", one_month_return)
    print("One month return percentage -> ", one_m)
    print("TTM month return -> ", ttm_return)
    print("TTM month return percentage  -> ", TTM)
    print("Amount Invested -> ", amount_invested)

    print(f"Response from Model: {response.text}")

    url = "https://storage.cloud.google.com/public_bucket_fintech_app/Market%20Summary.pdf"
    print(url)

    res = {"fulfillment_response": {"messages": [{"text": {"text": [response.text]}}]}}
    print(res)
    return res
