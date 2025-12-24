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

import os
import sys

from pathlib import Path

import typer

from common import get_credentials
from google.cloud import storage
from rich.console import Console

# Add src directory to path to allow for absolute imports from the project root.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from backend.app_settings import get_application_settings

app_settings = get_application_settings()
app = typer.Typer()
console = Console()


@app.command()
def create(
    bucket_name: str = typer.Option(..., help="The name of the GCS bucket to create."),
    project: str = typer.Option("my-project-id", help="ID of the Google Cloud project"),
    location: str = typer.Option("US", help="Location for the GCS bucket."),
):
    """Creates a new GCS bucket."""
    credentials = get_credentials()
    storage_client = storage.Client(credentials=credentials, project=project)

    bucket = storage_client.bucket(bucket_name)
    if bucket.exists():
        console.log(f"Bucket {bucket_name} already exists.")
        return

    console.log(f"Creating bucket {bucket_name} in project {project}...")
    storage_client.create_bucket(bucket, location=location)
    console.log(f"Bucket {bucket_name} created successfully.")


@app.command()
def upload_pdfs(
    bucket_name: str = typer.Option(..., help="The name of the GCS bucket."),
    source_folder: str = typer.Option("src/backend/data", help="The local folder to upload files from."),
    project: str = typer.Option("my-project-id", help="ID of the Google Cloud project"),
):
    """Uploads all PDF files from a local directory to a GCS bucket."""
    credentials = get_credentials()
    storage_client = storage.Client(credentials=credentials, project=project)
    bucket = storage_client.bucket(bucket_name)

    if not bucket.exists():
        console.log(
            f"[bold red]Error:[/bold red] Bucket '{bucket_name}' does not exist. Please create it first using the 'create' command."
        )
        raise typer.Exit(code=1)

    console.log(f"Uploading PDF files from '{source_folder}' to GCS bucket '{bucket_name}'...")

    for filename in os.listdir(source_folder):
        if filename.endswith(".pdf"):
            source_path = os.path.join(source_folder, filename)
            blob = bucket.blob(filename)

            console.log(f"Uploading {source_path} to gs://{bucket_name}/{filename}")
            blob.upload_from_filename(source_path)
            console.log(f"File {filename} uploaded to {bucket_name}.")


if __name__ == "__main__":
    app()
