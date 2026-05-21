import os
import pathlib
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

from .tools import get_user_preferences
from .agents import flight_booking_agent, hotel_booking_agent
from .telemetry import init_telemetry

init_telemetry()

PROMPTS_DIR = pathlib.Path(__file__).parent / "prompts"

def load_prompt(filename: str) -> str:
    with open(PROMPTS_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()

# Use DEMO_AGENT_MODEL for root agent to support Live API (audio)
MODEL_NAME = os.getenv("DEMO_AGENT_MODEL", "gemini-2.5-flash-native-audio")

is_audio = "audio" in MODEL_NAME.lower() or "live" in MODEL_NAME.lower()
prompt_file = "orchestrator_v1_audio.txt" if is_audio else "orchestrator_v1.txt"

# Define common config for all agents (No Thinking Budget)
config_no_thinking = types.GenerateContentConfig(
    thinking_config=types.GenerationConfigThinkingConfig(
        thinking_budget=0
    )
)

# Apply to sub-agents
flight_booking_agent.generate_content_config = config_no_thinking
hotel_booking_agent.generate_content_config = config_no_thinking

# Reset parent agent to avoid Pydantic validation error on reload
flight_booking_agent.parent_agent = None
hotel_booking_agent.parent_agent = None

session_orchestrator = LlmAgent(
    name="session_orchestrator",
    model=MODEL_NAME,
    description=(
        "**Purpose:** Main travel booking coordinator. Welcomes user, manages general questions, and delegates to specialists.\n\n"
        "**Sub-Agents orchestrated:**\n"
        "1. **FlightBookingAgent**: For searching, booking, and cancelling flights.\n"
        "2. **HotelBookingAgent**: For searching, booking, and cancelling hotel rooms.\n\n"
        "**Behavior constraints:**\n"
        "- Route silently without announcing the transition\n"
        "- Never mention tools, agents, or internal mechanisms to the user"
    ),
    instruction=load_prompt(prompt_file),
    tools=[
        FunctionTool(func=get_user_preferences)
    ],
    sub_agents=[flight_booking_agent, hotel_booking_agent],
    generate_content_config=config_no_thinking
)

root_agent = session_orchestrator
