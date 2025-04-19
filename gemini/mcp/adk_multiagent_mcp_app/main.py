"""
Main function to run FastAPI server.
"""

import asyncio
import contextlib
import json
import logging
from typing import Dict, List, Any, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.staticfiles import StaticFiles
from google.adk.agents.llm_agent import LlmAgent
from google.adk.artifacts.in_memory_artifact_service import InMemoryArtifactService
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, StdioServerParameters
from google.genai import types
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect


class AllServerConfigs(BaseModel):
    """Define a Pydantic model for server configurations."""

    configs: Dict[str, StdioServerParameters]


load_dotenv()

APP_NAME = "ADK MCP App"

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

server_configs_instance = AllServerConfigs(
    configs={
        "weather": weather_server_params,
        "bnb": bnb_server_params,
        "ct": ct_server_params,
    }
)

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


async def _collect_tools(
    server_config_dict: AllServerConfigs, master_stack: contextlib.AsyncExitStack
) -> Dict[str, Any]:
    """Connects to servers, collects tools, and manages resources.

    Assumes MCPToolset.from_server exists and returns (tools, exit_stack).
    """
    all_tools: Dict[str, Any] = {}
    # Ensure server_config_dict has the expected structure, e.g., a .configs attribute
    if not hasattr(server_config_dict, "configs") or not isinstance(
        server_config_dict.configs, dict
    ):
        logging.error("server_config_dict does not have a valid '.configs' dictionary.")
        return {}  # Return empty if structure is wrong

    for key, server_params in server_config_dict.configs.items():
        individual_exit_stack: Optional[contextlib.AsyncExitStack] = None
        try:
            # *** Assumes MCPToolset is defined and imported ***
            tools, individual_exit_stack = await MCPToolset.from_server(
                connection_params=server_params
            )

            if individual_exit_stack:
                # Enter the individual stack into the master stack for cleanup
                await master_stack.enter_async_context(individual_exit_stack)
            # Removed warning for no stack, as MCPToolset might legitimately not return one

            if tools:
                all_tools[key] = tools  # Use key directly
            else:
                logging.warning("Connection successful,but no tools returned.")

        except FileNotFoundError as file_error:
            logging.error("Command or script not found for %s", file_error)
        except ConnectionRefusedError as conn_refused:
            logging.error("Connection refused for %s", conn_refused)

    # Handle case where no tools were collected at all
    if not all_tools:
        logging.warning(
            "No tools were collected from any server. Agent may not function as expected."
        )
        all_tools = {"weather": [], "bnb": [], "ct": []}

    # Ensure expected keys exist if downstream code requires them
    expected_keys = ["weather", "bnb", "ct"]  # Adjust as needed
    for k in expected_keys:
        if k not in all_tools:
            logging.info(
                "Tools  were not collected. Ensuring key exists with empty list."
            )
            all_tools[k] = []

    return all_tools


# --- Helper Function for Agent Creation ---
def _create_root_agent(all_tools: Dict[str, Any]) -> LlmAgent:
    """Creates the hierarchy of agents based on the collected tools.

    Assumes LlmAgent is defined and imported.
    """

    # Prepare tool lists, defensively accessing keys
    booking_tools = all_tools.get("bnb", [])
    weather_tools = all_tools.get("weather", [])
    # Create a new list to avoid modifying the original list in all_tools if needed elsewhere
    combined_booking_tools = list(booking_tools)
    combined_booking_tools.extend(weather_tools)

    ct_tools = all_tools.get("ct", [])

    # --- Agent Creation ---
    # *** Assumes LlmAgent is defined and imported ***
    booking_agent = LlmAgent(
        model=MODEL_ID,
        name="booking_assistant",
        instruction="""Use booking_tools to handle inquiries related to
        booking accommodations (rooms, condos, houses, apartments, town-houses),
        and checking weather information.
        Format your response using Markdown.
        If you don't know how to help, or none of your tools are appropriate for it,
        call the function "agent_exit" hand over the task to other sub agent.""",
        tools=combined_booking_tools,
    )

    cocktail_agent = LlmAgent(
        model=MODEL_ID,
        name="cocktail_assistant",
        instruction="""Use ct_tools to handle all inquiries related to cocktails,
        drink recipes, ingredients,and mixology.
        Format your response using Markdown.
        If you don't know how to help, or none of your tools are appropriate for it,
        call the function "agent_exit" hand over the task to other sub agent.""",
        tools=ct_tools,
    )

    root_agent = LlmAgent(
        model=MODEL_ID,
        name="ai_assistant",
        instruction=ROOT_AGENT_INSTRUCTION,
        sub_agents=[cocktail_agent, booking_agent],
    )
    return root_agent


# --- Helper Function for Running the Agent and Processing Results ---
async def _run_agent_and_get_response(
    runner: Any,  # Replace Any with imported Runner type
    session_id: str,
    content: types.Content,  # Assuming types.Content is correct
) -> List[str]:
    """Runs the agent asynchronously and collects model responses.

    Assumes Runner is defined and imported, and has run_async method.
    """
    logging.info("Running agent for session %s", session_id)
    # *** Assumes runner is an instance of the imported Runner class ***
    events_async = runner.run_async(
        session_id=session_id, user_id=session_id, new_message=content
    )

    response_parts = []
    async for event in events_async:
        # Refined event processing to be more robust
        try:
            if hasattr(event, "content") and event.content.role == "model":
                if hasattr(event.content, "parts") and event.content.parts:
                    # Check if the part has text before accessing it
                    part_text = getattr(event.content.parts[0], "text", None)
                    if (
                        isinstance(part_text, str) and part_text
                    ):  # Ensure it's a non-empty string
                        response_parts.append(part_text)
        except AttributeError as e:
            logging.warning("Could not process event attribute: %s", e)

    logging.info("Agent run finished.")
    return response_parts


# --- Main Function (Refactored) ---
async def run_multi_agent(
    server_config_dict: AllServerConfigs, session_id: str, query: str
) -> List[str]:
    """
    Runs the multi-agent system by collecting tools, creating agents,
    and processing the query.

    Assumes MCPToolset, LlmAgent, Runner, and necessary configurations/services
    are available in the execution environment.
    """
    content = types.Content(role="user", parts=[types.Part(text=query)])
    response: List[str] = []  # Initialize clearly

    # Ensure necessary services are available (could also be passed as arguments)
    if artifacts_service is None or session_service is None:
        logging.error("Artifact or Session service is not initialized.")
        # Depending on requirements, you might return an error or raise exception
        return ["Error: Services not available."]

    async with contextlib.AsyncExitStack() as stack:  # Master stack
        # 1. Collect tools from all servers
        all_tools = await _collect_tools(server_config_dict, stack)

        # If tool collection fundamentally failed, might return early
        if (
            not all_tools and not server_config_dict.configs
        ):  # Check if configs was empty to begin with
            logging.warning("No server configurations provided.")
            # Return empty or specific message based on requirements
            return ["No servers configured to connect to."]
        if not any(
            all_tools.values()
        ):  # Check if all tool lists are empty after trying
            logging.warning("Tool collection resulted in empty tool lists.")
            # Decide if processing should continue with no tools

        # 2. Create the agent hierarchy
        root_agent = _create_root_agent(all_tools)

        # 3. Set up the runner
        # *** Assumes Runner is defined and imported ***
        runner = Runner(
            app_name=APP_NAME,
            agent=root_agent,
            artifact_service=artifacts_service,
            session_service=session_service,
        )

        # 4. Run the agent and get the response
        response = await _run_agent_and_get_response(runner, session_id, content)

        logging.info("Exiting context stack...")
        # Master stack cleanup happens automatically here

    return response


async def run_adk_agent_async(
    websocket: WebSocket, server_config_dict: AllServerConfigs, session_id: str
) -> None:
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
        logging.info("Client %s disconnected.", session_id)
    finally:
        logging.info("Agent task ending for session")


# FastAPI web app

app = FastAPI()
STATIC_DIR = "static"  # Or your directory name


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(
    websocket: WebSocket, session_id: str
) -> None:  # Use str for session_id
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
            run_adk_agent_async(websocket, server_configs_instance, session_id)
        )
        # Keep the endpoint alive while the agent task runs.
        await agent_task

    except WebSocketDisconnect:
        # This block executes when the client disconnects
        logging.info("Client %s disconnected.", session_id)


app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
