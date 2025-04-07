# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Function calling chat agent for the Concierge demo."""

from concierge import schemas, settings, utils
from concierge.langgraph_server import langgraph_agent
from concierge.nodes import chat, save_turn
from concierge.tools import find_inventory, find_products, find_stores

# pylint: disable=line-too-long
FUNCTION_CALLING_SYSTEM_PROMPT = """
You are a chat assistant for the Cymbal Retail site which manages inventory for
stores/businesses across many industries. Help answer any user questions.
Whenever you don't know something, use one or more of your tools before responding
to retrieve live data about stores, products, and inventory.

The purpose of each tool is:
- find_products: Search for products given some stores, price range, and/or open text search query
- find_stores: Search for stores given its name, some offered products, and/or a search radius near the user.
- find_inventory: Search for the inventory of a given product/store pair.

Note: the user's location is stored in the persistent session storage.
It can be retrieved in the background for the store search radius.
""".strip()
# pylint: enable=line-too-long


def load_agent(
    runtime_settings: settings.RuntimeSettings,
) -> langgraph_agent.LangGraphAgent:
    """Loads the function calling chat agent for the Concierge demo."""

    chat_node = chat.build_chat_node(
        node_name="chat",
        next_node="save-turn",
        system_prompt=FUNCTION_CALLING_SYSTEM_PROMPT,
        function_spec_loader=lambda turn: load_function_specs(
            turn=turn,
            runtime_settings=runtime_settings,
        ),
    )

    save_turn_node = save_turn.build_save_turn_node(node_name="save-turn")

    gemini_agent = langgraph_agent.LangGraphAgent(
        state_graph=utils.load_graph(
            schema=chat.ChatState,
            nodes=[chat_node, save_turn_node],
            entry_point=chat_node,
        ),
        default_configurable={
            "chat_config": chat.ChatConfig(
                project=runtime_settings.project,
                region=runtime_settings.region,
                chat_model_name=runtime_settings.chat_model_name,
            ),
        },
        checkpointer_config=runtime_settings.checkpointer,
    )

    return gemini_agent


def load_function_specs(
    turn: schemas.BaseTurn,
    runtime_settings: settings.RuntimeSettings,
) -> list[schemas.FunctionSpec]:
    """Load a list of function specs containing function declarations and callable handlers."""

    assert runtime_settings.cymbal_stores_table_uri is not None
    assert runtime_settings.cymbal_products_table_uri is not None
    assert runtime_settings.cymbal_inventory_table_uri is not None
    assert runtime_settings.cymbal_embedding_model_uri is not None

    user_coordinate = turn.get("user_location")

    find_stores_handler = find_stores.generate_find_stores_handler(
        project=runtime_settings.project,
        cymbal_dataset_location=runtime_settings.cymbal_dataset_location,
        cymbal_stores_table_uri=runtime_settings.cymbal_stores_table_uri,
        cymbal_inventory_table_uri=runtime_settings.cymbal_inventory_table_uri,
        user_coordinate=user_coordinate,
    )
    find_stores_fd = find_stores.find_stores_fd
    assert (
        find_stores_fd.name is not None
    ), "Function name must be set for automatic function calling"

    find_products_handler = find_products.generate_find_products_handler(
        project=runtime_settings.project,
        cymbal_dataset_location=runtime_settings.cymbal_dataset_location,
        cymbal_products_table_uri=runtime_settings.cymbal_products_table_uri,
        cymbal_inventory_table_uri=runtime_settings.cymbal_inventory_table_uri,
        cymbal_embedding_model_uri=runtime_settings.cymbal_embedding_model_uri,
    )
    find_products_fd = find_products.find_products_fd
    assert (
        find_products_fd.name is not None
    ), "Function name must be set for automatic function calling"

    find_inventory_handler = find_inventory.generate_find_inventory_handler(
        project=runtime_settings.project,
        cymbal_dataset_location=runtime_settings.cymbal_dataset_location,
        cymbal_inventory_table_uri=runtime_settings.cymbal_inventory_table_uri,
    )
    find_inventory_fd = find_inventory.find_inventory_fd
    assert (
        find_inventory_fd.name is not None
    ), "Function name must be set for automatic function calling"

    return [
        schemas.FunctionSpec(fd=find_products_fd, callable=find_products_handler),
        schemas.FunctionSpec(fd=find_stores_fd, callable=find_stores_handler),
        schemas.FunctionSpec(fd=find_inventory_fd, callable=find_inventory_handler),
    ]
