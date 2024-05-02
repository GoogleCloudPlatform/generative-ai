"""This is a python utility file."""

# pylint: disable=E0401

import os.path

from config import config
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def show_chatty_threads():
    """Shows basic usage of the Gmail API.
    Prints the threads in the user's mailbox.
    """
    scopes = [config["MAIL_TRIAL_SCOPE"]]
    creds = None

    if os.path.exists("mail_token.json"):
        creds = Credentials.from_authorized_user_file("mail_token.json", scopes)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "keys/read_mail.json", scopes
            )
            creds = flow.run_local_server(port=0)
        with open("mail_token.json", "w", encoding="utf-8") as token:
            token.write(creds.to_json())
    try:
        service = build("gmail", "v1", credentials=creds)

        # pylint: disable=maybe-no-member
        # pylint: disable:R1710
        threads = (
            service.users().threads().list(userId="me").execute().get("threads", [])
        )
        return threads, service

    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


if __name__ == "__main__":
    for thread in show_chatty_threads():
        print(thread)
