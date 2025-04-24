"""
Copyright 2025 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    https://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.

"""

import asyncio
import base64
import json
import logging
import os
import re
import shutil
from contextlib import AsyncExitStack
from typing import (
    Any,
    Dict,
    List,  # Added Optional, Union, List, Dict
    Literal,
    Optional,
    Union,
)

# Import necessary MCP components (ensure 'mcp' is installed)
from dotenv import load_dotenv
from google import genai
from google.genai import types

# --- Corrected MCP Client Imports ---
try:
    # Ensure MCP library is installed: pip install mcp
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

except ImportError:
    print("Error: Failed to import MCP client components.")
    print("Please check the documentation for your 'mcp' library version.")
    exit(1)


# Configure logging - Set default level to INFO
# Change to logging.WARNING or logging.ERROR to hide more messages
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# --- Configuration Class ---
class Configuration:
    @staticmethod
    def load_env() -> None:
        load_dotenv()

    @staticmethod
    def load_config(file_path: str) -> dict[str, Any]:
        try:
            with open(file_path, "r") as f:
                return json.load(f)
        except FileNotFoundError as e:
            logging.error(f"Configuration file not found: {file_path}")
            raise
        except json.JSONDecodeError:
            logging.error(f"Invalid JSON in configuration file: {file_path}")
            raise


# --- Server Class (Manages connection to one server process) ---
class Server:
    def __init__(self, name: str, config: dict[str, Any]) -> None:
        self.name: str = name
        self.config: dict[str, Any] = config
        self.stdio_context: Any | None = None
        self.session: ClientSession | None = None
        self._cleanup_lock: asyncio.Lock = asyncio.Lock()
        self.exit_stack: AsyncExitStack = AsyncExitStack()

    async def initialize(self) -> None:
        command = shutil.which("python") or shutil.which("python3")
        if not command:
            raise EnvironmentError(
                "Please ensure Python is installed and available in your system's PATH."
            )
        server_script_path = self.config.get("script_path")
        if not server_script_path:
            raise ValueError(f"Server config for '{self.name}' missing 'script_path'")

        server_params = StdioServerParameters(
            command=command,
            args=[server_script_path],
            env={**os.environ, **self.config.get("env", {})},
        )
        try:
            logging.debug(
                f"Starting server '{self.name}' with command: {command} {server_script_path}"
            )
            stdio_transport = await self.exit_stack.enter_async_context(
                stdio_client(server_params)
            )
            read, write = stdio_transport
            session = await self.exit_stack.enter_async_context(
                ClientSession(read, write)
            )
            await session.initialize()
            self.session = session
            logging.info(f"Server '{self.name}' initialized successfully.")
        except Exception as e:
            logging.error(f"Error initializing server {self.name}: {e}")
            await self.cleanup()
            raise

    async def list_tools(self) -> list["Tool"]:  # <<< MODIFIED TYPE HINT HERE >>>
        """List available tools from the server."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        tools_response = await self.session.list_tools()
        tools = []
        logging.debug(
            f"Raw tools response from server: {tools_response}"
        )  # Added debug log

        for item in tools_response:
            # Assuming the response format is still [("tools", [list_of_tool_spec_objects])]
            if isinstance(item, tuple) and item[0] == "tools":
                tool_spec_list = item[1]
                if not isinstance(tool_spec_list, list):
                    logging.warning(
                        f"Expected a list of tools, but got: {type(tool_spec_list)}"
                    )
                    continue

                for tool_spec in tool_spec_list:
                    # Access attributes directly using dot notation
                    # Use getattr for safety, providing None as default
                    tool_name = getattr(tool_spec, "name", None)
                    tool_desc = getattr(tool_spec, "description", None)
                    # input_schema might be named differently, check common names
                    tool_schema = getattr(
                        tool_spec, "input_schema", getattr(tool_spec, "inputSchema", {})
                    )  # Try both common names

                    if tool_name:  # Only add if we could get a name
                        tools.append(Tool(tool_name, tool_desc, tool_schema))
                    else:
                        logging.warning(
                            f"Could not extract name from tool spec object: {tool_spec}"
                        )

        logging.debug(f"Parsed tools: {[t.name for t in tools]}")  # Added debug log
        return tools

    async def execute_tool(
        self,
        tool_name: str,
        arguments: dict[str, Any],
        retries: int = 1,
        delay: float = 1.0,
    ) -> Any:
        """Execute a tool with retry mechanism."""
        if not self.session:
            raise RuntimeError(f"Server {self.name} not initialized")

        attempt = 0
        last_exception = None
        while attempt < retries + 1:
            try:
                logging.debug(
                    f"Attempt {attempt + 1}: Executing {tool_name} on server {self.name}..."
                )
                result = await self.session.call_tool(tool_name, arguments)
                logging.debug(f"Tool {tool_name} executed successfully.")
                if (
                    isinstance(result, dict)
                    and "progress" in result
                    and "total" in result
                ):
                    progress = result["progress"]
                    total = result["total"]
                    percentage = (progress / total) * 100 if total else 0
                    logging.debug(f"Progress: {progress}/{total} ({percentage:.1f}%)")
                return result

            except Exception as e:
                last_exception = e
                attempt += 1
                logging.warning(
                    f"Error executing tool {tool_name} on server {self.name}: {e}. Attempt {attempt} of {retries + 1}."
                )
                if attempt < retries + 1:
                    logging.debug(f"Retrying in {delay} seconds...")
                    await asyncio.sleep(delay)
                else:
                    logging.error(
                        f"Max retries reached for tool {tool_name}. Failing. Exception: {last_exception}"
                    )
                    raise RuntimeError(
                        f"Tool execution failed after {retries + 1} attempts for tool '{tool_name}'"
                    ) from last_exception

    async def cleanup(self) -> None:
        """Clean up server resources."""
        async with self._cleanup_lock:
            if self.session or self.exit_stack._exit_callbacks:
                logging.debug(f"Cleaning up server {self.name}...")
                try:
                    await self.exit_stack.aclose()
                    self.session = None
                    self.stdio_context = None
                    logging.debug(f"Server {self.name} cleaned up.")
                except Exception as e:
                    logging.error(f"Error during cleanup of server {self.name}: {e}")


# --- Tool Class (Simple local representation) ---
class Tool:
    """Represents a tool listed by the server."""

    def __init__(
        self,
        name: str | None,
        description: str | None,
        input_schema: dict[str, Any] | None,
    ) -> None:
        self.name: str = name or "Unknown Tool"
        self.description: str = description or "No description"
        self.input_schema: dict[str, Any] = input_schema or {}

    def format_for_llm(self) -> str:
        """Format tool information for LLM.

        Returns:
            A formatted string describing the tool.
        """
        args_desc = []
        # Use get with default {} to avoid error if input_schema is None or missing 'properties'
        properties = self.input_schema.get("properties", {})
        required_args = self.input_schema.get("required", [])

        for param_name, param_info in properties.items():
            arg_desc = (
                f"- {param_name}: {param_info.get('description', 'No description')}"
            )
            if param_name in required_args:
                arg_desc += " (required)"
            args_desc.append(arg_desc)

        # Ensure there's always an "Arguments:" line, even if empty
        arguments_section = "Arguments:\n" + (
            "\n".join(args_desc) if args_desc else "  (No arguments defined)"
        )

        return f"""
Tool: {self.name}
Description: {self.description}
{arguments_section}
"""


# --- LLMClient Class (Cleaned) ---
class LLMClient:
    """Manages communication with the LLM provider."""

    def __init__(self, model_name: str, project: str, location: str) -> None:
        self.model_name: str = model_name
        self.project: str = project
        self.location: str = location
        self._client: Optional[genai.Client] = None
        self._chat_session: Optional[genai.ChatSession] = None  # Adjusted type hint
        self._generation_config: Optional[types.GenerationConfig] = None
        self._system_instruction: Optional[str] = None

    def _initialize_client(self):
        """Initializes the Gen AI client if not already done."""
        if not self._client:
            try:
                self._client = genai.Client(
                    vertexai=False,
                    # project=self.project,
                    # location=self.location,
                    api_key=os.getenv(
                        "GOOGLE_API_KEY",
                        "--Missing API Key. Add API key here or in .env file. Use Secret Manager for production.--",
                    ),
                )
                logging.info(
                    f"Gen AI client initialized for project '{self.project}' in '{self.location}'."
                )
            except Exception as e:
                logging.exception("Failed to initialize Gen AI client.")
                raise ConnectionError(
                    "Could not initialize connection to the LLM service."
                ) from e

    def set_generation_config(self, config: types.GenerationConfig) -> None:
        """Sets the generation configuration for subsequent calls."""
        self._generation_config = config
        logging.debug(f"Generation config set: {config}")

    def set_system_instruction(self, system_instruction: str) -> None:
        """Sets the system instruction and initializes the chat session."""
        self._initialize_client()  # Ensure client is ready
        if (
            not self._client
        ):  # Should not happen if _initialize_client works, but belt-and-suspenders
            raise ConnectionError("LLM Client not initialized.")

        try:
            # Create a new chat session with the system instruction
            # Note: Depending on the exact gen ai version, system instructions might be
            # handled differently (e.g., as the first message). This assumes `create`
            # handles it or we send it as the first message implicitly.
            # Let's assume the original pattern of sending it first was intended.
            self._chat_session = self._client.chats.create(model=self.model_name)
            self._chat_session.send_message(system_instruction)
            # Sending the system instruction as the first message
            # Important: Check if the library expects a specific format or role for system instructions
            # If `create` supports `system_instruction=` kwarg, use that instead.
            # For now, mimicking the original code's behavior.
            # A more robust approach would use the library's designated system instruction mechanism if available.
            # self._chat_session.send_message(system_instruction) # Sending it here might consume the first turn
            logging.info(
                "LLM chat session initialized."
            )  # System instruction set is implied

        except Exception as e:
            logging.exception(
                "Failed to create LLM chat session or set system instruction."
            )
            self._chat_session = None  # Ensure session is None on failure
            raise ConnectionError("Could not create LLM chat session.") from e

    @staticmethod
    def extract_tool_call_json(text: str) -> Optional[Dict[str, Any]]:
        """
        Extracts a JSON object formatted for tool calls from markdown code blocks.

        Specifically looks for ```json { "tool": ..., "arguments": ... } ```

        Args:
            text: The input string potentially containing the JSON tool call.

        Returns:
            The loaded Python dictionary representing the tool call, or None if
            extraction/parsing fails or if it's not a valid tool call structure.
        """
        # Regex to find ```json ... ``` block
        # Using non-greedy matching .*? for the content
        match = re.search(r"```json\s*(\{.*?\})\s*```", text, re.DOTALL | re.IGNORECASE)
        json_string = None

        if match:
            json_string = match.group(1).strip()
            logging.debug(f"Extracted JSON string from ```json block:\n{json_string}")
        else:
            # Fallback: If no ```json block, maybe the entire text is the JSON?
            # Be cautious with this, might parse unintended text.
            # Let's only consider it if it looks like a JSON object.
            text_stripped = text.strip()
            if text_stripped.startswith("{") and text_stripped.endswith("}"):
                json_string = text_stripped
                logging.debug(
                    "No ```json block found, attempting to parse entire stripped text as JSON."
                )
            # else: # If it doesn't look like JSON, don't try parsing
            #     logging.debug("No JSON code block found, and text doesn't look like a JSON object.")
            #     return None # Decided against this strict check for now, mimic original more closely

        if not json_string:
            # If after trying both, we have nothing, return None
            # This also catches the case where the original text was empty or whitespace
            if text.strip():  # Only log if there was actual text content
                logging.debug(
                    f"Could not extract a JSON string from the LLM response: >>>{text}<<<"
                )
            return None

        # Load the extracted string into a Python JSON object
        try:
            loaded_json = json.loads(json_string)
            # Validate if it looks like a tool call
            if (
                isinstance(loaded_json, dict)
                and "tool" in loaded_json
                and "arguments" in loaded_json
            ):
                logging.debug(
                    "Successfully parsed JSON and validated tool call structure."
                )
                return loaded_json
            else:
                logging.debug(
                    "Parsed JSON but it does not match expected tool call structure."
                )
                return None  # Not a valid tool call structure
        except json.JSONDecodeError as e:
            logging.warning(
                f"Error decoding JSON: {e}. String was: >>>{json_string}<<<"
            )
            return None
        except Exception as e:  # Catch other potential errors during loading
            logging.error(f"An unexpected error occurred during JSON parsing: {e}")
            return None

    def get_response(self, current_messages: List[Dict[str, str]]) -> str:
        """
        Sends the current conversation history to the LLM and returns the response text.

        Args:
            current_messages: A list of message dictionaries representing the
                                    conversation history (including the latest user message).

        Returns:
            The LLM's raw response text.

        Raises:
            ConnectionError: If the chat session is not initialized or the API call fails.
            Exception: For other potential LLM API errors.
        """
        if not self._chat_session:
            raise ConnectionError(
                "LLM chat session is not initialized. Call set_system_instruction first."
            )
        if not self._client:  # Should be initialized if session exists
            raise ConnectionError("LLM Client not initialized.")

        logging.debug(f"Sending messages to LLM: {current_messages}")
        logging.debug(f"Using generation config: {self._generation_config}")

        try:
            # Construct the messages in the format expected by the API
            # The API might expect a specific structure, e.g., alternating 'user' and 'model' roles.
            # Assuming the current_messages list is already in the correct format.
            # Add the system instruction if it wasn't handled at session creation.
            # Note: The original `set_system_instruction` sent it as the first message implicitly.
            # If the chat history is empty, we might need to send the system instruction first.
            # Let's assume the `ChatSession` class manages history correctly including system prompt logic.

            # Pass generation_config if it's set
            response = self._chat_session.send_message(
                current_messages,  # Pass the whole history
            )

            response_text = response.text
            logging.debug(f"Received raw LLM response: {response_text}")
            return response_text

        except Exception as e:
            logging.exception("Error during LLM API call.")
            # More specific error handling could be added here based on google.genai exceptions
            raise ConnectionError(f"Failed to get response from LLM: {e}") from e


# --- Chat Session (Orchestrates interaction - Cleaned) ---
class ChatSession:
    """Orchestrates the interaction between user and Gemini tools via MCP server."""

    def __init__(self, gemini_server: Server, llm_client: LLMClient) -> None:
        self.gemini_server: Server = gemini_server
        self.llm_client: LLMClient = llm_client
        # Store available tools once fetched
        self.available_tools: List[Tool] = []
        # Store the conversation history
        self.messages: List[
            Dict[str, Any]
        ] = []  # Use Any for content type flexibility (str or dict)
        self.llm_model_name = llm_client.model_name

    async def cleanup_servers(self) -> None:
        """Clean up the Gemini server properly."""
        # Adjusted to only clean the single gemini_server
        if self.gemini_server:
            logging.info(f"Cleaning up server: {self.gemini_server.name}")
            try:
                await self.gemini_server.cleanup()
            except Exception as e:
                logging.warning(
                    f"Warning during server cleanup ({self.gemini_server.name}): {e}"
                )

    async def _prepare_llm(self) -> bool:
        """Initializes the server, lists tools, and sets up the LLM client."""
        try:
            # 1. Initialize the server
            await self.gemini_server.initialize()

            # 2. List available tools
            self.available_tools = await self.gemini_server.list_tools()
            if not self.available_tools:
                logging.warning(
                    f"No tools found on server {self.gemini_server.name}. Interaction will be limited."
                )
                # Decide if you want to proceed without tools or exit
                # return False # Example: Exit if no tools
            else:
                logging.info(
                    f"Available tools: {[tool.name for tool in self.available_tools]}"
                )

            # 3. Format tool descriptions for the system prompt
            tools_description = "\n".join(
                [tool.format_for_llm() for tool in self.available_tools]
            )

            # 4. Define System Instruction
            system_instruction_content = (
                "You are a helpful assistant with access to these tools:\n\n"
                f"{tools_description}\n"
                "Choose the appropriate tool based on the complexity of user's question. "
                "If no tool is needed, reply directly.\n\n"
                "IMPORTANT: When you need to use a tool, you must ONLY respond with "
                "the exact format below, nothing else:\n"
                "{\n"
                '    "tool": "tool-name",\n'
                '    "arguments": {\n'
                '        "argument-name": "value"\n'
                "    }\n"
                "}\n\n"
                "After receiving a tool's response:\n"
                "1. Transform the raw data into a natural, conversational response\n"
                "2. Keep responses concise but informative\n"
                "3. Focus on the most relevant information\n"
                "4. Use appropriate context from the user's question\n"
                "5. Avoid simply repeating the raw data\n\n"
                "6. When the tool is `translate_llm`, it requires the following arguments: `{'text': 'the text to translate', 'source_language': 'source language code (e.g., en, fr)', 'target_language': 'target language code (e.g., fr, en)'}`.\n\n"
                "7. When you used a tool always respond by starting 'As per tool-name': \n\n"
                "Please use only the tools that are explicitly defined above. "
            )
            # Note: Removed the potentially confusing "{response} - {tool used}" format requirement
            # The instructions now clearly state to mention the tool in the final natural response.

            # 5. Define Generation Configuration
            generate_content_config = types.GenerationConfig(
                temperature=0.2,
                top_p=0.8,
                max_output_tokens=1024,
                # response_modalities = ["TEXT"], # Often inferred, might not be needed
                # system_instruction=system_instruction, # Pass via set_system_instruction or initial message
            )

            # 6. Configure LLM Client
            # self.llm_client.set_generation_config(generate_content_config)
            self.llm_client.set_system_instruction(system_instruction_content)

            # 7. Initialize message history (Optional: Add system prompt if API doesn't handle it separately)
            # Some APIs treat the system instruction separately, others expect it in the message list.
            # Since we called set_system_instruction which initializes the chat,
            # we start with an empty message history here for the user/assistant turns.
            # self.messages = []
            # Example if system instruction needs to be first message:
            self.messages = [
                {"role": "system", "content": system_instruction_content}
            ]  # Adjust role if needed ('system'/'user'/'context')

            logging.info("LLM client and system prompt prepared successfully.")
            return True

        except (
            FileNotFoundError,
            json.JSONDecodeError,
            ValueError,
            EnvironmentError,
            ConnectionError,
        ) as e:
            logging.error(f"Initialization failed: {e}")
            return False
        except Exception as e:
            logging.exception("An unexpected error occurred during preparation:")
            return False

    async def _execute_tool_and_get_result(
        self, tool_name: str, arguments: Dict[str, Any]
    ) -> str:
        """Finds the correct server and executes the tool."""
        # Simplified: Assumes the single gemini_server has the tool if listed
        tool_exists = any(tool.name == tool_name for tool in self.available_tools)

        if not tool_exists:
            error_msg = (
                f"Error: Tool '{tool_name}' is not listed as available on the server."
            )
            logging.error(error_msg)
            return error_msg  # Return error message for LLM

        logging.info(f"Executing tool: {tool_name} with arguments: {arguments}")
        try:
            # Use the gemini_server instance directly
            result = await self.gemini_server.execute_tool(tool_name, arguments)

            # Format the result for the LLM. Simple string conversion for now.
            # Could be JSON stringified if the result is complex.
            result_str = (
                json.dumps(result) if isinstance(result, (dict, list)) else str(result)
            )
            logging.info(
                f"Tool '{tool_name}' execution successful. Result: {result_str}"
            )
            return result_str  # Return result string for LLM

        except (RuntimeError, Exception) as e:
            error_msg = f"Error executing tool '{tool_name}': {str(e)}"
            logging.error(error_msg)
            return error_msg  # Return error message for LLM

    async def start(self) -> None:
        """Main chat session handler."""
        # Prepare LLM and tools first
        if not await self._prepare_llm():
            print("Failed to initialize the chat session. Exiting.")
            await self.cleanup_servers()  # Ensure cleanup even on init failure
            return

        print("\nChat session started. Type 'quit' or 'exit' to end.")

        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ["quit", "exit"]:
                    logging.info("\nExiting...")
                    break
                if not user_input:
                    continue

                # 1. Add user message to history
                # Use the role the API expects, usually 'user'
                self.messages.append({"role": "user", "content": user_input})

                # 2. Get LLM response (potential tool call or direct answer)
                llm_raw_response = self.llm_client.get_response(user_input)

                # 3. Attempt to parse the response as a tool call
                parsed_tool_call = self.llm_client.extract_tool_call_json(
                    llm_raw_response
                )

                # 4. Check if it's a tool call
                if parsed_tool_call:
                    # It's a tool call
                    tool_name = parsed_tool_call.get("tool")
                    arguments = parsed_tool_call.get("arguments", {})

                    # Optional: Add the LLM's tool call decision to history
                    # The exact format/role depends on the API (e.g., 'assistant'/'model'/'tool_call')
                    # Using 'assistant' role for the raw response containing the call
                    self.messages.append(
                        {"role": "assistant", "content": llm_raw_response}
                    )

                    # 5. Execute the tool
                    tool_result_content = await self._execute_tool_and_get_result(
                        tool_name, arguments
                    )

                    # 6. Add tool result to history
                    # Use a specific role if the API supports it (e.g., 'tool', 'function'), otherwise use a generic one.
                    # Using 'user' or a custom role like 'tool_result' might work. Let's use 'user' for simplicity here
                    # as if the *system* is providing this info back for the next turn. Adjust if API dictates otherwise.
                    # A dedicated 'tool' role is often preferred in newer APIs.
                    self.messages.append(
                        {
                            "role": "user",
                            "content": f"Tool execution result for {tool_name}: {tool_result_content}",
                        }
                    )  # Providing context

                    # 7. Get the LLM's final response summarizing the tool result
                    logging.debug("Asking LLM to process tool result...")
                    final_response = self.llm_client.get_response(tool_result_content)

                    # 8. Add final assistant response to history
                    self.messages.append(
                        {"role": "assistant", "content": final_response}
                    )
                    print(
                        f"\nAssistant: {final_response} - MCP Client Model: {self.llm_model_name}"
                    )

                else:
                    # It's a direct answer (not a tool call)
                    # Add assistant's direct response to history
                    self.messages.append(
                        {"role": "assistant", "content": llm_raw_response}
                    )
                    print(
                        f"\nAssistant: {llm_raw_response} - Response by Default Model: {self.llm_model_name}"
                    )

                # Optional: Trim history to prevent exceeding token limits
                # e.g., keep only the last N messages

            except KeyboardInterrupt:
                logging.info("\nExiting...")
                break
            except ConnectionError as e:
                logging.error(f"Connection Error: {e}. Cannot continue.")
                print(
                    f"Assistant: Sorry, I'm having trouble connecting to the service. Please try again later."
                )
                break  # Exit loop on connection errors
            except Exception as e:
                logging.exception("An unexpected error occurred in the main chat loop:")
                print(
                    f"Assistant: Sorry, an unexpected error occurred ({e}). Please try again."
                )
                # Optional: Clear last user message from history if needed?
                # if self.messages and self.messages[-1]["role"] == "user":
                #     self.messages.pop()

        # Cleanup after the loop finishes
        await self.cleanup_servers()


async def main() -> None:
    """Initialize and run the chat session."""
    config_loader = Configuration()
    try:
        # Load .env variables (like API keys)
        config_loader.load_env()
        # Load server configurations
        server_configs = config_loader.load_config("servers_config.json")
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logging.error(f"Failed to load configuration: {e}. Exiting.")
        return
    except Exception as e:
        logging.error(f"Error during initial configuration loading: {e}. Exiting.")
        return

    gemini_server_config_data = server_configs.get("geminiServer")
    if not gemini_server_config_data or "config" not in gemini_server_config_data:
        logging.error(
            "Configuration for 'geminiServer' is missing or incomplete in servers_config.json"
        )
        return

    # Extract LLM specific config (adjust keys as needed in your config)
    # Example: Get project/location from env vars or config file
    llm_project = os.getenv(
        "GOOGLE_CLOUD_PROJECT", "cloud-project-test"
    )  # Default if not set
    llm_location = os.getenv(
        "GOOGLE_CLOUD_LOCATION", "us-central1"
    )  # Default if not set
    llm_model = os.getenv(
        "LLM_MODEL_NAME", "gemma-3-27b-it"
    )  # Default model, more flexible

    # --- Initialize Components ---
    try:
        gemini_server = Server(
            gemini_server_config_data.get("name", "gemini_llm_server"),
            gemini_server_config_data["config"],
        )

        llm_client = LLMClient(
            model_name=llm_model, project=llm_project, location=llm_location
        )

        # --- Start Chat ---
        chat_session = ChatSession(gemini_server, llm_client)
        await chat_session.start()

    except Exception as e:
        logging.error(f"Failed to initialize components or start chat session: {e}")
        # Perform cleanup if possible, although server might not be initialized
        if "gemini_server" in locals() and gemini_server.session:
            await gemini_server.cleanup()


if __name__ == "__main__":
    # load_dotenv() is called inside main() now for better encapsulation
    asyncio.run(main())
