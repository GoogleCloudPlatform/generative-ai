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

FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ backend/
COPY widget/ widget/
COPY scripts/fetch_html2canvas.py scripts/
# Pinned, checksum-verified html2canvas build for voice-mode page snapshots.
RUN python scripts/fetch_html2canvas.py
COPY demo/ demo/
COPY site/ site/

ENV PORT=8080
EXPOSE 8080

# Run uvicorn directly: no auto-reload in production.
CMD ["sh", "-c", "exec uvicorn backend.server:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
