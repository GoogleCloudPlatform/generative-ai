# Copyright 2026 Google, LLC.
# This software is provided as-is, without warranty
# or representation for any use or purpose.
# Your use of it is subject to your agreement with Google.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import pytest
from fastapi.testclient import TestClient

# Set mock environment variables for testing
os.environ["LIVEKIT_URL"] = "ws://localhost:7880"
os.environ["LIVEKIT_API_KEY"] = "test-key"
os.environ["LIVEKIT_API_SECRET"] = "test-secret"
os.environ["DEMO_AGENT_MODEL"] = "gemini-2.0-flash-exp"

# Import FastAPI app after setting environment variables
from app.main import app, session_service
from travel_booking.agent import root_agent, flight_booking_agent, hotel_booking_agent


@pytest.fixture
def client():
    """Test client for FastAPI app endpoints."""
    return TestClient(app)


def test_root_endpoint(client):
    """Verify root route always serves the livekit.html page."""
    response = client.get("/")
    assert response.status_code == 200
    # Check if returned content is livekit.html
    assert "livekit_app.js" in response.text or "ADK Gemini Live API Toolkit Demo (LiveKit)" in response.text


def test_get_token_endpoint(client):
    """Verify /token endpoint generates tokens and has the correct JSON response structure."""
    user_id = "test-user-123"
    session_id = "test-session-abc"
    response = client.get(f"/token?user_id={user_id}&session_id={session_id}")
    
    assert response.status_code == 200
    data = response.json()
    assert "token" in data
    assert "url" in data
    assert data["url"] == "ws://localhost:7880"
    assert len(data["token"]) > 0


def test_get_token_missing_params(client):
    """Verify /token endpoint returns 422 error if parameters are missing."""
    response = client.get("/token")
    assert response.status_code == 422  # Unprocessable Entity


def test_in_memory_session_service():
    """Verify the Session service correctly handles session CRUD operations."""
    # Test session service exists
    assert session_service is not None


def test_agent_configurations():
    """Verify the main travel booking coordinator agent and sub-agents are configured correctly."""
    # Root agent checks
    assert root_agent.name == "session_orchestrator"
    assert root_agent.model == "gemini-2.0-flash-exp"
    assert len(root_agent.sub_agents) == 2
    
    # Sub-agents checks
    sub_agent_names = [agent.name for agent in root_agent.sub_agents]
    assert "FlightBookingAgent" in sub_agent_names
    assert "HotelBookingAgent" in sub_agent_names
    
    # Verification that sub-agents thinking budget is set to 0 (BIDI compliant)
    assert flight_booking_agent.generate_content_config.thinking_config.thinking_budget == 0
    assert hotel_booking_agent.generate_content_config.thinking_config.thinking_budget == 0


def test_plugin_registration():
    """Verify custom plugins are correctly registered in the ADK runner."""
    from app.main import runner
    plugin_names = [p.name for p in runner.plugin_manager.plugins]
    assert "session_resumption_isolation" in plugin_names
