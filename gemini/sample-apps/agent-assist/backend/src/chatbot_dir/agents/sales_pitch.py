"""This is a python utility file."""

from utils.gemini_text import GeminiText

PROMPT = """
Modify the sales pitch given below emphasizing the content related to the query.

Original Sales Pitch:
{original}

Query: {query}

Modified Sales Pitch:
"""


def sales_pitch_component(query: str, policy_name: str) -> str:
    """Generates a modified sales pitch emphasizing the content related to the query.

    Args:
        query (str): The user's query.
        policy_name (str): The name of the policy to use for the sales pitch.

    Returns:
        str: The modified sales pitch.
    """
    SP_PATH = f"data/static/sales_pitch/{policy_name}.txt"

    with open(SP_PATH) as f:
        original = f.read()

    gt = GeminiText()
    response = gt.generate_response(PROMPT.format(query=query, original=original))

    print("sales pitch:", response)
    return response
