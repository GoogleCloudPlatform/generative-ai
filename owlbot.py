# Copyright 2023 Google LLC
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

from logging import Logger
from pathlib import Path
import re
import subprocess

import synthtool as s
import synthtool.gcp as gcp
from synthtool.log import logger

logger: Logger = logger

_EXCLUDED_DIRS = [r"^\."]


def walk_through_owlbot_dirs(dir: Path, search_for_changed_files: bool) -> list[str]:
    """
    Walks through all sample directories
    Returns:
    A list of directories
    """
    owlbot_dirs: list[str] = []
    packages_to_exclude = _EXCLUDED_DIRS
    if search_for_changed_files:
        try:
            # Need to run this step first in the post processor since we only clone
            # the branch the PR is on in the Docker container
            output = subprocess.run(
                ["git", "fetch", "origin", "main:main", "--deepen=200"], check=False
            )
            output.check_returncode()
        except subprocess.CalledProcessError as error:
            if error.returncode == 128:
                logger.info(f"Error: ${error.output}; skipping fetching main")
            else:
                raise error
    for path_object in dir.glob("**/requirements.txt"):
        object_dir = str(Path(path_object).parents[0])
        if (
            path_object.is_file()
            and object_dir != str(dir)
            and not re.search(
                "(?:% s)" % "|".join(packages_to_exclude), str(Path(path_object))
            )
        ):
            if search_for_changed_files:
                if (
                    subprocess.run(
                        ["git", "diff", "--quiet", "main...", object_dir], check=False
                    ).returncode
                    == 1
                ):
                    owlbot_dirs.append(object_dir)
            else:
                owlbot_dirs.append(object_dir)
    for path_object in dir.glob("owl-bot-staging/*"):
        owlbot_dirs.append(
            f"{Path(path_object).parents[1]}/packages/{Path(path_object).name}"
        )
    return owlbot_dirs


templated_files = gcp.CommonTemplates().py_library()

# Copy the standard noxfile from templated_files
s.move(templated_files / "noxfile.py")

dirs: list[str] = walk_through_owlbot_dirs(Path.cwd(), search_for_changed_files=True)
if dirs:
    lint_paths = ", ".join(f'"{d}"' for d in dirs)
    # Update LINT_PATHS in order to run black on changed files
    s.replace(
        "noxfile.py",
        r"""LINT_PATHS = \["docs", "google", "tests", "noxfile.py", "setup.py"\]""",
        f"""LINT_PATHS = [{lint_paths}]""",
    )

    # TODO: Remove once https://github.com/googleapis/synthtool/pull/1811 is merged.
    s.replace(
        "noxfile.py",
        r"""BLACK_VERSION = "black==22.3.0"\nISORT_VERSION = "isort==5.10.1""",
        r"""BLACK_VERSION = "black[jupyter]==23.3.0"\nISORT_VERSION = "isort==5.11.0""",
    )

    # ----------------------------------------------------------------------------
    # Run blacken session
    # ----------------------------------------------------------------------------

    s.shell.run(["nox", "-s", "blacken"], hide_output=False)
