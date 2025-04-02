# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Gemini agent with a semantic router layer to select sub-agents."""

import enum

from concierge import settings, utils
from concierge.langgraph_server import langgraph_agent
from concierge.nodes import chat, router, save_turn


class RouterTarget(enum.Enum):
    """Enumeration representing the possible targets for routing user queries."""

    CUSTOMER_SERVICE = "Customer Support Assistant"
    """Target for customer service related queries."""
    RETAIL_SEARCH = "Conversational Retail Search Assistant"
    """Target for retail search related queries."""
    UNSUPPORTED = "Unsupported"
    """Target for unsupported queries."""


# pylint: disable=line-too-long
ROUTING_SYSTEM_PROMPT = f"""
You are an expert in classifying user queries for an agentic workflow for Cymbal, a retail company.
First reason through how you will classify the query given the conversation history.
Then, classify user queries to be sent to one of several AI assistants that can help the user.

Classify every inputted query as:
- "{RouterTarget.RETAIL_SEARCH.value}": Any pleasantries/general conversation or discussion of Cymbal retail products/stores/inventory, including live data.
- "{RouterTarget.CUSTOMER_SERVICE.value}": Queries related to customer service such as item returns, policies, complaints, FAQs, escalations, etc.
- "{RouterTarget.UNSUPPORTED.value}": Any query that is off topic or out of scope for one of the other agents.

<examples>
input: Is the Meinl Byzance Jazz Ride 18" available?
output: {RouterTarget.RETAIL_SEARCH.value}

input: Recommend a good pair of running shoes.
output: {RouterTarget.RETAIL_SEARCH.value}

input: How do i initiate a return?
output: {RouterTarget.CUSTOMER_SERVICE.value}

input: you suck, why do you refuse to be useful!
output: {RouterTarget.CUSTOMER_SERVICE.value}

input: How far is the earth from the sun?
output: {RouterTarget.UNSUPPORTED.value}

input: What's the weather like today?
output: {RouterTarget.UNSUPPORTED.value}
</examples>
""".strip()
# pylint: enable=line-too-long


def load_agent(
    runtime_settings: settings.RuntimeSettings,
) -> langgraph_agent.LangGraphAgent:
    """Loads the agent with a semantic router layer to select sub-agents."""

    customer_service_node = chat.build_chat_node(
        node_name="customer-service",
        next_node="save-turn",
        system_prompt="""
You are a customer service assistant for the Cymbal retail company.
Answer customer service questions about the company.
Cymbal offers both online retail and physical stores and carries
any safe and appropriate product you can think of.
Feel free to make up information about this fictional company,
this is just for the purposes of a demo.
""".strip(),
    )

    retail_search_node = chat.build_chat_node(
        node_name="retail-search",
        next_node="save-turn",
        system_prompt="""
You are a retail search assistant for the Cymbal Retail company.
Answer questions about the company.
Cymbal offers both online retail and physical stores and
carries any safe and appropriate product you can think of.
Feel free to make up information about this fictional company,
this is just for the purposes of a demo.
""".strip(),
    )

    unsupported_node = chat.build_chat_node(
        node_name="unsupported",
        next_node="save-turn",
        system_prompt="""
You are a retail search assistant for the Cymbal Retail company.
The latest user question has been classified as unsupported by your capabilities and scope.
Please explain this to the user and guide them to discuss topics related to
the Cymbal Retail company and their products/stores.
""".strip(),
    )

    router_node = router.build_semantic_router_node(
        node_name="semantic-router",
        system_prompt=ROUTING_SYSTEM_PROMPT,
        class_node_mapping={
            RouterTarget.CUSTOMER_SERVICE.value: customer_service_node.name,
            RouterTarget.RETAIL_SEARCH.value: retail_search_node.name,
            RouterTarget.UNSUPPORTED.value: unsupported_node.name,
        },
    )

    save_turn_node = save_turn.build_save_turn_node(node_name="save-turn")

    gemini_agent = langgraph_agent.LangGraphAgent(
        state_graph=utils.load_graph(
            schema=chat.ChatState,
            nodes=[
                router_node,
                customer_service_node,
                retail_search_node,
                unsupported_node,
                save_turn_node,
            ],
            entry_point=router_node,
        ),
        default_configurable={
            "chat_config": chat.ChatConfig(
                project=runtime_settings.project,
                region=runtime_settings.region,
                chat_model_name=runtime_settings.chat_model_name,
            ),
            "router_config": router.RouterConfig(
                project=runtime_settings.project,
                region=runtime_settings.region,
                router_model_name=runtime_settings.router_model_name,
                max_router_turn_history=runtime_settings.max_router_turn_history,
            ),
        },
        checkpointer_config=runtime_settings.checkpointer,
    )

    return gemini_agent
