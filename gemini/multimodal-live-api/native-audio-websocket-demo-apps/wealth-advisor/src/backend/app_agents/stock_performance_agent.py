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


import json

from copy import deepcopy
from typing import Any, Dict, Optional

from backend.app_logging import get_logger
from backend.app_settings import get_application_settings
from google import genai
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.tools import BaseTool, ToolContext, google_search
from google.genai import types
from google.genai.types import GenerateContentConfig
from pydantic import BaseModel

logger = get_logger(__name__)

app_settings = get_application_settings()

stock_performance_agent = Agent(
    name="stock_performance_agent",
    model=app_settings.agent.chat_model,
    instruction="Use the `google_search` tool for accessing real-time stock performance, focusing on current market price and year-to-date returns. "
    "Restrict your search to only the stock specified by the client. Be sure to only include the stock class (e.g. Alphabet class C) the client holds in their portfolio in your search. "
    "The client's stock portfolio, including stock-specific classes, is in the client profile information. Always reference this for performing the search accurately."
    "You MUST use the tool's output to address the client's question or comment. Do NOT simply respond with general stock performance without tying it back to the client's investment portfolio. "
    "You may reference the client's profile information, which includes financial investments details, to help generate a response for calculating how the client's stock investments are performing (e.g. returns on investment)."
    "Be sure to provide brief, concise, yet accurate information. Keep responses short: 2-3 sentences."
    "Example search result: The current price for GOOGL is $235.17, with a YTD return of 23.36%. "
    "You MUST generate a valid JSON string based on the search results. The JSON string must only contain the keys 'stockName', 'price', and 'ytdReturn'. Do NOT wrap the JSON in markdown code blocks or any other formatting."
    'Example Output: {{"stockName": "GOOGL", "price": "$235.17", "ytdReturn": "23.36%"}}',
    description="An AI agent that leverages it's tools to access real-time stock performance information from the internet for the client, relating it to their financial profile data.",
    tools=[google_search]
)
