# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
from typing import AsyncIterator

from concierge.agents.gemini_chat import schemas
from google import genai  # type: ignore[import-untyped]
from google.genai import types as genai_types  # type: ignore[import-untyped]
from langchain_core.runnables import config as lc_config
from langgraph import types as lg_types
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = "Answer questions about the Cymbal retail company. Cymbal offers both online retail and physical stores. Feel free to make up information about this fictional company, this is just for the purposes of a demo."


async def ainvoke(
    state: schemas.GraphSession,
    config: lc_config.RunnableConfig,
) -> lg_types.Command[schemas.PostProcessNodeTargetLiteral]:
    """
    Asynchronously invokes the chat node to generate a response using a Gemini model.

    This function takes the current conversation state and configuration, interacts with the
    Gemini model to generate a response based on the user's input and conversation history,
    and streams the response back to the user.

    Args:
        state: The current state of the conversation session.
        config: The LangChain RunnableConfig containing agent-specific configurations.

    Returns:
        A Command object that specifies the next node to transition to (post-processing) and the
        updated conversation state. This state includes the model's response and the updated
        conversation history.
    """

    agent_config = schemas.AgentConfig.model_validate(
        config["configurable"].get("agent_config", {})
    )

    stream_writer = get_stream_writer()

    current_turn = state.get("current_turn")
    assert current_turn is not None, "current turn must be set"

    user_input = current_turn.get("user_input")
    assert user_input is not None, "user input must be set"

    # Initialize generate model
    client = genai.Client(
        vertexai=True,
        project=agent_config.project,
        location=agent_config.region,
    )

    # Add new user input to history
    turns = state.get("turns", [])
    history = [content for turn in turns for content in turn.get("messages", [])]
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=user_input)],
    )
    contents = history + [user_content]

    try:
        # generate streaming response
        response: AsyncIterator[
            genai_types.GenerateContentResponse
        ] = await client.aio.models.generate_content_stream(
            model=agent_config.chat_model_name,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                candidate_count=1,
                temperature=0.2,
                seed=0,
                system_instruction=CHAT_SYSTEM_PROMPT,
            ),
        )

        # stream response text to custom stream writer
        response_text = ""
        async for chunk in response:
            response_text += chunk.text
            stream_writer({"text": chunk.text})

        response_content = genai_types.Content(
            role="model",
            parts=[genai_types.Part.from_text(text=response_text)],
        )

    except Exception as e:
        logger.exception(e)
        # unexpected error, display it
        response_text = f"An unexpected error occurred during generation, please try again.\n\nError = {str(e)}"
        stream_writer({"error": response_text})

        response_content = genai_types.Content(
            role="model",
            parts=[genai_types.Part.from_text(text=response_text)],
        )

    current_turn["response"] = response_text.strip()
    current_turn["messages"] = [user_content, response_content]

    return lg_types.Command(
        update=schemas.GraphSession(current_turn=current_turn),
        goto=schemas.POST_PROCESS_NODE_NAME,
    )
