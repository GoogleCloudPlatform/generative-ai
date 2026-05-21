from google.adk.agents import LlmAgent
from travel_booking.agent import root_agent, session_orchestrator
from travel_booking.agents import flight_booking_agent, hotel_booking_agent

def test_root_agent_structure():
    assert isinstance(root_agent, LlmAgent)
    assert root_agent == session_orchestrator
    assert root_agent.name == "session_orchestrator"
    assert len(root_agent.sub_agents) == 2
    
    # Verify sub-agents are registered under root agent
    sub_agent_names = [sa.name for sa in root_agent.sub_agents]
    assert "FlightBookingAgent" in sub_agent_names
    assert "HotelBookingAgent" in sub_agent_names

def test_flight_booking_agent_structure():
    assert isinstance(flight_booking_agent, LlmAgent)
    assert flight_booking_agent.name == "FlightBookingAgent"
    
    # Verify registered tools (FunctionTools)
    tool_names = [t.name for t in flight_booking_agent.tools]
    assert "search_flights" in tool_names
    assert "book_flight" in tool_names
    assert "cancel_flight" in tool_names
    
    # Verify HotelBookingAgent is configured as a sub-agent
    assert len(flight_booking_agent.sub_agents) == 1
    assert flight_booking_agent.sub_agents[0] == hotel_booking_agent

def test_hotel_booking_agent_structure():
    assert isinstance(hotel_booking_agent, LlmAgent)
    assert hotel_booking_agent.name == "HotelBookingAgent"
    
    # Verify registered tools (FunctionTools)
    tool_names = [t.name for t in hotel_booking_agent.tools]
    assert "search_hotels" in tool_names
    assert "book_hotel" in tool_names
    assert "cancel_hotel" in tool_names
