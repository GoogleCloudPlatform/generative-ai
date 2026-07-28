import os
import pathlib
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
from ..tools import (
    search_hotels,
    book_hotel,
    cancel_hotel
)

PROMPTS_DIR = pathlib.Path(__file__).parent.parent / "prompts"

def load_prompt(filename: str) -> str:
    with open(PROMPTS_DIR / filename, "r", encoding="utf-8") as f:
        return f.read()

MODEL_NAME = os.getenv("DEMO_AGENT_MODEL", "gemini-2.5-flash-native-audio")

is_audio = "audio" in MODEL_NAME.lower() or "live" in MODEL_NAME.lower()
prompt_file = "hotel_booking_audio.txt" if is_audio else "hotel_booking.txt"

hotel_booking_agent = LlmAgent(
    name="HotelBookingAgent",
    model=MODEL_NAME,
    description=(
        "**Purpose:** Help users search, book, and cancel hotel bookings.\n\n"
        "**Use this agent for:**\n"
        "- Hotel searches matching location, check-in and check-out dates\n"
        "- Booking hotel rooms with guest name\n"
        "- Cancelling existing hotel bookings\n\n"
        "**Behavior constraints:**\n"
        "- Never mention tool/agent names explicitly to the user"
    ),
    instruction=load_prompt(prompt_file),
    tools=[
        FunctionTool(func=search_hotels),
        FunctionTool(func=book_hotel),
        FunctionTool(func=cancel_hotel)
    ]
)
