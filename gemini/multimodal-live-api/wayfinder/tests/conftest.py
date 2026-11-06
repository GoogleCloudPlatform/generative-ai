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

"""Test setup: hermetic environment and project root on sys.path."""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "test-project")
os.environ["AUTH_ENABLED"] = "false"
os.environ["VERTEX_SEARCH_ENGINES"] = "{}"
os.environ["ALLOWED_ORIGINS"] = "*"
for var in (
    "GEMINI_MODEL",
    "GEMINI_FALLBACK_MODEL",
    "GEMINI_TEXT_MODEL",
    "GOOGLE_CLOUD_LOCATION",
    "API_KEYS",
    "API_KEYS_FILE",
    "SELF_ORIGIN",
):
    os.environ.pop(var, None)
