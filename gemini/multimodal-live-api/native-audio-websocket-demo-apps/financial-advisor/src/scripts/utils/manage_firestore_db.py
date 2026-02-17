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


"""
A Python script to create a new Firestore database with collections for a user.
"""

import json
import sys

from pathlib import Path

import typer

from google.api_core import exceptions
from google.cloud import firestore, firestore_admin_v1
from rich.console import Console

# Add src directory to path to allow for absolute imports from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from common import get_credentials

from backend.app_settings import get_application_settings

app = typer.Typer()
console = Console()
app_settings = get_application_settings()


def _populate_user_data(db: firestore.Client, user_id: str, project_id: str):
    """Populates the database for a given user."""
    console.log(f"Populating Firestore database for user '{user_id}' in project '{project_id}'...")

    # Load data from JSON file
    json_file_path = Path(__file__).resolve().parents[3] / "src" / "backend" / "data" / "client_data.json"
    try:
        with open(json_file_path, "r") as f:
            client_data = json.load(f)
    except FileNotFoundError:
        console.log(f"[red]Error: client_data.json not found at {json_file_path}[/red]")
        raise typer.Exit(code=1)
    except json.JSONDecodeError:
        console.log("[red]Error: Could not decode JSON from client_data.json[/red]")
        raise typer.Exit(code=1)

    try:
        user_doc_ref = db.collection("users").document(user_id)
        user_doc_ref.set({}, merge=True)
        subcollection_ref = user_doc_ref.collection("client_data")
        subcollection_ref.document("profile").set(client_data, merge=True)
        console.log(f"[green]Successfully populated Firestore database for user '{user_id}'.[/green]")
    except Exception as e:
        console.log(f"[red]An error occurred during data population: {e}[/red]")
        raise typer.Exit(code=1)


@app.command()
def create_db(
    project_id: str = typer.Option("my-project-id", help="ID of the Google Cloud project"),
    user_id: str = typer.Option("financial_advisor_demo_user", help="The user ID to create the documents for."),
    location: str = typer.Option("nam5", help="The location for the new Firestore database."),
    database_id: str = typer.Option(
        app_settings.google_cloud.firestore_db_name, help="The ID of the Firestore database."
    ),
):
    """
    Creates a new Firestore database with collections for a user.

    This script establishes a Firestore structure as follows:
    - A top-level collection named 'users'.
    - A document within 'users' for each 'user_id'.
    - A subcollection named 'client_data' under each user's document.
    - A single document named 'profile' within the 'client_data' subcollection,
      containing the client data from 'src/backend/data/client_data.json'.
    """
    console.log(f"Checking for Firestore database '{database_id}' in project '{project_id}'...")

    credentials = get_credentials()

    try:
        db = firestore.Client(project=project_id, credentials=credentials, database=database_id)
        list(db.collections())  # This will raise an exception if the database does not exist.
    except (exceptions.NotFound, Exception):
        console.log(
            f"Firestore database '{database_id}' not found or accessible in project '{project_id}'. Creating one..."
        )
        try:
            admin_client = firestore_admin_v1.FirestoreAdminClient(credentials=credentials)
            parent = f"projects/{project_id}"

            operation = admin_client.create_database(
                request={
                    "parent": parent,
                    "database_id": database_id,
                    "database": {
                        "location_id": location,
                        "type": "FIRESTORE_NATIVE",
                    },
                }
            )
            console.log("Waiting for database creation to complete...")
            operation.result()

            console.log(
                f"[green]Successfully created Firestore database '{database_id}' in location '{location}'.[/green]"
            )
            db = firestore.Client(project=project_id, credentials=credentials, database=database_id)
        except Exception as e:
            console.log(f"[red]Failed to create Firestore database: {e}[/red]")
            # If creation fails, we might still try to populate if it was a race condition,
            # but usually we should stop. However, to be robust, we re-raise.
            raise typer.Exit(code=1)

    _populate_user_data(db, user_id, project_id)


@app.command()
def update_db(
    project_id: str = typer.Option("my-project-id", help="ID of the Google Cloud project"),
    user_id: str = typer.Option(
        "financial_advisor_demo_user",
        help="The user ID to create the documents for.",
    ),
):
    """
    Updates or creates the documents for a user in Firestore.

    This script populates the user's 'client_data' subcollection with a single
    document 'profile' from 'src/backend/data/client_data.json'.
    It assumes the Firestore database has already been created. If the user
    document already exists, its data will be merged with the data from the
    JSON file.
    """
    console.log(f"Checking for Firestore database in project '{project_id}'...")

    credentials = get_credentials()

    try:
        db = firestore.Client(project=project_id, credentials=credentials)
        list(db.collections())  # This will raise an exception if the database does not exist.
    except exceptions.NotFound:
        console.log(f"[red]Firestore database not found in project '{project_id}'.[/red]")
        console.log("[yellow]Please create it first by running the 'create-db' command.[/yellow]")
        raise typer.Exit(code=1)

    _populate_user_data(db, user_id, project_id)


@app.command()
def update_field(
    field_path: str = typer.Argument(
        ..., help="Dot-separated path to the field to update (e.g., 'personal_profile.name.first_name')."
    ),
    new_value: str = typer.Argument(..., help="The new value for the field."),
    project_id: str = typer.Option("my-project-id", help="ID of the Google Cloud project"),
    user_id: str = typer.Option(
        "financial_advisor_demo_user",
        help="The user ID to update the document for.",
    ),
):
    """
    Updates a single field in a user's profile document in Firestore.
    """
    console.log(f"Updating field '{field_path}' for user '{user_id}' in project '{project_id}'...")

    credentials = get_credentials()

    try:
        db = firestore.Client(project=project_id, credentials=credentials)
        list(db.collections())
    except exceptions.NotFound:
        console.log(f"[red]Firestore database not found in project '{project_id}'.[/red]")
        raise typer.Exit(code=1)

    try:
        doc_ref = db.collection("users").document(user_id).collection("client_data").document("profile")
        # Check if document exists before updating
        if not doc_ref.get().exists:
            console.log(f"[red]Profile document for user '{user_id}' does not exist.[/red]")
            console.log("[yellow]Please create it first by running the 'create-db' or 'update-db' command.[/yellow]")
            raise typer.Exit(code=1)

        # Typer doesn't automatically convert types for arguments, so we try to guess
        try:
            # Try to parse as JSON (for bool, numbers, etc.)
            value_to_set = json.loads(new_value)
        except json.JSONDecodeError:
            # Fallback to string
            value_to_set = new_value

        doc_ref.update({field_path: value_to_set})
        console.log(f"[green]Successfully updated field '{field_path}'.[/green]")
    except Exception as e:
        console.log(f"[red]An error occurred during field update: {e}[/red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
