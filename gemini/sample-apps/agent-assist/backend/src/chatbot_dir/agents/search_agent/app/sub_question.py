"""This is a python utility file."""

# pylint: disable=E0401

PROMPT_FOR_SUBQUESTION = """
You're presented with various queries that compare different policies.
Your task is to simplify these complex queries into simple straightforward questions.
These revised questions should seek comparable details from the policies.
Please craft a query that can be used for comparing multiple policies.
Ensure the questions you generate are clear and based only on existing information,
avoiding assumptions or speculative details.

---------------------

Examples:

INPUT: Compare Arogyasanjeevani Life Insurance and HDFC Ergo Insurance for cataract coverage
OUTPUT: What are the cataract coverage details?
---------------------
INPUT: Which policy is recommended for a 40-year-old diabetic?
OUTPUT: Please provide all the inclusions for diabetes for the 40-year-old age group.
---------------------
INPUT: Contrast Travel Insure and Allianz Global Assistance for lost baggage coverage
OUTPUT: What is the extent of lost baggage coverage?
---------------------
INPUT: Recommend the best policy for maternity benefits between Max Bupa Health Companion and ICICI Prudential Health Protector.
OUTPUT: Can you specify the maternity benefits?
---------------------
INPUT: Recommend the best policy for maternity benefits.
OUTPUT: Can you specify the maternity benefits?
---------------------
INPUT: Evaluate LIC Jeevan Anand and SBI Life Smart Money Back for critical illness coverage
OUTPUT: Provide details regarding critical illness coverage.
---------------------
INPUT: Recommend the most suitable policy for pre-existing condition.
OUTPUT: Please outline the coverage provided for pre-existing conditions.
---------------------
INPUT: Assess Bajaj Allianz Health Guard and Reliance HealthWise for outpatient department (OPD) expenses.
OUTPUT: Can you detail the coverage of outpatient department (OPD) expenses?
---------------------
INPUT: {}
OUTPUT: """


def get_reformed_subquestion(tb, query: str) -> str:
    """Reforms the given query into a subquestion.

    Args:
    query: The query to be reformed.

    Returns:
    The reformed subquestion.
    """
    prompt = PROMPT_FOR_SUBQUESTION.format(query)
    return tb.generate_response(prompt)
