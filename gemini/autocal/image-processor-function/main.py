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
Async Google Cloud Run function that is triggered through Eventarc by a
document written in the `screenshots` Firestore collection.

The schema of the `screenshots` collection is:

{
  image: string; // Path to original screenshot in GCS
  ID: string; // UUID for this transaction
  type: string; // MIME type (e.g., image/png)
  timestamp?: Date; // Date/time of image upload
}

Upon receiving an event, the image pointed to by the `image` field is processed
through Gemini and the resulting calendar entry is written to the `state`
collection with the following schema:

{
  processed: boolean; // Whether the image has been processed
  error: boolean; // Whether there's been an error
  active: boolean; // Whether the screenshot is active in the UI
  image?: string; // Path to original screenshot in GCS
  ID?: string; // UUID for this transaction
  message?: string; // Any messages (e.g., an error message)
  event?: CalendarEvent; // The main fields of a calendar event
  timestamp?: Date; // Date/time of last event update
}
"""

import datetime
import json
import os

from cloudevents.http import CloudEvent
import functions_framework
from google import genai
from google.api_core.exceptions import (
    GoogleAPICallError,
    InvalidArgument,
    NotFound,
    PermissionDenied,
    ResourceExhausted,
)

# from google.protobuf.json_format import MessageToDict
import google.cloud.firestore
from google.events.cloud import firestore as firestoredata
from google.genai.types import GenerateContentConfig, Part

# Initialize the Gemini model
MODEL_ID = os.environ.get("MODEL_ID", "gemini-2.0-flash-001")
LOCATION = os.environ.get("LOCATION", "europe-west1")

client = genai.Client(vertexai=True, location=LOCATION)

# Initialize Firestore client
db = google.cloud.firestore.Client()

# Define the response schema for the analysis
response_schema = {
    "type": "OBJECT",
    "properties": {
        "summary": {"type": "STRING"},
        "location": {"type": "STRING"},
        "description": {"type": "STRING"},
        "start": {"type": "STRING"},
        "end": {"type": "STRING"},
    },
    "required": ["summary", "description", "start", "end"],
}

# Define the prompt for the analysis
PROMPT_TEMPLATE = """ The current date and time is: {current_datetime}.

Analyze the provided screenshot and extract the following information:

summary: A brief summary of the event.
location: The location of the event.
start time: The start date and time of the event in YYYY-MM-DDTHH:MM:SS format. Assume the event starts in the future.
end time: The end date and time of the event in YYYY-MM-DDTHH:MM:SS format. Calculate this using the duration, if no duration is mentioned, assume the event is an hour long.
Ensure the start and end objects include the correct timeZone based on the information in the screenshot.
duration: The duration of the event in minutes. This could be also written as mins.Use this to calculate the end time if provided.
Ensure the start and end objects include the correct timeZone based on the information in the screenshot.
description: A short description of the event.

The response should have the following schema:

{{
    "type": "OBJECT",
    "properties": {{
        "summary": {{"type": "STRING"}},
        "location": {{"type": "STRING"}},
        "description": {{"type": "STRING"}},
        "start": {{"type": "STRING"}},
        "end": {{"type": "STRING"}}
    }}
}}

"""


@functions_framework.cloud_event
def image_processor(cloud_event: CloudEvent) -> None:
    """Triggered by a change to a Firestore document.

    Args:
        cloud_event: cloud event with information on the firestore event trigger
    """
    firestore_payload = firestoredata.DocumentEventData()
    # Not sure how to parse the protobuf without using this protected method
    # pylint: disable=protected-access
    firestore_payload._pb.ParseFromString(cloud_event.data)

    print(f"Function triggered by change to: {cloud_event['source']}")

    # Again, not sure how to do this without accessing the fields directly
    # pylint: disable=no-member
    gcs_url = firestore_payload.value.fields.get("image").string_value
    mime_type = firestore_payload.value.fields.get("type").string_value
    document_id = firestore_payload.value.fields.get("ID").string_value

    if not all([gcs_url, mime_type, document_id]):
        print(f"Missing required fields in document: {cloud_event.data}")
        return

    # Get the current date and time
    current_datetime = datetime.datetime.now().isoformat()

    # Format the prompt with the current date and time
    prompt = PROMPT_TEMPLATE.format(current_datetime=current_datetime)
    try:
        response = client.models.generate_content(
            model=MODEL_ID,
            contents=[
                Part.from_uri(file_uri=gcs_url, mime_type=mime_type),
                prompt,
            ],
            config=GenerateContentConfig(
                response_mime_type="application/json", response_schema=response_schema
            ),
        )
    except (InvalidArgument, PermissionDenied, NotFound, ResourceExhausted) as e:
        # Handle Gemini API errors
        print(f"Gemini API error: {e}")
        doc_ref = db.collection("state").document(document_id)
        firestore_document = {"error": True, "message": f"Gemini API error: {e}"}
        doc_ref.set(firestore_document, merge=True)
        raise e
    except ValueError as e:
        # Handle file/URI issues
        print(f"Invalid file URI or MIME type: {e}")
        doc_ref = db.collection("state").document(document_id)
        firestore_document = {
            "error": True,
            "message": f"Invalid file URI or MIME type: {e}",
        }
        doc_ref.set(firestore_document, merge=True)
        raise e
    except GoogleAPICallError as e:
        # Handle other Google API errors
        print(f"General Google API error: {e}")
        doc_ref = db.collection("state").document(document_id)
        firestore_document = {
            "error": True,
            "message": f"General Google API error: {e}",
        }
        doc_ref.set(firestore_document, merge=True)
        raise e
    except Exception as e:
        # Catch any other unexpected errors
        print(f"An unexpected error occurred: {e}")
        doc_ref = db.collection("state").document(document_id)
        firestore_document = {
            "error": True,
            "message": f"An unexpected error occurred: {e}",
        }
        doc_ref.set(firestore_document, merge=True)
        raise e

    print(f"Raw Gemini Response: {response.text}")
    event_data = json.loads(response.text)
    print(event_data)

    # firestore document
    firestore_document = {"processed": True, "event": event_data}

    # Write the event data to Firestore
    try:
        doc_ref = db.collection("state").document(document_id)
        doc_ref.set(firestore_document, merge=True)
        print(f"Successfully wrote data to Firestore document: {document_id}")
    except GoogleAPICallError as e:
        print(f"Error writing to Firestore: {e}")
        return
