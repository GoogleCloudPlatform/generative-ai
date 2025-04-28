import os
import subprocess

# Get the list of files in the directory
TARGET = os.listdir("/workspace/generative-ai/gemini/getting-started")

# Install dependencies
subprocess.run(["pip", "install", "-U", "nbqa", "flake8-nb", "pylint"], check=True)

# Loop through the files and run pylint and flake8
for filename in TARGET:
    try:
        # Construct the full path to the notebook file
        notebook_path = os.path.join(
            "/workspace/generative-ai/gemini/getting-started", filename
        )

        # Run pylint on the notebook https://pypi.org/project/pylint/
        subprocess.run(["nbqa", "pylint", notebook_path], check=True)

        # Run flake8 on the notebook https://flake8-nb.readthedocs.io/en/latest/usage.html PEP8
        subprocess.run(["nbqa", "flake8_nb", notebook_path], check=True)

    except subprocess.CalledProcessError as e:
        print(f"Error linting {filename}: {e}")
