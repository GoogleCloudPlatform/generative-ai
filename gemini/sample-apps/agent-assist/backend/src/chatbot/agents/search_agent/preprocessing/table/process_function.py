from .one_shot.prompt import PROMPT_FOR_TABLE
from .text_bison import TextBison


def processTable(table_df_string: str) -> str:
    """
    Processes a table in dataframe string format using TextBison.

    Args:
        table_df_string (str): The table in dataframe string format.

    Returns:
        str: The processed table in dataframe string format.

    """
    tb = TextBison()
    prompt = PROMPT_FOR_TABLE.format(table_df_string)
    df_string = tb.generate_response(prompt)
    return df_string
