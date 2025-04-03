# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Tools for deploying the end-to-end Concierge demo."""

# pylint: disable=too-many-arguments,too-many-positional-arguments

from typing import Any
import uuid

import click
from scripts.langgraph_demo import (
    backend,
    cloudbuild,
    dataset,
    defaults,
    frontend,
    terraform,
)
import yaml


@click.option(
    "--project-id",
    required=True,
    help="Target project ID to create the dataset in.",
)
@click.option(
    "--location",
    required=False,
    help="Multi-region location for the BigQuery dataset (US, EU, etc).",
    default="US",
)
def create_dataset(project_id: str, location: str = "US") -> dataset.GeneratedDataset:
    """Create a mock Cymbal Retail dataset."""

    return dataset.create(project=project_id, location=location)


# pylint: disable=too-many-locals
@click.option(
    "--seed-project",
    required=True,
    help="Seed project ID used when creating the demo project.",
)
@click.option(
    "--project-id",
    required=True,
    help="Target project ID to create for the demo.",
)
@click.option(
    "--billing-account",
    required=True,
    help="GCP billing account ID to use for project creation.",
)
@click.option(
    "--support-email",
    required=True,
    help="Support email to display on the demo OAuth screen.",
)
@click.option(
    "--demo-users",
    required=True,
    help=(
        "Member(s) to grant access to the hosted Gen AI Concierge demo."
        " Each entry should include the kind of member (e.g. user:*, group:*, etc)."
    ),
    multiple=True,
)
@click.option(
    "--state-bucket",
    required=True,
    help="GCS state backend bucket for managing terraform state.",
)
@click.option(
    "--region",
    required=False,
    help="Default region for creating resources (default=us-central1).",
    default="us-central1",
)
@click.option(
    "--random-project-suffix/--no-random-project-suffix",
    required=False,
    help="Indicate if a random suffix should be added to the project ID (default=False)",
    default=False,
)
@click.option(
    "--state-bucket-prefix",
    required=False,
    help="Prefix to insert to GCS path when storing terraform state.",
    default=None,
)
@click.option(
    "--org-id",
    required=False,
    help="GCP organization to create the project in.",
    default=None,
)
@click.option(
    "--folder-id",
    required=False,
    help="GCP folder to create the project in.",
    default=None,
)
@click.option(
    "--auto-approve/--no-auto-approve",
    required=False,
    help="Indicate if the terraform should auto-apply changes (Default=False).",
    default=False,
)
def deploy(
    seed_project: str,
    project_id: str,
    region: str,
    random_project_suffix: bool,
    billing_account: str,
    support_email: str,
    demo_users: tuple[str],
    state_bucket: str,
    state_bucket_prefix: str | None = None,
    org_id: str | None = None,
    folder_id: str | None = None,
    auto_approve: bool = False,
) -> dict[str, Any]:
    """Deploy the end-to-end Concierge demo."""

    # only use default source dirs. Maybe enable user-provided in future?
    terraform_dir = str(defaults.TERRAFORM_DIR)
    backend_dir = str(defaults.BACKEND_DIR)
    frontend_dir = str(defaults.FRONTEND_DIR)
    cymbal_product_path = str(defaults.PRODUCT_GCS_DATASET_PATH)
    cymbal_store_path = str(defaults.STORE_GCS_DATASET_PATH)
    cymbal_inventory_path = str(defaults.INVENTORY_GCS_DATASET_PATH)

    log_section("Initializing terraform module...")

    terraform.init(
        terraform_dir=terraform_dir,
        state_bucket=state_bucket,
        state_bucket_prefix=state_bucket_prefix,
    )

    log_section("Applying terraform...")

    terraform.apply(
        terraform_dir=terraform_dir,
        seed_project=seed_project,
        project_id=project_id,
        region=region,
        random_project_suffix=random_project_suffix,
        billing_account=billing_account,
        support_email=support_email,
        demo_users=demo_users,
        org_id=org_id,
        folder_id=folder_id,
        auto_approve=auto_approve,
    )

    tf_outputs = terraform.outputs(terraform_dir=terraform_dir)
    real_project_id = tf_outputs["project-id"]["value"]
    cymbal_dataset_id = tf_outputs["cymbal-retail-dataset-id"]["value"]
    cymbal_dataset_location = tf_outputs["cymbal-retail-dataset-location"]["value"]
    cymbal_connection_id = tf_outputs["cymbal-retail-connection-id"]["value"]
    build_service_account = tf_outputs["cloud-build-service-account"]["value"]
    build_service_account_id = (
        f"projects/{project_id}/serviceAccounts/{build_service_account}"
    )
    backend_service_account = tf_outputs["cloud-run-service-account"]["value"]
    artifact_registry_repository = tf_outputs["artifact-registry-repo"]["value"]
    artifact_registry_location = tf_outputs["artifact-registry-location"]["value"]
    network_id = str(tf_outputs["vpc-id"]["value"])
    network_name = network_id.rsplit("/", maxsplit=1)[-1]
    subnetwork_id = str(tf_outputs["subnet-id"]["value"])
    subnetwork_name = subnetwork_id.rsplit("/", maxsplit=1)[-1]
    alloydb_secret_name = tf_outputs["concierge-alloydb-connection-secret-name"][
        "value"
    ]
    frontend_service_account = tf_outputs["app-engine-service-account"]["value"]

    log_section("Creating mock Cymbal Retail dataset...")

    generated_dataset = dataset.create(
        project=project_id,
        location=cymbal_dataset_location,
        dataset_id=cymbal_dataset_id,
        connection_id=cymbal_connection_id,
        product_path=cymbal_product_path,
        store_path=cymbal_store_path,
        inventory_path=cymbal_inventory_path,
    )

    tag_id = uuid.uuid1()

    log_section("Building backend agent server...")

    backend_image_url = (
        f"{artifact_registry_location}-docker.pkg.dev"
        f"/{project_id}/{artifact_registry_repository}/"
        f"backend:{tag_id.hex}"
    )
    cloudbuild.build(
        project=project_id,
        service_account=build_service_account_id,
        image_url=backend_image_url,
        source_dir=backend_dir,
    )

    backend_service = "concierge"

    log_section(f"Deploying backend agent server ({backend_service})...")

    backend.deploy(
        service=backend_service,
        project=project_id,
        region=region,
        network=network_id,
        subnetwork=subnetwork_id,
        service_account=backend_service_account,
        image_url=backend_image_url,
        alloydb_secret_name=alloydb_secret_name,
        cymbal_dataset_location=cymbal_dataset_location,
        cymbal_products_table_uri=generated_dataset["products_table_uri"],
        cymbal_stores_table_uri=generated_dataset["stores_table_uri"],
        cymbal_inventory_table_uri=generated_dataset["inventory_table_uri"],
        cymbal_embedding_model_uri=generated_dataset["embedding_model_uri"],
    )

    backend_service_description = backend.describe(
        project=project_id,
        region=region,
        service=backend_service,
    )
    backend_host = backend_service_description["status"]["url"]

    log_section("Adding frontend SA as an invoker of the backend service...")

    frontend_sa_member = f"serviceAccount:{frontend_service_account}"
    backend.add_invoker(
        service=backend_service,
        project=project_id,
        region=region,
        invoker=frontend_sa_member,
    )

    log_section("Building frontend demo server...")

    frontend_image_url = (
        f"{artifact_registry_location}-docker.pkg.dev"
        f"/{project_id}/{artifact_registry_repository}/"
        f"frontend:{tag_id.hex}"
    )

    cloudbuild.build(
        project=project_id,
        service_account=build_service_account_id,
        image_url=frontend_image_url,
        source_dir=frontend_dir,
    )

    log_section("Deploying frontend demo...")

    frontend.deploy(
        project=project_id,
        network=network_name,
        subnetwork=subnetwork_name,
        service_account=frontend_service_account,
        concierge_host=backend_host,
        frontend_image_url=frontend_image_url,
    )

    outputs = {
        "project_id": real_project_id,
        "region": region,
        "network": network_name,
        "subnetwork": subnetwork_name,
        "terraform": {
            "state_bucket": state_bucket,
            "state_bucket_prefix": state_bucket_prefix,
        },
        "cymbal_bigquery_dataset": generated_dataset,
        "build_service_account": build_service_account,
        "backend": {
            "service": backend_service,
            "host": backend_host,
            "image_url": backend_image_url,
            "service_account": backend_service_account,
        },
        "frontend": {
            "service": "default",
            "host": f"{project_id}.uc.r.appspot.com",
            "image_url": frontend_image_url,
            "service_account": frontend_service_account,
        },
    }

    output_str = yaml.safe_dump(outputs)
    click.echo(f"Displaying the key generated resources:\n\n{output_str}")

    log_section("🚀 End-to-end deployment is complete! 🚀")

    return outputs


# pylint: enable=too-many-locals


def log_section(message: str) -> None:
    """Log section with spacing and bold styling."""

    click.echo("\n\n" + click.style(message, bold=True) + "\n\n")
