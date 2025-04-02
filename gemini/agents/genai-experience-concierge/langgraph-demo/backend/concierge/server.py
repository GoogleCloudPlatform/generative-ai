# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""FastAPI server for hosting LangGraph agents."""

import contextlib
from typing import AsyncGenerator

from concierge import settings
from concierge.agents import (
    function_calling,
    gemini,
    guardrails,
    semantic_router,
    task_planner,
)
from concierge.langgraph_server import fastapi_app
import fastapi

# Build compiled LangGraph agents with optional checkpointer based on config

runtime_settings = settings.RuntimeSettings()
gemini_agent = gemini.load_agent(runtime_settings=runtime_settings)
guardrails_agent = guardrails.load_agent(runtime_settings=runtime_settings)
function_calling_agent = function_calling.load_agent(runtime_settings=runtime_settings)
semantic_router_agent = semantic_router.load_agent(runtime_settings=runtime_settings)
task_planner_agent = task_planner.load_agent(runtime_settings=runtime_settings)

# setup each agent during server startup


@contextlib.asynccontextmanager
async def lifespan(_app: fastapi.FastAPI) -> AsyncGenerator[None, None]:
    """Setup each agent during server startup."""

    await gemini_agent.setup()
    await guardrails_agent.setup()
    await function_calling_agent.setup()
    await semantic_router_agent.setup()
    await task_planner_agent.setup()

    yield


app = fastapi.FastAPI(lifespan=lifespan)


@app.get("/")
async def root() -> int:
    """Root endpoint."""
    return 200


@app.get("/health")
async def health() -> int:
    """Health endpoint."""
    return 200


# register agent routers

app.include_router(
    router=fastapi_app.build_agent_router(
        agent=gemini_agent,
        router=fastapi.APIRouter(
            prefix="/gemini",
            tags=["Gemini Chat"],
        ),
    ),
)

app.include_router(
    router=fastapi_app.build_agent_router(
        agent=guardrails_agent,
        router=fastapi.APIRouter(
            prefix="/gemini-with-guardrails",
            tags=["Gemini with Guardrails"],
        ),
    ),
)

app.include_router(
    router=fastapi_app.build_agent_router(
        agent=function_calling_agent,
        router=fastapi.APIRouter(
            prefix="/function-calling",
            tags=["Function Calling"],
        ),
    ),
)

app.include_router(
    router=fastapi_app.build_agent_router(
        agent=semantic_router_agent,
        router=fastapi.APIRouter(
            prefix="/semantic-router",
            tags=["Semantic Router"],
        ),
    ),
)

app.include_router(
    router=fastapi_app.build_agent_router(
        agent=task_planner_agent,
        router=fastapi.APIRouter(
            prefix="/task-planner",
            tags=["Task Planner"],
        ),
    ),
)
