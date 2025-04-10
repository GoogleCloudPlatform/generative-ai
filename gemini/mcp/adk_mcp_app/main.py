import os
import json
import asyncio
import logging
from pathlib import Path
from dotenv import load_dotenv
from google.adk.runners import Runner
from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
)
from google.adk.agents.llm_agent import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService

load_dotenv()

APP_NAME = "ADK MCP example"
session_service = InMemorySessionService()
artifacts_service = InMemoryArtifactService()


async def get_tools_async(server_params):
    """Gets tools from MCP Server."""
    tools, exit_stack = await MCPToolset.from_server(connection_params=server_params)
    # MCP requires maintaining a connection to the local MCP Server.
    # Using exit_stack to clean up server connection before exit.
    return tools, exit_stack


async def get_agent_async(server_params):
    """Creates an ADK Agent with tools from MCP Server."""
    tools, exit_stack = await get_tools_async(server_params)
    root_agent = LlmAgent(
        model="gemini-2.5-pro-preview-03-25",
        name="ai_assistant",
        instruction="You're a helpful assistant. Use tools to get information to answer user questions, please format your answer in markdown format.",
        tools=tools,
    )
    return root_agent, exit_stack

ct_server_params = StdioServerParameters(
    command="python",
    args=["./mcp_server/cocktail.py"],
)


async def run_agent(server_params, session_id, question):
    query = question
    print("[user]: ", query)
    content = types.Content(role="user", parts=[types.Part(text=query)])
    root_agent, exit_stack = await get_agent_async(server_params)
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        artifact_service=artifacts_service,
        session_service=session_service,
    )
    events_async = runner.run_async(
        session_id=session_id, user_id=session_id, new_message=content
    )

    response = []
    async for event in events_async:
        if event.content.role == "model" and event.content.parts[0].text:
            print("[agent]:", event.content.parts[0].text)
            response.append(event.content.parts[0].text)

    await exit_stack.aclose()
    return response


async def run_adk_agent_async(websocket, server_params, session_id):
    """Client to agent communication"""
    try:
        # Your existing setup for the agent might be here
        logging.info(f"Agent task started for session {session_id}")
        while True:
            text = await websocket.receive_text()
            response = await run_agent(server_params, session_id, text)
            if not response:
                continue
            # Send the text to the client
            ai_message = "\n".join(response)
            await websocket.send_text(json.dumps({"message": ai_message}))
            await asyncio.sleep(0)
            
    except WebSocketDisconnect:
        # This block executes when the client disconnects
        logging.info(f"Client {session_id} disconnected.")
    except Exception as e:
        # Catch other potential errors in your agent logic
        logging.error(f"Error in agent task for session {session_id}: {e}", exc_info=True)
    finally:
        logging.info(f"Agent task ending for session {session_id}")
       
# FastAPI web app

app = FastAPI()

STATIC_DIR = Path("static")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
async def root():
    """Serves the index.html"""
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: int):
    """Client websocket endpoint"""

    # Wait for client connection
    await websocket.accept()
    print(f"Client #{session_id} connected")

    # Start agent session
    session_id = str(session_id)
    session = session_service.create_session(
        app_name=APP_NAME, user_id=session_id, session_id=session_id, state={}
    )

    # Start tasks
    agent_task = asyncio.create_task(
        run_adk_agent_async(websocket, ct_server_params, session_id)
    )

    await asyncio.gather(agent_task)

    # Disconnected
    print(f"Client #{session_id} disconnected")
