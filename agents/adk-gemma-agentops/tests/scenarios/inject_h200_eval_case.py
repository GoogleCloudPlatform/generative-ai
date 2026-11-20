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

"""Appends a sanitized H200 production trace to `golden.evalset.json`.

Used in Closed-Loop Test Case 1 to simulate newly arrived production telemetry
exposing a missing `nvidia-h200-141gb` GPU rate (`$14.10/hr`, `$8,460.00/mo`
for 2 replicas at 10 hours/day) while `app/agent.py` remains untouched.
"""

import json
import pathlib
from collections.abc import Mapping
from typing import Any

EVALSET_REL_PATH = pathlib.Path("tests/eval/evalsets/golden.evalset.json")


def build_h200_eval_case() -> Mapping[str, Any]:
    """Builds the sanitized H200 pricing evaluation case in ADK EvalSet format."""
    return {
        "eval_id": "calculate_h200_serving_cost",
        "conversation": [
            {
                "invocation_id": "inv-005",
                "user_content": {
                    "parts": [
                        {
                            "text": (
                                "Calculate the monthly serving cost on"
                                " gemini_agent_platform for 2 nvidia-h200-141gb"
                                " replicas running 10 hours per day."
                            )
                        }
                    ],
                    "role": "user",
                },
                "final_response": {
                    "parts": [
                        {
                            "text": (
                                "The monthly serving cost is $8,460, with"
                                " $11,844 in savings from off-hours"
                                " hibernation."
                            )
                        }
                    ],
                    "role": "model",
                },
                "intermediate_data": {
                    "tool_uses": [
                        {
                            "name": "calculate_serving_cost",
                            "args": {
                                "platform": "gemini_agent_platform",
                                "gpu_type": "nvidia-h200-141gb",
                                "hours_per_day": 10,
                                "replicas": 2,
                            },
                        }
                    ],
                    "intermediate_responses": [],
                },
            }
        ],
        "session_input": {
            "app_name": "app",
            "user_id": "eval_user_05",
            "state": {},
        },
    }


def inject_h200_case(repo_root: pathlib.Path) -> pathlib.Path:
    """Idempotently appends `calculate_h200_serving_cost` to the golden evalset.

    Args:
        repo_root: Root directory of the standalone agent repository.

    Returns:
        Path to the updated `golden.evalset.json` file.
    """
    evalset_path = repo_root / EVALSET_REL_PATH
    evalset_payload = json.loads(evalset_path.read_text(encoding="utf-8"))
    h200_case = dict(build_h200_eval_case())

    existing_cases = [
        case_item
        for case_item in evalset_payload.get("eval_cases", [])
        if case_item.get("eval_id") != h200_case["eval_id"]
    ]
    evalset_payload["eval_cases"] = [*existing_cases, h200_case]
    evalset_path.write_text(
        json.dumps(evalset_payload, indent=2) + "\n",
        encoding="utf-8",
    )
    return evalset_path


def main() -> None:
    """Entry point for Closed-Loop Test Case 1 evalset injection."""
    repo_root = pathlib.Path(__file__).resolve().parents[2]
    updated_path = inject_h200_case(repo_root)
    print(f"Injected 'calculate_h200_serving_cost' into {updated_path}")


if __name__ == "__main__":
    main()
