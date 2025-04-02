# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# disable duplicate code to make it easier for copying a single agent folder
# pylint: disable=duplicate-code

from concierge.agents.task_planner import schemas, utils
from google import genai
from google.genai import types as genai_types
from tenacity import retry, retry_if_exception, stop_after_attempt, wait_exponential


@retry(
    retry=retry_if_exception(utils.is_retryable_error),
    wait=wait_exponential(min=1, max=10),
    stop=stop_after_attempt(3),
    reraise=True,
)
async def generate_plan(
    current_turn: schemas.Turn,
    project: str,
    region: str,
    model_name: str,
    history: list[schemas.Turn] | None = None,
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
        genai_types.Content(role=role, parts=[genai_types.Part.from_text(text=text)])
        for turn in history + [current_turn]
        for role, text in (
            ("user", turn.get("user_input")),
            ("model", turn.get("response") or "EMPTY"),
        )
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
