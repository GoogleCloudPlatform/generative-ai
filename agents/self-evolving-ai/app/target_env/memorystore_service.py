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

"""Google Cloud Memorystore (Redis) Service Client with LRU Eviction Monitoring."""
import os
import threading
import time
from typing import Dict, Any, Optional

try:
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


class CloudMemorystoreService:  # pylint: disable=too-many-instance-attributes
    """Manages Google Cloud Memorystore for Redis connection with strict LRU capacity hooks."""

    def __init__(
        self,
        host: Optional[str] = None,
        port: int = 6379,
        max_keys: int = 5,
    ):
        self.host = host or os.getenv("MEMORYSTORE_HOST", None)
        self.port = port
        self.max_keys = max_keys
        self.lock = threading.Lock()

        self.eviction_count: int = 0
        self.hit_count: int = 0
        self.miss_count: int = 0

        # In-memory cache buffer with strict LRU semantics
        self._store: Dict[str, Any] = {}
        self._access_history: Dict[str, float] = {}

    def get(self, key: str) -> Optional[str]:
        """Fetch item with LRU touch."""
        with self.lock:
            if key in self._store:
                self.hit_count += 1
                self._access_history[key] = time.time()
                return self._store[key]
            self.miss_count += 1
            return None

    def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:  # pylint: disable=unused-argument
        """Store item with LRU eviction enforcement when capacity is reached."""
        with self.lock:
            # Check capacity
            if len(self._store) >= self.max_keys and key not in self._store:
                # Evict Least Recently Used key
                lru_key = min(self._access_history.keys(), key=lambda k: self._access_history[k])
                del self._store[lru_key]
                del self._access_history[lru_key]
                self.eviction_count += 1

            self._store[key] = value
            self._access_history[key] = time.time()
            return True

    def purge_cache(self) -> int:
        """Simulate catastrophic cache drop."""
        with self.lock:
            count = len(self._store)
            self._store.clear()
            self._access_history.clear()
            self.eviction_count += count
            return count

    def reset_stats(self) -> None:
        """Reset stats to baseline."""
        with self.lock:
            self._store.clear()
            self._access_history.clear()
            self.eviction_count = 0
            self.hit_count = 0
            self.miss_count = 0

    def get_stats(self) -> Dict[str, Any]:
        """Return real-time Memorystore telemetry."""
        with self.lock:
            total = self.hit_count + self.miss_count
            hit_ratio = (self.hit_count / total) if total > 0 else 1.0
            return {
                "active_keys": len(self._store),
                "max_keys": self.max_keys,
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "hit_ratio": round(hit_ratio, 2),
                "eviction_count": self.eviction_count,
                "service_tier": "Google Cloud Memorystore (Basic/Standard Tier)",
            }
