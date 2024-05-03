"""This is a python utility file."""

# pylint: disable=E0401

from datetime import date
import json

import pandas as pd  # type: ignore
import pandasql as ps  # type: ignore
from utils.text_bison import TextBison

# SQL_PROMPT is a string template that is used to generate the SQL query.
# It takes two arguments: question and date_today.
SQL_PROMPT = """
You are an SQL Expert. Given an input question, use sqlite syntax to generate a sql query by choosing
one or multiple of the following tables. Write query in between <SQL></SQL>.

The table is a Insurance Database Table whose name is df where each row represents a single customer.
The column keys are : username, agentname, converted, satisfaction_score, current_policy, policy_start_date, policy_end_date, old_policy, policy_amount, platform and last_contacted
Today's date is {date_today}. Use this for date/time related queries.

Please provide the SQL query for this question:
Question:{question}
Query:

"""

# FINAL_ANSWER_PROMPT is a string template that is used to generate the final answer.
# It takes two arguments: question and df.
FINAL_ANSWER_PROMPT = """

You are an experienced programmer and also good at English Language. You need to understand the output answer of a question.
The output has been returned as a dataframe in pandas which would be given to you as a string.
Based on the question and the dataframe, you need re-frame the answer given in the dataframe into natural language.
QUESTION: {question}
DATAFRAME: {df}
ANSWER:

"""


def generate_answer(question: str) -> str:
    """Generates an answer to a question using a database.

    Args:
        question (str): The question to answer.

    Returns:
        str: The answer to the question.
    """
    tb = TextBison()
    with open("data/policy.json", encoding="UTF-8") as f:
        policy_json = json.load(f)

    today = date.today()
    formatted_date = today.strftime("%d/%m/%Y")
    # diabling pylint unused variable check here, variable used in locals()
    df = pd.DataFrame(policy_json)  # pylint: disable=W0641
    prompt = SQL_PROMPT.format(question=question, date_today=formatted_date)
    answer = tb.generate_response(prompt=prompt)
    answer = answer.replace("<SQL>", "")
    sql_query = answer.replace("</SQL>", "")
    sql_query = sql_query.strip()
    print("sql_query : ", sql_query)

    try:
        answer_df = ps.sqldf(sql_query, locals())
        print(answer_df)
        temp_df = answer_df.astype(str)
        prompt = FINAL_ANSWER_PROMPT.format(question=question, df=temp_df)
        answer_natural_language = tb.generate_response(prompt)
        print("answer_natural_language : ", answer_natural_language)
        return answer_natural_language

    except ValueError as e:
        print(e)
        return "Unable to answer. Try again!!"


if __name__ == "__main__":
    print(generate_answer("How many claims are there?"))
