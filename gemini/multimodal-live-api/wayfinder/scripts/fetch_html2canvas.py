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

"""Download the pinned html2canvas build that the widget uses for snapshots.

The backend serves this file at /vendor/html2canvas.min.js so host pages don't
load code from a public CDN at runtime. The download is pinned to one version
and checked against a SHA-256 digest before it is written.

Usage:
    python scripts/fetch_html2canvas.py
"""

import hashlib
import sys
import urllib.request
from pathlib import Path

VERSION = "1.4.1"
URL = f"https://cdn.jsdelivr.net/npm/html2canvas@{VERSION}/dist/html2canvas.min.js"
SHA256 = "e87e550794322e574a1fda0c1549a3c70dae5a93d9113417a429016838eab8cb"
DEST = (
    Path(__file__).resolve().parent.parent
    / "widget"
    / "third_party"
    / "html2canvas"
    / "html2canvas.min.js"
)


def _digest(data: bytes) -> str:
    """Returns the hex SHA-256 digest of data."""
    return hashlib.sha256(data).hexdigest()


def main() -> int:
    """Downloads and verifies html2canvas; returns a process exit code."""
    if DEST.is_file() and _digest(DEST.read_bytes()) == SHA256:
        print(f"html2canvas {VERSION} already present: {DEST}")
        return 0

    with urllib.request.urlopen(URL, timeout=30) as response:
        data = response.read()

    actual = _digest(data)
    if actual != SHA256:
        print(
            f"html2canvas checksum mismatch: expected {SHA256}, got {actual}",
            file=sys.stderr,
        )
        return 1

    DEST.parent.mkdir(parents=True, exist_ok=True)
    DEST.write_bytes(data)
    print(f"Downloaded html2canvas {VERSION} to {DEST}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
