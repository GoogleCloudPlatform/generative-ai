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


def replace_in_file(
    file_path: Path, search_str: str, replacement_file_path: Path
) -> None:
    """Replace a string in a file with contents from another file."""
    with open(replacement_file_path, "r") as f:
        replacement_content = f.read()

    with open(file_path, "r") as f:
        content = f.read()

    with open(file_path, "w") as f:
        f.write(content.replace(search_str, replacement_content))


def append_file_contents(source_file: Path, target_file: Path) -> None:
    """Append contents of one file to another."""
    with open(source_file, "r") as source, open(target_file, "a") as target:
        target.write(source.read())


def main() -> None:
    """Set up the agentic RAG pattern by copying and updating Terraform files.

    Makes a backup of the deployment folder, then updates various Terraform files
    with pattern-specific configurations by replacing content and appending updates.
    """
    base_path = Path(
        "app/patterns/agentic_rag_vertex_ai_search/pattern_setup/resources_to_copy"
    )
    terraform_path = base_path / "deployment/terraform"
    deployment_path = Path("deployment/terraform")
    # Make backup copy of deployment folder
    deployment_backup_path = Path(".deployment_backup")
    if deployment_backup_path.exists():
        shutil.rmtree(deployment_backup_path)
    print(f"Creating backup of deployment folder at '{deployment_backup_path}'")
    shutil.copytree("deployment", deployment_backup_path, dirs_exist_ok=True)

    # Replace content in build_triggers.tf
    build_triggers_replacements = {
        "# Your other CD Pipeline substitutions": terraform_path
        / "substitute__cd_pipeline_triggers.tf_updates",
        "# Your other Deploy to Prod Pipeline substitutions": terraform_path
        / "substitute__deploy_to_prod_pipeline_triggers.tf_updates",
    }

    for search_str, replacement_file in build_triggers_replacements.items():
        replace_in_file(
            deployment_path / "build_triggers.tf", search_str, replacement_file
        )

    # Append contents to various tf files
    tf_files_to_append = {
        "iam.tf": "append__iam.tf_updates",
        "service_accounts.tf": "append__service_accounts.tf_updates",
        "storage.tf": "append__storage.tf_updates",
        "variables.tf": "append__variables.tf_updates",
    }

    for target_file, source_file in tf_files_to_append.items():
        append_file_contents(
            terraform_path / source_file, deployment_path / target_file
        )

    # Append to env.tfvars
    append_file_contents(
        terraform_path / "vars/append__env.tfvars_updates",
        deployment_path / "vars/env.tfvars",
    )

    # Copy files
    shutil.copy(
        terraform_path / "data_store.tf_updates", deployment_path / "data_store.tf"
    )
    shutil.copytree(base_path / "deployment/cd", "deployment/cd", dirs_exist_ok=True)
    # Additional operations on dev folder
    # Define files to append in dev directory
    dev_files_to_append = {
        "dev/vars/env.tfvars": "dev/vars/append__env.tfvars_updates",
        "dev/variables.tf": "dev/append__variables.tf_updates",
        "dev/iam.tf": "dev/append__iam.tf_updates",
        "dev/service_accounts.tf": "dev/append__service_accounts.tf_updates",
        "dev/storage.tf": "dev/append__storage.tf_updates",
    }

    # Append contents to each file
    for target_file, source_file in dev_files_to_append.items():
        append_file_contents(
            terraform_path / source_file, deployment_path / target_file
        )
    shutil.copy(
        terraform_path / "dev/data_store.tf_updates",
        deployment_path / "dev/data_store.tf",
    )

    # Setup data ingestion
    data_processing_path = Path("data_processing")
    data_processing_path.mkdir(exist_ok=True)
    shutil.copytree(
        base_path / "data_processing", data_processing_path, dirs_exist_ok=True
    )
    for filename in ("chain.py", "retrievers.py", "templates.py"):
        shutil.copy(base_path / "app" / filename, Path("app") / filename)

    # Setup tests
    test_integration_path = Path("tests/integration")
    shutil.copy(
        base_path / "tests/integration/test_chain.py",
        test_integration_path / "test_chain.py",
    )

    print("Successfully copied pattern files")


if __name__ == "__main__":
    main()
