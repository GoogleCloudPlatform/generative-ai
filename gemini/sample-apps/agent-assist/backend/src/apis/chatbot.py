import json
from datetime import datetime

from chatbot import orchestration_engine


def chatbot_entry(data: dict = {}) -> dict:
    """
    This function is the main entry point for the chatbot. It takes a dictionary of data as input and returns a dictionary of data as output.

    Args:
        data (dict): A dictionary of data representing the input to the chatbot.

    Returns:
        dict: A dictionary of data representing the output from the chatbot.
    """
    if type(data.get("query")) is not list:
        chat_history = []

    query = data.get("query")
    chat_history = data.get("chat_history")

    chat_history = process_history(chat_history)
    with open("data/static/oe_examples/logs.json") as f:
        logs = json.load(f)

    logs.append(
        {
            "datetime": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
            "query": query,
            "chat_history": chat_history,
        }
    )
    with open("data/static/oe_examples/logs.json", "w") as f:
        json.dump(logs, f)

    result = orchestration_engine.run(query, chat_history)
    return result


def process_history(chat_history: list) -> str:
    """
    This function processes the chat history and returns a string that can be used to display the chat history.

    Args:
        chat_history (list): A list of dictionaries representing the chat history.

    Returns:
        str: A string representing the chat history.
    """

    history = []

    for message in chat_history:
        if message["type"] == "user":
            history.append("Q: " + message["message"])
        else:
            if message["message"] in [
                "Plan",
                "Code Flow",
                "Intermediate Response - Search",
            ]:
                continue
            history.append("A: " + message["message"] + str(message.get("payload", "")))
    return "\n".join(history)


def process_response(response: dict) -> str:
    """
    This function processes the response from the orchestration engine and returns a string that can be used to display the response.

    Args:
        response (dict): A dictionary representing the response from the orchestration engine.

    Returns:
        str: A string representing the response from the orchestration engine.
    """

    intent, data = response.values()

    if intent == "search":
        result = data["search_result"]
    elif intent == "sales_pitch":
        result = data["sales_pitch"]
    elif intent == "calender":
        if data["task"] == "schedule":
            result = "Ok. We have set up a meeting."
    elif intent == "email":
        result = data["body"]
    elif intent == "fallback":
        result = data["response"]

    return result
