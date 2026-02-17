# Copyright 2026 Google LLC
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


#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
A Python script to create a Google Cloud Platform service account within a specified project.

This script leverages the `gcloud` command-line tool and requires it to be
installed and authenticated with sufficient permissions to create service
accounts and manage IAM policies.

Required Permissions (before running script):
    roles/discoveryengine.admin
    roles/editor
    roles/iam.serviceAccountAdmin
    roles/iam.serviceAccountKeyAdmin
    roles/resourcemanager.projectIamAdmin
    roles/secretmanager.admin
    roles/serviceusage.serviceUsageAdmin
"""

# import argparse
# import logging

# import subprocess
# import sys
# from pathlib import Path
import typer

from common import run_gcloud_command
from rich.console import Console

# # Add src directory to path to allow for absolute imports from the project root.
# sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
# from backend.settings import get_application_settings

# backend.app_settings = get_application_settings()
app = typer.Typer()
console = Console()


def create_service_account(project_id: str, account_id: str, display_name: str) -> bool:
    """
    Creates a new service account in the specified Google Cloud project if it doesn't exist.

    Args:
        project_id (str): The ID of the Google Cloud project.
        account_id (str): The ID for the new service account (e.g., 'my-sa').
        display_name (str): The display name for the new service account.
    """
    console.log(f"[blue]Checking for service account '{account_id}' in project '{project_id}'...[/blue]")
    service_account_email = f"{account_id}@{project_id}.iam.gserviceaccount.com"
    service_account_exists_command = [
        "gcloud",
        "iam",
        "service-accounts",
        "describe",
        service_account_email,
        f"--project={project_id}",
    ]
    if run_gcloud_command(command=service_account_exists_command):
        console.log(f"[green]Service account {service_account_email} already exists.[/green]")
        return True
    else:
        console.log(f"[blue]Service account '{account_id}' not found. Creating it...[/blue]")
        create_service_account_command = [
            "gcloud",
            "iam",
            "service-accounts",
            "create",
            account_id,
            f"--project={project_id}",
            f"--display-name={display_name}",
        ]
        console.log(f"[blue]Creating service account {service_account_email}...[/blue]")

        if run_gcloud_command(
            command=create_service_account_command,
        ):
            console.log(f"[green]Service account '{account_id}' created successfully.[/green]")
            return True
        else:
            console.log(f"[red]Failed to create service account {service_account_email}.[/red]")
            return False


@app.command()
def main(
    project_id: str = typer.Option(default="my-project-id", help="ID of the Google Cloud project"),
    account_id: str = typer.Option(default="my-srvc-acct-id", help="ID of the service account"),
    display_name: str = typer.Option(
        default="Financial Advisor Service Account", help="Display name of the service account"
    ),
):
    create_service_account(project_id, account_id, display_name)


if __name__ == "__main__":
    # main()
    app()

# def main():
#     """
#     Main function to parse arguments and orchestrate the creation of the service account.
#     """
#     parser = argparse.ArgumentParser(
#         description="Create a Google Cloud Service Account and assign it specific IAM roles.",
#         formatter_class=argparse.RawTextHelpFormatter,
#     )
#     parser.add_argument(
#         "--project_id",
#         default=app_settings.vertex_ai.google_cloud_project,
#         required=True,
#         help="The ID of your Google Cloud project.",
#     )
#     parser.add_argument(
#         "--account_id", required=True, help="The unique ID for the new service account (e.g., 'my-new-app-sa')."
#     )
#     parser.add_argument(
#         "--display_name", required=True, help="The display name for the service account (e.g., 'My New App SA')."
#     )

#     args = parser.parse_args()

#     if create_service_account(args.project_id, args.account_id, args.display_name):
#         assign_iam_roles(args.project_id, args.account_id)

#     logging.info("Script finished.")


# if __name__ == "__main__":
# main()
