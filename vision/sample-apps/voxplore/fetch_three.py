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

"""Downloads the three.js files that generated scenes import, into frontend/vendor/.

Run once after cloning, from this folder:

    python fetch_three.py
"""

import hashlib
import io
import sys
import tarfile
import urllib.request
from pathlib import Path

VERSION = "0.187.0"
URL = f"https://registry.npmjs.org/three/-/three-{VERSION}.tgz"
SHA256 = "ff540832ded0cfe919764d24a3d88f3e2a05f23303f876423e4f893841e90728"
VENDOR_DIR = Path(__file__).resolve().parent / "frontend" / "vendor"

FILES = {
    "package/build/three.module.js": "three.module.js",
    "package/build/three.core.js": "three.core.js",
    "package/examples/jsm/controls/OrbitControls.js": "addons/controls/OrbitControls.js",
    "package/examples/jsm/renderers/CSS2DRenderer.js": "addons/renderers/CSS2DRenderer.js",
    "package/LICENSE": "THREE_LICENSE",
}


def main() -> int:
    print(f"Downloading three.js {VERSION}")
    with urllib.request.urlopen(URL, timeout=120) as response:
        archive = response.read()
    if hashlib.sha256(archive).hexdigest() != SHA256:
        print(
            "The downloaded archive does not match the expected checksum. Nothing was written."
        )
        return 1
    with tarfile.open(fileobj=io.BytesIO(archive), mode="r:gz") as package:
        for member, target in FILES.items():
            path = VENDOR_DIR / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(package.extractfile(member).read())
    print(f"Wrote {len(FILES)} files to {VENDOR_DIR}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
