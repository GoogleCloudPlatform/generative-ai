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

"""Generates the scenes listed in scene_library/topics.json ahead of time.

A session then opens them instantly when the avatar names the same topic. Any other request is
still generated live. Run from the project folder:

    python prewarm_scenes.py              # the topics that are not in the library yet
    python prewarm_scenes.py --force      # regenerate all of them
    python prewarm_scenes.py "pendulum"   # only this topic
"""

import argparse
import asyncio
import json
import time
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

from voxplore import genmedia  # noqa: E402

TOPICS = Path(__file__).resolve().parent / "scene_library" / "topics.json"


async def main():
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "topics", nargs="*", help="topics to generate; all of them when omitted"
    )
    parser.add_argument(
        "--force", action="store_true", help="regenerate scenes that already exist"
    )
    args = parser.parse_args()

    wanted = {genmedia.topic_slug(topic) for topic in args.topics}
    for entry in json.loads(TOPICS.read_text(encoding="utf-8")):
        slug = genmedia.topic_slug(entry["topic"])
        if wanted and slug not in wanted:
            continue
        if not args.force and (genmedia.LIBRARY_DIR / f"{slug}.js").is_file():
            print(f"{entry['topic']}: already in the library")
            continue
        started = time.monotonic()
        try:
            source = await genmedia.generate_scene(entry["description"])
        except Exception as e:
            print(f"{entry['topic']}: failed: {e}")
            continue
        path = genmedia.save_library_scene(entry["topic"], source)
        print(
            f"{entry['topic']}: {path.name}, {source.count(chr(10)) + 1} lines, {time.monotonic() - started:.0f} s"
        )


if __name__ == "__main__":
    asyncio.run(main())
