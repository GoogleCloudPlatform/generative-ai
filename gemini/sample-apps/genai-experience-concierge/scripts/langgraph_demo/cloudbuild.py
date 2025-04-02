# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Tools for running cloud build jobs."""

import subprocess


def build(
    project: str,
    service_account: str,
    image_url: str,
    source_dir: str,
) -> None:
    """
    Build and push a container image to Google Container Registry or Artifact Registry.

    This command uses `gcloud builds submit` to build a container image from the
    specified directory and push it to the given image URI.

    Args:
        project (str): Name of the project to run the build job in.
        service_account (str): Service account for build job.
        image_url (str): Image URI (including tag) to push the built image to.
        source_dir (str): Directory to call the build from.

    Raises:
        subprocess.CalledProcessError: If the `gcloud` command fails.
    """
    subprocess.run(
        [
            "gcloud",
            "builds",
            "submit",
            "--project",
            project,
            "--service-account",
            service_account,
            "--default-buckets-behavior",
            "REGIONAL_USER_OWNED_BUCKET",
            "-t",
            image_url,
            source_dir,
        ],
        check=True,
    )
