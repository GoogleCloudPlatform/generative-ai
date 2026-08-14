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
"""Shared, dependency-free constants for the Prism event protocol.

Kept separate from app.agent so the UI server (serve.py) can import the sentinel
without constructing the whole agent graph (important for the decoupled Cloud Run
frontend, which talks to a remote Agent Runtime instead of running the agent)."""

# Sentinel prefix the orchestrator uses to mark structured progress events in the
# model stream; the SSE layer parses these out for the frontend.
PRISM_EVENT = "\u241fPRISM\u241f"

# The deployed ADK app / agent_directory name (matches App(name=...) and the
# agent_directory in deployment_metadata.json).
APP_NAME = "app"
