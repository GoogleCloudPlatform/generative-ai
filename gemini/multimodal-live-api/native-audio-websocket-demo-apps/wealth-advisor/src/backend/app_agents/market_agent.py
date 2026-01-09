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


#!/usr/bin/env python
# -*- coding: utf-8 -*-
# src/backend/app_agents/market_agent.py

from google.adk.agents import Agent
from google.adk.tools import google_search
from backend.app_settings import ApplicationSettings, get_application_settings

settings: ApplicationSettings = get_application_settings()

# Define a specialized agent for market research
market_research_agent = Agent(
    name="market_research_agent",
    model=settings.agent.chat_model,
    description="Useful for finding current market summaries, index performance (S&P 500, Nasdaq), and financial news.",
    instruction="""
    You are a market researcher. 
    1. When asked for a summary, use Google Search to find the latest performance of major indices (S&P 500, Nasdaq, Dow Jones) and key market events from reliable financial news sources (Bloomberg, CNBC, Yahoo Finance).
    2. Synthesize this into a concise 3-5 sentence summary of the current market mood (Bullish/Bearish/Neutral) and key drivers.
    3. Always cite the date of the information found.
    """,
    # This connects the agent to the live Google Search Engine
    tools=[google_search],
)