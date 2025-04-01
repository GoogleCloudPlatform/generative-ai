# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import contextlib

from concierge import agent_settings as settings
from concierge.agents import (
    function_calling,
    gemini_chat,
    gemini_chat_with_guardrails,
    semantic_router,
    task_planner,
)
from concierge.langgraph_server import fastapi_app, langgraph_agent
import fastapi

# Build compiled LangGraph agents with optional checkpointer based on config

gemini_agent = langgraph_agent.LangGraphAgent(
    state_graph=gemini_chat.load_graph(),
    agent_config=settings.gemini_config,
    checkpointer_config=settings.checkpointer_config,
)

guardrail_agent = langgraph_agent.LangGraphAgent(
    state_graph=gemini_chat_with_guardrails.load_graph(),
    agent_config=settings.guardrail_config,
    checkpointer_config=settings.checkpointer_config,
)

function_calling_agent = langgraph_agent.LangGraphAgent(
    state_graph=function_calling.load_graph(),
    agent_config=settings.fc_config,
    checkpointer_config=settings.checkpointer_config,
)

semantic_router_agent = langgraph_agent.LangGraphAgent(
    state_graph=semantic_router.load_graph(),
    agent_config=settings.router_config,
    checkpointer_config=settings.checkpointer_config,
)

task_planner_agent = langgraph_agent.LangGraphAgent(
    state_graph=task_planner.load_graph(),
    agent_config=settings.planner_config,
    checkpointer_config=settings.checkpointer_config,
)

# setup each agent during server startup


@contextlib.asynccontextmanager
async def lifespan(app: fastapi.FastAPI):
    await gemini_agent.setup()
    await guardrail_agent.setup()
    await function_calling_agent.setup()
    await semantic_router_agent.setup()
    await task_planner_agent.setup()

    yield


app = fastapi.FastAPI(lifespan=lifespan)


@app.get("/")
async def root():
    return 200


@app.get("/health")
async def health():
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
        agent=guardrail_agent,
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
