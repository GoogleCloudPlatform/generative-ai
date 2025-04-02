# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Chat response generation with optional support for streamed function calling."""

import logging
from typing import Literal, TypedDict

from concierge import schemas, utils
from google import genai
from google.genai import types as genai_types
from langchain_core.runnables import config as lc_config
from langgraph import types as lg_types
from langgraph.config import get_stream_writer
import pydantic

logger = logging.getLogger(__name__)


class ChatState(TypedDict, total=False):
    """Stores the active turn and conversation history."""

    current_turn: schemas.BaseTurn | None
    """The current conversation turn."""

    turns: list[schemas.BaseTurn]
    """List of all conversation turns in the session."""


class ChatConfig(pydantic.BaseModel):
    """Configuration settings for the chat node."""

    project: str
    """The Google Cloud project ID."""
    region: str
    """The Google Cloud region."""
    chat_model_name: str
    """The name of the Gemini chat model."""


def build_chat_node(
    node_name: str,
    next_node: str,
    system_prompt: str,
    function_spec_loader: schemas.RuntimeFunctionSpecLoader | None = None,
) -> schemas.Node:
    """Builds a LangGraph node for generating chat responses using a Gemini model."""

    async def ainvoke(
        state: ChatState,
        config: lc_config.RunnableConfig,
    ) -> lg_types.Command[Literal[next_node]]:
        """
        Asynchronously invokes the chat node to generate a response using a Gemini model.

        This function takes the current conversation state, including the user's input
        and conversation history to generate a response using a Gemini model. It supports
        function calling to retrieve live data and streams the function calls, responses,
        and response text before updating the state.

        Runtime configuration should be passed in `config.configurable.chat_config`.

        Args:
            state: The current state of the conversation session.
            config: The LangChain RunnableConfig (unused in this function).

        Returns:
            A Command object specifying the next node to transition to (post-processing)
            and the updated conversation state.
        """
        nonlocal function_spec_loader

        chat_config = ChatConfig.model_validate(
            config.get("configurable", {}).get("chat_config", {})
        )

        stream_writer = get_stream_writer()

        current_turn = state.get("current_turn")
        assert current_turn is not None, "current turn must be set"

        function_specs = []
        if function_spec_loader:
            function_specs = function_spec_loader(turn=current_turn)

        # Initialize generate model
        client = genai.Client(
            vertexai=True,
            project=chat_config.project,
            location=chat_config.region,
        )

        response_text = ""
        new_contents = [utils.load_user_content(current_turn=current_turn)]
        try:
            tools = []
            if function_specs:
                tools = [
                    genai_types.Tool(
                        function_declarations=[spec.fd for spec in function_specs],
                    )
                ]
            # generate streaming response
            response = utils.generate_content_stream(
                model=chat_config.chat_model_name,
                contents=[
                    content
                    for turn in state.get("turns", [])
                    for content in turn.get("messages", [])
                ]
                + new_contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    tools=tools,
                    temperature=0.6,
                    candidate_count=1,
                    seed=42,
                    automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(
                        disable=True
                    ),
                ),
                client=client,
                fn_map={spec.fd.name: spec.callable for spec in function_specs},
            )

            async for content in response:
                used_content = False
                for part in content.parts or []:
                    if part.text:
                        response_text += part.text
                        used_content = True
                        stream_writer({"text": part.text})
                    if part.function_call:
                        used_content = True
                        stream_writer(
                            {
                                "function_call": part.function_call.model_dump(
                                    mode="json"
                                )
                            }
                        )
                    if part.function_response:
                        used_content = True
                        stream_writer(
                            {
                                "function_response": part.function_response.model_dump(
                                    mode="json"
                                )
                            }
                        )

                if used_content:
                    new_contents.append(content.model_copy(deep=True))

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(e)
            # unexpected error, display it
            response_text = (
                "An unexpected error occurred during generation, please try again."
                f"\n\nError = {str(e)}"
            )
            stream_writer({"error": response_text})

            new_contents.append(
                genai_types.Content(
                    role="model",
                    parts=[genai_types.Part.from_text(text=response_text)],
                )
            )

        current_turn["response"] = response_text.strip()
        current_turn["messages"] = new_contents

        return lg_types.Command(
            update=ChatState(current_turn=current_turn),
            goto=next_node,
        )

    return schemas.Node(name=node_name, fn=ainvoke)
