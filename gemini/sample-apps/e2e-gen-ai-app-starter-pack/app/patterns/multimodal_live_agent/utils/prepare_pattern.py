# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from pathlib import Path
import shutil


def main() -> None:
    """Reorganize the project structure.

    - Creates backup of app folder
    - Moves pattern files to root app folder
    - Moves frontend folder to root
    - Moves test folder to root
    - Copies pyproject.toml and poetry.lock to root
    """
    # Define paths
    app_path = Path("app")
    backup_app_path = Path("_app_backup")
    pattern_path = Path("_app_backup/patterns/multimodal_live_agent")
    root_path = Path(".")

    # Create backup of app folder
    if backup_app_path.exists():
        shutil.rmtree(backup_app_path)
    shutil.copytree(str(app_path), str(backup_app_path))

    # Move pattern files to root app folder
    if app_path.exists():
        shutil.rmtree(app_path)
    app_path.mkdir()
    pattern_app_path = pattern_path / "app"
    if pattern_app_path.exists():
        shutil.copytree(str(pattern_app_path), str(app_path), dirs_exist_ok=True)

    # Move frontend folder to root
    frontend_path = pattern_path / "frontend"
    if frontend_path.exists():
        root_frontend = root_path / "frontend"
        if root_frontend.exists():
            shutil.rmtree(root_frontend)
        shutil.copytree(str(frontend_path), str(root_frontend))

    # Move test folder to root
    test_path = pattern_path / "tests"
    if test_path.exists():
        root_test = root_path / "tests"
        if root_test.exists():
            shutil.rmtree(root_test)
        shutil.copytree(str(test_path), str(root_test))
    # Delete pattern folder from root app
    patterns_path = root_path / "app" / "patterns"
    if patterns_path.exists():
        shutil.rmtree(patterns_path)

    # Delete streamlit app
    streamlit_path = root_path / "streamlit"
    if streamlit_path.exists():
        shutil.rmtree(streamlit_path)

    # Move pattern README to root as PATTERN_README
    pattern_readme = pattern_path / "README.md"
    if pattern_readme.exists():
        root_readme = root_path / "PATTERN_README.md"
        shutil.copy(str(pattern_readme), str(root_readme))

    # Copy poetry files to root if they exist
    for filename in ["pyproject.toml", "poetry.lock"]:
        pattern_file = pattern_path / filename
        shutil.copy(str(pattern_file), str(root_path / filename))

    print("Successfully reorganized project structure")


if __name__ == "__main__":
    main()
