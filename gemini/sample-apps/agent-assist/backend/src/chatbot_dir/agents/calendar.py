from datetime import datetime

from dateutil.parser import parse

from utils.cal import Calendar
from utils.gemini_text import GeminiText

PROMPT = """
You are the helper to an intelligent AI powered chatbot.
You have to deal everything related to handling the calendar events in the bot.

The functionalities available are:

1. schedule : schedules an appointment with a given person at a given date and time
2. get_appointments : gets the list of the coming future appointments

You have to extract the following information for each of the functionality from the given query-

- schedule : the meeting date, the participant, the start_time and the end_time.
Important things to note for schedule:
* in case the end_time could not be extracted from the query, add one hour to the start_time to get the end_time
* in case either the start_time, the participant or the date is missing output INVALID

- get_appointments : the number_of_upcoming_appointments or the time_frame for which the future appointments need to be returned
Important things to note for get_appointments:
* in case both number_of_upcoming_appointments and time_frame cannot be extracted, return 1 week

-----------------------
Examples:

-----------------------
QUERY: Schedule an appointment with Nitin Chandak on 11/02/2024 at 10:00AM

EXPLANATION: The task is schedule. The participant is Nitin Chandak. The meeting date is 11/02/2024, start_time is 10:00AM and since no end_time is mentioned, therefore the end_time for this is 10:00AM plus one hour, i.e. 11:00AM.

OUTPUT: {{"task": "schedule", "date":"11/02/2024", "start_time":"10:00AM", "end_time":"11:00AM", "participant":"Nitin Chandak"}}
-----------------------
QUERY: Book an appointment with Shashwat Saxena

EXPLANATION: The task is schedule. The participant is Shashwat Saxena, but the date as well as the start_time is missing, therefore INVALID

OUTPUT: INVALID
-----------------------
QUERY: Show my upcoming five appointments.

EXPLANATION: The task is get_appointments. The number_of_upcoming_appointments is 5.

OUTPUT: {{"task": "get_appointments", "number_of_upcoming_appointments":5}}
-----------------------
QUERY: Show my upcoming  appointments.

EXPLANATION: The task is get_appointments. The number_of_upcoming_appointments or the time_frame isn't specified. Therefore, we should return 7 as the time frame since by defualt if nothing is mentioned, we need to return appointments for the coming week

OUTPUT: {{"task": "get_appointments", "time_frame":7}}
-----------------------
QUERY: Show my upcoming for the next 15 days.

EXPLANATION: The task is get_appointments. The time_frame is 15 days.

OUTPUT: {{"task": "get_appointments", "time_frame":15}}
-----------------------
QUERY: {query}

EXPLANATION:
"""


def calendar_component(query, chat_history="[]"):
    """
    This function takes a query and a chat history as input and returns a dictionary with the following keys:
    - task: The task to be performed. This can be either "schedule" or "get_appointments".
    - date: The date of the appointment. This is only present if the task is "schedule".
    - start_time: The start time of the appointment. This is only present if the task is "schedule".
    - end_time: The end time of the appointment. This is only present if the task is "schedule".
    - participant: The participant in the appointment. This is only present if the task is "schedule".
    - number_of_upcoming_appointments: The number of upcoming appointments to return. This is only present if the task is "get_appointments".
    - time_frame: The time frame for which to return upcoming appointments. This is only present if the task is "get_appointments".
    - event: The event object created in the calendar. This is only present if the task is "schedule".

    Args:
        query (str): The query to be processed.
        chat_history (str, optional): The chat history. Defaults to "[]".

    Returns:
        dict: A dictionary with the keys described above.
    """
    gemini = GeminiText()
    response = gemini.generate_response(PROMPT.format(query=query))
    response = response.split("OUTPUT:")[1]
    response = response.strip()
    if response != "INVALID":
        response_dict = eval(response)

        if response_dict["task"] == "schedule":
            start_time = response_dict["start_time"]
            end_time = response_dict["end_time"]
            meet_date_str = response_dict["date"]

            start_time = parse(start_time).time()
            end_time = parse(end_time).time()
            meet_date = parse(meet_date_str, dayfirst=True).date()

            startDateTime = datetime(
                meet_date.year,
                meet_date.month,
                meet_date.day,
                start_time.hour,
                start_time.minute,
            ).isoformat()
            endDateTime = datetime(
                meet_date.year,
                meet_date.month,
                meet_date.day,
                end_time.hour,
                end_time.minute,
            ).isoformat()

            print("start", startDateTime)
            print("end", endDateTime)
            calendar = Calendar()
            event = calendar.create_event(
                [
                    "channitdak@gmail.com",
                ],
                startDateTime,
                endDateTime,
            )

            response_dict["event"] = event

    return response


if __name__ == "__main__":
    query = "Set up an appointment with Koustav Sen on 11/02/2024 at 1:00PM"
    calendar_component(query)
