# Copyright 2026 Google LLC
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

import google.auth
import google.auth.transport.requests

class AuthService:
    def __init__(self):
        # Initialize Google auth with cloud-platform scopes
        self.scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        self.credentials, self.project_id = google.auth.default(scopes=self.scopes)

    def get_token(self) -> str:
        """
        Retrieves a refreshed access token using Application Default Credentials (ADC).
        """
        if not self.credentials.valid:
            auth_request = google.auth.transport.requests.Request()
            self.credentials.refresh(auth_request)
        return self.credentials.token
