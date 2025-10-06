# Copyright 2024 Google, LLC. This software is provided as-is, without
# warranty or representation for any use or purpose. Your use of it is
# subject to your agreement with Google.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from fastapi.testclient import TestClient
from main import app
import pytest

client = TestClient(app)


def test_read_root() -> None:
    """Test the root endpoint returns the index page."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "SWOT Analysis" in response.text


def test_analyze_endpoint() -> None:
    """Test the analyze endpoint with a valid URL."""
    test_url = "https://example.com"
    response = client.post("/analyze", data={"url": test_url})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_analyze_invalid_url() -> None:
    """Test the analyze endpoint with an invalid URL."""
    test_url = "not-a-valid-url"
    response = client.post("/analyze", data={"url": test_url})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_analyze_empty_url() -> None:
    """Test the analyze endpoint with an empty URL."""
    response = client.post("/analyze", data={"url": ""})
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_status_endpoint() -> None:
    """Test the status endpoint."""
    response = client.get("/status")
    assert response.status_code == 200
    assert response.headers["content-type"] == "text/html; charset=utf-8"


def test_result_endpoint_no_result() -> None:
    """Test the result endpoint when no analysis is complete."""
    response = client.get("/result")
    assert response.status_code == 200
    assert response.text.strip() == ""


@pytest.mark.asyncio
async def test_full_analysis_flow() -> None:
    """Test the complete analysis flow from submission to result."""
    # 1. Submit URL for analysis
    test_url = "https://google.com"
    analyze_response = client.post("/analyze", data={"url": test_url})
    assert analyze_response.status_code == 200

    # 2. Check status
    status_response = client.get("/status")
    assert status_response.status_code == 200

    # 3. Check result (might be empty initially)
    result_response = client.get("/result")
    assert result_response.status_code == 200


def test_concurrent_requests() -> None:
    """Test handling of concurrent analysis requests."""
    test_url = "https://google.com"
    # Submit multiple requests in quick succession
    responses = [client.post("/analyze", data={"url": test_url}) for _ in range(3)]

    # All requests should be accepted
    for response in responses:
        assert response.status_code == 200
