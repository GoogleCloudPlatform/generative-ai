# pylint: skip-file
# type: ignore
# -*- coding: utf-8 -*-
#
# Copyright 2024 Google LLC
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
import sys
import urllib.parse

import nbformat

DEFAULT_RUFF_LINE_LENGTH = 88

# --- Notebook Link Constants ---
LINK_PREFIXES = {
    "colab_link": "https://colab.research.google.com/github/GoogleCloudPlatform/generative-ai/blob/main/",
    "colab_enterprise_link": "https://console.cloud.google.com/agent-platform/colab/import/",
    "github_link": "https://github.com/GoogleCloudPlatform/generative-ai/blob/main/",
    "workbench_link": "https://console.cloud.google.com/agent-platform/workbench/instances?download_url=",
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


def wrap_param_blocks(
    cell_source: str, max_line_length: int = DEFAULT_RUFF_LINE_LENGTH
) -> tuple[str, bool]:
    """Wraps long '@param' lines in a code cell with '# fmt: off/on'."""
    if "@param" not in cell_source:
        return cell_source, False

    source_lines = cell_source.split("\n")
    clean_source_lines = [
        line for line in source_lines if line.strip() not in ["# fmt: off", "# fmt: on"]
    ]

    param_indices = [
        i
        for i, line in enumerate(clean_source_lines)
        if "@param" in line and len(line) >= max_line_length
    ]

    if not param_indices:
        return cell_source, False

    first_param_index = param_indices[0]
    last_param_index = param_indices[-1]

    new_source_lines = []
    for i, line in enumerate(clean_source_lines):
        if i == first_param_index:
            new_source_lines.append("# fmt: off")
        new_source_lines.append(line)
        if i == last_param_index:
            new_source_lines.append("# fmt: on")

    new_source = "\n".join(new_source_lines)
    return new_source, new_source != cell_source


def process_notebooks(
    notebook_paths: list[str],
    max_line_length: int = DEFAULT_RUFF_LINE_LENGTH,
) -> None:
    """Processes notebooks in a single pass: wraps '@param' blocks and fixes links."""
    print("Processing notebooks ('@param' blocks and links)...")
    links_updated_count = 0

    for notebook_path in notebook_paths:
        try:
            with open(notebook_path, encoding="utf-8") as f:
                notebook = nbformat.read(f, as_version=4)

            relative_notebook_path = os.path.relpath(
                notebook_path, start=os.getcwd()
            ).lower()
            check_links = "vector-search-2-intro" not in notebook_path
            params_modified = False
            links_modified = False

            for cell in notebook.cells:
                if cell.cell_type == "code":
                    updated_source, changed = wrap_param_blocks(
                        cell.source, max_line_length=max_line_length
                    )
                    if changed:
                        cell.source = updated_source
                        params_modified = True
                elif (
                    check_links
                    and cell.cell_type == "markdown"
                    and "<table" in cell.source
                    and "colab" in cell.source
                ):
                    updated_source, changed = fix_markdown_links(
                        cell.source, relative_notebook_path
                    )
                    if changed:
                        cell.source = updated_source
                        links_modified = True

            if params_modified:
                print(
                    f"  -> Wrapped '@param' blocks with '# fmt: off/on' in {notebook_path}"
                )

            if links_modified:
                links_updated_count += 1
                print(f"  -> Fixed links in {notebook_path}")

            if params_modified or links_modified:
                with open(notebook_path, "w", encoding="utf-8") as f:
                    nbformat.write(notebook, f)

        except Exception as e:
            print(f"Could not process notebook {notebook_path}. Error: {e}")

    if links_updated_count > 0:
        print(f"Fixed links in {links_updated_count} notebooks.")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(
            "Usage: python notebook_processor.py <notebook_path1> <notebook_path2> ..."
        )
        sys.exit(1)

    process_notebooks(sys.argv[1:])
