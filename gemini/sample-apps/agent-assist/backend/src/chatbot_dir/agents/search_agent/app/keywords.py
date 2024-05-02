"""This is a python utility file."""

from utils.text_bison import TextBison

PROMPT_LEXICAL = """
Given a query related to Home insurance policies, output the defining term in the query.
The defining term is the word/phrase that defines the query and can be used to extract all the provisions in the policy related to that term.

Query: What are the coverages for earthquake damage in Home Shield Insurance?
Output: earthquake damage

Query: Compare Home Shield and Bharat Griha Raksha Plus for accidental fire damage.
Output: accidental fire damage

Query: What are the best policies for protection against burglary?
Output: burglary

Query: What are the exclusions for Bharat Griha Raksha Plus?
Output: exclusions

Query: {}
Output: """

PROMPT_SEMANTIC = """
Given a query related to Home insurance policies, output the sentences into a transformed phrase suitable for vector matching.

Query: What are the coverages for earthquake damage in Home Shield Insurance?
Output: coverages for earthquake damage

Query: Compare Home Shield and Bharat Griha Raksha Plus for accidental fire damage.
Output: coverages for accidental fire damage

Query: What are the best policies for protection against burglary?
Output: protection againstburglary

Query: {}
Output: """


def get_keywords(query: str, forLexical: bool = True) -> str:
    """Gets the keywords from a query.

    Args:
        (str) query: The query to get the keywords from.
        (bool) forLexical: A boolean value indicating whether to get
            the lexical or semantic keywords.

    Returns:
        (str) The keywords from the query.
    """
    if forLexical:
        PROMPT = PROMPT_LEXICAL
    else:
        PROMPT = PROMPT_SEMANTIC

    tb = TextBison()
    response = tb.generate_response(PROMPT.format(query))

    print("lexical", forLexical, "keywords", response)
    return response
