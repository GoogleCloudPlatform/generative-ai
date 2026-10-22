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

"""Non-blocking, batched writer for Google Cloud Logging.

Calling `Logger.log_struct()` performs a synchronous gRPC `WriteLogEntries` round-trip. Doing that
on the request path (one call per simulated checkout) serializes a 50-request burst behind ~50
network calls. This writer queues entries and ships them in batches from a single daemon thread,
and flushes any remaining entries at interpreter exit.
"""

import atexit
import queue
import threading
import time
from typing import Any


class BackgroundCloudLogWriter:
    """Queue structured log entries and commit them to Cloud Logging in background batches."""

    def __init__(self, gcp_logger: Any, max_batch: int = 200, max_queue: int = 20_000):
        self._logger = gcp_logger
        self._max_batch = max_batch
        self._queue: queue.Queue[tuple] = queue.Queue(maxsize=max_queue)
        self.dropped_entries = 0
        self._thread = threading.Thread(
            target=self._run, name="cloud-log-writer", daemon=True
        )
        self._thread.start()
        atexit.register(self.flush)

    def submit(self, payload: dict[str, Any], severity: str = "INFO") -> None:
        """Enqueue an entry without blocking (drops under extreme backpressure rather than stalling)."""
        try:
            self._queue.put_nowait((payload, severity))
        except queue.Full:
            self.dropped_entries += 1

    def flush(self, timeout: float = 5.0) -> None:
        """Wait (bounded) until queued entries have been committed."""
        deadline = time.monotonic() + timeout
        while self._queue.unfinished_tasks and time.monotonic() < deadline:
            time.sleep(0.05)

    def _run(self) -> None:
        while True:
            items = [self._queue.get()]
            while len(items) < self._max_batch:
                try:
                    items.append(self._queue.get_nowait())
                except queue.Empty:
                    break
            try:
                batch = self._logger.batch()
                for payload, severity in items:
                    batch.log_struct(payload, severity=severity)
                batch.commit()
            except Exception:  # pylint: disable=broad-exception-caught
                pass  # Telemetry export must never break the workload
            finally:
                for _ in items:
                    self._queue.task_done()
