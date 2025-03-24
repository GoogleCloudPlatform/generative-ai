# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Autocal Legacy

This is a Streamlit app that processes screenshots uses Gemini 2.0 Flash
and adds them to Google Calendar.

It requires a Google Calendar API key to run.
"""

import json
import os
import streamlit as st

from dotenv import load_dotenv
from typing import Any

from PIL import Image
from google.cloud import storage
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google import genai
from google.genai.types import (
    GenerateContentConfig,
)
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from vertexai.generative_models import (
    Part,
)

# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Load variables from .env file
load_dotenv()

# Your Google Cloud Project ID and region
PROJECT_ID = os.environ.get("PROJECT_ID")

# Default location if not specified
if PROJECT_ID is None:
    st.error("Expected PROJECT_ID to be set")
    st.stop()

LOCATION = os.environ.get("LOCATION", "europe-west1")
MODEL_ID = os.environ.get("MODEL_ID", "gemini-2.0-flash-001")

client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

BUCKET_NAME = os.environ["BUCKET_NAME"]


def upload_blob(destination_blob_name: Any, file_content: Any) -> str:
    """Uploads a file to the bucket."""

    storage_client = storage.Client()
    bucket = storage_client.bucket(BUCKET_NAME)
    blob = bucket.blob(destination_blob_name)

    # Reset the file pointer to the beginning before reading in upload_blob
    file_content.seek(0)
    blob.upload_from_file(file_content)

    print(f"File {destination_blob_name} uploaded to {BUCKET_NAME}.")
    st.write("File:  ", destination_blob_name, "  uploaded.")

    file_url = f"gs://{BUCKET_NAME}/{destination_blob_name}"
    return file_url


# Initialize the Gemini model
MODEL_ID = "gemini-2.0-flash-001"

# Define the response schema for the analysis
response_schema = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "location": {"type": "STRING"},
        "description": {"type": "STRING"},
        "start time": {"type": "STRING"},
        "end time": {"type": "STRING"},
    },
    "required": ["summary", "description", "start time", "end time"],
}

# Define the prompt for the analysis
PROMPT = """Analyze the provided screenshot and extract the following information:

summary: A brief summary of the event.
location: The location of the event.
start time: The start date and time of the event in YYYY-MM-DDTHH:MM:SS format.
end time: The end date and time of the event in YYYY-MM-DDTHH:MM:SS format. Calculate this using the duration, if no duration is mentioned, assume the event is an hour long.
Ensure the start and end objects include the correct timeZone based on the information in the screenshot.
duration: The duration of the event in minutes. This could be also written as mins.Use this to calculate the end time if provided.
Ensure the start and end objects include the correct timeZone based on the information in the screenshot.
description: A short description of the event.

The response should have the following schema:

{
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "location": {"type": "STRING"},
        "description": {"type": "STRING"},
        "start time": {"type": "STRING"},
        "end time": {"type": "STRING"}
    }
}

"""


def create_calendar_event(event_data: Any) -> None:
    """Creates a Google Calendar event."""

    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
            creds = flow.run_local_server(port=0)
        with open("token.json", mode="w", encoding="utf-8") as token:
            token.write(creds.to_json())

    try:
        service = build("calendar", "v3", credentials=creds)
        event = {
            "summary": event_data.get("summary", "New Event"),
            "location": event_data.get("location", ""),
            "description": event_data.get("description", ""),
            "start": {
                "dateTime": event_data.get("start time"),
                "timeZone": "Europe/London",  # Adjust time zone if needed
            },
            "end": {
                "dateTime": event_data.get("end time"),
                "timeZone": "Europe/London",  # Adjust time zone if needed
            },
        }
        # Allow raw access to the events api
        # pylint: disable=no-member
        event = service.events().insert(calendarId="primary", body=event).execute()
        print(f"Event Created {event.get('htmlLink')}")
        st.write(f"Event created: {event.get('htmlLink')}")

    except HttpError as error:
        print(f"An error occurred: {error}")
        st.error(f"An error occurred: {error}")


if __name__ == "__main__":
    # Set up the Streamlit app
    st.title("📸🗓️ AutoCal")

    # Add a file uploader for images
    uploaded_files = st.file_uploader("Choose a file", accept_multiple_files=True)

    if len(uploaded_files) == 0:
        st.error("Please upload at least one file.")
        st.stop()

    uploaded_file = uploaded_files[0]

    # Reset the file pointer before opening with Pillow
    uploaded_file.seek(0)
    image = Image.open(uploaded_file)
    st.image(image, caption="Uploaded Image.", use_container_width=True)

    # Reset the file pointer before uploading to GCS
    uploaded_file.seek(0)
    GCS_URL = upload_blob(uploaded_file.name, uploaded_file)

    # Button to trigger analysis
    submit = st.button("Add to Calendar")

    if submit and GCS_URL:
        print(GCS_URL)
        response = client.models.generate_content(
            model=MODEL_ID,
            # pylint: disable=unexpected-keyword-arg,no-value-for-parameter
            contents=[
                Part.from_uri(file_uri=str(GCS_URL), mime_type="image/jpeg"),
                PROMPT,
            ],
            config=GenerateContentConfig(
                response_mime_type="application/json", response_schema=response_schema
            ),
        )
        st.subheader("Analysis Result:")
        print(f"Raw Gemini Response: {response.text}")
        gemini_response = json.loads(response.text)
        st.write(gemini_response)
        create_calendar_event(gemini_response)
