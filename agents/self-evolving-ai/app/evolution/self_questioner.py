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

"""AgentEvolver: Self-Questioning Shadow Sandbox & Curiosity Fault Injector."""
import threading
import time
from typing import Dict, Any
from app.target_env.memorystore_service import CloudMemorystoreService
from app.target_env.cloudsql_service import CloudSqlDatabaseService


class TokenBucketRateLimiter:
    """Thread-safe token bucket rate limiter used to admit shadow sandbox probes."""

    def __init__(self, capacity: int = 10, replenishment_rate: float = 40.0):
        self.capacity = capacity
        self.replenishment_rate = replenishment_rate
        self.tokens = float(capacity)
        self.last_update = time.perf_counter()
        self.lock = threading.Lock()

    def acquire(self, tokens: int = 1) -> bool:
        """Refill the bucket for elapsed time and try to consume `tokens`; return True if admitted."""
        with self.lock:
            now = time.perf_counter()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(float(self.capacity), self.tokens + (elapsed * self.replenishment_rate))
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            return False


class ShadowSandboxEnvironment:
    """Isolated shadow sandbox replicating production topology for zero-risk chaos probing."""

    def __init__(self, tested_capacity: int = 10, tested_rate: float = 40.0):
        self.cache = CloudMemorystoreService(max_keys=5)
        self.db = CloudSqlDatabaseService(max_connections=2, query_latency_ms=25.0)
        self.rate_limiter = TokenBucketRateLimiter(capacity=tested_capacity, replenishment_rate=tested_rate)
        self.total_probes: int = 0
        self.starvation_count: int = 0
        self.throttled_count: int = 0

    def purge_shadow_cache(self) -> int:
        """Purge shadow cache to test worst-case cold-start stampedes."""
        return self.cache.purge_cache()

    def run_concurrent_probe(self, num_requests: int = 100) -> Dict[str, Any]:
        """Fire high-concurrency burst through shadow sandbox rate limiter."""
        latencies = []
        errors_500 = 0
        throttled_429 = 0
        success_200 = 0
        threads = []
        probe_lock = threading.Lock()

        def worker(req_id: int) -> None:
            nonlocal errors_500, throttled_429, success_200
            t_start = time.perf_counter()
            admitted = self.rate_limiter.acquire(1)
            if not admitted:
                el = (time.perf_counter() - t_start) * 1000.0
                with probe_lock:
                    throttled_429 += 1
                    latencies.append(el)
                return

            cart_key = f"cart_shadow_{req_id % 15}"
            val = self.cache.get(cart_key)
            if not val:
                try:
                    self.db.execute_checkout_transaction(cart_key, timeout_s=0.5)
                    self.cache.set(cart_key, "SHADOW_VAL")
                    with probe_lock:
                        success_200 += 1
                except TimeoutError:
                    with probe_lock:
                        errors_500 += 1
            else:
                with probe_lock:
                    success_200 += 1
            el = (time.perf_counter() - t_start) * 1000.0
            with probe_lock:
                latencies.append(el)

        for i in range(num_requests):
            t = threading.Thread(target=worker, args=(i,))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        self.total_probes = num_requests
        self.starvation_count = errors_500
        self.throttled_count = throttled_429

        p99 = sorted(latencies)[int(len(latencies) * 0.99)] if latencies else 20.0
        return {
            "burst_size": num_requests,
            "success_200": success_200,
            "throttled_429": throttled_429,
            "errors_500": errors_500,
            "p99_latency_ms": round(p99, 1),
            "invariant_holds": (errors_500 == 0),
        }
