import os
import pathlib
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from ..tools import (
    search_flights,
    book_flight,
    cancel_flight
)
from .hotel_booking import hotel_booking_agent

PROMPTS_DIR = pathlib.Path(__file__).parent.parent / "prompts"

def load_prompt(filename: str) -> str:
    with open(PROMPTS_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()

MODEL_NAME = os.getenv("DEMO_AGENT_MODEL", "gemini-2.5-flash-native-audio")

is_audio = "audio" in MODEL_NAME.lower() or "live" in MODEL_NAME.lower()
prompt_file = "flight_booking_audio.txt" if is_audio else "flight_booking.txt"

flight_booking_agent = LlmAgent(
    name="FlightBookingAgent",
    model=MODEL_NAME,
    description=(
        "**Purpose:** Help users search, book, and cancel flights.\n\n"
        "**Use this agent for:**\n"
        "- Flight searches matching origin, destination, and date\n"
        "- Booking flights with passenger name\n"
        "- Cancelling existing flight bookings\n\n"
        "**Sub-Agents orchestrated:**\n"
        "- **HotelBookingAgent**: Use when user wants to search or book hotels for their trip.\n\n"
        "**Behavior constraints:**\n"
        "- Silence handoff to HotelBookingAgent\n"
        "- Never mention tool/agent names explicitly to the user"
    ),
    instruction=load_prompt(prompt_file),
    tools=[
        FunctionTool(func=search_flights),
        FunctionTool(func=book_flight),
        FunctionTool(func=cancel_flight)
    ],
    sub_agents=[hotel_booking_agent]
)
