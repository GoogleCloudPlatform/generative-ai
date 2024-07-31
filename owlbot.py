# Copyright 2022 Google LLC
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

import synthtool as s
import synthtool.gcp as gcp

templated_files = gcp.CommonTemplates().python_notebooks()

# Copy the standard noxfile from templated_files
s.move(templated_files / "noxfile.py")

# Update BLACK_PATHS in order to run black on all files
s.replace(
    "noxfile.py",
    r"""LINT_PATHS = \["docs", "google", "tests", "noxfile.py", "setup.py"\]""",
    r"""LINT_PATHS = ["."]""",
)

# ----------------------------------------------------------------------------
# Run blacken session
# ----------------------------------------------------------------------------

s.shell.run(["nox", "-s", "format"], hide_output=False)

# Sort Spelling Allowlist
spelling_allow_file = ".github/actions/spelling/allow.txt"

with open(spelling_allow_file, "r", encoding="utf-8") as file:
    unique_words = sorted(set(file))

with open(spelling_allow_file, "w", encoding="utf-8") as file:
    file.writelines(unique_words)
