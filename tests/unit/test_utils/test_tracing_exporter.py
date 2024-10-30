# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=W0621, W0613, W0212

from typing import Any, Generator
from unittest.mock import Mock, patch

from app.utils.tracing import CloudTraceLoggingSpanExporter
from google.cloud import logging as google_cloud_logging
from google.cloud import storage
from opentelemetry.sdk.trace import ReadableSpan
import pytest


@pytest.fixture
def mock_logging_client() -> Mock:
    """Create a mock logging client."""
    return Mock(spec=google_cloud_logging.Client)


@pytest.fixture
def mock_storage_client() -> Mock:
    """Create a mock storage client."""
    return Mock(spec=storage.Client)


@pytest.fixture
def mock_credentials() -> Any:
    """Create mock credentials."""
    return Mock()


@pytest.fixture
def patch_auth(mock_credentials: Any) -> Generator[Mock, None, None]:
    """Patch the google.auth.default function."""
    with patch(
        "google.auth.default", return_value=(mock_credentials, "project")
    ) as mock_auth:
        yield mock_auth


@pytest.fixture
def patch_clients(
    mock_logging_client: Mock, mock_storage_client: Mock
) -> Generator[None, None, None]:
    """Patch the logging and storage clients."""
    with patch("google.cloud.logging.Client", return_value=mock_logging_client):
        with patch("google.cloud.storage.Client", return_value=mock_storage_client):
            yield


@pytest.fixture
def exporter(
    mock_logging_client: Mock,
    mock_storage_client: Mock,
    patch_auth: Any,
    mock_credentials: Any,
    patch_clients: Any,
) -> CloudTraceLoggingSpanExporter:
    """Create a CloudTraceLoggingSpanExporter instance for testing."""
    exporter = CloudTraceLoggingSpanExporter(
        project_id="test-project",
        logging_client=mock_logging_client,
        storage_client=mock_storage_client,
        bucket_name="test-bucket",
    )
    return exporter


def test_init(exporter: CloudTraceLoggingSpanExporter) -> None:
    """Test the initialization of CloudTraceLoggingSpanExporter."""
    assert exporter.project_id == "test-project"
    assert exporter.bucket_name == "test-bucket"
    assert exporter.debug is False


def test_store_in_gcs(exporter: CloudTraceLoggingSpanExporter) -> None:
    """Test the store_in_gcs method of CloudTraceLoggingSpanExporter."""
    span_id = "test-span-id"
    content = "test-content"
    uri = exporter.store_in_gcs(content, span_id)
    assert uri == f"gs://test-bucket/spans/{span_id}.json"
    exporter.bucket.blob.assert_called_once_with(f"spans/{span_id}.json")


@patch("json.dumps")
def test_process_large_attributes_small_payload(
    mock_json_dumps: Mock, exporter: CloudTraceLoggingSpanExporter
) -> None:
    """Test processing of small payload attributes."""
    mock_json_dumps.return_value = "a" * 100  # Small payload
    span_dict = {"attributes": {"key": "value"}}
    result = exporter._process_large_attributes(span_dict, "span-id")
    assert result == span_dict


@patch("json.dumps")
def test_process_large_attributes_large_payload(
    mock_json_dumps: Mock, exporter: CloudTraceLoggingSpanExporter
) -> None:
    """Test processing of large payload attributes."""
    mock_json_dumps.return_value = "a" * (400 * 1024 + 1)  # Large payload
    span_dict = {
        "attributes": {
            "key1": "value1",
            "traceloop.association.properties.key2": "value2",
        }
    }
    result = exporter._process_large_attributes(span_dict, "span-id")
    assert "uri_payload" in result["attributes"]
    assert "url_payload" in result["attributes"]
    assert "key1" not in result["attributes"]
    assert "traceloop.association.properties.key2" in result["attributes"]


@patch.object(CloudTraceLoggingSpanExporter, "_process_large_attributes")
def test_export(
    mock_process_large_attributes: Mock, exporter: CloudTraceLoggingSpanExporter
) -> None:
    """Test the export method of CloudTraceLoggingSpanExporter."""
    mock_span = Mock(spec=ReadableSpan)
    mock_span.get_span_context.return_value.trace_id = 123
    mock_span.get_span_context.return_value.span_id = 456
    mock_span.to_json.return_value = '{"key": "value"}'

    mock_process_large_attributes.return_value = {"processed": "data"}

    exporter.export([mock_span])

    mock_process_large_attributes.assert_called_once()
    exporter.logger.log_struct.assert_called_once()
