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

"""Provides a repository class for interacting with Google Cloud Tasks.

Handles the creation of tasks in a specified Google Cloud Tasks queue.
It retrieves necessary configuration like queue name, target URL, and project ID
from environment variables and Google Cloud authentication defaults.

Requires the following environment variables to be set:
    - TASK_QUEUE_NAME: The name of the Cloud Tasks queue.
    - FUNCTION_URL: The URL of the HTTP target (e.g., a Cloud Function)
                    that the task will invoke.
"""

from google.cloud.tasks_v2 import CloudTasksClient, HttpMethod
import google.auth
from src.model.event import IntentCreateEvent
from json import dumps
from os import getenv

LOCATION = "us-central1"
INTENT_CREATION_QUEUE = getenv("TASK_QUEUE_NAME")
URL = getenv("FUNCTION_URL")


def get_project_id():
    """Retrieves the default Google Cloud project ID using 
    application default credentials.

    Returns:
        The Google Cloud project ID as a string if found, otherwise None.

    Raises:
        google.auth.exceptions.DefaultCredentialsError: If default credentials
            are not found or configured correctly.
    """
    try:
        _, project_id = google.auth.default()
        return project_id
    except google.auth.exceptions.DefaultCredentialsError as e:
        print(f"Error: {e}")
        return None


class TaskRepository:
    """Repository for managing interactions with Google Cloud Tasks.

    Currently supports creating tasks to trigger intent creation processing.

    Attributes:
        client: An instance of the google.cloud.tasks_v2.CloudTasksClient.
        project_id: The determined Google Cloud project ID.
    """

    def __init__(self):
        """Initializes the TaskRepository.

        Creates a CloudTasksClient instance and retrieves the project ID.

        Raises:
            RuntimeError: If the Google Cloud project ID cannot be determined.
        """
        self.client = CloudTasksClient()

    def create(self, event: IntentCreateEvent):
        """Creates a Cloud Task to handle an IntentCreateEvent.

        Constructs an HTTP task targeting the configured FUNCTION_URL and
        enqueues it in the specified INTENT_CREATION_QUEUE. The event data
        is sent as the JSON body of the POST request.

        Args:
            event: The IntentCreateEvent data to be sent in the task payload.

        Returns:
            The created google.cloud.tasks_v2.types.Task object.

        Raises:
            google.api_core.exceptions.GoogleAPICallError: If there's an issue
                communicating with the Cloud Tasks API (e.g., queue not found,
                permission errors).
            ValueError: If required configuration (queue, URL) is missing.
                        (Raised during __init__)
            RuntimeError: If the project ID could not be determined.
                          (Raised during __init__)
        """
        # Construct the fully qualified queue name.
        project_id = get_project_id()
        parent = self.client.queue_path(
            project_id, LOCATION, INTENT_CREATION_QUEUE
        )

        task = {
            "http_request": {
                "http_method": HttpMethod.POST,
                "url": URL,
                "headers": {"Content-type": "application/json"},
            }
        }

        converted_payload = dumps(event.to_dict()).encode()
        task["http_request"]["body"] = converted_payload
        response = self.client.create_task(
            request={"parent": parent, "task": task}
        )

        print(f"Created task {response.name}")
        return response
