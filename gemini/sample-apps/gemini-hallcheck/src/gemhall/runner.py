import asyncio
import random
import time
from collections import deque

from google import genai
from google.genai import types
from google.genai.errors import ClientError


class _AsyncRateLimiter:
    def __init__(self, rpm: int | None = None):
        self.rpm = rpm
        self._win = 60.0
        self._q = deque()
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        if not self.rpm:
            return
        while True:
            async with self._lock:
                now = asyncio.get_event_loop().time()
                while self._q and now - self._q[0] > self._win:
                    self._q.popleft()
                if len(self._q) < self.rpm:
                    self._q.append(now)
                    return
                sleep_for = self._win - (now - self._q[0]) + 0.01
            await asyncio.sleep(sleep_for)


class _RateLimiter:
    def __init__(self, rpm: int | None = None):
        self.rpm = rpm
        self._win = 60.0
        self._q = deque()

    def acquire(self) -> None:
        if not self.rpm:
            return
        while True:
            now = time.monotonic()
            while self._q and now - self._q[0] > self._win:
                self._q.popleft()
            if len(self._q) < self.rpm:
                self._q.append(now)
                return
            sleep_for = self._win - (now - self._q[0]) + 0.01
            time.sleep(sleep_for)


class GeminiRunner:
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        *,
        temperature: float = 0.0,
        thinking_budget: int = 0,
        seed: int | None = 1234,
        rpm_limit: int | None = None,
        max_retries: int = 6,
    ):
        self.client = genai.Client()
        self.model = model
        self.temperature = temperature
        self.thinking_budget = thinking_budget
        self.seed = seed
        self.max_retries = max_retries
        self._rl = _RateLimiter(rpm_limit)

    def generate(self, prompt: str) -> str:
        cfg = types.GenerateContentConfig(
            temperature=self.temperature,
            seed=self.seed,
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget)
            if self.thinking_budget is not None
            else None,
            max_output_tokens=128,
        )
        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            self._rl.acquire()
            try:
                resp = self.client.models.generate_content(
                    model=self.model, contents=prompt, config=cfg
                )
                return (resp.text or "").strip()
            except ClientError as e:
                if (
                    getattr(e, "status_code", None) == 429
                    and attempt < self.max_retries
                ):
                    delay = None
                    try:
                        details = (
                            (getattr(e, "response_json", {}) or {})
                            .get("error", {})
                            .get("details", [])
                        )
                        for d in details:
                            if d.get("@type", "").endswith("RetryInfo"):
                                s = d.get("retryDelay", "0s")
                                if s.endswith("s"):
                                    delay = float(s[:-1])
                                break
                    except Exception:
                        pass
                    sleep_s = delay if delay is not None else min(60.0, backoff)
                    sleep_s *= 0.8 + 0.4 * random.random()  # jitter
                    time.sleep(sleep_s)
                    backoff *= 2
                    continue
                raise
        return None


class AsyncGeminiRunner:
    def __init__(
        self,
        model: str = "gemini-2.5-flash",
        *,
        temperature: float = 0.0,
        thinking_budget: int = 0,
        seed: int | None = 1234,
        rpm_limit: int | None = None,
        max_retries: int = 6,
    ):
        self.client = genai.Client()
        self.model = model
        self.temperature = temperature
        self.thinking_budget = thinking_budget
        self.seed = seed
        self.max_retries = max_retries
        self._rl = _AsyncRateLimiter(rpm_limit)

    async def generate(self, prompt: str) -> str:
        cfg = types.GenerateContentConfig(
            temperature=self.temperature,
            seed=self.seed,
            thinking_config=types.ThinkingConfig(thinking_budget=self.thinking_budget)
            if self.thinking_budget is not None
            else None,
            max_output_tokens=128,
        )
        backoff = 1.0
        for attempt in range(1, self.max_retries + 1):
            await self._rl.acquire()
            try:
                resp = await self.client.aio.models.generate_content(
                    model=self.model, contents=prompt, config=cfg
                )
                return (resp.text or "").strip()
            except ClientError as e:
                if (
                    getattr(e, "status_code", None) == 429
                    and attempt < self.max_retries
                ):
                    delay = None
                    try:
                        details = (
                            (getattr(e, "response_json", {}) or {})
                            .get("error", {})
                            .get("details", [])
                        )
                        for d in details:
                            if d.get("@type", "").endswith("RetryInfo"):
                                s = d.get("retryDelay", "0s")
                                if s.endswith("s"):
                                    delay = float(s[:-1])
                                break
                    except Exception:
                        pass
                    sleep_s = delay if delay is not None else min(60.0, backoff)
                    sleep_s *= 0.8 + 0.4 * random.random()  # jitter
                    await asyncio.sleep(sleep_s)
                    backoff *= 2
                    continue
                raise
        return None
