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
