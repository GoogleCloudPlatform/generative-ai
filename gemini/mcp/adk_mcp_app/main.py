import json
import logging
from pathlib import Path

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from google.adk.agents import LlmAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types
from starlette.websockets import WebSocketDisconnect

load_dotenv()

APP_NAME = "ADK MCP example"
STATIC_DIR = Path("static")

session_service = InMemorySessionService()
artifacts_service = InMemoryArtifactService()

ct_server_params = StdioServerParameters(
    command="python",
    args=["./mcp_server/cocktail.py"],
)


def create_agent(server_params: StdioServerParameters):
    """Creates an ADK Agent with tools from MCP Server."""
    agent_instruction = """You are Gemini, a helpful and reliable AI assistant. Your main goal is to provide clear, accurate, and well-supported answers.
     - When needed, use your tools to find the most current information to address the user's query.
     - Carefully combine the information you find into a complete answer.
     - If you cannot find the specific information requested using your tools, let the user know.
     - Please format your response using Markdown to make it easy to read and understand.
    """
    root_agent = LlmAgent(
        model="gemini-2.5-flash",
        name="ai_assistant",
        instruction=agent_instruction,
        tools=[MCPToolset(connection_params=server_params)],
    )
    return root_agent


async def process_message_with_runner(runner: Runner, session_id: str, question: str):
    """Processes a single message using the provided runner."""
    content = types.Content(role="user", parts=[types.Part(text=question)])
    events_async = runner.run_async(
        session_id=session_id, user_id=session_id, new_message=content
    )

    response_parts = []
    async for event in events_async:
        if event.content.role == "model" and event.content.parts[0].text:
            print("[agent]:", event.content.parts[0].text)
            response_parts.append(event.content.parts[0].text)

    return response_parts


async def run_adk_agent_session(
    websocket: WebSocket, server_params: StdioServerParameters, session_id: str
):
    """Handles client-to-agent communication over WebSocket for a session."""
    root_agent = create_agent(server_params)
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        artifact_service=artifacts_service,
        session_service=session_service,
    )
    logging.info(f"Agent session started for {session_id} with runner and agent.")

    try:
        while True:
            text = await websocket.receive_text()
            logging.info(f"Received from {session_id}: {text}")
            response_parts = await process_message_with_runner(runner, session_id, text)
            if not response_parts:
                continue
            # Send the text to the client
            ai_message = "\n".join(response_parts)
            logging.info(
                f"Sending to {session_id}: {ai_message[:100]}..."
            )  # Log snippet
            await websocket.send_text(json.dumps({"message": ai_message}))

    except WebSocketDisconnect:
        # This block executes when the client disconnects
        logging.info(f"Client {session_id} disconnected.")
    finally:
        logging.info(f"Closing runner for session {session_id}...")
        await runner.close()
        logging.info(f"Runner closed for session {session_id}. Agent session ending.")


# FastAPI web app

app = FastAPI()

STATIC_DIR = "static"  # Or your directory name


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, session_id: str
):  # Use str for session_id
    """Client websocket endpoint"""
    await websocket.accept()
    logging.info(f"Client #{session_id} connected and WebSocket accepted.")

    try:
        # Start agent session
        # Ensure session is created before starting the agent task
        await session_service.create_session(
            app_name=APP_NAME, user_id=session_id, session_id=session_id, state={}
        )
        logging.info(f"ADK Session created for {session_id}.")

        # Start agent communication task
        await run_adk_agent_session(websocket, ct_server_params, session_id)

    except WebSocketDisconnect:
        # This might be redundant if run_adk_agent_session handles it,
        # but good for logging the endpoint's perspective.
        logging.info(f"WebSocket endpoint for {session_id} detected disconnect.")
    finally:
        logging.info(f"WebSocket endpoint for session {session_id} is concluding.")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
