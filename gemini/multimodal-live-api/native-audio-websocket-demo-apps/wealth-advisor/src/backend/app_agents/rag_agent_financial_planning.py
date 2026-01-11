# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
from backend.app_logging import get_logger
from vertexai.preview import rag
from .utils import _corpus_exists
from google.adk.agents import Agent
from google.adk.tools import FunctionTool

if "RUN_CONTAINER_LOCALLY" in os.environ and "FINANCIAL_ADVISOR_AE_ENV" not in os.environ:
    from backend.app_settings import get_application_settings
elif "RUN_CONTAINER_LOCALLY" not in os.environ and "FINANCIAL_ADVISOR_AE_ENV" in os.environ:
    from backend.app_settings import get_application_settings
else:
    from backend.app_settings import get_application_settings

settings = get_application_settings()
logger = get_logger(__name__)


def search_financial_documents(query: str) -> str:
    """
    Searches internal financial planning documents for information on products, rates, and retirement plans.

    Args:
        query: The search query (e.g., "What are the CD rates?", "How does a 529 plan work?").

    Returns:
        A summary of the relevant information found in the documents.
    """
    logger.info(f"[RAG Tool] Starting search for query: '{query}'")

    rag_corpus_name = _corpus_exists()
    logger.info(f"[RAG Tool] Resolved corpus name: {rag_corpus_name}")

    if not rag_corpus_name:
        logger.warning("[RAG Tool] RAG Corpus not found or configured.")
        return "Error: Financial knowledge base (RAG Corpus) not found or configured."

    try:
        logger.info(f"[RAG Tool] Executing retrieval_query against {rag_corpus_name}...")
        response = rag.retrieval_query(
            rag_resources=[rag.RagResource(rag_corpus=rag_corpus_name)],
            text=query,
            rag_retrieval_config=rag.RagRetrievalConfig(
                top_k=3,  # Keep it concise
            ),
        )
        logger.info("[RAG Tool] Retrieval query completed.")

        if response and response.contexts and response.contexts.contexts:
            # Combine the retrieved contexts into a single string
            results = []
            for context in response.contexts.contexts:
                results.append(context.text)

            combined_result = "\n\n".join(results)
            logger.info(
                f"[RAG Tool] Found {len(results)} contexts. Returning result (len={len(combined_result)}). Preview: {combined_result[:200]}..."
            )
            return combined_result
        else:
            logger.info("[RAG Tool] No relevant information found.")
            return "No relevant information found in the financial documents."

    except Exception as e:
        logger.error(f"[RAG Tool] Error during retrieval: {str(e)}", exc_info=True)
        return f"Error searching financial documents: {str(e)}"


financial_rag_tool = FunctionTool(search_financial_documents)

rag_agent_financial_planning = Agent(
    name="financial_planning_rag_agent",
    model=settings.agent.chat_model,
    instruction="You are a financial planning assistant. Use the `search_financial_documents` tool to answer questions about financial products, retirement planning, and CD rates based on the internal knowledge base. If the tool returns no information, state that you don't have that information in your knowledge base.",
    tools=[financial_rag_tool],
    description="Agent for searching financial planning documents.",
)
