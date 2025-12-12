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
