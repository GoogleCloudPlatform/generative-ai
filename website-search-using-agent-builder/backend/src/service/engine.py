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

"""Service for interacting with Google Cloud Discovery Engine Engines."""

from typing import List
from google.cloud.discoveryengine_v1 import (
    EngineServiceClient,
    ListEnginesRequest,
)
from google.api_core.client_options import ClientOptions

from src.model.search import PROJECT_ID, Engine

LOCATIONS = [
    "global",
    "us",
]


class EngineService:
    """Provides methods to list Discovery Engine Engines."""

    def get_all(self) -> List[Engine]:
        """
        Retrieves all available Discovery Engines for the configured project
        across specified locations.

        Fetches engines from predefined locations ('global', 'us') within the
        default collection.

        Returns:
            A list of Engine objects, each containing details about a
            discovered engine. Returns an empty list if no engines are found
            or if an error occurs during API calls.

        Raises:
            Prints error logs if API calls fail for a specific location.
        """
        engines = []
        for location in LOCATIONS:
            client_options = (
                ClientOptions(
                    api_endpoint=f"{location}-discoveryengine.googleapis.com"
                )
                if location != "global"
                else None
            )

            # Create a client
            client = EngineServiceClient(client_options=client_options)
            list_engines = client.list_engines(
                ListEnginesRequest(
                    parent=f"projects/{PROJECT_ID}/locations/{location}"
                    "/collections/default_collection"
                )
            )
            for engine in list_engines.engines:
                engines.append(
                    Engine(
                        name=engine.display_name,
                        engine_id=engine.name.split("/")[-1],
                        region=location,
                    )
                )
        return engines
