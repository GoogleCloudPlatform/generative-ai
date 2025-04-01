# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging

from concierge.agents.function_calling import schemas, utils
from concierge.agents.function_calling.tools import (
    find_inventory,
    find_products,
    find_stores,
)
from google import genai  # type: ignore[import-untyped]
from google.genai import types as genai_types  # type: ignore[import-untyped]
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

    user_input = current_turn.get("user_input")
    assert user_input is not None, "user input must be set"

    user_latitude = current_turn.get("user_latitude")
    user_longitude = current_turn.get("user_longitude")

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

    response_text = ""
    new_contents = [user_content.model_copy(deep=True)]
    try:
        find_stores_handler = find_stores.generate_find_stores_handler(
            project=agent_config.project,
            cymbal_dataset_location=agent_config.cymbal_dataset_location,
            cymbal_stores_table_uri=agent_config.cymbal_stores_table_uri,
            cymbal_inventory_table_uri=agent_config.cymbal_inventory_table_uri,
            user_latitude=user_latitude,
            user_longitude=user_longitude,
        )
        find_stores_fd = find_stores.find_stores_fd
        assert (
            find_stores_fd.name is not None
        ), "Function name must be set for automatic function calling"

        find_products_handler = find_products.generate_find_products_handler(
            project=agent_config.project,
            cymbal_dataset_location=agent_config.cymbal_dataset_location,
            cymbal_products_table_uri=agent_config.cymbal_products_table_uri,
            cymbal_inventory_table_uri=agent_config.cymbal_inventory_table_uri,
            cymbal_embedding_model_uri=agent_config.cymbal_embedding_model_uri,
        )
        find_products_fd = find_products.find_products_fd
        assert (
            find_products_fd.name is not None
        ), "Function name must be set for automatic function calling"

        find_inventory_handler = find_inventory.generate_find_inventory_handler(
            project=agent_config.project,
            cymbal_dataset_location=agent_config.cymbal_dataset_location,
            cymbal_inventory_table_uri=agent_config.cymbal_inventory_table_uri,
        )
        find_inventory_fd = find_inventory.find_inventory_fd
        assert (
            find_inventory_fd.name is not None
        ), "Function name must be set for automatic function calling"

        # generate streaming response
        response = utils.generate_content_stream(
            model=agent_config.chat_model_name,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                system_instruction=CHAT_SYSTEM_PROMPT,
                tools=[
                    genai_types.Tool(
                        function_declarations=[
                            find_products_fd,
                            find_stores_fd,
                            find_inventory_fd,
                        ]
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
            fn_map={
                find_products_fd.name: find_products_handler,
                find_stores_fd.name: find_stores_handler,
                find_inventory_fd.name: find_inventory_handler,
            },
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

    except Exception as e:
        logger.exception(e)
        # unexpected error, display it
        response_text = f"An unexpected error occured during generation, please try again.\n\nError = {str(e)}"
        stream_writer({"error": response_text})

    current_turn["response"] = response_text.strip()
    current_turn["messages"] = new_contents

    return lg_types.Command(
        update=schemas.GraphSession(current_turn=current_turn),
        goto=schemas.POST_PROCESS_NODE_NAME,
    )
