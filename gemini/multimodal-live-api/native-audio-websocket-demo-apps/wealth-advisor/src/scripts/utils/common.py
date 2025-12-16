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


import subprocess
import sys

from pathlib import Path
from typing import List, Union

import typer

from dotenv import load_dotenv
from google.api_core import exceptions
from google.auth import default
from google.cloud import secretmanager_v1
from google.cloud.secretmanager import SecretManagerServiceClient
from rich.console import Console

# Add src directory to path to allow for absolute imports from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app_settings import get_application_settings

console = Console()
app_settings = get_application_settings()


def get_credentials():
    """Retrieves credentials for Google Cloud authentication."""
    # Simplified to rely on ADC as per the refactoring plan
    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    credentials, _ = default(scopes=scopes)
    return credentials


def _load_gcp_environment_variables():
    """Used for loading a .env file"""
    env_path = Path(__file__).parent.parent / "src/backend/.env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)


def run_gcloud_command(command: List[str], ignore_creation_errors: bool = False):
    try:
        result = subprocess.run(command, text=True, capture_output=True, check=False)
        console.log(f"[blue]Running command: {' '.join(command)}[/blue]")
        console.log(f"[blue]Command Output: {result.stdout.strip()}[/blue]")
        if result.returncode != 0:
            if ignore_creation_errors and ("already exists" in result.stderr or "denied" in result.stderr):
                console.log(f"[yellow]Warning: {result.stderr.strip()}[/yellow]")
                return True
            console.log(f"[red]Error: {result.stderr.strip()}[/red]")
            return False
        return True
    except FileNotFoundError:
        console.log(f"[red]Error: command not found: {command[0]}[/red]")
        return False


def create_or_update_secret(
    client: SecretManagerServiceClient, project_id: str, secret_id: str, secret_value: Union[str, bool]
):
    """Creates a secret if it doesn't exist, and adds a new version with the secret value."""
    parent = f"projects/{project_id}"
    secret_path = f"{parent}/secrets/{secret_id}"

    try:
        request = secretmanager_v1.GetSecretRequest(
            name=secret_path,
        )
        client.get_secret(request=request)
        console.log(f"Secret [yellow]{secret_id}[/yellow] already exists.")
    except exceptions.ServiceUnavailable as e:
        console.log("[bold red]Service Unavailable:[/bold red] Could not connect to Google Cloud services.")
        console.log("This may be due to an authentication error or network issue.")
        console.log(f"Details: {e}")
        raise typer.Exit(1)
    except exceptions.NotFound:
        console.log(f"Secret [yellow]{secret_id}[/yellow] not found, creating it.")
        client.create_secret(
            request={
                "parent": parent,
                "secret_id": secret_id,
                "secret": {"replication": {"automatic": {}}},
            }
        )
        console.log(f"Secret [green]{secret_id}[/green] created.")

    if isinstance(secret_value, bool):
        secret_value = str(secret_value)

    payload_bytes = secret_value.encode("UTF-8")

    # Check for existing versions to avoid creating duplicates
    versions = list(client.list_secret_versions(request={"parent": secret_path}))
    for version in versions:
        if version.state == "ENABLED":
            response = client.access_secret_version(name=version.name)
            if response.payload.data == payload_bytes:
                console.log(
                    f"[yellow]Secret version for [yellow]{secret_id}[/yellow] with the same payload already exists. Skipping.[/yellow]"
                )
                return

    console.log(f"Adding new secret version for [yellow]{secret_id}[/yellow].")
    client.add_secret_version(request={"parent": secret_path, "payload": {"data": payload_bytes}})
    console.log(f"Successfully added new version to secret [green]{secret_id}[/green].")


def get_secret_value(client: SecretManagerServiceClient, project_id: str, secret_id: str) -> str:
    """Retrieves the latest version of a secret's value."""
    secret_path = f"projects/{project_id}/secrets/{secret_id}/versions/latest"

    try:
        response = client.access_secret_version(name=secret_path)
        return response.payload.data.decode("UTF-8")
    except exceptions.NotFound:
        console.log(f"[red]Secret {secret_id} not found.[/red]")
        raise
    except exceptions.PermissionDenied:
        console.log(f"[red]Permission denied to access secret {secret_id}.[/red]")
        raise
    except Exception as e:
        console.log(f"[red]An unexpected error occurred: {e}[/red]")
        raise
