# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Streamlit demo home page."""

from concierge_ui import demo_page, remote_settings
from concierge_ui.agents import (
    function_calling,
    gemini_chat,
    gemini_chat_with_guardrails,
    semantic_router,
    task_planner,
)
import streamlit as st

settings = remote_settings.RemoteAgentConfigs()

home_page = st.Page("home.py", title="Home", icon="🏠")

gemini_chat_page = st.Page(
    lambda: demo_page.build_demo_page(
        title="Gemini Chat",
        icon="⭐",
        description="""
This demo illustrates a simple "agent" which just consists of plain Gemini 2.0 Flash with conversation history.
Response text is streamed using a custom [langgraph.config.get_stream_writer](https://langchain-ai.github.io/langgraph/reference/config/#langgraph.config.get_stream_writer).
""".strip(),
        chat_handler=gemini_chat.chat_handler,
        config=settings.gemini,
    ),
    title="Gemini Chat",
    icon="⭐",
    url_path="gemini",
)

guardrail_chat_page = st.Page(
    lambda: demo_page.build_demo_page(
        title="Gemini Chat With Guardrails",
        icon="🛡️",
        description="""
This demo illustrates a Gemini-based chatbot protected with a custom guardrail classifier.

Before generating a chat response, the user input and conversation history is passed to
a smaller, faster Gemini model which classifies the response as allowed or blocked.

* If the input is blocked, a fallback response is returned to the user.
* Otherwise, a larger Gemini model is used to generate and stream a response.
    """.strip(),
        chat_handler=gemini_chat_with_guardrails.chat_handler,
        config=settings.guardrail,
    ),
    url_path="guardrail",
    title="Gemini Chat With Guardrails",
    icon="🛡️",
)

function_calling_page = st.Page(
    lambda: demo_page.build_demo_page(
        title="Function Calling Agent",
        icon="📞",
        description="""
This demo utilizes a collection of function declarations to search over a synthetic BigQuery dataset for a fictional company named "Cymbal Retail". The dataset contains information about products, store locations, and product-store inventory. The function declarations allow for structured query generation to enable the LLM to query the database in a secure, controlled manner. In addition to exact filtering mechanisms like setting a maximum product price or store search radius, the demo utilizes integrated BQML embedding support ([reference](https://cloud.google.com/bigquery/docs/reference/standard-sql/bigqueryml-syntax-generate-embedding#text-embedding)) to re-rank results using product name/description semantic similarity.

This approach can be contrasted with Natural-Language-To-SQL (NL2SQL) which can generate and execute arbitrary SQL, making it more flexible but more prone to errors and security risks ([learn more about NL2SQL](https://cloud.google.com/blog/products/data-analytics/nl2sql-with-bigquery-and-gemini)).

Retail Search Assistant Use Cases:

1. **Store Search:** Filter by store name, search radius, product IDs, and number of results.

1. **Product Search:** Filter by store IDs, price range, number of results, and rank by product name/description.

1. **Inventory Search:** for a given product-store pair.
""".strip(),
        chat_handler=function_calling.chat_handler,
        config=settings.function_calling,
    ),
    title="Function Calling Agent",
    icon="📞",
    url_path="function-calling",
)


semantic_router_page = st.Page(
    lambda: demo_page.build_demo_page(
        title="Semantic Router",
        icon="↗️",
        description="""
This demo uses an LLM-based intent detection classifier to route each user query to either a "Retail Search" or "Customer Support" expert assistant. The experts are mocked as simple Gemini calls with a system prompt for this demo, but represent an arbitrary actor that can share session history with all other sub-agents. For example, the customer support agent might be implemented with [Contact Center as a Service](https://cloud.google.com/solutions/contact-center-ai-platform) while the retail search assistant is built with Gemini and deployed on Cloud Run.

The semantic router layer can provide a useful facade to enable a single interface for multiple drastically different agent backends.
""".strip(),
        chat_handler=semantic_router.chat_handler,
        config=settings.semantic_router,
    ),
    title="Semantic Router",
    icon="↗️",
    url_path="semantic-router",
)


task_planner_page = st.Page(
    lambda: demo_page.build_demo_page(
        title="Task Planner",
        icon="📝",
        description="""
The task planner design pattern (similar to ["Deep Research"](https://gemini.google/overview/deep-research)) is a multi-agent architecture useful for tasks requiring more complex reasoning, planning, and multi-tool use. The task planner is built of three core agents:

1. A _Planner_ that receives user input and either (1) responds directly to simple queries (e.g. "Hi") or (2) generates a research plan, including list of tasks to execute.

1. An _Executor_ that receives a plan and uses its tools to perform each task and update the plan with the executed task result.

1. A _Reflector_ that reviews the executed plan and either (1) generates a final response to the user or (2) generates a new plan and jumps back to step 2.

This architecture is often much slower than single-agent designs because a single turn can consist of a large number of LLM calls and tool usage. This demo is particularly slow because the "Executor" agent only supports linear plans and executes each task in parallel. There is research on alternative approaches such as [LLM Compiler](https://arxiv.org/abs/2312.04511) that attempt to improve this design by constructing DAGs to enable parallel task execution.

The "Executor" agent in this demo is a Gemini model equipped with the Google Search Grounding Tool ([documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/ground-with-google-search)) to enable live web search while executing tasks.
""".strip(),
        chat_handler=task_planner.chat_handler,
        config=settings.task_planner,
    ),
    title="Task Planner",
    icon="📝",
    url_path="task-planner",
)


pg = st.navigation(
    [
        home_page,
        gemini_chat_page,
        guardrail_chat_page,
        semantic_router_page,
        function_calling_page,
        task_planner_page,
    ]
)
pg.run()
