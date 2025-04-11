# Copyright 2024 Google, LLC.
# This software is provided as-is, without warranty
# or representation for any use or purpose.
# Your use of it is subject to your agreement with Google.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from dataclasses import dataclass, field
import logging
import os
import sys
from typing import Any, Callable, List, Optional

from bs4 import BeautifulSoup
from google import genai
import httpx
import praw
from pydantic import BaseModel, Field
from pydantic_ai import Agent, ModelRetry, RunContext
from pydantic_ai.models.vertexai import VertexAIModel
from pydantic_ai.tools import ToolDefinition

# --- General Configuration ---
USER_AGENT = "SwotAgent/1.0"
ANALYZE_URL = "https://wikipedia.org"
RETRIES = 3
logging.basicConfig(level=logging.INFO)
sys.excepthook = lambda *args: None

# --- Google Cloud Configuration ---
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
SERVICE_ACCOUNT_FILE = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
LOCATION = "us-central1"
MODEL = "gemini-2.0-flash-live-preview-04-09"

# --- Reddit API Configuration ---
REDDIT_MAX_INSIGHTS = 5
REDDIT_MAX_INSIGHT_LENGTH = 400
REDDIT_CLIENT_ID = os.environ.get("REDDIT_CLIENT_ID")
REDDIT_CLIENT_SECRET = os.environ.get("REDDIT_CLIENT_SECRET")


@dataclass
class SwotAgentDeps:
    """Dependencies for the SwotAgent."""

    request: Optional[Any] = None
    update_status_func: Optional[Callable] = None
    tool_history: List[str] = field(default_factory=list)
    try:
        reddit: praw.Reddit = praw.Reddit(
            client_id=REDDIT_CLIENT_ID,
            client_secret=REDDIT_CLIENT_SECRET,
            user_agent=USER_AGENT,
            check_for_async=False,
        )
    except praw.exceptions.PRAWException as e:
        reddit = None
        logging.info(
            f"Reddit client not initialized. Please set the REDDIT_CLIENT_ID and REDDIT_CLIENT_SECRET environment variables: {e}"
        )
    try:
        client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    except ValueError as e:
        client = None
        logging.info(
            f"Gemini client not initialized. Please set the GOOGLE_CLOUD_PROJECT and GOOGLE_APPLICATION_CREDENTIALS environment variables: {e}"
        )


class SwotAnalysis(BaseModel):
    """Represents a SWOT analysis with strengths, weaknesses, opportunities, threats, and an overall analysis."""

    strengths: List[str] = Field(
        description="Internal strengths of the product/service"
    )
    weaknesses: List[str] = Field(
        description="Internal weaknesses of the product/service"
    )
    opportunities: List[str] = Field(description="External opportunities in the market")
    threats: List[str] = Field(description="External threats in the market")
    analysis: str = Field(
        description="A comprehensive analysis explaining the SWOT findings and their implications"
    )


async def report_tool_usage(
    ctx: RunContext[SwotAgentDeps], tool_def: ToolDefinition
) -> ToolDefinition:
    """Reports tool usage and results to update_status_func."""

    if tool_def.name in ctx.deps.tool_history:
        # Tool has already been used and reported
        return tool_def

    if ctx.deps.update_status_func:
        await ctx.deps.update_status_func(
            ctx.deps.request,
            f"Using tool: {tool_def.name}...",
        )
        ctx.deps.tool_history.append(tool_def.name)

    return tool_def


swot_agent = Agent(
    model=VertexAIModel(
        model_name=MODEL,
        service_account_file=SERVICE_ACCOUNT_FILE,
        project_id=PROJECT_ID,
        region=LOCATION,
    ),
    deps_type=SwotAgentDeps,
    result_type=SwotAnalysis,
    system_prompt="""
        You are a strategic business analyst tasked with performing SWOT analysis.
        Analyze the given URL, identify internal strengths and weaknesses,
        and evaluate external opportunities and threats based on market conditions
        and competitive landscape. Use community insights to validate findings.

        For each category:
        - Strengths: Focus on internal advantages and unique selling points
        - Weaknesses: Identify internal limitations and areas for improvement
        - Opportunities: Analyze external factors that could be advantageous
        - Threats: Evaluate external challenges and competitive pressures

        Provide a detailed analysis that synthesizes these findings into actionable insights.
    """,
    retries=RETRIES,
)


@swot_agent.result_validator
def validate_analysis(
    _ctx: RunContext[SwotAgentDeps], value: SwotAnalysis
) -> SwotAnalysis:
    """Validates the SWOT analysis for completeness and quality."""
    issues = []

    # Check minimum number of points in each category
    min_points = 2
    categories = {
        "Strengths": value.strengths,
        "Weaknesses": value.weaknesses,
        "Opportunities": value.opportunities,
        "Threats": value.threats,
    }

    for category_name, points in categories.items():
        if len(points) < min_points:
            issues.append(
                f"{category_name}: Should have at least {min_points} points. Currently has {len(points)}."
            )

    # Check analysis length
    min_analysis_length = 100
    if len(value.analysis) < min_analysis_length:
        issues.append(
            f"Analysis should be at least {min_analysis_length} characters. Currently {len(value.analysis)} characters."
        )

    if issues:
        logging.info(f"Validation issues: {issues}")
        raise ModelRetry("\n".join(issues))

    return value


# --- Tools ---
@swot_agent.tool(prepare=report_tool_usage)
async def fetch_website_content(_ctx: RunContext[SwotAgentDeps], url: str) -> str:
    """Fetches the HTML content of the given URL."""
    logging.info(f"Fetching website content for: {url}")
    async with httpx.AsyncClient(follow_redirects=True) as http_client:
        try:
            response = await http_client.get(url)
            response.raise_for_status()
            html_content = response.text
            soup = BeautifulSoup(html_content, "html.parser")
            text_content = soup.get_text(separator=" ", strip=True)
            return text_content
        except httpx.HTTPError as e:
            logging.info(f"Request failed: {e}")
            raise


# pylint: disable=W0718
@swot_agent.tool(prepare=report_tool_usage)
async def analyze_competition(
    ctx: RunContext[SwotAgentDeps],
    product_name: str,
    product_description: str,
) -> str:
    """Analyzes the competition for the given product using the Gemini model."""
    logging.info(f"Analyzing competition for: {product_name}")

    prompt = f"""
    You are a competitive analysis expert. Analyze the competition for the following product:
    Product Name: {product_name}
    Product Description: {product_description}

    Provide a detailed analysis of:
    1. Key competitors and their market position
    2. Competitive advantages and disadvantages
    3. Market trends and potential disruptions
    4. Entry barriers and competitive pressures
    """

    if not ctx.deps.client:
        logging.info("Error: Gemini client not initialized.")
        return ""
    try:
        response = await ctx.deps.client.aio.models.generate_content(
            model=MODEL,
            contents=prompt,
        )
        return response.text
    except Exception as e:
        logging.info(f"Error analyzing competition: {e}")
        return f"Error analyzing competition: {e}"


@swot_agent.tool(prepare=report_tool_usage)
async def get_reddit_insights(
    ctx: RunContext[SwotAgentDeps],
    query: str,
    subreddit_name: str = "googlecloud",
) -> str:
    """Gathers insights from a specific subreddit related to a query using PRAW."""
    logging.info(f"Getting Reddit insights from r/{subreddit_name} for query: {query}")
    if not ctx.deps.reddit:
        logging.info("Error: Reddit client not initialized.")
        return ""
    try:
        subreddit = ctx.deps.reddit.subreddit(subreddit_name)
        search_results = subreddit.search(
            query, limit=REDDIT_MAX_INSIGHTS, sort="relevance", time_filter="all"
        )

        insights = []
        for post in search_results:
            insights.append(
                f"Title: {post.title}\n"
                f"URL: {post.url}\n"
                f"Content: {post.selftext[:REDDIT_MAX_INSIGHT_LENGTH]}...\n"
            )
        return "\n".join(insights)
    except praw.exceptions.PRAWException as e:
        logging.info(f"Error fetching Reddit data: {e}")
        return f"Error fetching Reddit data: {e}"


# pylint: disable=W0718
async def run_agent(
    url: str = ANALYZE_URL,
    deps: SwotAgentDeps = SwotAgentDeps(),
) -> SwotAnalysis | Exception:
    """
    Runs the SWOT analysis agent.

    Args:
        url: The URL to analyze.
        deps: The dependencies for the agent.

    Returns:
        The SWOT analysis result or an exception if an error occurred.
    """

    try:
        deps.tool_history = []
        result = await swot_agent.run(
            f"Perform a comprehensive SWOT analysis for this product: {url}",
            deps=deps,
        )
        logging.info(f"Agent result: {result}")

        # Send the final result to the UI via update_status_func
        if deps.update_status_func:
            await deps.update_status_func(deps.request, "Analysis Complete")

        return result.data
    except Exception as e:
        logging.exception(f"Error during agent run: {e}")

        # Send the error to the UI via update_status_func
        if deps.update_status_func:
            await deps.update_status_func(deps.request, f"Error: {e}")

        return e


if __name__ == "__main__":
    data = asyncio.run(run_agent())
    logging.info(data)
