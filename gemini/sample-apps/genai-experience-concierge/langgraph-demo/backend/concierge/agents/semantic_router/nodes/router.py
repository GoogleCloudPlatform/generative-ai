# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import logging
from typing import Literal

from langgraph import types as lg_types
from langgraph.config import get_stream_writer
from langchain_core.runnables import config as lc_config
from google import genai  # type: ignore[import-untyped]
from google.genai import types as genai_types  # type: ignore[import-untyped]

from concierge.agents.semantic_router import schemas

logger = logging.getLogger(__name__)

UNSUPPORTED_FALLBACK_MESSAGE = "I'm sorry, I am unable to process your request as it is outside of my current capabilities. Please try asking me about our retail business or customer support."

ROUTER_SYSTEM_PROMPT = f"""
You are an expert in classifying user queries for an agentic workflow for Cymbal, a retail company.
First reason through how you will classify the query given the conversation history.
Then, classify user queries to be sent to one of several AI assistants that can help the user.

Classify every inputted query as: "{schemas.RouterTarget.customer_service.value}", "{schemas.RouterTarget.retail_search.value}", "{schemas.RouterTarget.unsupported.value}".

Class target descriptions:
- "{schemas.RouterTarget.retail_search.value}": Any pleasantries/general conversation or discussion of Cymbal retail products/stores/inventory, including live data.
- "{schemas.RouterTarget.customer_service.value}": Queries related to customer service such as item returns, policies, complaints, FAQs, escalations, etc.
- "{schemas.RouterTarget.unsupported.value}": Any query that is off topic or out of scope for one of the other agents.

<examples>
input: Is the Meinl Byzance Jazz Ride 18" available?
output: {schemas.RouterTarget.retail_search.value}

input: Recommend a good pair of running shoes.
output: {schemas.RouterTarget.retail_search.value}

input: How do i initiate a return?
output: {schemas.RouterTarget.customer_service.value}

input: you suck, why do you refuse to be useful!
output: {schemas.RouterTarget.customer_service.value}

input: How far is the earth from the sun?
output: {schemas.RouterTarget.unsupported.value}

input: What's the weather like today?
output: {schemas.RouterTarget.unsupported.value}
</examples>
""".strip()


async def ainvoke(
    state: schemas.GraphSession,
    config: lc_config.RunnableConfig,
) -> lg_types.Command[
    Literal[
        schemas.RETAIL_NODE_TARGET_LITERAL,
        schemas.CUSTOMER_SERVICE_NODE_TARGET_LITERAL,
        schemas.POST_PROCESS_NODE_TARGET_LITERAL,
    ]
]:
    """
    Asynchronously invokes the router node to classify user input and determine the next action.

    This function takes the current conversation state and configuration, interacts with the
    Gemini model to classify the user's input based on predefined categories, and
    determines which sub-agent should handle the request.

    Args:
        state: The current state of the conversation session, including user input and history.
        config: The LangChain RunnableConfig containing agent-specific configurations.

    Returns:
        A Command object that specifies the next node to transition to (retail, customer service, or post-processing)
        and the updated conversation state. This state includes the router classification.
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
    turns = state.get("turns", [])[: agent_config.max_router_turn_history]
    history = [content for turn in turns for content in turn.get("messages", [])]
    user_content = genai_types.Content(
        role="user",
        parts=[genai_types.Part.from_text(text=user_input)],
    )
    contents = history + [user_content]

    # generate streaming response
    response = await client.aio.models.generate_content(
        model=agent_config.router_model_name,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            candidate_count=1,
            temperature=0.2,
            seed=0,
            system_instruction=ROUTER_SYSTEM_PROMPT,
            response_mime_type="application/json",
            response_schema=schemas.RouterClassification,
        ),
    )

    router_classification = schemas.RouterClassification.model_validate_json(
        response.text
    )

    stream_writer(
        {
            "router_classification": {
                "target": router_classification.target.value,
                "reason": router_classification.reason,
            }
        }
    )

    current_turn["router_classification"] = router_classification

    next_node = None
    match router_classification.target:
        case schemas.RouterTarget.retail_search:
            next_node = schemas.RETAIL_NODE_NAME
        case schemas.RouterTarget.customer_service:
            next_node = schemas.CUSTOMER_SERVICE_NODE_NAME
        case schemas.RouterTarget.unsupported:
            next_node = schemas.POST_PROCESS_NODE_NAME
            current_turn["response"] = UNSUPPORTED_FALLBACK_MESSAGE
            stream_writer({"text": current_turn["response"]})
        case _:  # never
            raise RuntimeError(
                f"Unhandled router classification target: {router_classification.target}"
            )

    return lg_types.Command(
        update=schemas.GraphSession(current_turn=current_turn),
        goto=next_node,
    )
