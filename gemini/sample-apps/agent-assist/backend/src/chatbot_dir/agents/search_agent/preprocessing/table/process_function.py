"""This is a python utility file."""

# pylint: disable=all

from src.chatbot_dir.agents.search_agent.preprocessing.table.one_shot.PROMPT import (
    PROMPT_FOR_TABLE,
)
from src.chatbot_dir.agents.search_agent.preprocessing.table.text_bison import TextBison


def processTable(table_df_string: str) -> str:
    """Processes a table in dataframe string format using TextBison.

    Args:
        table_df_string (str): The table in dataframe string format.

    Returns:
        str: The processed table in dataframe string format.
    """
    tb = TextBison()
    PROMPT = PROMPT_FOR_TABLE.format(table_df_string)
    df_string = tb.generate_response(PROMPT)
    return df_string
