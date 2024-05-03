"""This is a python utility file."""

# pylint: disable=E0401

import base64
from datetime import datetime

from utils.mail_trial import show_chatty_threads
from utils.text_bison import TextBison

PROMPT = """
Summarise the following email thread:

INPUT: {}

OUTPUT:

"""


def get_data_from_threads(service, emailid, threads):
    """Gets the data from the email threads.

    Args:
        service: The service object.
        emailid: The email id of the user.
        threads: The list of threads.

    Returns:
        tuple[str, datetime]: A tuple containing the
          email thread content and the last contacted date.
    """
    return_str = ""
    date_value = datetime(1666, 10, 10)
    date = {"value": date_value}
    for thread in threads:
        tdata = service.users().threads().get(userId="me", id=thread["id"]).execute()
        mail_ids = {
            x["value"]
            for x in tdata["messages"][0]["payload"]["headers"]
            if x["name"] == "From" or x["name"] == "To"
        }
        mail_present = any(emailid in mail for mail in mail_ids)

        if mail_present:
            for data in tdata["messages"]:
                labels = data["labelIds"]
                if "INBOX" in labels or "SENT" in labels:
                    try:
                        message = data["payload"]["parts"][0]["body"]["data"]
                        message = base64.b64decode(message)
                    except ValueError as e:
                        print("Error: " + str(e))
                        message = ""
                    try:
                        subject = next(
                            (
                                x["value"]
                                for x in data["payload"]["headers"]
                                if x["name"] == "Subject"
                            ),
                            "",
                        )
                    except ValueError as e:
                        print("Error: " + str(e))
                        subject = ""

                    try:
                        date = next(
                            (
                                x
                                for x in data["payload"]["headers"]
                                if x["name"] == "Date"
                            ),
                            {"value": datetime.now().date()},
                        )
                    except ValueError as e:
                        print("Error: " + str(e))
                        date = {"value": datetime.now().date()}

                    return_str += (
                        f"FROM: {data['payload']['headers'][0]['value']}\n---------\n"
                        f"TO: {data['payload']['headers'][1]['value']}\n---------\n"
                        f"MESSAGE: {subject}\n{message}\n---------\n"
                    )
            if return_str:
                break

    return return_str, date["value"]


def get_email_threads_summary(
    user_email_id: str = "channitdak@gmail.com",
) -> tuple[str, datetime]:
    """Gets the email threads summary.

    Args:
        user_email_id (str): The email id of the user.

    Returns:
        tuple[str, datetime]: A tuple containing the email
          thread summary and the last contacted date.
    """
    threads, service = show_chatty_threads()
    tb = TextBison()
    email_thread_content, last_contacted_date = get_data_from_threads(
        service, user_email_id, threads
    )
    print(email_thread_content, last_contacted_date)
    email_thread_summary = tb.generate_response(PROMPT.format(email_thread_content))
    print(email_thread_summary)
    return email_thread_summary, last_contacted_date


if __name__ == "__main__":
    get_email_threads_summary()
