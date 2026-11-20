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
# ruff: noqa: INP001

"""Applies the `nvidia-h200-141gb` pricing fix and Gate 1 unit regression test.

Used in Closed-Loop Test Case 2 after Gate 3A catches the silent L4 fallback
(`$690.00 != $8,460.00`). Adds `"nvidia-h200-141gb": 14.10` to `app/agent.py`
and appends `test_calculate_serving_cost_h200` to `tests/unit/test_agent_unit.py`.
"""

import pathlib

AGENT_REL_PATH = pathlib.Path("app/agent.py")
UNIT_TEST_REL_PATH = pathlib.Path("tests/unit/test_agent_unit.py")

_H100_ANCHOR = '"nvidia-h100-80gb": 10.80,'
_H200_ENTRY = '"nvidia-h100-80gb": 10.80,\n        "nvidia-h200-141gb": 14.10,'
_DOCSTRING_ANCHOR = (
    "gpu_type: GPU accelerator type ('nvidia-l4', 'nvidia-a100-40gb',"
    " 'nvidia-h100-80gb')."
)
_DOCSTRING_FIXED = (
    "gpu_type: GPU accelerator type ('nvidia-l4', 'nvidia-a100-40gb',"
    " 'nvidia-a100-80gb', 'nvidia-h100-80gb', 'nvidia-h200-141gb')."
)

_GATE3_HEADER = (
    "\n# ----------------------------------------------------------------------"
    "-----\n# Gate 3:"
)
_REGRESSION_TEST_SNIPPET = (
    "\ndef test_calculate_serving_cost_h200() -> None:\n"
    '    """Verifies H200 ($14.10/hr) pricing from production feedback."""\n'
    "    pricing_result = calculate_serving_cost(\n"
    '        platform="gemini_agent_platform",\n'
    '        gpu_type="nvidia-h200-141gb",\n'
    "        hours_per_day=10,\n"
    "        replicas=2,\n"
    "    )\n"
    '    assert pricing_result["hourly_rate_per_replica_usd"] == 14.10\n'
    '    assert pricing_result["monthly_cost_usd"] == 8460.00\n\n'
)


def apply_h200_fix(repo_root: pathlib.Path) -> None:
    """Idempotently updates `app/agent.py` and `tests/unit/test_agent_unit.py`.

    Args:
        repo_root: Root directory of the standalone agent repository.

    Raises:
        RuntimeError: If expected insertion anchors are missing in target files.
    """
    agent_path = repo_root / AGENT_REL_PATH
    agent_source = agent_path.read_text(encoding="utf-8")
    updated_agent = False
    if '"nvidia-h200-141gb"' not in agent_source:
        if _H100_ANCHOR not in agent_source:
            raise RuntimeError(f"Expected anchor {_H100_ANCHOR!r} not in {agent_path}")
        agent_source = agent_source.replace(_H100_ANCHOR, _H200_ENTRY, 1)
        updated_agent = True
    if _DOCSTRING_ANCHOR in agent_source:
        agent_source = agent_source.replace(_DOCSTRING_ANCHOR, _DOCSTRING_FIXED, 1)
        updated_agent = True
    if updated_agent:
        agent_path.write_text(agent_source, encoding="utf-8")
        print(
            f"Updated {agent_path} with nvidia-h200-141gb ($14.10/hr) and tool schema"
        )

    unit_test_path = repo_root / UNIT_TEST_REL_PATH
    unit_test_source = unit_test_path.read_text(encoding="utf-8")
    if "def test_calculate_serving_cost_h200" not in unit_test_source:
        if _GATE3_HEADER not in unit_test_source:
            raise RuntimeError(
                f"Expected Gate 3 section header not in {unit_test_path}"
            )
        unit_test_source = unit_test_source.replace(
            _GATE3_HEADER,
            _REGRESSION_TEST_SNIPPET + _GATE3_HEADER,
            1,
        )
        unit_test_path.write_text(unit_test_source, encoding="utf-8")
        print(f"Added test_calculate_serving_cost_h200 to {unit_test_path}")


def main() -> None:
    """Entry point for Closed-Loop Test Case 2 local TDD remediation."""
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    apply_h200_fix(repo_root)


if __name__ == "__main__":
    main()
