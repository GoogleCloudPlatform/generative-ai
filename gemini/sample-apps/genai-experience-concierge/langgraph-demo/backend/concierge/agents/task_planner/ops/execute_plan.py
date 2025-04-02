# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

# disable duplicate code to make it easier for copying a single agent folder
# pylint: disable=duplicate-code

from typing import AsyncGenerator

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
async def execute_plan(
    plan: schemas.Plan,
    project: str,
    region: str,
    model_name: str,
) -> AsyncGenerator[tuple[int, schemas.Task]]:
    """
    Executes a given plan step-by-step and yields the results of each task.

    This function iterates through the tasks in a given plan, executes each task using a Gemini model
    with Google Search tool enabled, and yields the index and updated task with the result.

    Args:
        plan: The plan to execute, containing a list of tasks.
        project: The Google Cloud project ID.
        region: The Google Cloud region.
        model_name: The name of the Gemini model to use.

    Yields:
        An asynchronous generator that yields tuples of (index, task), where index is the task's
        position in the plan and task is the updated task with the execution result.
    """

    executed_plan = plan.model_copy(deep=True)

    client = genai.Client(vertexai=True, project=project, location=region)

    search_tool = genai_types.Tool(google_search=genai_types.GoogleSearch())
    system_instruction = "Your mission is to execute the research goal provided and respond with findings. The result is not provided directly to the user, but instead provided to another agent to summarize findings."

    for idx, task in enumerate(executed_plan.tasks):
        if task.result is not None:
            continue

        # last task will be missing result. Will fill in from agent response.
        all_tasks = executed_plan.tasks[: idx + 1]
        all_tasks_string = "\n---\n".join(
            f"Goal: {task.goal}\n\nResult: {task.result or ''}" for task in all_tasks
        )

        contents = f"# Plan\nHigh Level Goal: {plan.goal}\n---\n{all_tasks_string}"

        content_response = await client.aio.models.generate_content(
            model=model_name,
            contents=contents,
            config=genai_types.GenerateContentConfig(
                tools=[search_tool],
                system_instruction=system_instruction,
            ),
        )

        task.result = content_response.text

        yield idx, task
