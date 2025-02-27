# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=E0611

import os
from typing import Dict, List

from app.retrievers import get_compressor, get_retriever
from app.templates import format_docs, inspect_conversation_template, rag_template
import google
from langchain_core.documents import Document
from langchain_core.messages import BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_core.tools import tool
from langchain_google_vertexai import ChatVertexAI, VertexAIEmbeddings
from langgraph.graph import END, MessagesState, StateGraph
from langgraph.prebuilt import ToolNode
import vertexai

EMBEDDING_MODEL = "text-embedding-004"
LLM_MODEL = "gemini-1.5-flash-002"
TOP_K = 5

VERTEX_AI_LOCATION = os.getenv("REGION", "us-central1")
AGENT_BUILDER_LOCATION = os.getenv("AGENT_BUILDER_LOCATION", "us")
DATA_STORE_ID = os.getenv("DATA_STORE_ID", "sample-datastore")

# Initialize Google Cloud and Vertex AI
credentials, project_id = google.auth.default()
vertexai.init(project=project_id)

embedding = VertexAIEmbeddings(model_name=EMBEDDING_MODEL, location=VERTEX_AI_LOCATION)

retriever = get_retriever(
    project_id=project_id,
    data_store_id=DATA_STORE_ID,
    agent_builder_location=AGENT_BUILDER_LOCATION,
    embedding=embedding,
)
compressor = get_compressor(project_id=project_id)


@tool(response_format="content_and_artifact")
def retrieve_docs(query: str) -> tuple[str, List[Document]]:
    """
    Useful for retrieving relevant documents based on a query.
    Use this when you need additional information to answer a question.

    Args:
        query (str): The user's question or search query.

    Returns:
        List[Document]: A list of the top-ranked Document objects, limited to TOP_K (5) results.
    """
    # Use the retriever to fetch relevant documents based on the query
    retrieved_docs = retriever.invoke(query)
    # Re-rank docs with Vertex AI Rank for better relevance
    ranked_docs = compressor.compress_documents(documents=retrieved_docs, query=query)
    # Format ranked documents into a consistent structure for LLM consumption
    formatted_docs = format_docs.format(docs=ranked_docs)
    return (formatted_docs, ranked_docs)


@tool
def should_continue() -> None:
    """
    Use this tool if you determine that you have enough context to respond to the questions of the user.
    """
    return None


tools = [retrieve_docs, should_continue]

llm = ChatVertexAI(model=LLM_MODEL, temperature=0, max_tokens=1024, streaming=True)

# Set up conversation inspector
inspect_conversation = inspect_conversation_template | llm.bind_tools(
    tools, tool_choice="any"
)

# Set up response chain
response_chain = rag_template | llm


def inspect_conversation_node(
    state: MessagesState, config: RunnableConfig
) -> Dict[str, BaseMessage]:
    """Inspects the conversation state and returns the next message using the conversation inspector."""
    response = inspect_conversation.invoke(state, config)
    return {"messages": response}


def generate_node(
    state: MessagesState, config: RunnableConfig
) -> Dict[str, BaseMessage]:
    """Generates a response using the RAG template and returns it as a message."""
    response = response_chain.invoke(state, config)
    return {"messages": response}


# Flow:
# 1. Start with agent node that inspects conversation using inspect_conversation_node
# 2. Agent node connects to tools node which can either:
#    - Retrieve relevant docs using retrieve_docs tool
#    - End tool usage with should_continue tool
# 3. Tools node connects to generate node which produces final response
# 4. Generate node connects to END to complete the workflow

workflow = StateGraph(MessagesState)
workflow.add_node("agent", inspect_conversation_node)
workflow.add_node("generate", generate_node)
workflow.set_entry_point("agent")

workflow.add_node(
    "tools",
    ToolNode(
        tools=tools,
        # With False, tool errors won't be caught by LangGraph
        handle_tool_errors=False,
    ),
)
workflow.add_edge("agent", "tools")
workflow.add_edge("tools", "generate")

workflow.add_edge("generate", END)

chain = workflow.compile()
