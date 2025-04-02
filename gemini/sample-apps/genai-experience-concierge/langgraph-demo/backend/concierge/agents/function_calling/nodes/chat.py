# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# disable duplicate code to make it easier for copying a single agent folder
# pylint: disable=duplicate-code

import logging

from concierge.agents.function_calling import schemas, tools, utils
from google import genai
from google.genai import types as genai_types
from langchain_core.runnables import config as lc_config
from langgraph import types as lg_types
from langgraph.config import get_stream_writer

logger = logging.getLogger(__name__)

CHAT_SYSTEM_PROMPT = """"
You are a chat assistant for the Cymbal Retail site which manages inventory for stores/businesses across many industries.
Help answer any user questions.
Whenever you don't know something, use one or more of your tools before responding to retrieve live data about stores, products, and inventory.
The purpose of each tool is:
- find_products: Search for products given some stores, price range, and/or open text search query
- find_stores: Search for stores given its name, some offered products, and/or a search radius near the user.
- find_inventory: Search for the inventory of a given product/store pair.
Note: the user's location is stored in the persistent session storage. It can be retrieved in the background for the store search radius.
""".strip()


async def ainvoke(
    state: schemas.GraphSession,
    config: lc_config.RunnableConfig,
) -> lg_types.Command[schemas.PostProcessNodeTargetLiteral]:
    """
    Asynchronously invokes the chat node to generate a response using a Gemini model.

    This function takes the current conversation state, including the user's input and conversation history,
    and generates a response using a Gemini model. It supports function calling to retrieve live data about
    stores, products, and inventory. It streams the response text and updates the conversation state with the
    generated response and function call results.

    Args:
        state: The current state of the conversation session.
        config: The LangChain RunnableConfig (unused in this function).

    Returns:
        A Command object specifying the next node to transition to (post-processing)
        and the updated conversation state.
    """

    agent_config = schemas.AgentConfig.model_validate(
        config["configurable"].get("agent_config", {})
    )

    stream_writer = get_stream_writer()

    current_turn = state.get("current_turn")
    assert current_turn is not None, "current turn must be set"

    # Initialize generate model
    client = genai.Client(
        vertexai=True,
        project=agent_config.project,
        location=agent_config.region,
    )

    response_text = ""
    new_contents = [load_user_content(current_turn=current_turn)]
    try:
        function_specs = tools.load_function_specs(
            turn=current_turn,
            agent_config=agent_config,
        )

        # generate streaming response
        response = utils.generate_content_stream(
            model=agent_config.chat_model_name,
            contents=[
                content
                for turn in state.get("turns", [])
                for content in turn.get("messages", [])
            ]
            + new_contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=CHAT_SYSTEM_PROMPT,
                tools=[
                    genai_types.Tool(
                        function_declarations=[spec.fd for spec in function_specs],
                    )
                ],
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
            for part in content.parts:
                if part.text:
                    response_text += part.text
                    used_content = True
                    stream_writer({"text": part.text})
                if part.function_call:
                    used_content = True
                    stream_writer(
                        {"function_call": part.function_call.model_dump(mode="json")}
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
        response_text = f"An unexpected error occurred during generation, please try again.\n\nError = {str(e)}"
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
        update=schemas.GraphSession(current_turn=current_turn),
        goto=schemas.POST_PROCESS_NODE_NAME,
    )


def load_user_content(current_turn: schemas.Turn) -> genai_types.Content:
    """Load user input from current turn into a Content object."""

    user_input = current_turn.get("user_input")
    assert user_input is not None, "user input must be set"

    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=user_input)],
    )

    return user_content
