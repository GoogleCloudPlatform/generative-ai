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

import time

from locust import HttpUser, between, task


class DummyUser(HttpUser):
    """Simulates a user for testing purposes."""

    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks

    @task
    def dummy_task(self) -> None:
        """A dummy task that simulates work without making actual requests."""
        # Simulate some processing time
        time.sleep(0.1)

        # Record a successful dummy request
        self.environment.events.request.fire(
            request_type="POST",
            name="dummy_endpoint",
            response_time=100,
            response_length=1024,
            response=None,
            context={},
            exception=None,
        )
