# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Generate a plan for the executor."""

from concierge import utils
from concierge.nodes.task_planning import schemas
from google import genai
from google.genai import types as genai_types


@utils.default_retry
async def generate_plan(
    current_turn: schemas.PlannerTurn,
    project: str,
    region: str,
    model_name: str,
    history: list[schemas.PlannerTurn] | None = None,
) -> schemas.PlanOrRespond:
    """
    Generates a plan or a direct response based on the current turn and conversation history.

    This function uses a Gemini model to analyze the user's input and the conversation history
    to determine whether to generate a step-by-step plan for further action or to provide a
    direct response to the user.

    Args:
        current_turn: The current turn in the conversation, containing the user's input.
        project: The Google Cloud project ID.
        region: The Google Cloud region.
        model_name: The name of the Gemini model to use.
        history: A list of previous turns in the conversation (optional).

    Returns:
        A PlanOrRespond object, which can either contain a Response object (to respond to the user)
        or a Plan object (to generate a new plan).
    """

    history = history or []

    client = genai.Client(vertexai=True, project=project, location=region)

    contents = [
        content
        for turn in history + [current_turn]
        for content in get_turn_contents(turn)
    ]

    content_response = await client.aio.models.generate_content(
        model=model_name,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schemas.PlanOrRespond,
            system_instruction="""
# Mission
For the given user input, come up with a response to the user or a simple step by step plan.

## Choices
If you can provide a direct response without executing any sub-tasks, provide a response action.
If you need clarification or have follow up questions, provide a response action.
If the user input requires research to answer or looking up realtime data, provide a plan action.

## Instructions for plans
The plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps.
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.
None of the steps are allowed to be user-facing, they must all be executed by the research agent with no input from the user.
A different responder agent will generate a final response to the user after the researcher executes the plan tasks.
Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan.
""".strip(),
        ),
    )

    plan_reflection = schemas.PlanOrRespond.model_validate_json(content_response.text)

    return plan_reflection


def get_turn_contents(
    turn: schemas.PlannerTurn,
) -> tuple[genai_types.Content, genai_types.Content]:
    """Extract user and model contents for plan generation using the given turn."""

    user_content = genai_types.UserContent(turn["user_input"])

    model_parts = list[str]()

    # add plan part if it exists
    plan = turn.get("plan")
    if plan is not None:
        task_strings = "\n---\n".join(
            f"Goal: {task.goal}\n\nResult: {task.result or ''}" for task in plan.tasks
        )
        plan_str = f"# Plan\nHigh Level Goal: {plan.goal}\n---\n{task_strings}"
        model_parts.append(plan_str)

    # add response or indicate response does not exist yet
    model_parts.append(turn.get("response") or "RESPONSE NOT CREATED YET")

    model_content = genai_types.ModelContent(model_parts)

    return (user_content, model_content)
