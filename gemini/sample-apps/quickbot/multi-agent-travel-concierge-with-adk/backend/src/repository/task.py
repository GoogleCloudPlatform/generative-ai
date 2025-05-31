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

from google.cloud.tasks_v2 import CloudTasksClient, HttpMethod
import google.auth
from src.model.event import IntentCreateEvent
from json import dumps
from os import getenv

LOCATION="us-central1"
INTENT_CREATION_QUEUE=getenv("TASK_QUEUE_NAME")
URL=getenv("FUNCTION_URL", "")

def get_project_id():
    try:
        _, project_id = google.auth.default()
        return project_id
    except google.auth.exceptions.DefaultCredentialsError as e:
        print(f"Error: {e}")
        return None

class TaskRepository():

    def __init__(self):
        self.client = CloudTasksClient()
    
    def create(self, event: IntentCreateEvent):
        # Construct the fully qualified queue name.
        project_id = get_project_id()
        parent = self.client.queue_path(project_id, LOCATION, INTENT_CREATION_QUEUE)

        task = {
            "http_request": {
                "http_method": HttpMethod.POST,
                "url": URL,
                "headers": {"Content-type": "application/json"},
            }
        }
        
        converted_payload = dumps(event.to_dict()).encode()
        task["http_request"]["body"] = converted_payload
        response = self.client.create_task(request={"parent": parent, "task": task})

        print("Created task {}".format(response.name))
        return response
