#!/usr/bin/env bash
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

# Render the demo grounding docs (HTML) to PDF for Agent Search.
#
#   demo/acme-cloud-docs/*.html  -> ACME Cloud console demo (/cloud)
#   demo/acme-docs/*.html        -> ACME People HR demo (/hr)
#
# Requires a Chromium/Chrome binary. Override with CHROME_BIN if needed.
set -euo pipefail

CHROME="${CHROME_BIN:-}"
if [[ -z "$CHROME" ]]; then
  for c in chromium google-chrome google-chrome-stable chromium-browser; do
    if command -v "$c" >/dev/null 2>&1; then CHROME="$(command -v "$c")"; break; fi
  done
fi
if [[ -z "$CHROME" ]]; then
  echo "No Chromium/Chrome found. Install one or set CHROME_BIN=/path/to/chrome." >&2
  exit 1
fi

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
shopt -s nullglob
for dir in "$ROOT/demo/acme-cloud-docs" "$ROOT/demo/acme-docs"; do
  echo "Rendering $(basename "$dir")"
  for f in "$dir"/*.html; do
    "$CHROME" --headless=new --no-sandbox --disable-gpu --disable-dev-shm-usage \
      --no-pdf-header-footer --print-to-pdf="${f%.html}.pdf" "file://$f" >/dev/null 2>&1
    echo "  ✓ $(basename "${f%.html}.pdf")"
  done
done

cat <<'EOF'

Next (ACME Cloud example; repeat with demo/acme-docs and --origin acme-hr for the HR demo):
  gcloud storage buckets create gs://YOUR_PROJECT-wayfinder-docs --location=us-central1 --uniform-bucket-level-access
  gcloud storage cp demo/acme-cloud-docs/*.pdf gs://YOUR_PROJECT-wayfinder-docs/acme-cloud/
  .venv/bin/python scripts/provision_docs.py --project YOUR_PROJECT \
      --tenant acme-cloud-docs --origin acme-cloud \
      --gcs-uri gs://YOUR_PROJECT-wayfinder-docs/acme-cloud/
EOF
