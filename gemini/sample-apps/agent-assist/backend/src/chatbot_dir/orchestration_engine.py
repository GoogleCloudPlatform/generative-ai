"""This is a python utility file."""

# pylint: disable=E0401

from datetime import date, datetime
from typing import List

from dateutil.parser import parse
from flask_socketio import emit
from utils.cal import Calendar
from utils.get_email_threads import get_email_threads_summary
from utils.text_bison import TextBison

from .agents import database_search, search_agent
from .agents.fallback_component import fallback_component
from .agents.mail import mail_component
from .agents.sales_pitch import sales_pitch_component
from .example_pruning import get_similar_examples


def fallback(query: str, chat_history: str = "") -> str:
    """Fallback function to handle queries that do not match any of the other intents.

    Args:
        query (str): The user's query.
        chat_history (str, optional): The chat history of the conversation. Defaults to "".

    Returns:
        str: A response to the user's query.
    """
    response = fallback_component(query, chat_history, "")

    emit("chat", ["Generating..."])
    emit("chat", [{"intent": "Response ", "data": {"response": response}}])

    return response


def search(query: str, policy_list: List[str]) -> str:
    """Search function to handle queries related to insurance policies.

    Args:
        query (str): The user's query.
        policy_list (List[str]): A list of insurance policies to search for.

    Returns:
        str: A response to the user's query.
    """
    response = search_agent.run(query, policy_list)

    # emit("chat", ["Generating..."])
    # emit("chat", [{'intent': 'Search Result ', 'data': {'response': response}}])

    return response


def create_sales_pitch(prompt: str, policy_name: str) -> str:
    """Create sales pitch function to handle queries related to creating sales pitches.

    Args:
        prompt (str): The prompt for the sales pitch.
        policy_name (str): The name of the insurance policy to create a sales pitch for.

    Returns:
        str: A sales pitch for the given policy.
    """
    response = sales_pitch_component(prompt, policy_name)

    emit("chat", ["Generating..."])
    emit("chat", [{"intent": "Sales Pitch ", "data": {"response": response}}])

    return response


def generate_email(prompt: str, chat_history: str) -> tuple[str, str]:
    """Generate email function to handle queries related to generating emails.

    Args:
        PROMPT (str): The PROMPT for the email.
        chat_history (str): The chat history of the conversation.

    Returns:
        tuple[str, str]: A tuple containing the email subject and body.
    """
    return mail_component(query=prompt, chat_history=chat_history)


def send_email(email_id: str, subject: str, body: str) -> None:
    """Send email function to handle queries related to sending emails.

    Args:
        email_id (str): The email address of the recipient.
        subject (str): The subject of the email.
        body (str): The body of the email.
    """
    response = {
        "status": "valid",
        "intent": "email",
        "data": {"recipient": email_id, "subject": subject, "body": body},
    }

    emit("chat", ["Generating..."])
    emit("chat", [response])


def get_email_conversation_summary(email_id: str) -> dict:
    """Get email conversation summary function to
      handle queries related to getting email conversation summaries.

    Args:
        email_id (str): The email address of the user.

    Returns:
        str: A summary of the email conversation.
    """
    email_content, _ = get_email_threads_summary(email_id)
    response = {
        "status": "valid",
        "intent": "response",
        "data": {"response": str(email_content)},
    }

    emit("chat", ["Generating..."])
    emit("chat", [response])

    return response


def schedule_calendar_event(event_date, start_time, end_time, participants) -> None:
    """Schedule calendar event function to handle queries related to scheduling calendar events.

    Args:
        event_date: The date of the event.
        start_time: The start time of the event.
        end_time: The end time of the event.
        participants: A list of participants in the event.
    """
    if "undefined" in [event_date, start_time, end_time, participants]:
        response = {
            "status": "invalid",
            "intent": "calendar",
            "data": {
                "date": event_date,
                "start_time": start_time,
                "end_time": end_time,
                "participants": participants,
            },
        }

    else:
        start_time = parse(start_time).time()
        end_time = parse(end_time).time()
        meet_day = parse(event_date, dayfirst=True).date()

        start_date_time = datetime(
            meet_day.year,
            meet_day.month,
            meet_day.day,
            start_time.hour,
            start_time.minute,
        ).isoformat()
        end_date_time = datetime(
            meet_day.year,
            meet_day.month,
            meet_day.day,
            end_time.hour,
            end_time.minute,
        ).isoformat()

        print("start", start_date_time)
        print("end", end_date_time)
        calendar = Calendar()
        event = calendar.create_event(participants, start_date_time, end_date_time)

        response = {"status": "valid", "intent": "calendar", "data": {"event": event}}

    emit("chat", ["Generating..."])
    emit("chat", [response])


def get_calendar_events(dates: List[str]) -> dict:
    """Get calendar events function to handle queries related to getting calendar events.

    Args:
        dates (List[str]): A list of dates to get events for.

    Returns:
        List[str]: A list of calendar events.
    """
    calendar = Calendar()
    result = []
    for date_and_day in dates:
        result += calendar.get_events_by_date(date_and_day)

    response = {"status": "valid", "intent": "get_calendar_events", "data": result}

    emit("chat", ["Generating..."])
    emit("chat", [response])

    return response


def database_search_orchestrator(query: str) -> str:
    """Database search orchestrator function to handle queries related to searching the database.

    Args:
        query (str): The query to search for.

    Returns:
        str: The result of the database search.
    """
    response = database_search.generate_answer(query)

    emit("chat", ["Generating..."])
    emit(
        "chat", [{"intent": "Database Search Result ", "data": {"response": response}}]
    )

    return response


PROMPT = """
You are an AI-powered intelligent chatbot driver.
Your task is to act on a user input which might be a compound query or a simple query.
You have to think step-by-step on it and decide what to do.


-------------------------------


The things you have to do are:
1: Do coreference resolution on the user input. The coreference resolution might be explicit wherein you will need to reason out what the pronouns mean, or it may be implicit wherein you will have to look at the chat history of the conversation to figure out the missing details and subsequently reform the query. For explicit and implicit coreference resolution, leverage the chat history intelligently. Utilize contextual cues to discern pronouns, references, or implied subjects, enhancing the accuracy of the coreference resolution.
2: Think and reason out if the query is a compound query or not. A compound query is a query that involves more than one of the given intents, while a simple query is a query that involves only one of the given intents. If it is a compound query, you have to decompose the query into a series of logical steps that need to be carried out to perform the given task. If it is a simple query, you do not have to do anything in this step. You have a list of actions available as python function signatures. You have to make use of them to perform the task.
3. For achieving the above tasks, we will first build a step by step plan to solve the problem and then propose a solution for each step by leveraging the available actions. In case none of the other actions match, you need to use the fallback action.
4. An email list has been given to you with the following information:
    - A list of names of the users and their corresponding email
This email list needs to be used for retrieving the email id of the user for setting up a calendar and email related events.

-------------------------------

The list of actions available are:


1.  <PYTHON> search(query: str, policy_list: List[str]) -> str </PYTHON>
# This function takes the query and policy list as input and gives an answer to the query as the output. The policy list should strictly be from the following: ['Home Shield', 'Bharat Griha Raksha Plus', 'Micro Insurance - Home Insurance', 'My Asset Home Insurance'].

2. <PYTHON> generate_email(PROMPT: str, chat_history: str) -> tuple[str, str]  </PYTHON>
# This function generated an email subject and body for the given PROMPT.

3. <PYTHON> send_email(email_id: str, subject: str, body: str) -> None </PYTHON>
#This function sends an email to the email_id with the subject and body given as parameters. If the user name is given and not email id, get the email id from the email list below.

4. <PYTHON> get_email_conversation_summary(email_id: str) -> str </PYTHON>
#This function gets the email conversation from the email_id given as parameter.

5. <PYTHON> schedule_calendar_event(date: str, start_time: str, end_time: str, participants: List[str]) -> None </PYTHON>
#This function schedules an event given the data, start_time, end_time and participants.

6. <PYTHON> get_calendar_events(dates: List[str]) -> List[str] </PYTHON>
#This function gets the calendar events for the given dates.

7. <PYTHON> create_sales_pitch(PROMPT: str, policy_name: str) -> str </PYTHON>
#This function creates a sales pitch for the given policy name as per the PROMPT given. The policy name should strictly be from the following: ['Home Shield', 'Bharat Griha Raksha Plus', 'Micro Insurance - Home Insurance', 'My Asset Home Insurance']

8. <PYTHON> fallback(query: str, chat_history: str) -> str </PYTHON>
#This function returns a fallback response for the given query)

9. <PYTHON> database_search_orchestrator(query: str) -> str </PYTHON>
#This function returns a response for the given query from the database. The database is a Insurance Database Table whose name is df where each row represents a single customer. The column keys are : username, agentname, converted, satisfaction_score, current_policy, policy_start_date, policy_end_date, old_policy, policy_amount, platform and last_contacted


-------------------------------

Some important notes:
- DO NOT USE FUNCTIONS WHICH ARE NOT IN THE ABOVE LIST.
- In case the user query misses some arguments for the function signature, return the value "undefined" for that argument.
- For calendar events, use {date_today} for the current date, and make reason out timeframes from this.
- Always pass the variable chat_history as an argument for chat_history in the fallback function.
-------------------------------

The actions follow a logical order in case multiple actions are present in a query.
* Let us suppose the query is : Email comparison of Home Shield Insurance and Bharat Griha Raksha Plus for coverage of earthquake damage, to johnsmith@gmail.com. In this case, we need to email the comparison between the two insurance policies pertaining to earthquake damage to the given user. So, logically, first we need to find this comparison for which we need the function call <PYTHON> answer = search(query="Compare Home Shield Insurance and Bharat Griha Raksha Plus for coverage of earthquake damage", policy_list=["Home Shield Insurance", "Bharat Griha Raksha Plus"]) </PYTHON>"). After that we need to generate an email subject and body for the given PROMPT using the function call <PYTHON> subject, body = generate_email(PROMPT=answer, chat_history=chat_history) </PYTHON>), and then send the email to the user using the function call <PYTHON> result = send_email(email_id="johnsmith@gmail.com", subject=subject, body=body) </PYTHON>).

On a general level, the workflow is as follows:
search() -> create_sales_pitch() -> generate_email() -> send_email()


-------------------------------

EMAIL LIST:

{user_list}

-------------------------------

Examples:

-------------------------------

{examples}

-------------------------------


INPUT: {query}

CHAT_HISTORY: {chat_history}

PLAN:
Step 1:
"""


def run_orchestrator(query, chat_history):
    """Run function to execute the plan and generate the response.

    Args:
        query (str): The user's query.
        chat_history (str): The chat history of the conversation.
    """
    tb = TextBison()
    today = date.today()
    formatted_date = today.strftime("%d/%m/%Y")
    with open("data/user_list.txt", encoding="utf-8") as f:
        user_list = f.read()

    examples = get_similar_examples(query, chat_history)

    actions = tb.generate_response(
        PROMPT.format(
            query=query,
            chat_history=chat_history,
            date_today=formatted_date,
            user_list=user_list,
            examples=examples,
        )
    )

    end_index = actions.find("ACTION:")
    plan = "Step 1: \n " + actions[:end_index]

    actions = actions.split("ACTION:")[1]
    actions = actions.strip("[] ")
    actions = actions.split("<PYTHON>")[1:]
    actions = [action[: action.find("</PYTHON>")].strip() for action in actions]

    emit("chat", [{"intent": "Plan", "data": {"response": "```\n" + plan + "\n```"}}])
    emit("chat", ["Generating..."])

    actions_str = "\n".join(actions)
    emit(
        "chat",
        [
            {
                "intent": "Code Flow",
                "data": {"response": "```\n" + actions_str + "\n```"},
            }
        ],
    )

    print(actions_str)

    d = {"chat_history": chat_history}
    exec(actions_str, globals(), d)  # pylint: disable=W0122


if __name__ == "__main__":
    run_orchestrator(
        "Compare Homeshield and Bharat Griha Raksha Plus and send this to channit", []
    )
