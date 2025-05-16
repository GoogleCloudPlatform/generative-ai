import os
import subprocess

# Get the list of files from the Notebooks.txt file
notebook_paths = []
with open(".cloud-build/Notebooks.txt", "r") as f:
    for line in f:
        notebook_paths.append(line.strip())

# Install dependencies
subprocess.run(["pip", "install", "-U", "nbqa", "flake8-nb", "pylint"], check=True)

# Loop through the files and run pylint and flake8
for notebook_path_relative in notebook_paths:
    try:
        notebook_path = os.path.join("/workspace", notebook_path_relative)

        if not os.path.exists(notebook_path):
            print(f"Warning: Notebook not found at {notebook_path}, skipping linting.")
            continue

        # Run pylint on the notebook https://pypi.org/project/pylint/
        subprocess.run(["nbqa", "pylint", notebook_path], check=True)

        # Run flake8 on the notebook https://flake8-nb.readthedocs.io/en/latest/usage.html PEP8
        subprocess.run(["nbqa", "flake8_nb", notebook_path], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Error linting {notebook_path}: {e}")
