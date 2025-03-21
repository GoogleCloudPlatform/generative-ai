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

from cloudevents.http import CloudEvent
import functions_framework
import json
from google.events.cloud import firestore
from google import genai
from google.genai.types import (
    GenerateContentConfig,
    Part,
)
import google.cloud.firestore
import datetime

# Initialize the Gemini model
MODEL_ID = "gemini-2.0-flash-001"
LOCATION = "europe-west1"
client = genai.Client(vertexai=True, location=LOCATION)

# Initialize Firestore client
db = google.cloud.firestore.Client()

# Define the response schema for the analysis
response_schema = {
  "type": "OBJECT",
  "properties": {
    "summary": {
      "type": "STRING"
    },
    "location": {
      "type": "STRING"
    },
    "description": {
      "type": "STRING"
    },
    "start": {
      "type": "STRING"
    },
    "end": {
      "type": "STRING"
    }
  },
  "required": [
    "summary",
    "description",
    "start",
    "end"
  ]
}

# Define the prompt for the analysis
prompt_template = """ The current date and time is: {current_datetime}. 

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
    """Triggers by a change to a Firestore document.

    Args:
        cloud_event: cloud event with information on the firestore event trigger
    """
    firestore_payload = firestore.DocumentEventData()
    firestore_payload._pb.ParseFromString(cloud_event.data)


    print(f"Function triggered by change to: {cloud_event['source']}")

    print("\nNew  value:")
    print(firestore_payload.value)
    gcs_url = firestore_payload.value.fields.get("image").string_value
    mime_type = firestore_payload.value.fields.get("type").string_value
    document_id = firestore_payload.value.fields.get("ID").string_value

    # Get the current date and time
    current_datetime = datetime.datetime.now().isoformat()

    # Format the prompt with the current date and time
    prompt = prompt_template.format(current_datetime=current_datetime)

    response = client.models.generate_content(
        model=MODEL_ID,
        contents=[
            Part.from_uri(
                file_uri=gcs_url,
                mime_type=mime_type
            ),
            prompt,
        ],
        config=GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_schema
        ),
    )

    print(f"Raw Gemini Response: {response.text}")
    event_data = json.loads(response.text)
    print(event_data)

    # firestore document
    firestore_document = {"processed": True,
                          "event": event_data}

    # Write the event data to Firestore
    try:
        doc_ref = db.collection("state").document(document_id) # Use cloud event ID to make document unique
        doc_ref.set(firestore_document, merge=True)
        print(f"Successfully wrote data to Firestore document: {document_id}")
    except Exception as e:
        print(f"Error writing to Firestore: {e}")