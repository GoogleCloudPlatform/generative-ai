"""
Main function to run FastAPI server.
"""

import asyncio
import contextlib
import json
import logging
from typing import Dict, List, Any, Optional, Tuple
from contextlib import asynccontextmanager
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


# --- Configuration & Global Setup ---
load_dotenv()

APP_NAME = "ADK MCP App"
MODEL_ID = "gemini-2.0-flash"
STATIC_DIR = "static"

# Initialize services (globally or via dependency injection)
session_service = InMemorySessionService()
artifacts_service = InMemoryArtifactService()


class AllServerConfigs(BaseModel):
    """
    Pydantic model to hold configurations for various StdioServerParameters.

    Attributes:
        configs: A dictionary where keys are server names (e.g., "weather")
                and values are StdioServerParameters instances.
    """

    configs: Dict[str, StdioServerParameters]


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

server_configs_instance = AllServerConfigs(
    configs={
        "weather": weather_server_params,
        "bnb": bnb_server_params,
        "ct": ct_server_params,
    }
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


# --- Tool Collection ---
async def _collect_tools_stack(
    server_config_dict: AllServerConfigs,
) -> Tuple[Dict[str, Any], contextlib.AsyncExitStack]:
    """
    Connects to MCP servers, collects their tools, and returns the tools
    along with an AsyncExitStack to manage their life cycles.

    This function creates an AsyncExitStack. The caller is responsible
    for properly closing this stack (e.g., using `await stack.aclose()`)
    to ensure resources like server connections are cleaned up.

    Args:
        server_config_dict: An AllServerConfigs object containing the
                            configurations for the servers to connect to.

    Returns:
        A tuple containing:
            - all_tools (Dict[str, Any]): A dictionary where keys are server
            identifiers (e.g., "weather") and values are the collected tools
            from that server.
            - exit_stack (contextlib.AsyncExitStack): The AsyncExitStack managing
            the context of the connected MCP tool servers.
    """
    all_tools: Dict[str, Any] = {}
    exit_stack = contextlib.AsyncExitStack()
    stack_needs_closing = False
    try:
        if not hasattr(server_config_dict, "configs") or not isinstance(
            server_config_dict.configs, dict
        ):
            logging.error(
                "server_config_dict does not have a valid '.configs' dictionary."
            )
            return {}, exit_stack
        for key, server_params in server_config_dict.configs.items():
            individual_exit_stack: Optional[contextlib.AsyncExitStack] = None
            try:
                tools, individual_exit_stack = await MCPToolset.from_server(
                    connection_params=server_params
                )
                if individual_exit_stack:
                    await exit_stack.enter_async_context(individual_exit_stack)
                    stack_needs_closing = True
                if tools:
                    all_tools[key] = tools
                else:
                    logging.warning(
                        "Connection successful for key '%s', but no tools returned.",
                        key,
                    )
            except FileNotFoundError as file_error:
                logging.error(
                    "Command or script not found for key '%s': %s", key, file_error
                )
            except ConnectionRefusedError as conn_refused:
                logging.error("Connection refused for key '%s': %s", key, conn_refused)

        if not all_tools:
            logging.warning("No tools were collected from any server.")

        expected_keys = ["weather", "bnb", "ct"]
        for k in expected_keys:
            if k not in all_tools:
                logging.info(
                    "Tools for key '%s' were not collected. Ensuring key exists with empty list.",
                    k,
                )
                all_tools[k] = []
        return all_tools, exit_stack
    except Exception as e:
        logging.error(
            "Unhandled exception in _collect_tools_stack: %s", e, exc_info=True
        )
        if stack_needs_closing:
            await exit_stack.aclose()
        raise


# --- Agent Creation ---
async def create_agent_with_preloaded_tools(
    loaded_mcp_tools: Dict[str, Any],
) -> LlmAgent:
    """
    Creates the root LlmAgent and its sub-agents using pre-loaded MCP tools.

    Args:
        loaded_mcp_tools: A dictionary of tools, typically populated at application
                        startup, where keys are toolset identifiers (e.g., "bnb",
                        "weather", "ct") and values are the corresponding tools.

    Returns:
        An LlmAgent instance representing the root agent, configured with sub-agents.
    """
    booking_tools = loaded_mcp_tools.get("bnb", [])
    weather_tools = loaded_mcp_tools.get("weather", [])
    combined_booking_tools = list(booking_tools)
    combined_booking_tools.extend(weather_tools)
    ct_tools = loaded_mcp_tools.get("ct", [])

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


# --- Agent Execution Helpers ---
async def _run_agent_and_get_response(
    runner: Runner,
    session_id: str,
    content: types.Content,
) -> List[str]:
    """
    Runs the ADK agent asynchronously for a given session and content,
    collecting and returning textual responses from the model.

    Args:
        runner: An instance of the ADK Runner.
        session_id: The unique identifier for the current session.
        content: The user's message/content to send to the agent.

    Returns:
        A list of strings, where each string is a part of the model's response.
    """
    logging.info("Running agent for session %s", session_id)
    events_async = runner.run_async(
        session_id=session_id, user_id=session_id, new_message=content
    )

    response_parts: List[str] = []
    async for event in events_async:
        try:
            if hasattr(event, "content") and event.content.role == "model":
                if hasattr(event.content, "parts") and event.content.parts:
                    part_text = getattr(event.content.parts[0], "text", None)
                    if isinstance(part_text, str) and part_text:
                        response_parts.append(part_text)
        except AttributeError as e:
            logging.warning("Could not process event attribute during agent run: %s", e)
    logging.info("Agent run finished for session %s.", session_id)
    return response_parts


async def _get_runner_async(
    loaded_mcp_tools: Dict[str, Any], session_id: str, query: str
) -> List[str]:
    """
    Sets up and runs the root agent for a given query using preloaded tools.

    This function creates a root agent, initializes a runner, and then
    executes the agent with the user's query, returning the response parts.

    Args:
        loaded_mcp_tools: A dictionary of pre-loaded MCP tools.
        session_id: The unique identifier for the user's session.
        query: The user's input query as a string.

    Returns:
        A list of strings representing the parts of the agent's textual response.
        Returns an error message list if critical services are unavailable.
    """
    content = types.Content(role="user", parts=[types.Part(text=query)])

    if artifacts_service is None or session_service is None:
        logging.error(
            "Artifact or Session service is not initialized for _get_runner_async."
        )
        return ["Error: Core services not available."]

    if not loaded_mcp_tools:
        logging.error("MCP tools are not available for _get_runner_async.")
        return ["Error: Essential tools not loaded, cannot process request."]

    root_agent = await create_agent_with_preloaded_tools(loaded_mcp_tools)
    runner = Runner(
        app_name=APP_NAME,
        agent=root_agent,
        artifact_service=artifacts_service,
        session_service=session_service,
    )
    response = await _run_agent_and_get_response(runner, session_id, content)
    return response


# --- FastAPI Application ---


@asynccontextmanager
async def app_lifespan(app_instance: FastAPI) -> Any:
    """
    Manages application startup and shutdown operations for the FastAPI app.
    Args:
        app_instance: The FastAPI application instance.
    """
    logging.info("Application Lifespan: Startup initiated.")
    app_instance.state.mcp_tools = {}
    app_instance.state.mcp_tool_exit_stack = None

    try:
        collected_tools, tool_stack = await _collect_tools_stack(
            server_configs_instance
        )
        app_instance.state.mcp_tools = collected_tools
        app_instance.state.mcp_tool_exit_stack = tool_stack
        logging.info(
            "Application Lifespan: MCP Toolset initialized. Tools: %s",
            list(app_instance.state.mcp_tools.keys()),
        )
    except FileNotFoundError as file_error:
        logging.error("Command or script not found for key: %s", file_error)
    except ConnectionRefusedError as conn_refused:
        logging.error("Connection refused for key: %s", conn_refused)
    yield

    logging.info("Application Lifespan: Shutdown initiated.")
    if app_instance.state.mcp_tool_exit_stack:
        logging.info("Application Lifespan: Closing MCP Toolset connections.")
        try:
            await app_instance.state.mcp_tool_exit_stack.aclose()
            logging.info(
                "Application Lifespan: MCP Toolset connections closed successfully."
            )
        except ConnectionRefusedError as conn_refused:
            logging.error("Connection refused for key: %s", conn_refused)
    else:
        logging.warning(
            "Application Lifespan: No MCP Toolset exit stack found to close."
        )


# Instantiate FastAPI with the lifespan manager
app = FastAPI(lifespan=app_lifespan)


# --- WebSocket Communication ---
async def run_adk_agent_async(
    websocket: WebSocket, loaded_mcp_tools: Dict[str, Any], session_id: str
) -> None:
    """
    Handles the continuous WebSocket communication loop for a connected client.

    Receives text messages from the client, processes them using the ADK agent
    (via `_get_runner_async`), and sends the agent's responses back to the client.

    Args:
        websocket: The WebSocket connection object for the client.
        loaded_mcp_tools: Pre-loaded MCP tools for the agent.
        session_id: The unique identifier for the client's session.
    """
    try:
        while True:
            text = await websocket.receive_text()
            response_parts = await _get_runner_async(loaded_mcp_tools, session_id, text)

            if not response_parts:
                logging.info(
                    "Agent for session %s did not produce a direct text response for input: '%s'",
                    session_id,
                    text[:50],
                )
                # Consider if a specific message should be sent or just wait for next input.
                # For now, we assume if response_parts is empty, no direct message to user.
                continue

            ai_message = "\n".join(response_parts)
            await websocket.send_text(json.dumps({"message": ai_message}))
            await asyncio.sleep(0)

    except WebSocketDisconnect:
        logging.info("Client %s disconnected from run_adk_agent_async.", session_id)
    finally:
        logging.info("Agent WebSocket task ending for session %s.", session_id)


@app.websocket("/ws/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str) -> None:
    """
    FastAPI WebSocket endpoint for client connections.

    Accepts new WebSocket connections, creates a user session, and starts
    the `run_adk_agent_async` task to handle communication with the ADK agent.
    Ensures that MCP tools are loaded before starting the agent task.

    Args:
        websocket: The WebSocket connection object.
        session_id: The unique session identifier passed in the URL path.
    """
    await websocket.accept()
    logging.info("Client %s connected to WebSocket endpoint.", session_id)
    try:
        session_service.create_session(
            app_name=APP_NAME, user_id=session_id, session_id=session_id, state={}
        )

        # Access tools from app.state (set by the lifespan manager)
        loaded_mcp_tools = websocket.app.state.mcp_tools
        mcp_stack_exists = websocket.app.state.mcp_tool_exit_stack is not None

        if not loaded_mcp_tools or not mcp_stack_exists:
            logging.error(
                "MCP Tools not properly initialized. Cannot serve requests for session %s.",
                session_id,
            )
            await websocket.send_text(
                json.dumps(
                    {
                        "message": "Error: Server is not fully initialized. Please try again later."
                    }
                )
            )
            await websocket.close(code=1011)
            return

        await run_adk_agent_async(websocket, loaded_mcp_tools, session_id)

    except WebSocketDisconnect:
        logging.info(
            "Client %s disconnected from websocket_endpoint (early).", session_id
        )
    finally:
        logging.info("WebSocket endpoint cleanup for session %s.", session_id)


# Mount static files (e.g., for a web UI)
app.mount("/", StaticFiles(directory=STATIC_DIR, html=True), name="static")
