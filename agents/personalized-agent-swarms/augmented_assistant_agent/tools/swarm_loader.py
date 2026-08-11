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

"""Loads a user's mini-agent swarm from the swarms/ directory."""

import importlib.util
import json
from pathlib import Path

SWARMS_DIR = Path(__file__).parent.parent.parent / "swarms"

_loaded_swarms: dict[str, dict] = {}  # cache: user_id -> swarm data


def clear_cache():
    """Clear the swarm cache (useful for testing after trigger updates)."""
    _loaded_swarms.clear()


def load_swarm(user_id: str) -> dict:
    """Load and cache a user's swarm manifest, triggers, and agent modules.

    Returns:
        {
            "manifest": dict | None,
            "triggers": dict,           # agent_name -> trigger_config
            "agents": dict,             # agent_name -> loaded Python module
            "user_style": dict | None,  # behavioral style profile
        }
    """
    if user_id in _loaded_swarms:
        return _loaded_swarms[user_id]

    user_dir = SWARMS_DIR / user_id
    if not user_dir.exists():
        _loaded_swarms[user_id] = {
            "manifest": None,
            "triggers": {},
            "agents": {},
            "user_style": None,
        }
        return _loaded_swarms[user_id]

    # Load manifest
    manifest_path = user_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else {}

    # Load triggers
    triggers_path = user_dir / "triggers.json"
    triggers = json.loads(triggers_path.read_text()) if triggers_path.exists() else {}

    # Load user style profile (from behavioral patterns)
    style_path = user_dir / "user_style.json"
    user_style = json.loads(style_path.read_text()) if style_path.exists() else None

    # Dynamically load agent modules
    agents = {}
    agents_dir = user_dir / "agents"
    if agents_dir.exists():
        for agent_file in agents_dir.glob("*.py"):
            agent_name = agent_file.stem
            try:
                spec = importlib.util.spec_from_file_location(
                    f"swarm_agent_{user_id}_{agent_name}", agent_file
                )
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                agents[agent_name] = module
            except Exception as e:  # noqa: BLE001 — generated agent code can raise anything on import
                print(f"Warning: skipping broken agent {agent_name}: {e}")
                continue

    swarm = {
        "manifest": manifest,
        "triggers": triggers,
        "agents": agents,
        "user_style": user_style,
    }
    _loaded_swarms[user_id] = swarm
    return swarm
