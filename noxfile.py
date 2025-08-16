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

import nox

DEFAULT_PYTHON_VERSION = "3.11"

nox.options.sessions = [
    "format",
]
nox.options.reuse_existing_virtualenvs = True


@nox.session(python=DEFAULT_PYTHON_VERSION)
def format(session) -> None:
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
        session.run(
            "ruff",
            "check",
            "--fix-only",
            ruff_unsafe_fixes_flag,
            *lint_paths_py,
        )
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
            "nbqa",
            "nbformat",
        )

        session.run("python3", ".github/workflows/update_notebook_links.py", ".")

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
