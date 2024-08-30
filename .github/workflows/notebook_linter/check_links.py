import os
import sys
import urllib.parse

import nbformat

LINK_PREFIXES = {
    "colab_link": "https://colab.research.google.com/github/GoogleCloudPlatform/generative-ai/blob/main/",
    "colab_enterprise_link": "https://console.cloud.google.com/vertex-ai/colab/import/",
    "github_link": "https://github.com/GoogleCloudPlatform/generative-ai/blob/main/",
    "workbench_link": "https://console.cloud.google.com/vertex-ai/workbench/deploy-notebook?download_url=",
}

RAW_URL_PREFIX = (
    "https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/main/"
)


def fix_markdown_links(cell_source, relative_notebook_path: str):
    """Fixes links in a markdown cell and returns the updated source."""
    new_lines = []
    changes_made = False

    for line in cell_source.splitlines():
        for key, prefix in LINK_PREFIXES.items():
            if not prefix in line:
                continue

            start_index = line.find(prefix) + len(prefix)
            end_index = line.find(".ipynb", start_index) + len(".ipynb")
            correct_link = ""

            if key in {"colab_link", "github_link"}:
                correct_link = relative_notebook_path
            elif key == "colab_enterprise_link":
                encoded_path = urllib.parse.quote(
                    f"{RAW_URL_PREFIX}{relative_notebook_path}",
                    safe=":",
                )
                correct_link = f"{prefix}{encoded_path}"
            elif key == "workbench_link":
                correct_link = f"{prefix}{RAW_URL_PREFIX}{relative_notebook_path}"

            if correct_link not in line:
                print(f"Fixing {key} in {relative_notebook_path}: {line}")
                line = line.replace(line[start_index:end_index], correct_link)
                changes_made = True

        new_lines.append(line)

    return "\n".join(new_lines), changes_made


def fix_links_in_notebook(notebook_path: str):
    """Fixes specific types of links in a Jupyter notebook."""
    with open(notebook_path, "r", encoding="utf-8") as f:
        notebook = nbformat.read(f, as_version=4)

    relative_notebook_path = os.path.relpath(notebook_path, start=os.getcwd())

    for cell in notebook.cells:
        if cell.cell_type == "markdown" and "<table" in cell.source:
            updated_source, changes_made = fix_markdown_links(
                cell.source, relative_notebook_path
            )
            if changes_made:
                cell.source = updated_source
                with open(notebook_path, "w", encoding="utf-8") as f:
                    nbformat.write(notebook, f)
                print(f"Updated {notebook_path}\n")
                return


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python check_links.py <notebook_path>")
        sys.exit(1)

    fix_links_in_notebook(sys.argv[1])
