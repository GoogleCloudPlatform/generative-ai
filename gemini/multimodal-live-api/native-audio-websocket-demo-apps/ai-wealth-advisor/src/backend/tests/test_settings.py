import os
import pytest
from unittest.mock import patch, MagicMock
from backend.app_settings.settings import ApplicationSettings


# Mock google.auth.default to avoid actual GCP calls during tests
@pytest.fixture(autouse=True)
def mock_google_auth():
    with patch("google.auth.default") as mock:
        mock.return_value = (MagicMock(), "mock-project-id")
        yield mock


# Mock GoogleSecretManagerSettingsSource to avoid connecting to Secret Manager
@pytest.fixture(autouse=True)
def mock_secret_manager_source():
    with patch("gcp_pydantic_settings.secret_manager.GoogleSecretManagerSettingsSource") as mock:
        yield mock


def test_settings_defaults():
    # Set minimal required env vars if any (none expected for defaults now)
    # We clear env vars that might interfere
    with patch.dict(os.environ, {}, clear=True):
        settings = ApplicationSettings()

        # Check new fields
        assert settings.bank_name == "Financial Institution"
        assert settings.advisor_name == "Advisor"

        # Check groups exist
        assert settings.google_cloud is not None
        assert settings.agent is not None
        assert settings.voice is not None
        assert settings.search is not None

        # Check default values
        assert settings.voice.model_id == "gemini-live-2.5-flash-preview-native-audio-09-2025"
        assert settings.agent.chat_model == "gemini-2.5-flash"


def test_settings_env_overrides_with_aliases():
    """Test that legacy environment variables (aliases) still work."""
    env_vars = {
        "BANK_NAME": "My Bank",
        "ADVISOR_NAME": "My Advisor",
        # Test Alias: VERTEX_AI__ -> google_cloud
        "VERTEX_AI__PROJECT_ID": "env-project-id",
        "VERTEX_AI__LOCATION": "us-east1",
        # Test Alias: ADK__ -> agent
        "ADK__CHAT_MODEL": "gemini-1.5-pro",
        # Test Alias: GEMINI_LIVE__ -> voice
        "GEMINI_LIVE__VOICE_NAME": "Charon",
    }
    with patch.dict(os.environ, env_vars, clear=True):
        settings = ApplicationSettings()

        # Verify Overrides
        assert settings.bank_name == "My Bank"
        assert settings.advisor_name == "My Advisor"

        # Verify Alias Mapping
        assert settings.google_cloud.project_id == "env-project-id"
        assert settings.google_cloud.location == "us-east1"
        assert settings.agent.chat_model == "gemini-1.5-pro"
        assert settings.voice.voice_name == "Charon"
