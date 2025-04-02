# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Tools for managing the demo backend service."""

# pylint: disable=too-many-arguments,too-many-positional-arguments

import json
import subprocess
import tempfile

from scripts.langgraph_demo import defaults


def deploy(
    service: str,
    project: str,
    region: str,
    network: str,
    subnetwork: str,
    service_account: str,
    image_url: str,
    alloydb_secret_name: str,
    cymbal_dataset_location: str,
    cymbal_products_table_uri: str,
    cymbal_stores_table_uri: str,
    cymbal_inventory_table_uri: str,
    cymbal_embedding_model_uri: str,
) -> None:
    """
    Deploy a new Cloud Run revision.

    This command deploys a new revision of a Cloud Run service using the provided
    configuration. It generates a service YAML file from a template and then uses
    `gcloud run services replace` to deploy the service.

    Args:
        service (str): Name of the Cloud Run service to deploy.
        project (str): Name of the project for the target deployed service.
        region (str): Region to deploy the service.
        network (str): VPC network to deploy the service in.
        subnetwork (str): VPC subnetwork to deploy the service in.
        service_account (str): Service account to attach to the deployed service.
        image_url (str): Server container image URL to deploy.
        alloydb_secret_name (str): Secret name containing the AlloyDB connection URL.
            to attach to the runtime.
        cymbal_dataset_location (str): Location of the Cymbal Retail dataset.
        cymbal_products_table_uri (str): BigQuery URI for the Cymbal Retail products
            dataset (with embeddings).
        cymbal_stores_table_uri (str): BigQuery URI for the Cymbal Retail stores
            dataset.
        cymbal_inventory_table_uri (str): BigQuery URI for the Cymbal Retail inventory
            dataset.
        cymbal_embedding_model_uri (str): BigQuery URI for the Cymbal Retail embedding
            model.

    Raises:
        subprocess.CalledProcessError: If the `gcloud` command fails.
    """

    with defaults.SERVICE_YAML_TEMPLATE_PATH.open() as f:
        service_yaml_str = f.read().format(
            service=service,
            project=project,
            region=region,
            network=network,
            subnetwork=subnetwork,
            service_account=service_account,
            image_url=image_url,
            alloydb_secret_name=alloydb_secret_name,
            cymbal_dataset_location=cymbal_dataset_location,
            cymbal_products_table_uri=cymbal_products_table_uri,
            cymbal_stores_table_uri=cymbal_stores_table_uri,
            cymbal_inventory_table_uri=cymbal_inventory_table_uri,
            cymbal_embedding_model_uri=cymbal_embedding_model_uri,
        )

    with tempfile.NamedTemporaryFile("w") as f:
        f.write(service_yaml_str)
        f.flush()

        subprocess.run(
            [
                "gcloud",
                "run",
                "services",
                "replace",
                "--project",
                project,
                "--region",
                region,
                f.name,
            ],
            check=True,
        )


def describe(project: str, region: str, service: str) -> dict:
    """
    Describe a Cloud Run service and print its details in JSON format.

    This command uses `gcloud run services describe` to retrieve information about
    a Cloud Run service and prints the output as a formatted JSON string.

    Args:
        project (str): Name of the project to run the build job in.
        region (str): Region of the deployed service.
        service (str): Name of the Cloud Run service.

    Returns:
        dict: A dictionary containing the service description.

    Raises:
        subprocess.CalledProcessError: If the `gcloud` command fails.
    """
    service_description_process = subprocess.run(
        [
            "gcloud",
            "run",
            "services",
            "describe",
            "--project",
            project,
            "--region",
            region,
            service,
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
    )

    service_description_dict = dict(json.loads(service_description_process.stdout))

    return service_description_dict


def add_invoker(service: str, project: str, region: str, invoker: str) -> None:
    """
    Add the given member as a Cloud Run service invoker.

    This command grants the specified member principal the 'roles/run.invoker'
    role on the given Cloud Run service, allowing them to invoke the service.

    Args:
        service (str): Name of the Cloud Run service to deploy.
        project (str): Name of the project for the target deployed service.
        region (str): Region to deploy the service.
        invoker (str): A member principal to grant invoker permissions.

    Raises:
        subprocess.CalledProcessError: If the `gcloud` command fails.
    """

    subprocess.run(
        [
            "gcloud",
            "run",
            "services",
            "add-iam-policy-binding",
            "--project",
            project,
            "--region",
            region,
            service,
            "--member",
            invoker,
            "--role",
            "roles/run.invoker",
        ],
        check=True,
    )
