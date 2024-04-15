import os.path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient import errors
from googleapiclient.discovery import build

from config import config


class Email:
    """A class to handle email operations using the Google Script API."""

    def __init__(self):
        """Initializes the class with the necessary credentials and service
        object.
        """
        self.self_email = config["company_email"]
        self.SCOPES = [config["EMAIL_SCOPE"]]
        self.creds = None
        if os.path.exists("token.json"):
            self.creds = Credentials.from_authorized_user_file(
                "token.json", self.SCOPES
            )
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "../keys/credentials_desktop.json", self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            with open("token.json", "w") as token:
                token.write(self.creds.to_json())
        try:
            self.service = build("script", "v1", credentials=self.creds)
        except errors.HttpError as error:
            print("An error occurred: %s" % error)

    def extract(self, senderName: str) -> str:
        """
        Extracts the email address of the sender from the given sender name.

        Args:
            senderName (str): The name of the sender.

        Returns:
            str: The email address of the sender.

        """

    def send(
        self, receiverName: str, content: str, subject: str, attachment: str
    ) -> None:
        """
        Sends an email to the given receiver with the specified content,
        subject, and attachment.

        Args:
            receiverName (str): The name of the receiver.
            content (str): The content of the email.
            subject (str): The subject of the email.
            attachment (str): The path to the attachment file.

        """
