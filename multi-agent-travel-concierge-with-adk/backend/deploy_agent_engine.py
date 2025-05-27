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

"""Deployment script for Travel Concierge."""

import os

import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp
from google.cloud.storage.bucket import Bucket
# This root_agent comes after cloning the ADK repository by running prepare_code.sh
from travel_concierge.agent import root_agent # type: ignore

def create(env_vars: dict[str, str]) -> None:
    """Creates a new deployment."""
    app = AdkApp(
        agent=root_agent,
        enable_tracing=True,
        env_vars=env_vars,
    )

    remote_agent = agent_engines.create(
        app,
        requirements=[
            "google-adk (==0.5.0)",
            "google-cloud-aiplatform[agent_engines]@git+https://github.com/googleapis/python-aiplatform.git@copybara_738852226",
            "google-genai (>=1.5.0,<2.0.0)",
            "pydantic (>=2.10.6,<3.0.0)",
            "absl-py (>=2.2.1,<3.0.0)",
            "requests (>=2.32.3,<3.0.0)",
        ],
        extra_packages=[
            "./travel_concierge",  # The main package
            "./eval",
        ],
    )
    print(f"Created remote agent: {remote_agent.resource_name}")

    return remote_agent.resource_name


def delete(resource_id: str) -> None:
    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")
    return resource_id


def setup_remote_agent(bucket: Bucket) -> str | None:
    """
    Sets up the Vertex AI Agent Engine deployment using environment variables.

    Retrieves necessary configuration from environment variables, initializes
    Vertex AI, and calls the create function.

    Returns:
        The resource name of the created agent engine, or None if setup fails.
    """
    env_vars = {}

    # Retrieve configuration directly from environment variables
    project_id = os.getenv("_PROJECT_ID")
    location = os.getenv("_REGION")
    # Sample Scenario Path - Default is an empty itinerary
    # This will be loaded upon first user interaction.
    # Uncomment one of the two, or create your own.
    # _ADK_TRAVEL_CONCIERGE_SCENARIO=profiles/itinerary_seattle_example.json
    initial_states_path = os.getenv("_ADK_TRAVEL_CONCIERGE_SCENARIO") if os.getenv("_ADK_TRAVEL_CONCIERGE_SCENARIO") else "eval/itinerary_empty_default.json"
    map_key = os.getenv("_ADK_GOOGLE_PLACES_API_KEY")

    # Populate env_vars dictionary for the AdkApp
    if initial_states_path:
        env_vars["_ADK_TRAVEL_CONCIERGE_SCENARIO"] = initial_states_path
    if map_key:
        env_vars["_ADK_GOOGLE_PLACES_API_KEY"] = map_key

    # --- Validation ---
    missing_vars = []
    if not project_id:
        missing_vars.append("_PROJECT_ID")
    if not location:
        missing_vars.append("_REGION")
    if not initial_states_path:
        missing_vars.append("_ADK_TRAVEL_CONCIERGE_SCENARIO")
    if not map_key:
        missing_vars.append("_ADK_GOOGLE_PLACES_API_KEY")

    if missing_vars:
        print("Error: Missing required environment variables:")
        for var in missing_vars:
            print(f"- {var}")
        return None

    # --- Print confirmation (mask sensitive keys) ---
    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket.name}")
    print(f"INITIAL_STATE: {initial_states_path}")
    print(f"MAP KEY (PARTIAL): {map_key[:5]}...")  # Mask most of the key

    # --- Initialize Vertex AI ---
    try:
        vertexai.init(
            project=project_id,
            location=location,
            staging_bucket=f"gs://{bucket.name}",
        )
        print("Vertex AI initialized successfully.")
    except Exception as e:
        print(f"Error initializing Vertex AI: {e}")
        return None

    # --- Create the deployment ---
    try:
        resource_name = create(env_vars)
        return resource_name
    except Exception as e:
        print(f"Error during agent engine creation: {e}")
        return None  # Indicate failure


if __name__ == "__main__":
    setup_remote_agent()
