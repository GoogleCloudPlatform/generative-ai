import json
import asyncio
import logging
from pathlib import Path
import contextlib
from dotenv import load_dotenv
from google.adk.runners import Runner
from fastapi import FastAPI, WebSocket
from starlette.websockets import WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from google.adk.tools.mcp_tool.mcp_toolset import (
    MCPToolset,
    StdioServerParameters,
)
from google.adk.agents.llm_agent import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.genai import types
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from pydantic import BaseModel
from typing import Dict


class AllServerConfigs(BaseModel):
    configs: Dict[str, StdioServerParameters]


load_dotenv()

APP_NAME = "ADK MCP App"
STATIC_DIR = Path("static")

session_service = InMemorySessionService()
artifacts_service = InMemoryArtifactService()

# Create server parameters for stdio connection
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

server_config_dict = {
    "weather": weather_server_params,
    "bnb": bnb_server_params,
    "ct": ct_server_params,
}

MODEL_ID = "gemini-2.0-flash"

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


async def run_multi_agent(
    server_config_dict: AllServerConfigs, session_id: str, query: str
):

    logging.info("[user]: ", query)
    content = types.Content(role="user", parts=[types.Part(text=query)])

    all_tools = {}
    # Use a single ExitStack in the main task
    async with contextlib.AsyncExitStack() as stack:  # Master stack
        # logging.info("Setting up MCP connections sequentially...")
        for key, value in server_config_dict.items():
            server_params = value
            individual_exit_stack = (
                None  # Define outside try for broader scope if needed
            )
            try:
                # 1. AWAIT the call to run the function and get its results
                # logging.info(f"  Attempting connection for {server_params}...")
                tools, individual_exit_stack = await MCPToolset.from_server(
                    connection_params=server_params
                )

                # 2. Check if an exit stack was actually returned
                if individual_exit_stack is None:
                    logging.info(
                        f"  Warning: No exit stack returned for {server_params}. Cannot manage cleanup."
                    )

                # 3. Enter the *returned* individual_exit_stack into the master stack
                #    This makes the master stack responsible for cleaning it up later.
                # logging.info(f"  Registering cleanup stack for {server_params}...")
                await stack.enter_async_context(individual_exit_stack)

                # 4. Add the tools
                # logging.info(f"  Connection established for {server_params}, got tools.")
                # Check if tools is None or empty if connection might partially fail
                if tools:
                    all_tools.update({key: tools})
                else:
                    logging.info(
                        f"  Warning: Connection successful but no tools returned for {server_params}."
                    )

            except Exception as e:
                # Catch other errors during the MCPToolset.from_server call itself
                logging.error(f"Error setting up connection for {server_params}: {e}")
                # Optionally re-raise if errors are critical: raise

        # logging.info(f"Finished setup. Collected {len(all_tools)} servers.")

        # --- Agent Creation and Run (remains the same) ---
        if not all_tools:
            logging.info(
                "Warning: No tools were collected. Agent may not function as expected."
            )
            # set tools to empty lists
            all_tools = {" weather": [], "bnb": [], "ct": []}

        booking_tools = all_tools["bnb"]
        booking_tools.extend(all_tools["weather"])

        ct_tools = all_tools["ct"]

        booking_agent = LlmAgent(
            model=MODEL_ID,
            name="booking_assistant",
            instruction="Use booking_tools to handle inquiries related to booking accommodations (rooms, condos, houses, apartments, town-houses), and checking weather information. Format your response using Markdown",
            tools=booking_tools,
        )

        cocktail_agent = LlmAgent(
            model=MODEL_ID,
            name="cocktail_assistant",
            instruction="Use ct_tools to handle all inquiries related to cocktails, drink recipes, ingredients, and mixology. Format your response using Markdown",
            tools=ct_tools,
        )

        root_agent = LlmAgent(
            model=MODEL_ID,
            name="ai_assistant",
            instruction=ROOT_AGENT_INSTRUCTION,
            sub_agents=[cocktail_agent, booking_agent],
        )

        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            artifact_service=artifacts_service,
            session_service=session_service,
        )

        logging.info("Running agent...")
        events_async = runner.run_async(
            session_id=session_id, user_id=session_id, new_message=content
        )

        response = []
        async for event in events_async:
            # Your event processing logic...
            # if event.content.role == "user" and event.content.parts[0].text:
            #     logging.info("[user]:", event.content.parts[0].text)
            # if event.content.parts[0].function_response:
            #     logging.info("[-tool_response-]", event.content.parts[0].function_response)
            if event.content.role == "model" and event.content.parts[0].text:
                logging.info("[agent]:", event.content.parts[0].text)
                response.append(event.content.parts[0].text)

        # logging.info("Agent run finished. Exiting context stack...")
        # Master stack cleanup happens automatically here
        return response  # Or other appropriate return value


async def run_adk_agent_async(
    websocket: WebSocket, server_config_dict, session_id: str
):
    """Handles client-to-agent communication over WebSocket."""
    try:
        # Your existing setup for the agent might be here
        # logging.info(f"Agent task started for session {session_id}")
        while True:
            text = await websocket.receive_text()
            response = await run_multi_agent(server_config_dict, session_id, text)
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
        logging.error(
            f"Error in agent task for session {session_id}: {e}", exc_info=True
        )
    finally:
        logging.info(f"Agent task ending for session {session_id}")


# FastAPI web app

app = FastAPI()
STATIC_DIR = "static"  # Or your directory name


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, session_id: str
):  # Use str for session_id
    """Client websocket endpoint"""
    try:
        await websocket.accept()
        # logging.info(f"Client #{session_id} connected")

        # Start agent session
        session_service.create_session(
            app_name=APP_NAME, user_id=session_id, session_id=session_id, state={}
        )
        # Start agent communication task
        agent_task = asyncio.create_task(
            run_adk_agent_async(websocket, server_config_dict, session_id)
        )
        # Keep the endpoint alive while the agent task runs.
        await agent_task

    except Exception as e:
        # Catch any other unexpected error
        logging.error(
            f"!!! EXCEPTION in websocket_endpoint for session {session_id}: {e}",
            exc_info=True,
        )


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
