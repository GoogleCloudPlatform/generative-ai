import os
import sys
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

os.environ["PROJECT_ID"] = "test-project"
os.environ["LOCATION"] = "us-central1"
os.environ["BUCKET"] = "test-bucket"


@patch("vertexai.preview.prompts.list_versions")
@patch("src.gcp_prompt.GcpPrompt")
@patch("google.cloud.storage.Client")
@patch("vertexai.init")
def test_evaluation_load_prompt(mock_init, mock_storage, mock_gcp_prompt, mock_prompts):
    # Setup mock behavior
    mock_instance = mock_gcp_prompt.return_value
    mock_instance.existing_prompts = {"test_prompt": "123"}

    at = AppTest.from_file("pages/3_Evaluation.py")
    at.run(timeout=30)

    # Verify the warning is triggered
    at.button(key="load_prompt_button").click().run(timeout=30)

    warnings = [w.value for w in getattr(at, "warning", [])]
    assert any("Please select a prompt before loading." in w for w in warnings)
