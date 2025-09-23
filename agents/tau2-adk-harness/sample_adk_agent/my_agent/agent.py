# FILE: sample_adk_agent/my_agent/agent.py

from google.adk.agents import Agent
from typing import List

# These are the ADK-native tool definitions.
# Their signatures and docstrings are what the ADK agent's LLM will see.
# The code inside these functions will NEVER be executed by the harness.
def adk_find_flights(origin: str, destination: str, date: str) -> List[dict]:
    """
    Searches for available direct flights between an origin and a destination on a specific date.
    Args:
        origin: The three-letter IATA code for the origin airport (e.g., 'SFO').
        destination: The three-letter IATA code for the destination airport (e.g., 'JFK').
        date: The desired flight date in 'YYYY-MM-DD' format.
    Returns:
        A list of available flights, each represented as a dictionary.
    """
    pass # The harness executes the real tau2 tool.

def adk_get_booking_details(reservation_id: str) -> dict:
    """
    Retrieves the full details for a specific flight reservation using its ID.
    Args:
        reservation_id: The unique identifier for the reservation (e.g., '4WQ150').
    Returns:
        A dictionary containing the reservation details.
    """
    pass

def adk_cancel_reservation(reservation_id: str) -> dict:
    """
    Cancels an entire flight reservation using its unique ID.
    Args:
        reservation_id: The unique identifier for the reservation to be cancelled.
    Returns:
        A dictionary confirming the cancellation status.
    """
    pass

def adk_transfer_to_human(summary: str) -> dict:
    """
    Transfers the user to a human agent when a request cannot be handled by the available tools or policy.
    Args:
        summary: A brief summary of the user's issue for the human agent.
    Returns:
        A dictionary confirming the transfer.
    """
    pass

# This is the agent we will evaluate.
root_agent = Agent(
    name="adk_airline_agent",
    model="gemini-2.5-flash",
    description="An ADK agent for booking, finding, and cancelling flight reservations.",
    instruction=(
        "You are a task-oriented airline assistant. Your ONLY goal is to use the provided tools to fulfill the user's request. "
        "You MUST call a tool in your first turn if the user's request contains enough information to do so. "
        "Analyze the user's request and immediately call the appropriate tool to find, get details for, or cancel a reservation. "
        "NOTE: If the user wants to cancel you must first check if all criteria for cancellation are met! "
        "In particular check whether the flight was made within 24 hours. This is important!"
    ),
    tools=[
        adk_find_flights,
        adk_get_booking_details,
        adk_cancel_reservation,
        adk_transfer_to_human,
    ],
)