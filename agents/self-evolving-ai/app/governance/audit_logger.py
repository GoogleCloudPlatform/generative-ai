# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Google Cloud Logging Tamper-Evident Audit Trail."""

import time
from typing import Any

from app.config import CLOUD_LOG_NAME, PROJECT_ID, VERTEX_AI_AVAILABLE
from app.governance.cloud_log_writer import BackgroundCloudLogWriter

try:
    from google.cloud import logging as gcp_logging

    GCP_LOGGING_AVAILABLE = True
except ImportError:
    GCP_LOGGING_AVAILABLE = False


class CloudAuditLogger:
    """Tamper-evident audit logger streaming agent actions directly to Google Cloud Logging."""

    def __init__(self, project_id: str = PROJECT_ID, log_name: str = CLOUD_LOG_NAME):
        self.project_id = project_id
        self.log_name = log_name
        self._gcp_writer = None
        self.local_audit_buffer: list[dict[str, Any]] = []

        if GCP_LOGGING_AVAILABLE and VERTEX_AI_AVAILABLE:
            try:
                client = gcp_logging.Client(project=project_id)
                # Writes are batched off the request path and flushed at interpreter exit.
                self._gcp_writer = BackgroundCloudLogWriter(client.logger(log_name))
            except Exception:  # pylint: disable=broad-exception-caught
                self._gcp_writer = None

    def log_event(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        event_type: str,
        actor: str,
        action: str,
        status: str,
        details: dict[str, Any],
        severity: str = "INFO",
    ) -> dict[str, Any]:
        """Record an immutable security event."""
        payload = {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "project_id": self.project_id,
            "event_type": event_type,
            "actor": actor,
            "action": action,
            "status": status,
            "details": details,
        }

        # Send to Google Cloud Logging (non-blocking, batched)
        if self._gcp_writer:
            self._gcp_writer.submit(payload, severity=severity)

        self.local_audit_buffer.append(payload)
        return payload
