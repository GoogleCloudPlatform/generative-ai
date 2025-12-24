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
A Python script to enable a list of Google Cloud Platform (GCP) APIs
for a specified project.

This script leverages the `gcloud` command-line tool and requires it to be
installed and authenticated with sufficient permissions to enable APIs.

Required step before running script:
    gcloud auth login

Required Permissions (before running script):
    roles/serviceusage.serviceUsageAdmin
"""

from typing import List, Optional

import typer

from common import run_gcloud_command
from rich.console import Console
from rich.progress import track

app = typer.Typer()
console = Console()


DEFAULT_APIS_TO_ENABLE = [
    "aiplatform.googleapis.com",
    "analyticshub.googleapis.com",
    "appengine.googleapis.com",
    "appenginereporting.googleapis.com",
    "artifactregistry.googleapis.com",
    "autoscaling.googleapis.com",
    "bigquery.googleapis.com",
    "bigqueryconnection.googleapis.com",
    "bigquerydatapolicy.googleapis.com",
    "bigquerydatatransfer.googleapis.com",
    "bigquerymigration.googleapis.com",
    "bigqueryreservation.googleapis.com",
    "bigquerystorage.googleapis.com",
    "binaryauthorization.googleapis.com",
    "calendar-json.googleapis.com",
    "certificatemanager.googleapis.com",
    "chat.googleapis.com",
    "cloudaicompanion.googleapis.com",
    "cloudapis.googleapis.com",
    "cloudbuild.googleapis.com",
    "cloudfunctions.googleapis.com",
    "cloudresourcemanager.googleapis.com",
    "cloudscheduler.googleapis.com",
    "cloudtrace.googleapis.com",
    "compute.googleapis.com",
    "connectors.googleapis.com",
    "container.googleapis.com",
    "containeranalysis.googleapis.com",
    "containerfilesystem.googleapis.com",
    "containerregistry.googleapis.com",
    "containerscanning.googleapis.com",
    "datacatalog.googleapis.com",
    "dataflow.googleapis.com",
    "dataform.googleapis.com",
    "dataplex.googleapis.com",
    "dataprocrm.googleapis.com",
    "datastore.googleapis.com",
    "deploymentmanager.googleapis.com",
    "dialogflow.googleapis.com",
    "directions-backend.googleapis.com",
    "discoveryengine.googleapis.com",
    "distance-matrix-backend.googleapis.com",
    "dns.googleapis.com",
    "docs.googleapis.com",
    "documentai.googleapis.com",
    "drive.googleapis.com",
    "elevation-backend.googleapis.com",
    "eventarc.googleapis.com",
    "fcm.googleapis.com",
    "fcmregistrations.googleapis.com",
    "firebase.googleapis.com",
    "firebaseappdistribution.googleapis.com",
    "firebasedynamiclinks.googleapis.com",
    "firebasehosting.googleapis.com",
    "firebaseinstallations.googleapis.com",
    "firebaseremoteconfig.googleapis.com",
    "firebaseremoteconfigrealtime.googleapis.com",
    "firebaserules.googleapis.com",
    "firestore.googleapis.com",
    "geminicloudassist.googleapis.com",
    "generativelanguage.googleapis.com",
    "geocoding-backend.googleapis.com",
    "geolocation.googleapis.com",
    "gkebackup.googleapis.com",
    "gmail.googleapis.com",
    "iam.googleapis.com",
    "iamcredentials.googleapis.com",
    "iap.googleapis.com",
    "identitytoolkit.googleapis.com",
    "integrations.googleapis.com",
    "logging.googleapis.com",
    "maps-android-backend.googleapis.com",
    "maps-backend.googleapis.com",
    "maps-embed-backend.googleapis.com",
    "maps-ios-backend.googleapis.com",
    "mobilecrashreporting.googleapis.com",
    "monitoring.googleapis.com",
    "networkconnectivity.googleapis.com",
    "networkmanagement.googleapis.com",
    "notebooks.googleapis.com",
    "orgpolicy.googleapis.com",
    "osconfig.googleapis.com",
    "oslogin.googleapis.com",
    "people.googleapis.com",
    "places-backend.googleapis.com",
    "pubsub.googleapis.com",
    "roads.googleapis.com",
    "run.googleapis.com",
    "runtimeconfig.googleapis.com",
    "script.googleapis.com",
    "secretmanager.googleapis.com",
    "securetoken.googleapis.com",
    "serviceconsumermanagement.googleapis.com",
    "servicemanagement.googleapis.com",
    "serviceusage.googleapis.com",
    "speech.googleapis.com",
    "sql-component.googleapis.com",
    "static-maps-backend.googleapis.com",
    "storage-api.googleapis.com",
    "storage-component.googleapis.com",
    "storage.googleapis.com",
    "street-view-image-backend.googleapis.com",
    "streetviewpublish.googleapis.com",
    "tasks.googleapis.com",
    "testing.googleapis.com",
    "texttospeech.googleapis.com",
    "timezone-backend.googleapis.com",
    "visionai.googleapis.com",
]


def enable_apis(apis: List[str], project: Optional[str]) -> None:
    """
    Enables a list of APIs for the specified Google Cloud project.

    Args:
        project (str): The ID of the Google Cloud project.
        apis (list): A list of APIs to enable.
    """
    all_apis_enabled = True
    for api in track(apis, description="Enabling APIs..."):
        console.log(f"Enabling API: {api}")

        command = [
            "gcloud",
            "services",
            "enable",
            api,
            f"--project={project}",
        ]

        if not run_gcloud_command(command):
            console.log(f"[red]Failed to enable API: {api}[/red]")
            all_apis_enabled = False

    if all_apis_enabled:
        console.log("[green]Successfully enabled all specified APIs.[/green]")
    else:
        console.log("[yellow]One or more APIs could not be enabled.[/yellow]")


@app.command()
def main(
    project_id: str = typer.Option(default=None, help="ID of the Google Cloud project (required, e.g., 'your-gcp-project-id')"),
    apis_to_enable: List[str] = typer.Option(default=DEFAULT_APIS_TO_ENABLE, help="APIs to enable"),
):
    enable_apis(apis=apis_to_enable, project=project_id)


if __name__ == "__main__":
    app()
