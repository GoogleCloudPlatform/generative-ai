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

from absl import app, flags
from dotenv import load_dotenv
from travel_concierge.agent import root_agent
import vertexai
from vertexai import agent_engines
from vertexai.preview.reasoning_engines import AdkApp

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket.")

flags.DEFINE_string(
    "initial_states_path",
    None,
    "Relative path to the initial state file, .e.g eval/itinerary_empty_default.json",
)
flags.DEFINE_string("map_key", None, "API Key for Google Places API")

flags.DEFINE_string("resource_id", None, "ReasoningEngine resource ID.")
flags.DEFINE_bool("create", False, "Creates a new deployment.")
flags.DEFINE_bool("quicktest", False, "Try a new deployment with one turn.")
flags.DEFINE_bool("delete", False, "Deletes an existing deployment.")
flags.mark_bool_flags_as_mutual_exclusive(["create", "delete", "quicktest"])


def create(env_vars: dict[str, str]) -> None:
    """Creates a new deployment."""
    print(env_vars)
    app = AdkApp(
        agent=root_agent,
        enable_tracing=True,
        env_vars=env_vars,
    )

    remote_agent = agent_engines.create(
        app,
        requirements=[
            "google-adk (>=0.0.2)",
            "google-cloud-aiplatform[agent_engines] @ git+https://github.com/googleapis/python-aiplatform.git@copybara_738852226",
            "google-genai (>=1.5.0,<2.0.0)",
            "pydantic (>=2.10.6,<3.0.0)",
            "absl-py (>=2.2.1,<3.0.0)",
            "pydantic (>=2.10.6,<3.0.0)",
            "requests (>=2.32.3,<3.0.0)",
        ],
        extra_packages=[
            "./travel_concierge",  # The main package
            "./eval",  # The initial state files
        ],
    )
    print(f"Created remote agent: {remote_agent.resource_name}")
    return remote_agent.resource_name


def delete(resource_id: str) -> None:
    remote_agent = agent_engines.get(resource_id)
    remote_agent.delete(force=True)
    print(f"Deleted remote agent: {resource_id}")
    return resource_id


def send_message(resource_id: str, message: str) -> None:
    """Send a message to the deployed agent."""
    remote_agent = agent_engines.get(resource_id)
    session = remote_agent.create_session(
        user_id="traveler0115"
    )  # Optionally can provide initial states: state=initial_state
    print(f"Trying remote agent: {resource_id}")
    for event in remote_agent.stream_query(
        user_id="traveler0115",
        session_id=session["id"],
        message=message,
    ):
        print(event)
    print("Done.")


def setup_remote_agent() -> str:
    load_dotenv()
    env_vars = {}

    project_id = (
        FLAGS.project_id if FLAGS.project_id else os.getenv("GOOGLE_CLOUD_PROJECT")
    )
    location = FLAGS.location if FLAGS.location else os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket = FLAGS.bucket if FLAGS.bucket else os.getenv("GOOGLE_CLOUD_STORAGE_BUCKET")
    # Variables for Travel Concierge from .env
    initial_states_path = (
        FLAGS.initial_states_path
        if FLAGS.initial_states_path
        else os.getenv("TRAVEL_CONCIERGE_SCENARIO")
    )
    env_vars["TRAVEL_CONCIERGE_SCENARIO"] = initial_states_path
    map_key = (
        FLAGS.initial_states_path
        if FLAGS.initial_states_path
        else os.getenv("GOOGLE_PLACES_API_KEY")
    )
    env_vars["GOOGLE_PLACES_API_KEY"] = map_key

    print(f"PROJECT: {project_id}")
    print(f"LOCATION: {location}")
    print(f"BUCKET: {bucket}")
    print(f"INITIAL_STATE: {initial_states_path}")
    print(f"MAP: {map_key[:5]}")

    if not project_id:
        print("Missing required environment variable: GOOGLE_CLOUD_PROJECT")
        return
    elif not location:
        print("Missing required environment variable: GOOGLE_CLOUD_LOCATION")
        return
    elif not bucket:
        print("Missing required environment variable: GOOGLE_CLOUD_STORAGE_BUCKET")
        return
    elif not initial_states_path:
        print("Missing required environment variable: TRAVEL_CONCIERGE_SCENARIO")
        return
    elif not map_key:
        print("Missing required environment variable: GOOGLE_PLACES_API_KEY")
        return

    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=f"gs://{bucket}",
    )

    return create(env_vars)
