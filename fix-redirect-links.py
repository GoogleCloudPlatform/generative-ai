import os

import nbformat


def get_notebook_paths(folder_path: str) -> list[str]:
    """Gets the paths to all Jupyter notebooks in the specified folder.

    Args:
        folder_path (str): The path to the folder to search.

    Returns:
        list[str]: A list of the paths to all Jupyter notebooks in the specified folder.
    """

    all_notebook_paths = []

    try:
        for root, directories, files in os.walk(folder_path):
            file_paths = [os.path.join(root, f) for f in files if f.endswith(".ipynb")]
            all_notebook_paths += file_paths
    except FileNotFoundError:
        print(f"The folder '{folder_path}' does not exist.")

    return all_notebook_paths


def write_notebook(notebook_path: str, notebook_obj: nbformat.NotebookNode):
    """Writes a new content to a Jupyter notebook.

    Args:
        notebook_path (str): The path to the Jupyter notebook.
        notebook_obj (nbformat.NotebookNode): The Jupyter notebook to write to.
    """
    with open(notebook_path, "w") as f:
        nbformat.write(notebook_obj, f)


def populate_new_cell_content(notebook_path: str, header: str) -> str:
    """Creates a html code that contains links to run, view, and deploy a Jupyter notebook on various platforms.

    Args:
        notebook_path (str): The path to the Jupyter notebook.
        header (str): The header from the existing Jupyter notebook's cell
    Returns:
        str: A new cell content populated using the header and the notebookpath.
    """

    # redirect links
    colab_link = f"https://colab.research.google.com/github/GoogleCloudPlatform/generative-ai/blob/main/{notebook_path}"
    github_link = f"https://github.com/GoogleCloudPlatform/generative-ai/blob/main/{notebook_path}"
    raw_github_link = f"https://raw.githubusercontent.com/GoogleCloudPlatform/generative-ai/blob/main/{notebook_path}"
    vertex_link = f"https://console.cloud.google.com/vertex-ai/workbench/deploy-notebook?download_url={raw_github_link}"

    # product logos
    colab_logo = "https://cloud.google.com/ml-engine/images/colab-logo-32px.png"
    github_logo = "https://cloud.google.com/ml-engine/images/github-logo-32px.png"
    vertex_logo = (
        "https://lh3.googleusercontent.com/"
        "UiNooY4LUgW_oTvpsNhPpQzsstV5W8F7rYgxgGBD85cWJoLmrOzhVs_ksK_vgx40SHs7jCqkTkCk=e14-rj-sc0xffffff-h130-w32"
    )

    html_code = f"""
        <table align="left">
            <td style="text-align: center">
                <a href="{colab_link}">
                    <img src="{colab_logo}" alt="Google Colaboratory logo"><br> Run in Colab
                </a>
            </td>
            <td style="text-align: center">
                <a href="{github_link}">
                    <img src="{github_logo}" alt="GitHub logo"><br> View on GitHub
                </a>
            </td>
            <td style="text-align: center">
                <a href="{vertex_link}">
                    <img src="{vertex_logo}" alt="Vertex AI logo"><br> Open in Vertex AI Workbench
                </a>
            </td>
        </table>
    """

    formatted_html_code = ""
    for line in html_code.split("\n")[1:-1]:
        # Remove all leading and trailing spaces.
        line = line.strip() + "\n"

        # Format the code using 2 spaces for each indentation level.
        indent = "  "
        if line.startswith("<td") or line.startswith("</td"):
            line = (indent * 1) + line
        elif line.startswith("<a") or line.startswith("</a"):
            line = (indent * 2) + line
        elif line.startswith("<img"):
            line = (indent * 3) + line

        # Concat the lines back
        formatted_html_code += line

    # Concat existing header with the formatted html code
    new_cell_content = f"{header}\n\n{formatted_html_code}"
    return new_cell_content


def main():
    # Define a list of all the folders to check
    folders_to_check = ["language", "vision"]

    # For each folder, check all the Jupyter notebooks and fix the links
    for folder in folders_to_check:
        print(f" === Checking '{folder}' folder === ")
        notebooks_to_check = get_notebook_paths(folder)

        # If there are no notebooks in this folder, print a message and continue to the next folder
        if len(notebooks_to_check) == 0:
            print(" > No notebook found ⚠️ ", "\n")
            continue

        # For each notebook in this folder, read the contents and fix the links
        fixed_notebooks = []
        for notebook_path in notebooks_to_check:
            # Read the notebook, version 4 is the latest working version at the moment
            notebook_obj = nbformat.read(notebook_path, as_version=4)

            # Populate new cell content
            existing_cell_content = notebook_obj.cells[1].source
            header = existing_cell_content.split("\n\n")[0].strip()
            new_cell_content = populate_new_cell_content(notebook_path, header)

            # If there is a need to update the links, write the notebook back with the new cell content
            if new_cell_content != existing_cell_content:
                notebook_obj.cells[1].source = new_cell_content
                write_notebook(notebook_path, notebook_obj)
                fixed_notebooks.append(notebook_path)
                print(f"  > '{notebook_path}' - FIXED 🆕 ")

        # Print a final message with the number of notebooks that were fixed
        if fixed_notebooks:
            print(f" > Fixed {len(fixed_notebooks)} notebooks", "\n")
        else:
            print(" > All notebooks are good to go ✅. Fixing not required.", "\n")


if __name__ == "__main__":
    main()
