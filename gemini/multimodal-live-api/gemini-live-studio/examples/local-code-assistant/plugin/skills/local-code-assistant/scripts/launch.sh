#!/usr/bin/env bash
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# A packed skill bundle (make pack-skill) ships the app under assets/; inside
# the repository the app is the example directory four levels up.
if [[ -d "${SCRIPT_DIR}/../assets/local-code-assistant" ]]; then
  APP_DIR="$(cd "${SCRIPT_DIR}/../assets/local-code-assistant" && pwd)"
else
  APP_DIR="$(cd "${SCRIPT_DIR}/../../../.." && pwd)"
fi

echo "==> Starting Local Code Assistant (Gemini Live) from ${APP_DIR}..."
cd "${APP_DIR}"
exec go run . "$@"
