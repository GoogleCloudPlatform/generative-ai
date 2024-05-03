"""This is a python utility file."""

# pylint: disable=E0401

from flask_socketio import emit
from utils.gemini_text import GeminiText

from .chunks import get_chunks
from .comparison import comparison
from .coreference import get_chat_chain
from .keywords import get_keywords
from .sub_question import get_reformed_subquestion

PROMPT_RESULT = """
Given a query relating to Home insurance policies, you need to answer based on the CHUNKS given below.

----
CHUNKS:
{}
----
When comparing policies, consider the following points:
1. A good policy has higher sum insured.
2. Good policies also have additional coverages.
3. A policy covering more things is a better policy.

Lets think step by step before answering.

-------
Answer strictly from the policy chunks given. Do not answer anything from your own knowledge.

-------

QUERY: {}
OUTPUT: """


class Driver:
    """
    The Driver class is responsible for running the search agent.

    The Driver class has the following responsibilities:

    * Getting the chat chain.
    * Getting the keywords from the query.
    * Getting the chunks from the policies.
    * Getting the answer to the query.
    """

    def __init__(self):
        """Initializes the Driver class.

        This function initializes the Driver class with the following attributes:

        * `chat_chain`: A list of chat messages.
        * `tb`: A TextBison object.
        """
        self.chat_chain = get_chat_chain()
        self.tb = GeminiText()

    def run(self, query, policies) -> str:
        """
        Runs the driver.

        This function runs the driver and returns the answer to the query.

        Args:
            query(str): The query to be answered.
            policies(str): The list of policies to be compared.

        Returns:
            (str)The answer to the query.
        """
        try:
            single_policy_flag = len(policies) == 1
            keywords_lexical = get_keywords(query)
            keywords_semantic = get_keywords(query, False)
            chunk_list = self.get_chunks_str(
                policies, keywords_lexical, keywords_semantic
            )

            if single_policy_flag:
                reformed_question = query
                answer = self.get_answer_one_policy(chunk_list[0], reformed_question)

                emit("chat", ["Generating..."])
                emit(
                    "chat", [{"intent": "Search Result ", "data": {"response": answer}}]
                )
            else:
                reformed_question = get_reformed_subquestion(self.tb, query)
                print("reformed question:", reformed_question)
                emit("chat", ["Generating..."])
                emit(
                    "chat",
                    [
                        {
                            "intent": "Intermediate Response - Search",
                            "data": {
                                "response": (
                                    "Reformulated question: "
                                    + reformed_question
                                    + "\n\n"
                                )
                            },
                        }
                    ],
                )
                emit("chat", ["Generating..."])
                individual_policy_answers = [
                    self.get_answer_one_policy(chunk_str, reformed_question)
                    for chunk_str in chunk_list
                ]

                columns = {
                    policies[i]: individual_policy_answers[i]
                    for i in range(len(policies))
                }
                emit("chat", [{"intent": "Comparison", "data": columns}])
                print("individual policy answers:", individual_policy_answers)

                context_for_final_answer = ""
                for policy, answer in zip(policies, individual_policy_answers):
                    context_for_final_answer += (
                        f"POLICY:{policy}\n{answer}\n--------------------------\n"
                    )
                answer = comparison(self.tb, context_for_final_answer)

                emit("chat", ["Generating..."])
                emit(
                    "chat",
                    [{"intent": "Recommended Policy", "data": {"response": answer}}],
                )

        except ValueError as e:
            if e.args[0] == "Policy not found":
                answer = "Policy not in database"
            else:
                raise e

        return answer

    def get_answer_one_policy(self, chunk_str: str, reformed_question: str) -> str:
        """Gets the answer to the query for one policy.

        This function gets the answer to the query for one policy.

        Args:
            chunk_str(str): The string of chunks for the policy.
            reformed_question(str): The reformed question.

        Returns:
            (str) The answer to the query.
        """
        tb = GeminiText()
        response = tb.generate_response(
            PROMPT_RESULT.format(chunk_str, reformed_question)
        )
        return response

    def get_chunks_str(
        self, policies: list, keywords_lexical: str, keywords_semantic: str
    ) -> list:
        """Gets the string of chunks for the policies.

        This function gets the string of chunks for the policies.

        Args:
            policies(list): The list of policies.
            keywords_lexical(str): The list of lexical keywords.
            keywords_semantic(str): The list of semantic keywords.

        Returns:
            (str) The string of chunks for the policies.
        """
        chunk_str = ""
        chunks = get_chunks(policies, keywords_lexical, keywords_semantic)
        chunk_list = []
        for _, chunk_l in chunks.items():
            chunk_str = ""
            chunk_str += "\n --------- \n".join(chunk_l)
            chunk_list.append(chunk_str)

        return chunk_list
