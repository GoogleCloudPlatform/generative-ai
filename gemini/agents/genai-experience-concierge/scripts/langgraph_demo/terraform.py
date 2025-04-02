# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Tools for provisioning infrastructure through terraform."""

# pylint: disable=too-many-arguments,too-many-positional-arguments

import json
import subprocess

from scripts.langgraph_demo import defaults


def init(
    state_bucket: str,
    state_bucket_prefix: str | None = None,
    terraform_dir: str = str(defaults.TERRAFORM_DIR),
) -> None:
    """
    Initialize a Terraform working directory.

    This command initializes a Terraform working directory, configuring the backend
    to use a Google Cloud Storage (GCS) bucket for storing Terraform state.

    Args:
        terraform_dir (str): Path to the Terraform module directory.
        state_bucket (str): GCS bucket name for storing Terraform state.
        state_bucket_prefix (str, optional): Prefix to use within the GCS bucket. Defaults to None.

    Raises:
        subprocess.CalledProcessError: If the Terraform initialization fails.
    """
    init_args = [
        "terraform",
        f"-chdir={terraform_dir}",
        "init",
        "-reconfigure",
        f"-backend-config=bucket={state_bucket}",
    ]

    if state_bucket_prefix is not None:
        init_args.append(
            f"-backend-config=prefix={state_bucket_prefix}",
        )

    subprocess.run(init_args, check=True)


def apply(
    seed_project: str,
    project_id: str,
    billing_account: str,
    support_email: str,
    demo_users: tuple[str],
    org_id: str | None = None,
    folder_id: str | None = None,
    region: str = defaults.REGION,
    random_project_suffix: bool = False,
    terraform_dir: str = str(defaults.TERRAFORM_DIR),
    auto_approve: bool = False,
) -> None:
    """
    Apply Terraform configurations to create Google Cloud resources.

    This command applies the Terraform configurations defined in the specified
    directory to create or modify Google Cloud resources for the Concierge demo.

    Args:
        seed_project (str): Seed project ID used when creating the demo project.
        project_id (str): Target project ID to create for the demo.
        billing_account (str): Google Cloud billing account ID.
        support_email (str): Support email for the demo OAuth screen.
        demo_users (tuple[str]): Members to grant access to the demo.
        org_id (str, optional): Google Cloud organization ID. Defaults to None.
        folder_id (str, optional): Google Cloud folder ID. Defaults to None.
        region (str): Default region to deploy resources in. Defaults to us-central1.
        random_project_suffix (bool): Add a random suffix to the project ID. Defaults to False.
        terraform_dir (str): Path to the Terraform module directory.
        auto_approve (bool, optional): Auto-approve the Terraform apply. Defaults to False.

    Raises:
        subprocess.CalledProcessError: If the Terraform apply command fails.
    """

    random_project_suffix_str = str(random_project_suffix).lower()
    app_engine_users_str = json.dumps(list(demo_users))

    apply_args = [
        "terraform",
        f"-chdir={terraform_dir}",
        "apply",
        f"-var=seed_project_id={seed_project}",
        f"-var=project_id={project_id}",
        f"-var=random_project_suffix={random_project_suffix_str}",
        f"-var=billing_account={billing_account}",
        f"-var=iap_support_email={support_email}",
        f"-var=app_engine_users={app_engine_users_str}",
        f"-var=region={region}",
    ]

    if org_id is not None:
        apply_args.append(f"-var=org_id={org_id}")

    if folder_id is not None:
        apply_args.append(f"-var=folder_id={folder_id}")

    if auto_approve:
        apply_args.append("-auto-approve")

    subprocess.run(apply_args, check=True)


def outputs(terraform_dir: str = str(defaults.TERRAFORM_DIR)) -> dict:
    """
    Retrieve Terraform outputs as a dictionary.

    This command retrieves the outputs defined in the Terraform configuration
    and returns them as a Python dictionary.

    Args:
        terraform_dir (str): Path to the Terraform module directory.

    Returns:
        dict: A dictionary containing the Terraform outputs.

    Raises:
        subprocess.CalledProcessError: If the Terraform show command fails.
        AssertionError: If the Terraform outputs are not in dictionary format.
    """

    terraform_state_process = subprocess.run(
        ["terraform", f"-chdir={terraform_dir}", "show", "--json"],
        capture_output=True,
        check=True,
    )

    terraform_state = json.loads(terraform_state_process.stdout)
    tf_outputs = dict(terraform_state["values"]["outputs"])

    return tf_outputs
