# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Tools for managing the demo frontend application."""

# pylint: disable=too-many-arguments,too-many-positional-arguments

import subprocess
import tempfile

from scripts.langgraph_demo import defaults


def deploy(
    project: str,
    network: str,
    subnetwork: str,
    service_account: str,
    concierge_host: str,
    frontend_image_url: str,
) -> None:
    """
    Deploy a new App Engine version for the Concierge frontend demo.

    This command deploys a new version of the Concierge frontend demo to App Engine.
    It uses a template `app.yaml` file, populates it with provided configuration,
    and then uses `gcloud app deploy` to deploy the application.

    Args:
        project (str): Name of the Google Cloud project to deploy the app to.
        network (str): VPC network to deploy the app in.
        subnetwork (str): VPC subnetwork to deploy the app in.
        service_account (str): Service account to attach to the deployed app.
        concierge_host (str): The host URL for the concierge backend server.
        frontend_image_url (str): Frontend container image URL.

    Raises:
        subprocess.CalledProcessError: If the `gcloud app deploy` command fails.
    """

    with defaults.APP_YAML_TEMPLATE_PATH.open() as f:
        app_yaml_str = f.read().format(
            network=network,
            subnetwork=subnetwork,
            service_account=service_account,
            concierge_host=concierge_host,
        )

    with tempfile.NamedTemporaryFile("w") as f:
        f.write(app_yaml_str)
        f.flush()

        subprocess.run(
            [
                "gcloud",
                "app",
                "deploy",
                "--project",
                project,
                "--service-account",
                service_account,
                "--image-url",
                frontend_image_url,
                "--appyaml",
                f.name,
            ],
            check=True,
        )
