# Copyright 2025 Google LLC
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
A Python script to assign IAM roles to a service account within a specified project.

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

import typer

from common import run_gcloud_command
from rich.console import Console
from rich.progress import track

app = typer.Typer()
console = Console()

# Define the list of IAM roles to be assigned to the new service account.
ROLES_TO_ASSIGN = [
    "roles/discoveryengine.admin",  # Discovery Engine Admin
    "roles/editor",  # Editor
    "roles/secretmanager.admin",  # Secret Manager Admin
    "roles/discoveryengine.viewer",
    "roles/serviceusage.serviceUsageAdmin",  # Service Usage Admin
    "roles/serviceusage.serviceUsageConsumer",
    "roles/discoveryengine.editor",
    "roles/storage.admin",
    "roles/artifactregistry.admin",
    "roles/datastore.cloneAdmin",
    "roles/bigquery.dataViewer",
    "roles/bigquery.jobUser",
    "roles/bigquery.admin",
    "roles/logging.logWriter",
]


def assign_iam_roles(project_id: str, account_id: str, role: str):
    """
    Assigns the predefined IAM roles to the service account.

    Args:
        project_id (str): The ID of the GCP project.
        account_id (str): The ID of the service account.
    """
    console.log(f"Assigning IAM roles to service account '{account_id}'...")
    service_account_email = f"{account_id}@{project_id}.iam.gserviceaccount.com"
    all_roles_assigned = False
    command = [
        "gcloud",
        "projects",
        "add-iam-policy-binding",
        project_id,
        f"--member=serviceAccount:{service_account_email}",
        f"--role={role}",
    ]

    if run_gcloud_command(command):
        all_roles_assigned = True

    if all_roles_assigned:
        console.log(f"[green]Role {role} assigned to service account {service_account_email} successfully.[/green]")
    else:
        console.log(f"[yellow]Failed to assign role {role} to service account {service_account_email}.[/yellow]")


@app.command()
def main(
    project_id: str = typer.Option(default="my-project-id", help="ID of the GCP project"),
    account_id: str = typer.Option(default="my-srvc-acct-id", help="ID of the service account"),
    role: str = typer.Option(default=ROLES_TO_ASSIGN[0], help="IAM role to assign to the service account"),
):
    for role in track(ROLES_TO_ASSIGN, description="Assigning IAM roles..."):
        assign_iam_roles(project_id, account_id, role)


if __name__ == "__main__":
    app()
