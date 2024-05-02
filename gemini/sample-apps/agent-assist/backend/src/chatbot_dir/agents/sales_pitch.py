"""This is a python utility file."""

# pylint: disable=E0401

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
    sp_path = f"data/static/sales_pitch/{policy_name}.txt"

    with open(sp_path, encoding="utf-8") as f:
        original = f.read()

    gt = GeminiText()
    response = gt.generate_response(PROMPT.format(query=query, original=original))

    print("sales pitch:", response)
    return response
