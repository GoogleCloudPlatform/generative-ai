# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=R0801

import json
import os
import time

from locust import HttpUser, between, task


class ChatStreamUser(HttpUser):
    """Simulates a user interacting with the chat stream API."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task
    def chat_stream(self) -> None:
        """Simulates a chat stream interaction."""
        headers = {"Content-Type": "application/json"}
        if os.environ.get("_ID_TOKEN"):
            headers["Authorization"] = f'Bearer {os.environ["_ID_TOKEN"]}'

        data = {
            "input": {
                "messages": [
                    {"type": "human", "content": "Hello, AI!"},
                    {"type": "ai", "content": "Hello!"},
                    {"type": "human", "content": "Who are you?"},
                ],
                "user_id": "test-user",
                "session_id": "test-session",
            }
        }

        start_time = time.time()

        with self.client.post(
            "/stream_events",
            headers=headers,
            json=data,
            catch_response=True,
            name="/stream_events first event",
            stream=True,
        ) as response:
            if response.status_code == 200:
                events = []
                for line in response.iter_lines():
                    if line:
                        events.append(json.loads(line))
                        if events[-1]["event"] == "end":
                            break

                end_time = time.time()
                total_time = end_time - start_time

                if (
                    len(events) > 2
                    and events[0]["event"] == "metadata"
                    and events[-1]["event"] == "end"
                ):
                    response.success()
                    self.environment.events.request.fire(
                        request_type="POST",
                        name="/stream_events end",
                        response_time=total_time * 1000,  # Convert to milliseconds
                        response_length=len(json.dumps(events)),
                        response=response,
                        context={},
                    )
                else:
                    response.failure("Unexpected response structure")
            else:
                response.failure(f"Unexpected status code: {response.status_code}")
