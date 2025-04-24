# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Node to classify user input and determine the next action."""

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

DEFAULT_FALLBACK_RESPONSE = "I apologize, but I am unable to assist with this query as it falls outside the scope of my knowledge base."  # pylint: disable=line-too-long


class InputGuardrails(pydantic.BaseModel):
    """
    Represents the classification of a user request by the guardrails system.

    Attributes:
        blocked: Indicates whether the request should be blocked.
        reason: The reason for the classification decision.
        guardrail_response: A fallback message to be returned if the request is blocked.
    """  # pylint: disable=line-too-long

    blocked: bool = pydantic.Field(
        description="The classification decision on whether the request should be blocked.",
    )
    """Boolean indicating whether the request should be blocked."""

    reason: str = pydantic.Field(
        description="Reason why the response was given the classification value.",
    )
    """Explanation of why the request was classified as blocked or allowed."""

    guardrail_response: str = pydantic.Field(
        description=(
            "Guardrail fallback message if the response is blocked."
            " Should be safe to surface to users."
        ),
    )
    """A safe message to display to the user if their request is blocked."""


class GuardrailTurn(schemas.BaseTurn):
    """Represents a single turn in a conversation with guardrails."""

    input_guardrails: InputGuardrails | None
    """The guardrail classification for this turn, if any."""


class GuardrailState(TypedDict, total=False):
    """Stores the active turn and conversation history."""

    current_turn: GuardrailTurn | None
    """The current turn being processed."""

    turns: list[GuardrailTurn]
    """List of all turns in the session."""


class GuardrailConfig(pydantic.BaseModel):
    """Configuration settings for the guardrails node."""

    project: str
    region: str
    guardrail_model_name: str


def build_guardrail_node(
    node_name: str,
    allowed_next_node: str,
    blocked_next_node: str,
    system_prompt: str,
    guardrail_fallback_response: str = DEFAULT_FALLBACK_RESPONSE,
) -> schemas.Node:
    """Builds a LangGraph node for classifying user input as blocked or allowed."""

    NextNodeT = Literal[allowed_next_node, blocked_next_node]  # type: ignore

    async def ainvoke(
        state: GuardrailState,
        config: lc_config.RunnableConfig,
    ) -> lg_types.Command[NextNodeT]:
        """
        Asynchronously invokes the guardrails node to classify user input
        and determine the next action.

        This function classifies the user's input based on predefined guardrails,
        determining whether the input should be blocked or allowed. If blocked,
        a guardrail response is generated and the conversation is directed
        to the post-processing node. If allowed, the conversation proceeds to the chat node.

        Args:
            state: The current state of the conversation session, including user input and history.
            config: The LangChain RunnableConfig containing agent-specific configurations.

        Returns:
            A Command object that specifies the next node to transition to
            and the updated conversation state. This state includes the guardrail classification
            and the appropriate response to the user.
        """

        stream_writer = get_stream_writer()

        guardrail_config = GuardrailConfig.model_validate(
            config.get("configurable", {}).get("guardrail_config", {})
        )

        current_turn = state.get("current_turn")
        assert current_turn is not None, "current turn must be set"

        # Initialize generate model
        client = genai.Client(
            vertexai=True,
            project=guardrail_config.project,
            location=guardrail_config.region,
        )

        user_content = utils.load_user_content(current_turn=current_turn)
        contents = [
            content
            for turn in state.get("turns", [])
            for content in turn.get("messages", [])
        ] + [user_content]
        try:
            # generate streaming response
            response = await client.aio.models.generate_content(
                model=guardrail_config.guardrail_model_name,
                contents=contents,
                config=genai_types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    candidate_count=1,
                    temperature=0,
                    seed=0,
                    response_mime_type="application/json",
                    response_schema=InputGuardrails,
                ),
            )

            guardrail_classification = InputGuardrails.model_validate_json(
                response.text.strip() if response.text else ""
            )

        except Exception as e:  # pylint: disable=broad-exception-caught
            logger.exception(e)
            error_reason = str(e)

            guardrail_classification = InputGuardrails(
                blocked=True,
                reason=error_reason,
                guardrail_response=(
                    "An error occurred during response generation."
                    " Please try again later."
                ),
            )

        stream_writer(
            {
                "guardrail_classification": guardrail_classification.model_dump(
                    mode="json"
                )
            }
        )

        # Update current response with classification and default guardrail response
        current_turn["response"] = guardrail_fallback_response
        current_turn["input_guardrails"] = guardrail_classification

        # If request is not allowed, set current agent response to generative fallback.
        if (
            guardrail_classification.blocked
            and guardrail_classification.guardrail_response is not None
        ):
            current_turn["response"] = guardrail_classification.guardrail_response

        # determine next node and stream fallback response if blocked.
        next_node = allowed_next_node
        if guardrail_classification.blocked:
            stream_writer({"text": current_turn["response"]})
            next_node = blocked_next_node

        return lg_types.Command(
            update=GuardrailState(current_turn=current_turn),
            goto=next_node,
        )

    return schemas.Node(name=node_name, fn=ainvoke)
