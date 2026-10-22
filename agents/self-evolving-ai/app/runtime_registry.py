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

"""Process-wide handle to the live target environment.

ADK tools, the dynamic tool registry and the topology mutator all operate on the running
``TargetEnvironmentApp`` singleton, while the server lazily imports those same modules.
Resolving the singleton through this registry (instead of importing
``app.target_env.server`` directly) keeps the module dependency graph acyclic.
"""

import importlib
from typing import Any

_REGISTRY: dict[str, Any] = {}


def register_platform_env(env: Any) -> None:
    """Register the live ``TargetEnvironmentApp`` singleton (called once by the server module)."""
    _REGISTRY["platform_env"] = env


def get_platform_env() -> Any:
    """Return the live ``TargetEnvironmentApp``, importing the server module on first use."""
    if "platform_env" not in _REGISTRY:
        # Importing the server module creates the singleton and registers it.
        importlib.import_module("app.target_env.server")
    return _REGISTRY["platform_env"]
