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

"""Google Cloud SQL Database Service with Managed Connection Pool."""
import sqlite3
import threading
import time
from typing import Dict, Any


class CloudSqlDatabaseService:  # pylint: disable=too-many-instance-attributes
    """Simulates Google Cloud SQL instance with rigid connection pool limits."""

    def __init__(self, max_connections: int = 2, query_latency_ms: float = 100.0):
        self.max_connections = max_connections
        self.query_latency_s = query_latency_ms / 1000.0
        self.semaphore = threading.Semaphore(max_connections)
        self.lock = threading.Lock()

        self.active_connections: int = 0
        self.waiting_threads: int = 0
        self.total_queries: int = 0
        self.total_timeouts: int = 0
        self.window_timeouts: int = 0

        self._conn = sqlite3.connect(":memory:", check_same_thread=False)
        self._init_db()

    def _init_db(self) -> None:
        with self._conn:
            self._conn.execute(
                "CREATE TABLE IF NOT EXISTS cart_orders (cart_id TEXT PRIMARY KEY, amount REAL, created_at REAL)"
            )

    def execute_checkout_transaction(self, cart_id: str, timeout_s: float = 1.0) -> Dict[str, Any]:
        """Execute a transactional DB write under connection pool concurrency controls."""
        with self.lock:
            self.waiting_threads += 1

        # Hold a reference to the semaphore we acquire from, so a concurrent reset_pool()
        # (which swaps in a fresh semaphore) cannot cause us to release the wrong one.
        semaphore = self.semaphore
        acquired = semaphore.acquire(blocking=True, timeout=timeout_s)  # pylint: disable=consider-using-with

        with self.lock:
            self.waiting_threads -= 1

        if not acquired:
            with self.lock:
                self.total_timeouts += 1
                self.window_timeouts += 1
            raise TimeoutError(f"Cloud SQL connection pool exhausted! Timeout={timeout_s}s")

        with self.lock:
            self.active_connections += 1
            self.total_queries += 1

        try:
            # Emulate real network I/O and query latency
            time.sleep(self.query_latency_s)
            with self.lock:
                cursor = self._conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO cart_orders VALUES (?, ?, ?)",
                    (cart_id, 49.99, time.time()),
                )
                self._conn.commit()
            return {"status": "SUCCESS", "cart_id": cart_id, "amount": 49.99}
        finally:
            with self.lock:
                self.active_connections = max(self.active_connections - 1, 0)
            semaphore.release()

    def clear_window_saturation(self) -> None:
        """Clear window timeout saturation indicator before a new burst."""
        with self.lock:
            self.window_timeouts = 0

    def reset_pool(self) -> None:
        """Reset connection pool counters."""
        with self.lock:
            self.active_connections = 0
            self.waiting_threads = 0
            self.total_queries = 0
            self.total_timeouts = 0
            self.window_timeouts = 0
        self.semaphore = threading.Semaphore(self.max_connections)

    def get_pool_stats(self) -> Dict[str, Any]:
        """Return Cloud SQL connection pool utilization."""
        with self.lock:
            if self.active_connections > 0:
                utilization = self.active_connections / self.max_connections
            elif self.window_timeouts > 0:
                utilization = 1.0
            else:
                utilization = 0.0
            return {
                "active_connections": self.active_connections,
                "waiting_threads": self.waiting_threads,
                "pool_limit": self.max_connections,
                "pool_utilization": round(utilization, 2),
                "total_queries": self.total_queries,
                "total_timeouts": self.total_timeouts,
                "engine": "Google Cloud SQL (PostgreSQL/MySQL HA Instance)",
            }
