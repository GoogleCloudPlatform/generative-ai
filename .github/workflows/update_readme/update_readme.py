import os
from typing import List, Tuple
from pathlib import Path
import magika
import datetime
from vertexai.preview.generative_models import GenerativeModel
from vertexai.preview import caching
import re

PROJECT_ID = "document-ai-test-337818"  # @param {type:"string"}
LOCATION = "us-central1"  # @param {type:"string"}

import vertexai

vertexai.init(project=PROJECT_ID, location=LOCATION)


def extract_code(repo_dir: str) -> Tuple[List, str]:
    """Create an index, extract content of code/text files."""

    m = magika.Magika()

    code_index = []
    code_text = []

    for root, _, files in os.walk(repo_dir):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, repo_dir)
            file_type = m.identify_path(Path(file_path))
            if file_type.output.group in ("text", "code"):
                try:
                    with open(file_path, "r", errors="replace", encoding="utf-8") as f:
                        code_text.append(f"----- File: {relative_path} -----\n")
                        code_text.append("```")
                        code_text.append(f.read())
                        code_text.append("```")
                        code_text.append("\n-------------------------\n")
                    code_index.append(relative_path)
                except Exception:
                    pass

    return code_index, "".join(code_text)


def gemini(code_index: List[str], code_text: str, directory: str) -> str:
    MODEL_ID = "gemini-1.5-pro-001"  # @param {type:"string"}

    contents = f"""
        Context:
        - Here is an index of all of the files in the directory {directory}:
        \n\n{code_index}\n\n.
    """
    print("Code Index", code_index)
    # cached_content = caching.CachedContent.create(
    #     model_name=MODEL_ID,
    #     system_instruction="You are an expert software engineer, proficient in GitHub, Generative AI and Google Cloud.",
    #     contents=contents,
    #     ttl=datetime.timedelta(minutes=60),
    #     display_name="example-cache",
    # )

    prompt = f"""Context:
    {contents}
    
    Write a GitHub README.md file for the directory in the context.
    Give an outline of the files in the directory with links and descriptions of files.

    Just output the markdown, don't include the ``` code fences."""

    # model = GenerativeModel.from_cached_content(cached_content=cached_content)

    model = GenerativeModel(
        model_name=MODEL_ID,
        system_instruction="You are an expert software engineer, proficient in GitHub, Generative AI and Google Cloud.",
    )

    response = model.generate_content(prompt)

    return response.text


def update_readme() -> None:

    # Get all top-level directories
    top_level_dirs = [
        d for d in os.listdir(".") if os.path.isdir(d) and not d.startswith(".")
    ]
    for directory in top_level_dirs:
        readme_path = os.path.join(directory, "README.md")
        mode = "w+" if not os.path.exists(readme_path) else "a+"

        code_index, code_text = extract_code(directory)
        readme_content = gemini(code_index, code_text, directory)

        # # Regex pattern to match the format provided
        # pattern = r"```(.*?)```"

        # matches = re.findall(pattern, readme_content, re.DOTALL)[0]

        # file_content = matches[0].strip()
        # print(file_content)

        with open(readme_path, mode, encoding="utf-8") as f:
            f.seek(0)  # Move to the beginning of the file for 'a+' mode
            content = f.read()

            # Check if content exists, otherwise add default content
            if not content:
                f.write(readme_content)
            else:
                # You could add logic here to update existing READMEs if needed
                pass


if __name__ == "__main__":
    update_readme()
