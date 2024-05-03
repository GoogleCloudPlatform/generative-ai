"""This is a python utility file."""

# pylint: disable=E0401

from utils.gemini_text import GeminiText

from ..config import POLICIES

POLICIES_STR = ""
for POLICY_NAME, i in enumerate(POLICIES):
    POLICIES_STR += f"{i} - {POLICY_NAME}\n"

PROMPT = """
The insurance policies which we have are:

{}

Given a query, output all the insurance policies which the query is about.

Some important instructions:
1. The output should be a python list of policy indices.
2. In case the question asks for the best policy, output all insurance policies.
3. If the query has a policy which is not in the list, output "I do not know about <Policy Name>".
4. Do not use your own knowledge.

----------
Query: Compare HDFC Ergo and Max Bhupa.
Output: [1, 2]
----------
Query: What is covered in VidalTPA for cataract?
Output: I do not know about VidalTPA.
----------
Query: Is New India Insurance better than Arogyasanjeevni for a 40 year old diabetic?
Output: [0,3]
----------
Query: Which the best policy for a cancer patient?
Output: [0,1,2,3]
----------
Query: What are the coverages for hospitalisation in LifeSure Life Insurance?
Output: I do not know about LifeSure Life Insurance.
----------
Query: {}
Output: """


def get_policies(query: str):
    """Given a query, output all the insurance policies which the query is about.

    Args:
        query (str): The query to process.

    Returns:
        list| str: A list of policy indices or a string indicating that the policy is not known.
    """
    tb = GeminiText()

    response = tb.generate_response(PROMPT.format(POLICIES_STR, query))

    if "[" in response:
        response = response.strip("[] ")
        response_list = response.split(",")

        response_list_int = [int(x.strip()) for x in response_list]
        response_policies = [POLICIES[x] for x in response_list_int]
    print("policies names:", response_policies)

    if isinstance(response, str):
        raise ValueError("Policy not found")
    return response
