import copy
import json
import os


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


def read_notebook(notebook_path: str) -> dict:
    """Reads a Jupyter notebook and returns its contents as a dictionary.

    Args:
        notebook_path (str): The path to the Jupyter notebook to read.

    Returns:
        dict: The contents of the Jupyter notebook as a dictionary.
    """

    with open(notebook_path, "r") as nb:
        data = json.loads(nb.read())

    return data


def write_notebook(notebook_path: str, data: dict):
    """Writes a dictionary to a Jupyter notebook.

    Args:
        notebook_path (str): The path to the Jupyter notebook to write to.
        data (dict): The data to write to the Jupyter notebook.
    """

    with open(notebook_path, "w") as nb:
        nb.write(json.dumps(data, indent=4))


def populate_table(notebook_path: str) -> list[str]:
    """Creates a html table of links to run, view, and deploy a Jupyter notebook on various platforms.

    Args:
        notebook_path (str): The path to the Jupyter notebook.

    Returns:
        list[str]: A list of strings containing the HTML code for the table.
    """

    # css styles
    div_style = "display: inline-block; margin-top: 25px; margin-right: 15px"

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
        "UiNooY4LUgW_oTvpsNhPpQzsstV5W8F7rYgxgGBD85cWJoLmrOzhVs_ksK_vgx40SHs7jCqkTkCk="
        "e14-rj-sc0xffffff-h130-w32"
    )

    html_elements = f"""
    <div style="{div_style}">
        <a href="{colab_link}">
            <img src="{colab_logo}" alt="Google Colaboratory logo"> Run on Google Colab
        </a>
    </div>\n
    <div style="{div_style}">
        <a href="{github_link}">
            <img src="{github_logo}" alt="GitHub logo"> View on GitHub
        </a>
    </div>\n
    <div style="{div_style}">
        <a href="{vertex_link}">
            <img src="{vertex_logo}" alt="Vertex AI logo"> Deploy to Vertex AI Workbench
        </a>
    </div>"""

    # .strip() is needed here to remove the leading spaces. Leading spaces prevent markdown rendering.
    html_elements_as_list = [f"{x.strip()}\n" for x in html_elements.split("\n")]
    return html_elements_as_list


def fix_links_in_notebook(notebook_path: str, data: dict) -> dict:
    """Replace the existing html table with newly populated one in a Jupyter notebook.

    Args:
        notebook_path (str): The path to the Jupyter notebook.
        data (dict): The contents of the Jupyter notebook as a dictionary.

    Returns:
        dict: The contents of the Jupyter notebook as a dictionary, with the links fixed.
    """

    # Create a new html table list using existing and populated content
    existing_html_elements = data["cells"][1]["source"]
    populated_html_elements = populate_table(notebook_path)
    new_html_elements = existing_html_elements[:1] + populated_html_elements

    # Create a true copy and edit the cell with new html table
    new_data = copy.deepcopy(data)
    new_data["cells"][1]["source"] = new_html_elements
    return new_data


def main():
    # Define a list of all the folders to check
    folders_to_check = ["language", "vision"]

    # For each folder, check all the Jupyter notebooks and fix the links
    for folder in folders_to_check:
        print(f" === Checking '{folder}' folder === ")
        notebooks_to_check = get_notebook_paths(folder)

        # If there are no notebooks, print a message and exit
        if len(notebooks_to_check) == 0:
            print(" > No notebook found ⚠️ ", "\n")
            continue

        # For each notebook, read the contents and fix the links
        fixed_notebooks = []
        for notebook in notebooks_to_check:
            data = read_notebook(notebook)
            new_data = fix_links_in_notebook(notebook, data)

            # If the links were fixed, write the notebook back with the new links
            if new_data["cells"][1]["source"] != data["cells"][1]["source"]:
                fixed_notebooks.append(notebook)
                write_notebook(notebook, new_data)
                print(f"  > '{notebook}' - FIXED 🆕 ")

        # Print a final message with the number of notebooks that were fixed
        if fixed_notebooks:
            print(f" > Fixed {len(fixed_notebooks)} notebooks", "\n")
        else:
            print(" > All notebooks are good to go ✅ ", "\n")


if __name__ == "__main__":
    main()
