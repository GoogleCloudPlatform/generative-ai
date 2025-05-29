"""
Main function to run FastAPI server.
"""

import json
import logging
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


# --- Configuration & Global Setup ---
load_dotenv()

APP_NAME = "ADK MCP App"
MODEL_ID = "gemini-2.0-flash"
STATIC_DIR = "static"

# Initialize services (globally or via dependency injection)
session_service = InMemorySessionService()
artifacts_service = InMemoryArtifactService()

# --- Server Parameter Definitions ---
weather_server_params = StdioServerParameters(
    command="python",
    args=["./mcp_server/weather_server.py"],
)
ct_server_params = StdioServerParameters(
    command="python",
    args=["./mcp_server/cocktail.py"],
)
bnb_server_params = StdioServerParameters(
    command="npx", args=["-y", "@openbnb/mcp-server-airbnb", "--ignore-robots-txt"]
)


# --- Agent Instructions ---
ROOT_AGENT_INSTRUCTION = """
**Role:** You are a Virtual Assistant acting as a Request Router. You can help user with questions regarding cocktails, weather, and booking accommodations.
**Primary Goal:** Analyze user requests and route them to the correct specialist sub-agent.
**Capabilities & Routing:**
* **Greetings:** If the user greets you, respond warmly and directly.
* **Cocktails:** Route requests about cocktails, drinks, recipes, or ingredients to `cocktail_assistant`.
* **Booking & Weather:** Route requests about booking accommodations (any type) or checking weather to `booking_assistant`.
* **Out-of-Scope:** If the request is unrelated (e.g., general knowledge, math), state directly that you cannot assist with that topic.
**Key Directives:**
* **Delegate Immediately:** Once a suitable sub-agent is identified, route the request without asking permission.
* **Do Not Answer Delegated Topics:** You must **not** attempt to answer questions related to cocktails, booking, or weather yourself. Always delegate.
* **Formatting:** Format your final response to the user using Markdown for readability.
"""


# --- Agent Creation ---
async def create_agent() -> LlmAgent:
    """
    Creates the root LlmAgent and its sub-agents using pre-loaded MCP tools.

    Args:
        loaded_mcp_tools: A dictionary of tools, typically populated at application
                        startup, where keys are toolset identifiers (e.g., "bnb",
                        "weather", "ct") and values are the corresponding tools.

    Returns:
        An LlmAgent instance representing the root agent, configured with sub-agents.
    """
    booking_agent = LlmAgent(
        model=MODEL_ID,
        name="booking_assistant",
        instruction="""Use booking_tools to handle inquiries related to
        booking accommodations (rooms, condos, houses, apartments, town-houses),
        and checking weather information.
        Format your response using Markdown.
        If you don't know how to help, or none of your tools are appropriate for it,
        call the function "agent_exit" hand over the task to other sub agent.""",
        tools=[
            MCPToolset(connection_params=bnb_server_params),
            MCPToolset(connection_params=weather_server_params),
        ],
    )

    cocktail_agent = LlmAgent(
        model=MODEL_ID,
        name="cocktail_assistant",
        instruction="""Use ct_tools to handle all inquiries related to cocktails,
        drink recipes, ingredients,and mixology.
        Format your response using Markdown.
        If you don't know how to help, or none of your tools are appropriate for it,
        call the function "agent_exit" hand over the task to other sub agent.""",
        tools=[MCPToolset(connection_params=ct_server_params)],
    )

    root_agent = LlmAgent(
        model=MODEL_ID,
        name="ai_assistant",
        instruction=ROOT_AGENT_INSTRUCTION,
        sub_agents=[cocktail_agent, booking_agent],
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
    root_agent = await create_agent()
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
    except Exception as e:
        # Catch other potential errors in your agent logic
        logging.error(f"Error in agent session for {session_id}: {e}", exc_info=True)
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
    except Exception as e:
        # Catch any other unexpected error
        logging.error(
            f"!!! EXCEPTION in websocket_endpoint for session {session_id}: {e}",
            exc_info=True,
        )
        if not websocket.client_state == websocket.client_state.DISCONNECTED:
            await websocket.close(code=1011)  # Internal Error
    finally:
        logging.info(f"WebSocket endpoint for session {session_id} is concluding.")


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
