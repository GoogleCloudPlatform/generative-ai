# pylint: skip-file
# type: ignore
# -*- coding: utf-8 -*-
#
# Copyright 2023 Google LLC
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

import os
import subprocess
import urllib.parse

import nbformat
import nox

DEFAULT_PYTHON_VERSION = "3.11"
DEFAULT_RUFF_LINE_LENGTH = 88

# --- Notebook Link Constants ---
LINK_PREFIXES = {
    "colab_link": "https://colab.research.google.com/github/GoogleCloudPlatform/generative-ai/blob/main/",
    "colab_enterprise_link": "https://console.cloud.google.com/vertex-ai/colab/import/",
    "github_link": "https://github.com/GoogleCloudPlatform/generative-ai/blob/main/",
    "workbench_link": "https://console.cloud.google.com/vertex-ai/workbench/deploy-notebook?download_url=",
    "bigquery_studio_link": "https://console.cloud.google.com/bigquery/import?url=",
    "linkedin_link": "https://www.linkedin.com/sharing/share-offsite/?url=",
    "bluesky_link": "https://bsky.app/intent/compose?text=",
    "twitter_link": "https://twitter.com/intent/tweet?url=",
    "reddit_link": "https://reddit.com/submit?url=",
    "facebook_link": "https://www.facebook.com/sharer/sharer.php?u=",
}

GITHUB_URL_PREFIX = LINK_PREFIXES["github_link"]
RAW_URL_PREFIX = (
    "https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/"
)

nox.options.sessions = [
    "format",
]
nox.options.reuse_existing_virtualenvs = True


def fix_markdown_links(
    cell_source: str, relative_notebook_path: str
) -> tuple[str, bool]:
    """Fixes links in a markdown cell and returns the updated source."""
    new_lines = []
    changes_made = False

    encoded_url = urllib.parse.quote(f"{GITHUB_URL_PREFIX}{relative_notebook_path}")

    for line in cell_source.splitlines():
        for key, prefix in LINK_PREFIXES.items():
            if prefix not in line or "**NOTE:**" in line:
                continue

            start_index = line.find(prefix) + len(prefix)
            end_index = line.find(".ipynb", start_index) + len(".ipynb")
            correct_link = ""

            if key in {"colab_link", "github_link"}:
                correct_link = relative_notebook_path
            elif key == "colab_enterprise_link":
                correct_link = urllib.parse.quote(
                    f"{RAW_URL_PREFIX}{relative_notebook_path}",
                    safe=":",
                )
            elif key == "workbench_link":
                correct_link = f"{RAW_URL_PREFIX}{relative_notebook_path}"
            elif key == "bigquery_studio_link":
                correct_link = f"{GITHUB_URL_PREFIX}{relative_notebook_path}"
            elif key in {
                "linkedin_link",
                "bluesky_link",
                "twitter_link",
                "reddit_link",
                "facebook_link",
            }:
                correct_link = encoded_url

            if correct_link.lower() not in line.lower():
                line = line.replace(line[start_index:end_index], correct_link)
                changes_made = True

        new_lines.append(line)

    return "\n".join(new_lines), changes_made


def update_notebook_links(session: nox.Session, notebook_paths: list[str]) -> None:
    """Checks and fixes specific types of links in the provided list of notebooks."""
    session.log("Checking notebook links...")
    links_updated_count = 0

    for notebook_path in notebook_paths:
        # False positive
        if "vector-search-2-intro" in notebook_path:
            continue
        try:
            with open(notebook_path, encoding="utf-8") as f:
                notebook = nbformat.read(f, as_version=4)

            relative_notebook_path = os.path.relpath(
                notebook_path, start=os.getcwd()
            ).lower()
            notebook_modified = False

            for cell in notebook.cells:
                if (
                    cell.cell_type == "markdown"
                    and "<table" in cell.source
                    and "colab" in cell.source
                ):
                    updated_source, changes_made = fix_markdown_links(
                        cell.source, relative_notebook_path
                    )
                    if changes_made:
                        cell.source = updated_source
                        notebook_modified = True

            if notebook_modified:
                links_updated_count += 1
                with open(notebook_path, "w", encoding="utf-8") as f:
                    nbformat.write(notebook, f)
                session.log(f"  -> Fixed links in {notebook_path}")

        except Exception as e:
            session.warn(f"Could not check links in {notebook_path}. Error: {e}")

    if links_updated_count > 0:
        session.log(f"Fixed links in {links_updated_count} notebooks.")


def preprocess_notebook(
    session: nox.Session,
    notebook_paths: list[str],
    max_line_length: int = DEFAULT_RUFF_LINE_LENGTH,
) -> None:
    """Parses notebooks and wraps '@param' blocks with '# fmt: off/on'.

    This prevents ruff from formatting Google Colab form fields. The function
    finds the first and last lines containing '@param' in a cell and inserts
    the directives around that block. It modifies files in-place.
    """
    session.log("Checking for '@param' blocks to wrap with '# fmt: off/on'...")
    for path in notebook_paths:
        try:
            with open(path, encoding="utf-8") as f:
                notebook = nbformat.read(f, as_version=4)

            notebook_modified = False
            for cell in notebook.cells:
                if cell.cell_type != "code" or "@param" not in cell.source:
                    continue

                source_lines = cell.source.split("\n")

                clean_source_lines = [
                    line
                    for line in source_lines
                    if line.strip() not in ["# fmt: off", "# fmt: on"]
                ]

                param_indices = [
                    i
                    for i, line in enumerate(clean_source_lines)
                    if "@param" in line and len(line) >= max_line_length
                ]

                if not param_indices:
                    continue

                first_param_index = param_indices[0]
                last_param_index = param_indices[-1]

                # Reconstruct the cell source with new directives
                new_source_lines = []
                for i, line in enumerate(clean_source_lines):
                    if i == first_param_index:
                        new_source_lines.append("# fmt: off")
                    new_source_lines.append(line)
                    if i == last_param_index:
                        new_source_lines.append("# fmt: on")

                new_source = "\n".join(new_source_lines)

                if new_source != cell.source:
                    cell.source = new_source
                    notebook_modified = True

            if notebook_modified:
                session.log(
                    f"  -> Wrapped '@param' blocks with '# fmt: off/on' in {path}"
                )
                with open(path, "w", encoding="utf-8") as f:
                    nbformat.write(notebook, f)

        except Exception as e:
            session.warn(f"Could not process notebook {path}. Error: {e}")


@nox.session(python=DEFAULT_PYTHON_VERSION)
def format(session: nox.Session) -> None:
    """Formats Python files and Jupyter Notebooks.

    Pass '--all' to format all tracked files in the repository.
    Pass '--unsafe-fixes' to enable unsafe fixes with Ruff.
    Example: nox -s format -- --all --unsafe-fixes
    """
    # --- Argument Parsing ---
    format_all = "--all" in session.posargs
    ruff_unsafe_fixes_flag = (
        "--unsafe-fixes" if "--unsafe-fixes" in session.posargs else ""
    )

    spelling_allow_file = ".github/actions/spelling/allow.txt"
    if os.path.exists(spelling_allow_file):
        session.log(f"Sorting and de-duplicating {spelling_allow_file}")
        session.run(
            "sort",
            "-u",
            spelling_allow_file,
            "-o",
            spelling_allow_file,
            external=True,
        )

    if format_all:
        lint_paths_py = ["."]
        lint_paths_nb = ["."]
    else:
        target_branch = "main"

        unstaged_files = subprocess.run(
            ["git", "diff", "--name-only", "--diff-filter=ACMRTUXB", target_branch],
            stdout=subprocess.PIPE,
            text=True,
            check=False,
        ).stdout.splitlines()

        staged_files = subprocess.run(
            [
                "git",
                "diff",
                "--cached",
                "--name-only",
                "--diff-filter=ACMRTUXB",
                target_branch,
            ],
            stdout=subprocess.PIPE,
            text=True,
            check=False,
        ).stdout.splitlines()

        committed_files = subprocess.run(
            [
                "git",
                "diff",
                "HEAD",
                target_branch,
                "--name-only",
                "--diff-filter=ACMRTUXB",
            ],
            stdout=subprocess.PIPE,
            text=True,
            check=False,
        ).stdout.splitlines()

        changed_files = sorted(
            {
                file
                for file in (unstaged_files + staged_files + committed_files)
                if os.path.isfile(file)
            }
        )

        lint_paths_py = [
            f for f in changed_files if f.endswith(".py") and f != "noxfile.py"
        ]

        lint_paths_nb = [f for f in changed_files if f.endswith(".ipynb")]

        if not lint_paths_py and not lint_paths_nb:
            session.log("No changed Python or notebook files to lint.")
            return

    session.install(
        "autoflake",
        "ruff",
    )

    if lint_paths_py:
        session.run(
            "autoflake",
            "-i",
            "-r",
            "--remove-all-unused-imports",
            *lint_paths_py,
        )

        ruff_check_command = ["ruff", "check", "--fix-only"]
        if "--unsafe-fixes" in session.posargs:
            ruff_check_command.append("--unsafe-fixes")
        ruff_check_command.extend(lint_paths_py)
        session.run(*ruff_check_command)

        session.run(
            "ruff",
            "format",
            *lint_paths_py,
        )

    if lint_paths_nb:
        session.install(
            "git+https://github.com/tensorflow/docs",
            "ipython",
            "jupyter",
            "nbconvert",
            "nbqa>=1.9.1",
            "nbformat>=5.10.4",
        )

        preprocess_notebook(session, lint_paths_nb)
        update_notebook_links(session, lint_paths_nb)

        session.run(
            "nbqa",
            "autoflake",
            "-i",
            "-r",
            "--remove-all-unused-imports",
            *lint_paths_nb,
        )
        session.run(
            "nbqa",
            f"ruff check --fix-only {ruff_unsafe_fixes_flag}",
            *lint_paths_nb,
        )
        session.run(
            "nbqa",
            "ruff format",
            *lint_paths_nb,
        )
        session.run("python3", "-m", "tensorflow_docs.tools.nbfmt", *lint_paths_nb)
