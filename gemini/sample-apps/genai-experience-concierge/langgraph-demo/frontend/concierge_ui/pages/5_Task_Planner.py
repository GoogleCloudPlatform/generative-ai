# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

from concierge_ui import auth, demo_page, remote_settings as settings
from langgraph.pregel import remote

config = settings.RemoteAgentConfigs().task_planner

graph = remote.RemoteGraph(
    config.name,
    url=str(config.base_url),
    headers=auth.get_auth_headers(config),
)


def chat_handler(message: str, thread_id: str):
    """
    Handles chat interactions by streaming responses from a remote LangGraph.

    This function takes a user message and a thread ID, and streams responses from a remote LangGraph.
    It parses the streamed chunks, which can contain responses, execution plans, or executed tasks,
    and formats them into a human-readable text stream.

    Args:
        message (str): The user's input message.
        thread_id (str): The ID of the chat thread.

    Yields:
        str: Formatted text chunks representing the responses, plans, or executed tasks.
    """
    current_source = last_source = None
    task_idx = 0
    all_text = ""
    for stream_mode, chunk in graph.stream(
        input={"current_turn": {"user_input": message}},
        config={"configurable": {"thread_id": thread_id}},
        stream_mode=["custom"],
    ):
        assert isinstance(chunk, dict), "Expected dictionary chunk"

        text = ""

        if "response" in chunk:
            # if no prior text, then no plan was generated
            if all_text.strip() == "":
                text = chunk["response"]
            else:
                text = "### Reflection\n\n" + chunk["response"]

            current_source = "response"

        elif "plan" in chunk:
            plan_dict = chunk["plan"]
            plan_string = _stringify_plan(plan=plan_dict, include_results=False)
            text = f"### Generated execution plan...\n\n{plan_string}"
            current_source = "plan"

        elif "executed_task" in chunk:
            task_idx += 1
            task_dict = chunk["executed_task"]
            task_string = _stringify_task(task=task_dict, include_results=True)
            text = f"### Executed task #{task_idx}...\n\n{task_string}"
            current_source = f"executed_task_{task_idx}"

        else:
            print("unhandled chunk case:", chunk)

        if last_source is not None and last_source != current_source:
            text = "\n\n---\n\n" + text

        last_source = current_source

        all_text += text

        yield text


def _stringify_plan(plan: dict, include_results: bool = True) -> str:
    """
    Formats an execution plan dictionary into a human-readable string.

    This function takes an execution plan dictionary and converts it into a formatted string,
    including the goal and a list of tasks.

    Args:
        plan (dict): The execution plan dictionary.
        include_results (bool, optional): Whether to include task results in the output. Defaults to True.

    Returns:
        str: The formatted execution plan string.
    """
    tasks_str = "\n\n".join(
        f"**Task #{idx + 1}**\n\n"
        + _stringify_task(task, include_results=include_results)
        for idx, task in enumerate(plan["tasks"])
    )

    response = f"**Plan**: {plan['goal']}\n\n{tasks_str}"

    return response


def _stringify_task(task: dict, include_results: bool = True) -> str:
    """
    Formats a task dictionary into a human-readable string.

    This function takes a task dictionary and converts it into a formatted string,
    including the task goal and optionally the task result.

    Args:
        task (dict): The task dictionary.
        include_results (bool, optional): Whether to include the task result in the output. Defaults to True.

    Returns:
        str: The formatted task string.
    """
    output = f"**Goal**: {task['goal']}"

    if include_results:
        output += f"\n\n**Result**: {task.get('result') or 'incomplete'}"

    return output


demo_page.build_demo_page(
    id="task-planner",
    title="Task Planner",
    page_icon="📝",
    description="""
The task planner design pattern (similar to ["Deep Research"](https://gemini.google/overview/deep-research)) is a multi-agent architecture useful for tasks requiring more complex reasoning, planning, and multi-tool use. The task planner is built of three core agents:

1. A _Planner_ that receives user input and either (1) responds directly to simple queries (e.g. "Hi") or (2) generates a research plan, including list of tasks to execute.

1. An _Executor_ that receives a plan and uses its tools to perform each task and update the plan with the executed task result.

1. A _Reflector_ that reviews the executed plan and either (1) generates a final response to the user or (2) generates a new plan and jumps back to step 2.

This architecture is often much slower than single-agent designs because a single turn can consist of a large number of LLM calls and tool usage. This demo is particularly slow because the "Executor" agent only supports linear plans and executes each task in parallel. There is research on alternative approaches such as [LLM Compiler](https://arxiv.org/abs/2312.04511) that attempt to improve this design by constructing DAGs to enable parallel task execution.

The "Executor" agent in this demo is a Gemini model equipped with the Google Search Grounding Tool ([documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/ground-with-google-search)) to enable live web search while executing tasks.
""".strip(),
    chat_handler=chat_handler,
    config=config,
)
