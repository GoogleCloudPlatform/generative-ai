"""This is a python utility file."""

# pylint: disable=E0401

from config import config
from langchain.chains import ConversationChain
from langchain.chat_models import ChatVertexAI
from langchain.memory import ConversationBufferMemory
import vertexai

PROMPT = """
You are an expert in English Language.
You have to assist a chatbot in answering questions. You have to reframe the questions using your chat history to replace it, them and other such pronouns with the appropriate nouns coreferencing them from your chat history.
Make sure to think step by step before arriving at the answer.

In case there are no such pronouns, just return the original question.
Do not add anything from your own knowledge into the rephrased question.
Keep it as simple as possible.

Question: {}

Reframed Question:

"""


def get_chat_chain() -> ConversationChain:
    """
    Returns a ConversationChain object.

    Args:
        None

    Returns:
        ConversationChain: A ConversationChain object.
    """

    project_id = config["PROJECT_ID"]
    vertexai.init(project=project_id, location=config["LOCATION"])
    chat_llm = ChatVertexAI(temperature=0.08)
    chat_chain = ConversationChain(llm=chat_llm, memory=ConversationBufferMemory())
    return chat_chain


def get_rephrased_question(question: str, chat_chain: ConversationChain) -> str:
    """
    Rephrases a question using coreference resolution.

    Args:
        question (str): The question to be rephrased.
        chat_chain (ConversationChain):
          The ConversationChain object to use for coreference resolution.

    Returns:
        str: The rephrased question.
    """

    rephrased_question = chat_chain.run(PROMPT.format(question))
    print("rephrased_question: ", rephrased_question)
    return rephrased_question
