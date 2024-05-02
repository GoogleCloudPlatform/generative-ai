"""This is a python utility file."""

# pylint: disable=all

import json

import pandas as pd
import pandasql as ps
from utils.text_bison import TextBison

# It takes a question as input and generates a SQL query that can be used to answer the question.
SQL_PROMPT = """
You are an SQL Expert. Given an input question, use sqlite syntax to generate a sql query by choosing
one or multiple of the following tables. Write query in between <SQL></SQL>.

The first table is a User Policy table whose name is df1 where each row represents the policy of a user.
The column keys are : username, agentname, converted, satisfaction_score, current_policy, policy_start_date, policy_end_date, old_policy, policy_amount, platform.

The second table is a likes table whose name is df2 where each row represents a social media post.
The column keys are : campaignID, websiteVisitors, instaLikes, instaComments, facebookLikes, facebookComments, facebookShares, numberOfMailSent, numberOfMailOpen, facebookSales, newspaperSales, TVAdsSales, instaSales, mailSales, telephoneSales, totalSales.


Please provide the SQL query for this question. Note that the SQL query should be a valid query. It should not use columns which are not present in the table.
Question: {question}
Query:
"""

FINAL_ANSWER_PROMPT = """

You are an experienced programmer and also good at English Language. You need to understand the output answer of a question.
The output has been returned as a dataframe in pandas which would be given to you as a string.
Based on the question and the dataframe, you need re-frame the answer given in the dataframe into natural language.
QUESTION: {question}
DATAFRAME: {df}
ANSWER:

"""


def generate_answer(question: str) -> str:
    """Generates a natural language answer to a question using a dataframe.

    Args:
        question (str): The question to be answered.

    Returns:
        str: The natural language answer to the question.
    """
    tb = TextBison()

    with open("data/policy.json", "rb") as f:
        df1 = pd.DataFrame(json.load(f))

    with open("data/likes.json", "rb") as f:
        df2 = pd.DataFrame(json.load(f))

    PROMPT = SQL_PROMPT.format(question=question)
    answer = tb.generate_response(PROMPT=PROMPT)
    answer = answer.replace("<SQL>", "")
    sql_query = answer.replace("</SQL>", "")
    sql_query = sql_query.strip()
    print("sql_query : ", sql_query)

    try:
        answer_df = ps.sqldf(sql_query, locals())
        print(answer_df)
        temp_df = answer_df.astype(str)
        PROMPT = FINAL_ANSWER_PROMPT.format(question=question, df=temp_df)
        answer_natural_language = tb.generate_response(PROMPT)
        print("answer_natural_language : ", answer_natural_language)
        return answer_natural_language

    except Exception as e:
        print(e)
        return "Unable to answer. Try again!!"


if __name__ == "__main__":
    generate_answer("Which policy has the most users?")
