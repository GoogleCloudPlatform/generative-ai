from google.adk.agents import LlmAgent
from travel_booking.agent import session_orchestrator
from travel_booking.agents import flight_booking_agent, hotel_booking_agent

def test_orchestrator_sub_agents():
    # The root orchestrator must have FlightBookingAgent and HotelBookingAgent
    # registered as sub-agents, ensuring routing support between them.
    assert len(session_orchestrator.sub_agents) == 2
    sub_agent_names = [sa.name for sa in session_orchestrator.sub_agents]
    assert "FlightBookingAgent" in sub_agent_names
    assert "HotelBookingAgent" in sub_agent_names

def test_flight_booking_agent_sub_agents():
    # FlightBookingAgent must have HotelBookingAgent registered as a sub-agent
    # to support context handoffs when users request lodging.
    assert len(flight_booking_agent.sub_agents) == 1
    assert flight_booking_agent.sub_agents[0].name == "HotelBookingAgent"

def test_hotel_booking_agent_sub_agents():
    # HotelBookingAgent is a terminal leaf node and has no sub-agents.
    assert len(hotel_booking_agent.sub_agents) == 0
