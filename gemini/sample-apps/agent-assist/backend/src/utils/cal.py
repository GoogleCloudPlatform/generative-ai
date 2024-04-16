import os.path
from datetime import datetime
from typing import Any, Dict, List

import pytz
from config import config
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


class Calendar:
    """
    A class to interact with the Google Calendar API.
    """

    def __init__(self):
        """
        Initializes the Calendar class.
        """
        self.self_email = config["company_email"]
        self.SCOPES = [config["CALENDAR_SCOPE"]]
        self.creds = None
        if os.path.exists("cal_token.json"):
            self.creds = Credentials.from_authorized_user_file(
                "cal_token.json", self.SCOPES
            )
        if not self.creds or not self.creds.valid:
            if self.creds and self.creds.expired and self.creds.refresh_token:
                self.creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "keys/credentials_desktop.json", self.SCOPES
                )
                self.creds = flow.run_local_server(port=0)
            with open("cal_token.json", "w") as token:
                token.write(self.creds.to_json())
        try:
            self.service = build("calendar", "v3", credentials=self.creds)
        except HttpError as error:
            print("An error occurred: %s" % error)

    def create_event(
        self, email: list[str], startDateTime: str, endDateTime: str
    ) -> dict:
        """
        Creates an event on the user's calendar.

        Args:
            email (list[str]): A list of email addresses of the attendees.
            startDateTime (str): The start date and time of the event in ISO 8601 format.
            endDateTime (str): The end date and time of the event in ISO 8601 format.

        Returns:
            dict: The event created.
        """
        participants = [{"email": participant} for participant in email]
        participants.append({"email": self.self_email})

        print(participants)
        event = {
            "summary": "Meeting with " + (email[0]),
            "location": "GMeet",
            "description": "Meeting with " + (email[0]),
            "start": {
                "dateTime": startDateTime,
                "timeZone": "Asia/Kolkata",
            },
            "end": {
                "dateTime": endDateTime,
                "timeZone": "Asia/Kolkata",
            },
            "attendees": participants,
            "reminders": {
                "useDefault": False,
                "overrides": [
                    {"method": "email", "minutes": 24 * 60},
                    {"method": "popup", "minutes": 10},
                ],
            },
            "conferenceData": {
                "createRequest": {
                    "requestId": "meeting-with-kavach1",
                    "conferenceSolutionKey": {
                        "type": "hangoutsMeet",
                    },
                },
            },
        }
        event = (
            self.service.events()
            .insert(calendarId="primary", body=event, sendUpdates="all")
            .execute()
        )
        print("Event created: %s" % (event.get("htmlLink")))

        # print(event)
        return event

    def get_events_by_date(self, event_date):
        """
        Gets all events on the user's calendar for a given date.

        Args:
            event_date (str): The date to get events for in YYYY-MM-DD format.

        Returns:
            list[dict]: A list of events on the user's calendar for the given date.
        """

        split_date = event_date.split("/")
        event_date = datetime(
            int(split_date[2]), int(split_date[1]), int(split_date[0]), 00, 00, 00, 0
        )
        event_date_str = pytz.UTC.localize(event_date).isoformat()

        end: datetime = datetime(
            int(split_date[2]),
            int(split_date[1]),
            int(split_date[0]),
            23,
            59,
            59,
            999999,
        )
        end_string = pytz.UTC.localize(end).isoformat()

        events_result = (
            self.service.events()
            .list(calendarId="primary", timeMin=event_date_str, timeMax=end_string)
            .execute()
        )
        return events_result.get("items", [])
