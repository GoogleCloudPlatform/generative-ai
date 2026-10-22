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

"""Unit tests for APEX Layer 1 Gemini code synthesis gates (sandbox policy, restricted compile, behaviour)."""
import pytest

from app.adk_agents.code_synthesis import (
    REFERENCE_LIMITER_CODE,
    compile_in_sandbox,
    run_gates,
    sandbox_violations,
    synthesize_rate_limiter,
)


@pytest.mark.parametrize(
    "snippet, expected",
    [
        ("import os\n", "Import not in allow-list: os"),
        ("import subprocess\n", "Import not in allow-list: subprocess"),
        ("from socket import socket\n", "Import not in allow-list: socket"),
        ("x = open('/etc/passwd')\n", "Forbidden builtin/name: open"),
        ("x = getattr(object, 'mro')\n", "Forbidden builtin/name: getattr"),
        ("x = ().__class__.__bases__\n", "Dunder attribute access not allowed: __class__"),
        ("def f():\n    global y\n", "global/nonlocal statements are not allowed"),
    ],
)
def test_sandbox_policy_rejects_dangerous_constructs(snippet: str, expected: str) -> None:
    """The static sandbox policy flags each dangerous construct with a specific violation."""
    assert expected in sandbox_violations(snippet)


def test_restricted_namespace_blocks_unlisted_imports_at_runtime() -> None:
    """The restricted namespace refuses non-allow-listed imports at runtime."""
    # Even if static checks were bypassed, the guarded __import__ refuses non-allow-listed modules.
    with pytest.raises(ImportError):
        compile_in_sandbox("import json\n")


def test_reference_template_passes_all_gates() -> None:
    """The reviewed reference limiter passes every verification gate and throttles correctly."""
    cls, failures = run_gates(REFERENCE_LIMITER_CODE)
    assert failures == []
    limiter = cls(capacity=2, replenishment_rate=0.001)
    assert [limiter.acquire(), limiter.acquire(), limiter.acquire()] == [True, True, False]


def test_behavioural_gate_rejects_limiter_that_never_throttles() -> None:
    """The behavioural gate rejects a limiter that never sheds load."""
    broken = REFERENCE_LIMITER_CODE.replace("if self.tokens >= tokens:", "if True:")
    cls, failures = run_gates(broken)
    assert cls is None
    assert any("burst capacity check failed" in f for f in failures)


def test_gate_rejects_limiter_without_lock() -> None:
    """The thread-safety gate rejects a limiter without a lock."""
    unlocked = REFERENCE_LIMITER_CODE.replace("self.lock = threading.Lock()", "self.lock = None").replace(
        "with self.lock:", "if True:"
    )
    cls, failures = run_gates(unlocked)
    assert cls is None
    assert any("thread-safety contract" in f for f in failures)


def test_synthesis_offline_falls_back_to_verified_reference_template() -> None:
    """Offline synthesis falls back to the verified reference template."""
    result = synthesize_rate_limiter("cache stampede", "gemini-4-argon", llm_available=False)
    assert result.source == "reference_template"
    assert result.code == REFERENCE_LIMITER_CODE
    assert result.limiter_cls is not None
    assert any("reference template" in g for g in result.gate_log)
