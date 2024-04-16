import base64
from datetime import datetime

from utils.mail_trial import show_chatty_threads
from utils.text_bison import TextBison

PROMPT = """
Summarise the following email thread:

INPUT: {}

OUTPUT:

"""


def get_data_from_threads(service, emailid, threads) -> tuple:
    """Gets the data from the email threads.

    Args:
        service: The service object.
        emailid: The email id of the user.
        threads: The list of threads.

    Returns:
        (tuple)(str, datetime): A tuple containing the email thread content and the last contacted date.
    """
    returnStr = ""
    date_value = datetime(1666, 10, 10)
    date = {"value": date_value}
    for thread in threads:
        tdata = service.users().threads().get(userId="me", id=thread["id"]).execute()
        date = {"value": date_value}
        mailids = [
            x["value"]
            for x in tdata["messages"][0]["payload"]["headers"]
            if x["name"] == "From" or x["name"] == "To"
        ]
        mailpresent = False
        for mail in set(mailids):
            if emailid in mail:
                mailpresent = True

        if mailpresent:
            for data in tdata["messages"]:
                labels = data["labelIds"]
                if "INBOX" in labels or "SENT" in labels:
                    try:
                        message = data["payload"]["parts"][0]["body"]["data"]
                        message = base64.b64decode(message)
                    except Exception as e:
                        print("Error: " + str(e))
                        message = ""
                    try:
                        subject = [
                            x
                            for x in data["payload"]["headers"]
                            if x["name"] == "Subject"
                        ][0]["value"]
                    except Exception as e:
                        print("Error: " + str(e))
                        subject = ""

                    try:
                        if date["value"] == date_value:
                            date = [
                                x
                                for x in data["payload"]["headers"]
                                if x["name"] == "Date"
                            ][0]
                        temp = [
                            x
                            for x in data["payload"]["headers"]
                            if x["name"] == "From" or x["name"] == "To"
                        ]
                    except Exception as e:
                        print("Error: " + str(e))
                        date = {"value": datetime.now().date()}
                        temp = [
                            {"value": "teamkavaachinsurance@gmail.com"},
                            {"value": "channitdak@gmail.com"},
                        ]
                    returnStr += (
                        "FROM: "
                        + str(temp[0]["value"])
                        + "\n---------\n"
                        + "TO: "
                        + str(temp[1]["value"])
                        + "\n---------\n"
                        + "MESSAGE: "
                        + str(subject)
                        + "\n"
                        + str(message)
                        + "\n---------\n"
                    )
            if returnStr:
                break

        else:
            continue

    return returnStr, date["value"]


def get_email_threads_summary(userEmailId: str = "channitdak@gmail.com") -> tuple:
    """Gets the email threads summary.

    Args:
        (str) userEmailId: The email id of the user.

    Returns:
        (tuple) (str, datetime): A tuple containing the email thread summary and the last contacted date.
    """
    threads, service = show_chatty_threads()
    tb = TextBison()
    email_thread_content, lastContactedDate = get_data_from_threads(
        service, userEmailId, threads
    )
    print(email_thread_content, lastContactedDate)
    email_thread_summary = tb.generate_response(PROMPT.format(email_thread_content))
    print(email_thread_summary)
    return email_thread_summary, lastContactedDate


if __name__ == "__main__":
    get_email_threads_summary()
