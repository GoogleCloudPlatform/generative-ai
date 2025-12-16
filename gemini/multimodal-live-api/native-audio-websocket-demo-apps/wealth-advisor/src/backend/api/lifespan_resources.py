# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import os

from pathlib import Path
from typing import TYPE_CHECKING

from backend.app_agents.agent import create_root_agent
from backend.app_logging import setup_gcp_logging
from backend.app_prompts import Prompt
from backend.app_settings import get_application_settings
from fastapi.concurrency import asynccontextmanager
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.sessions.in_memory_session_service import InMemorySessionService

if TYPE_CHECKING:
    from fastapi import FastAPI


@asynccontextmanager
async def lifespan(app: "FastAPI"):
    """
    https://fastapi.tiangolo.com/advanced/events/#lifespan
    Application Lifespan: Logic that should be executed before the application starts up.
    """

    ###################
    # BEFORE START UP #
    ###################

    app_settings = get_application_settings()

    setup_gcp_logging(log_level=app_settings.log_level, use_json_logging=app_settings.use_json_logging)

    # Set GenAI/Vertex AI Environment Variables from Settings
    os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = str(app_settings.google_cloud.use_vertex_ai)
    if app_settings.google_cloud.project_id:
        os.environ["GOOGLE_CLOUD_PROJECT"] = app_settings.google_cloud.project_id
    os.environ["GOOGLE_CLOUD_LOCATION"] = app_settings.google_cloud.location

    app.state.app_settings = app_settings

    # Session Service: Default to In-Memory, but prepare for Redis
    # if app_settings.redis_url:
    #     logger.info("Using Redis Session Service")
    #     app.state.session_service = RedisSessionService(app_settings.redis_url)
    # else:
    app.state.session_service = InMemorySessionService()

    app.state.artifact_service = InMemoryArtifactService()

    root_agent_prompt = Prompt(
        prompt_name="root-agent-prompt",
        prompt_dir=Path(__file__).parent.parent / "app_prompts",
    ).prompt_financial_planning_v2_0

    # Initialize Root Agent
    root_agent = create_root_agent(prompt=root_agent_prompt)
    app.state.root_agent = root_agent

    yield

    ###############################
    # EXECUTE DURING APP SHUTDOWN #
    ###############################
