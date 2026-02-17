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
    instruction="Employ the `google_search` tool to fetch live market data, specifically current prices and YTD returns for client-specified stocks. "
    "Limit your query to the exact stock class found in the client's portfolio (e.g., Alphabet Class C vs A) as listed in their profile. "
    "Always reference the client's profile to ensure accuracy. "
    "Your response must directly address the client's inquiry using the tool's data. Avoid generic market commentary; tie everything back to their specific holdings. "
    "You can use the profile's investment details to calculate or discuss performance (like ROI). "
    "Keep your text response brief and precise (max 2-3 sentences). "
    "Example finding: GOOGL is at $235.17 with a 23.36% YTD return. "
    "CRITICAL: You must output a valid JSON string containing ONLY these keys: 'stockName', 'price', and 'ytdReturn'. "
    "Do NOT include markdown formatting or code blocks around the JSON."
    'Example JSON Output: {{"stockName": "GOOGL", "price": "$235.17", "ytdReturn": "23.36%"}}',
    description="An AI agent that leverages it's tools to access real-time stock performance information from the internet for the client, relating it to their financial profile data.",
    tools=[google_search]
)
