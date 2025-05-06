# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Reflect on the executed plan and either respond or generate a new plan."""

from concierge import utils
from concierge.nodes.task_planning import schemas
from google import genai
from google.genai import types as genai_types


@utils.default_retry
async def reflect_plan(
    user_input: str,
    executed_plan: schemas.Plan,
    project: str,
    region: str,
    model_name: str,
) -> schemas.PlanOrRespond:
    """
    Reflects on a user's input and an executed plan to determine the next action
    (response or new plan).

    This function uses a Gemini model to analyze the user's last message, the overall goal of the
    research agent, and the steps that were executed in the previous plan. Based on this analysis,
    it decides whether to generate a direct response to the user or to create a new plan for
    further action.

    Args:
        user_input: The user's most recent input.
        executed_plan: The plan that was previously executed.
        project: The Google Cloud project ID.
        region: The Google Cloud region.
        model_name: The name of the Gemini model to use.

    Returns:
        A PlanOrRespond object, which can either contain a Response object (to respond to the user)
        or a Plan object (to generate a new plan).
    """

    client = genai.Client(vertexai=True, project=project, location=region)

    system_instructions = """
# Mission
For the given user input, come up with a response to the user or a simple step by step plan.

## Choices
If you can provide a direct response without executing any sub-tasks, provide a response action.
If you need clarification or have follow up questions, provide a response action.
If the user input requires multiple steps to answer or looking up realtime data, provide a plan action.

## Instructions for plans
The plan should involve individual tasks, that if executed correctly will yield the correct answer. Do not add any superfluous steps.
The result of the final step should be the final answer. Make sure that each step has all the information needed - do not skip steps.
Only add steps to the plan that still NEED to be done. Do not return previously done steps as part of the plan.
""".strip()

    contents = f"""
The last user message was:
{user_input}

The main goal of the research agent was:
{executed_plan.goal}

The research agent executed the following tasks:
{executed_plan.tasks}
""".strip()

    content_response = await client.aio.models.generate_content(
        model=model_name,
        contents=contents,
        config=genai_types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=schemas.PlanOrRespond,
            system_instruction=system_instructions,
        ),
    )

    plan_reflection = schemas.PlanOrRespond.model_validate_json(content_response.text)

    return plan_reflection
