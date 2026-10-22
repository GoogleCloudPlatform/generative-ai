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

"""APEX Layer 1: Gemini-powered synthesis of dynamic tool code, gated by sandbox safety checks.

Pipeline for every synthesized artifact (LLM output is treated as untrusted code):
  1. Gemini generates a `TokenBucketRateLimiter` class from the live incident diagnosis.
  2. Static sandbox policy (AST): import allow-list, no dangerous builtins, no dunder access.
  3. Compilation in a restricted namespace (curated builtins, guarded import).
  4. Behavioural verification (unit tests run with a timeout): burst capacity, refill,
     mutable parameters, thread safety, stats contract.
Failures are fed back to Gemini for a bounded number of repair attempts. If Gemini is
unavailable or never passes the gates, a reviewed reference template is used instead and
the result is labelled as such.
"""
import ast
import builtins
import collections
import math
import re
import threading
import time
from dataclasses import dataclass, field
from types import ModuleType
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

ALLOWED_IMPORTS = {"time", "threading", "math", "collections"}

FORBIDDEN_NAMES = {
    "eval", "exec", "compile", "__import__", "open", "input", "breakpoint", "globals", "locals",
    "vars", "getattr", "setattr", "delattr", "help", "exit", "quit", "memoryview", "type",
    "__builtins__", "__loader__", "__spec__",
}

_SAFE_BUILTIN_NAMES = [
    "abs", "all", "any", "bool", "classmethod", "dict", "enumerate", "Exception", "float", "int",
    "isinstance", "len", "list", "max", "min", "object", "property", "range", "round",
    "RuntimeError", "set", "sorted", "staticmethod", "str", "sum", "super", "tuple", "TypeError",
    "ValueError", "zip", "None", "True", "False",
]


def sandbox_violations(code_str: str) -> List[str]:
    """Return the list of static sandbox-policy violations for a code string (empty == compliant)."""
    try:
        tree = ast.parse(code_str)
    except SyntaxError as e:
        return [f"Syntax error: {e}"]

    violations: List[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                    violations.append(f"Import not in allow-list: {alias.name}")
        elif isinstance(node, ast.ImportFrom):
            if (node.module or "").split(".")[0] not in ALLOWED_IMPORTS:
                violations.append(f"Import not in allow-list: {node.module}")
        elif isinstance(node, ast.Name) and node.id in FORBIDDEN_NAMES:
            violations.append(f"Forbidden builtin/name: {node.id}")
        elif isinstance(node, ast.Attribute) and node.attr.startswith("__") and node.attr != "__init__":
            violations.append(f"Dunder attribute access not allowed: {node.attr}")
        elif isinstance(node, (ast.Global, ast.Nonlocal)):
            violations.append("global/nonlocal statements are not allowed")
    return violations


def _guarded_import(  # pylint: disable=redefined-builtin
    name: str,
    globals: Optional[Mapping[str, object]] = None,
    locals: Optional[Mapping[str, object]] = None,
    fromlist: Sequence[str] = (),
    level: int = 0,
) -> ModuleType:
    if name.split(".")[0] not in ALLOWED_IMPORTS or level != 0:
        raise ImportError(f"Import of '{name}' is not permitted inside the APEX sandbox")
    return builtins.__import__(name, globals, locals, fromlist, level)


def sandbox_globals() -> Dict[str, Any]:
    """Restricted execution namespace: curated builtins + guarded import + time/threading."""
    safe_builtins = {n: getattr(builtins, n) for n in _SAFE_BUILTIN_NAMES if hasattr(builtins, n)}
    safe_builtins["__build_class__"] = builtins.__build_class__
    safe_builtins["__import__"] = _guarded_import
    return {
        "__builtins__": safe_builtins,
        "__name__": "apex_sandbox",
        "time": time,
        "threading": threading,
        "math": math,
        "collections": collections,
    }


def compile_in_sandbox(code_str: str, class_name: str = "TokenBucketRateLimiter") -> Any:
    """Execute code in the restricted namespace and return the requested class (or None)."""
    namespace = sandbox_globals()
    exec(compile(code_str, "<apex-synthesized>", "exec"), namespace)  # noqa: S102 (gated above)  # pylint: disable=exec-used
    return namespace.get(class_name)


def verify_rate_limiter_behavior(limiter_cls: Any, timeout_s: float = 3.0) -> List[str]:
    """Run behavioural unit tests against a synthesized limiter class. Returns failures (empty == pass)."""
    failures: List[str] = []

    def _tests() -> None:
        # 1. Burst capacity: exactly `capacity` admits, then throttle (negligible refill)
        lim = limiter_cls(capacity=3, replenishment_rate=0.001)
        results = [lim.acquire(1) for _ in range(4)]
        if results != [True, True, True, False]:
            failures.append(f"burst capacity check failed: acquire x4 -> {results} (expected [True, True, True, False])")

        # 2. Refill: drained bucket admits again after tokens replenish
        lim2 = limiter_cls(capacity=2, replenishment_rate=50.0)
        lim2.acquire(1)
        lim2.acquire(1)
        time.sleep(0.1)
        if lim2.acquire(1) is not True:
            failures.append("refill check failed: no token available after replenishment interval")

        # 3. Parameters must be mutable at runtime (TrafficShapingAgent retunes them)
        lim2.capacity = 5
        lim2.replenishment_rate = 10.0
        lim2.acquire(1)

        # 4. Thread safety: 4 threads x 50 acquires on a 100-token bucket admit exactly 100
        lim3 = limiter_cls(capacity=100, replenishment_rate=0.001)
        admitted: List[int] = []
        lock = threading.Lock()

        def worker() -> None:
            local = sum(1 for _ in range(50) if lim3.acquire(1))
            with lock:
                admitted.append(local)

        threads = [threading.Thread(target=worker) for _ in range(4)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        if sum(admitted) != 100:
            failures.append(f"thread-safety check failed: admitted {sum(admitted)} of 200 concurrent acquires (expected 100)")

        # 5. Stats contract
        stats = lim.get_stats()
        missing = {"capacity", "replenishment_rate", "total_admitted", "total_throttled"} - set(stats or {})
        if missing:
            failures.append(f"get_stats() missing keys: {sorted(missing)}")
        elif stats["total_admitted"] != 3 or stats["total_throttled"] != 1:
            failures.append(f"get_stats() counters wrong: {stats}")

    def _runner() -> None:
        try:
            _tests()
        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            failures.append(f"runtime error during verification: {type(e).__name__}: {e}")

    t = threading.Thread(target=_runner, daemon=True)
    t.start()
    t.join(timeout_s)
    if t.is_alive():
        failures.append(f"verification timed out after {timeout_s}s (possible infinite loop / deadlock)")
    return failures


# Reviewed template source; limiter implementations elsewhere intentionally mirror it.
# pylint: disable=duplicate-code
REFERENCE_LIMITER_CODE = '''
class TokenBucketRateLimiter:
    """APEX Layer 1 reference token bucket rate limiter (reviewed template)."""

    def __init__(self, capacity: int = 10, replenishment_rate: float = 40.0):
        self.capacity = capacity
        self.replenishment_rate = replenishment_rate
        self.tokens = float(capacity)
        self.last_update = time.perf_counter()
        self.lock = threading.Lock()
        self.total_throttled = 0
        self.total_admitted = 0

    def acquire(self, tokens: int = 1) -> bool:
        with self.lock:
            now = time.perf_counter()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(float(self.capacity), self.tokens + elapsed * self.replenishment_rate)
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.total_admitted += 1
                return True
            self.total_throttled += 1
            return False

    def get_stats(self):
        with self.lock:
            return {
                "capacity": self.capacity,
                "replenishment_rate": self.replenishment_rate,
                "current_tokens": round(self.tokens, 2),
                "total_admitted": self.total_admitted,
                "total_throttled": self.total_throttled,
            }
'''.strip() + "\n"
# pylint: enable=duplicate-code

_SYNTHESIS_PROMPT = """You are the APEX Layer 1 Harness Patching engine of an autonomous SRE system.
A production incident is in progress. Diagnosis from the multi-agent triage:

<diagnosis>
{diagnosis}
</diagnosis>

Write a Python class named `TokenBucketRateLimiter` that throttles ingress to protect the
database connection pool. Exact contract:
- `__init__(self, capacity: int = 10, replenishment_rate: float = 40.0)`; store them as the
  public, mutable attributes `self.capacity` and `self.replenishment_rate` (an operator agent
  retunes them at runtime, so read them on every call).
- Start with a full bucket. `acquire(self, tokens: int = 1) -> bool` refills lazily from elapsed
  `time.perf_counter()` time (never above `capacity`), consumes and returns True if enough tokens,
  otherwise returns False. Never sleep or block.
- Must be thread-safe (use `threading.Lock`).
- `get_stats(self) -> dict` with keys: capacity, replenishment_rate, current_tokens,
  total_admitted, total_throttled (counts of acquire calls admitted / rejected).

Sandbox rules (violations are rejected): only `time`, `threading`, `math`, `collections` may be
used (they are pre-imported); no file, network, OS or process access; no eval/exec/getattr/type;
no dunder attribute access other than `__init__`; no global state.
Return ONLY the code in a single ```python block, no explanation.{feedback}"""


@dataclass
class SynthesisResult:
    """Outcome of a synthesis run: the vetted code, its compiled class and provenance/gate log."""

    code: str
    limiter_cls: Any
    source: str  # "gemini" | "reference_template"
    model: str
    attempts: int
    gate_log: List[str] = field(default_factory=list)


def _extract_code(text: str) -> str:
    match = re.search(r"```(?:python)?\s*\n(.*?)```", text or "", re.S)
    return (match.group(1) if match else (text or "")).strip() + "\n"


def run_gates(code: str) -> Tuple[Any, List[str]]:
    """Run all sandbox gates; returns (limiter_cls or None, list of failures)."""
    violations = sandbox_violations(code)
    if violations:
        return None, [f"AST sandbox policy: {v}" for v in violations]
    # Static contract: races are rarely observable under the GIL, so require an explicit lock.
    if not re.search(r"threading\.(R?Lock)\(", code):
        return None, ["thread-safety contract: acquire() must be guarded by threading.Lock()/RLock()"]
    try:
        cls = compile_in_sandbox(code)
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
        return None, [f"sandbox compilation failed: {type(e).__name__}: {e}"]
    if cls is None:
        return None, ["class `TokenBucketRateLimiter` not defined"]
    failures = verify_rate_limiter_behavior(cls)
    return (cls if not failures else None), failures


def synthesize_rate_limiter(  # pylint: disable=too-many-locals
    diagnosis: str,
    model_name: str,
    llm_available: bool = True,
    max_attempts: int = 3,
) -> SynthesisResult:
    """Ask Gemini to synthesize the limiter, enforcing all gates; fall back to the reference template."""
    gate_log: List[str] = []
    feedback = ""
    attempts = 0

    if llm_available:
        try:
            from google import genai  # pylint: disable=import-outside-toplevel
            from google.genai import types as genai_types  # pylint: disable=import-outside-toplevel

            client = genai.Client()
            gen_config = genai_types.GenerateContentConfig(
                automatic_function_calling=genai_types.AutomaticFunctionCallingConfig(disable=True),
            )
        except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
            client = None
            gate_log.append(f"Gemini client unavailable: {type(e).__name__}")

        for attempt in range(1, max_attempts + 1 if client else 1):
            attempts = attempt
            try:
                resp = client.models.generate_content(
                    model=model_name,
                    contents=_SYNTHESIS_PROMPT.format(diagnosis=(diagnosis or "n/a")[:4000], feedback=feedback),
                    config=gen_config,
                )
                code = _extract_code(resp.text)
            except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught
                gate_log.append(f"attempt {attempt}: Gemini call failed ({type(e).__name__})")
                continue

            cls, failures = run_gates(code)
            if cls is not None:
                gate_log.append(f"attempt {attempt}: all gates PASSED (AST sandbox, restricted compile, 5 behavioural tests)")
                return SynthesisResult(code, cls, "gemini", model_name, attempt, gate_log)

            gate_log.append(f"attempt {attempt}: REJECTED - " + "; ".join(failures[:3]))
            feedback = (
                "\n\nYour previous attempt was REJECTED by the verification gates:\n- "
                + "\n- ".join(failures[:5])
                + "\nFix these issues and return the full corrected class."
            )

    cls, failures = run_gates(REFERENCE_LIMITER_CODE)
    if cls is None:  # pragma: no cover - the reviewed template must always pass
        raise RuntimeError(f"Reference limiter template failed verification: {failures}")
    gate_log.append("using reviewed reference template (gates PASSED)")
    return SynthesisResult(REFERENCE_LIMITER_CODE, cls, "reference_template", model_name, attempts, gate_log)
