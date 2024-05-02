"""This is a python utility file."""

# pylint: disable=E0401

from utils.text_bison import TextBison

PROMPT = """
You are the helper to an intelligent AI powered chatbot.
You have to deal everything related to handling the calendar events in the bot.

The functionalities available are:

1. send_email : generates the email to be sent to the user based on given context
2. get_email_summary : gets the email thread conversation and generates a summary of it

--------------------

Important things to note for send_email:
- you need to extract the receipient to whom the email has to be sent

--------------------

Important things to note for get_email_summary:
- you need to extract the user for whom the conversation history has to be summarised

--------------------

Examples:

--------------------
INPUT: Send a reply to Koustav Sen

EXPLANATION: Since we need to send a reply to Koustav Sen, therefore the action is send_email. The receipient is Koustav Sen.

OUTPUT: {{ "action": "send_email", "receipient": "Koustav Sen" }}

--------------------
INPUT: Get email conversation summary for Shashwat Saxena

EXPLANATION: Since we need to get the email conversation summary for Shashwat Saxena, therefore the action is get_email_summary. The user is Shashwat Saxena.

OUTPUT: {{ "action": "get_email_summary", "user": "Shashwat Saxena" }}

--------------------
INPUT: Send the sales pitch to channitdak@gmail.com

EXPLANATION: Since we need to send the sales pitch to channitdak@gmail.com, therefore the action is send_email. The receipient is channitdak@gmail.com.

OUTPUT: {{ "action": "send_email", "receipient": "channitdak@gmail.com" }}
--------------------
INPUT: {input}

EXPLANATION:
"""

PROMPT_EMAIL_BODY = """
You are an intelligent Ai assistant.
Your job is take a query, chat_history and context as input and generate an email body.
Do not include subject in the email body.

QUERY: {query}

CONTEXT: {context}

CHAT_HISTORY: {chat_history}

EMAIL BODY:
"""

PROMPT_EMAIL_SUBJECT = """
You are an intelligent Ai assistant.
Your job is take a query, chat_history and context as input and generate subject for the email.

Important Instruction:
Gie only the subject in a line.
Do not try to explain how you got it.

QUERY: {query}

CONTEXT: {context}

CHAT_HISTORY: {chat_history}

EMAIL SUBJECT:
"""


def mail_component(query: str, chat_history: str, context: str = "") -> tuple[str, str]:
    """
    This function takes a query, chat_history and context as input and
    generates an email subject and body.

    Args:
        query (str): The user's query.
        chat_history (str): The chat history between the user and the bot.
        context (str): The context of the conversation.

    Returns:
        tuple[str, str]: A tuple containing the email subject and body.
    """
    gemini = TextBison()
    email_body = gemini.generate_response(
        PROMPT_EMAIL_BODY.format(
            query=query, context=context, chat_history=chat_history
        )
    )
    email_subject = gemini.generate_response(
        PROMPT_EMAIL_SUBJECT.format(
            query=query, context=context, chat_history=chat_history
        )
    )

    return email_subject, email_body
