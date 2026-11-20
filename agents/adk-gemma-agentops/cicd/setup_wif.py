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

# ruff: noqa: INP001

"""Provisions Google Cloud APIs, least-privilege IAM, and GitHub Actions OIDC WIF.

Idempotent CLI utility for Stage 2 (`staging`) and Stage 3 (`prod`). Treats
`ALREADY_EXISTS` responses as clean no-ops and retries transient Google Cloud API/IAM
propagation errors on brand-new projects.
"""

import argparse
import shutil
import subprocess
import sys
import time
from collections.abc import Sequence

DEFAULT_RETRY_DELAYS: tuple[float, ...] = (5.0, 10.0, 15.0, 15.0, 15.0)

API_PROPAGATION_ERRORS: tuple[str, ...] = (
    "permission_denied",
    "iam_permission_denied",
    "service_disabled",
    "has not been used",
    "is disabled",
    "not_found",
    "not found",
    "unavailable",
)

IAM_PROPAGATION_ERRORS: tuple[str, ...] = (
    "does not exist",
    "not_found",
    "not found",
    "concurrent policy changes",
    "aborted",
    "unavailable",
)

REQUIRED_APIS: tuple[str, ...] = (
    "run.googleapis.com",
    "aiplatform.googleapis.com",
    "cloudbuild.googleapis.com",
    "artifactregistry.googleapis.com",
    "cloudtrace.googleapis.com",
    "iamcredentials.googleapis.com",
)

COMPUTE_SA_ROLES: tuple[str, ...] = (
    "roles/cloudbuild.builds.builder",
    "roles/artifactregistry.writer",
    "roles/storage.admin",
    "roles/aiplatform.user",
    "roles/cloudtrace.agent",
    "roles/logging.logWriter",
)

CD_SA_PROJECT_ROLES: tuple[str, ...] = (
    "roles/run.admin",
    "roles/cloudbuild.builds.editor",
    "roles/artifactregistry.admin",
    "roles/storage.admin",
    "roles/iam.serviceAccountUser",
    "roles/aiplatform.user",
)


def run_cli(  # noqa: PLR0913  # pylint: disable=too-many-arguments
    cmd: Sequence[str],
    *,
    dry_run: bool = False,
    ignore_already_exists: bool = False,
    ignore_not_found: bool = False,
    retry_on: Sequence[str] = (),
    retry_delays: Sequence[float] = DEFAULT_RETRY_DELAYS,
) -> str:
    """Runs a `gcloud` or `gh` subprocess with structured retry handling."""
    if dry_run:
        print(f"  [dry-run] {' '.join(cmd)}")
        return ""

    max_attempts = 1 + len(retry_delays) if retry_on else 1
    last_returncode = 0
    last_stderr = ""

    for attempt in range(1, max_attempts + 1):
        proc = subprocess.run(  # noqa: S603
            list(cmd), capture_output=True, text=True, check=False
        )
        if proc.returncode == 0:
            return proc.stdout.strip()

        last_returncode = proc.returncode
        last_stderr = (proc.stderr or "").strip()
        lower = last_stderr.lower()

        if ignore_already_exists and (
            "already_exists" in lower or "already exists" in lower
        ):
            return ""
        if ignore_not_found and (
            "not_found" in lower or "not found" in lower or "does not exist" in lower
        ):
            return ""

        if any(token in lower for token in retry_on) and attempt < max_attempts:
            delay = retry_delays[attempt - 1]
            print(
                f"  Waiting for Google Cloud propagation (retry {attempt}/"
                f"{max_attempts - 1} in {delay:g}s)...",
                flush=True,
            )
            time.sleep(delay)
            continue
        break

    raise RuntimeError(
        f"Command failed (exit {last_returncode}): {' '.join(cmd)}\n{last_stderr}"
    )


def _bind_project_role(
    project_id: str,
    member: str,
    role: str,
    *,
    dry_run: bool,
    ignore_not_found: bool = False,
) -> None:
    run_cli(
        [
            "gcloud",
            "projects",
            "add-iam-policy-binding",
            project_id,
            f"--member={member}",
            f"--role={role}",
            "--condition=None",
        ],
        dry_run=dry_run,
        ignore_not_found=ignore_not_found,
        retry_on=() if ignore_not_found else IAM_PROPAGATION_ERRORS,
    )


def _bind_sa_role(  # noqa: PLR0913  # pylint: disable=too-many-arguments
    service_account: str,
    project_id: str,
    member: str,
    role: str,
    *,
    dry_run: bool,
    ignore_not_found: bool = False,
) -> None:
    run_cli(
        [
            "gcloud",
            "iam",
            "service-accounts",
            "add-iam-policy-binding",
            service_account,
            f"--project={project_id}",
            f"--member={member}",
            f"--role={role}",
            "--condition=None",
        ],
        dry_run=dry_run,
        ignore_not_found=ignore_not_found,
        retry_on=() if ignore_not_found else IAM_PROPAGATION_ERRORS,
    )


def resolve_project_number(project_id: str, *, dry_run: bool) -> str:
    """Resolves the numeric Google Cloud project number."""
    if dry_run:
        return "123456789012"
    project_number = run_cli(
        [
            "gcloud",
            "projects",
            "describe",
            project_id,
            "--format=value(projectNumber)",
        ]
    )
    if not project_number:
        raise RuntimeError(f"Could not resolve projectNumber for '{project_id}'.")
    return project_number


def configure_wif_and_github_vars(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-locals
    *,
    env_tier: str,
    project_id: str,
    project_number: str,
    region: str,
    gha_sa: str,
    github_repo: str,
    dry_run: bool,
) -> None:
    """Creates the OIDC Workload Identity Pool/Provider and sets GitHub vars."""
    print(f"==> [4/4] Configuring Keyless WIF (OIDC) for {github_repo}...")
    run_cli(
        [
            "gcloud",
            "iam",
            "workload-identity-pools",
            "create",
            "github-pool",
            "--location=global",
            "--display-name=GitHub Actions Pool",
            f"--project={project_id}",
        ],
        dry_run=dry_run,
        ignore_already_exists=True,
        retry_on=API_PROPAGATION_ERRORS,
    )

    attr_mapping = (
        "google.subject=assertion.sub,"
        "attribute.actor=assertion.actor,"
        "attribute.repository=assertion.repository,"
        "attribute.repository_owner=assertion.repository_owner"
    )
    attr_condition = f"assertion.repository == '{github_repo}'"
    common_provider_args = [
        "github-provider",
        "--location=global",
        "--workload-identity-pool=github-pool",
        f"--attribute-mapping={attr_mapping}",
        f"--attribute-condition={attr_condition}",
        f"--project={project_id}",
    ]
    try:
        run_cli(
            [
                "gcloud",
                "iam",
                "workload-identity-pools",
                "providers",
                "create-oidc",
                *common_provider_args,
                "--display-name=GitHub Actions Provider",
                "--issuer-uri=https://token.actions.githubusercontent.com",
            ],
            dry_run=dry_run,
            retry_on=IAM_PROPAGATION_ERRORS,
        )
    except RuntimeError as err:
        msg = str(err).lower()
        if "already exists" not in msg and "already_exists" not in msg:
            raise
        run_cli(
            [
                "gcloud",
                "iam",
                "workload-identity-pools",
                "providers",
                "update-oidc",
                *common_provider_args,
            ],
            dry_run=dry_run,
            retry_on=IAM_PROPAGATION_ERRORS,
        )

    wif_member = (
        f"principalSet://iam.googleapis.com/projects/{project_number}/"
        "locations/global/workloadIdentityPools/github-pool/"
        f"attribute.repository/{github_repo}"
    )
    for role in (
        "roles/iam.workloadIdentityUser",
        "roles/iam.serviceAccountTokenCreator",
    ):
        _bind_sa_role(gha_sa, project_id, wif_member, role, dry_run=dry_run)

    wif_provider = (
        f"projects/{project_number}/locations/global/"
        "workloadIdentityPools/github-pool/providers/github-provider"
    )
    gh_bin = shutil.which("gh")
    gh_ready = dry_run or bool(
        gh_bin
        and subprocess.run(  # noqa: S603
            [gh_bin, "auth", "status"], capture_output=True, check=False
        ).returncode
        == 0
    )
    if not gh_ready:
        print("Note: Authenticate gh CLI ('gh auth login') or set variables manually:")
        print(f"  WIF Provider   : {wif_provider}")
        print(f"  Service Account: {gha_sa}")
        return

    print(f"==> Registering GitHub Actions variables on {github_repo}...")
    gh_vars = (
        {
            "GCP_PROJECT_ID": project_id,
            "GCP_REGION": region,
            "WIF_PROVIDER_STAGING": wif_provider,
            "WIF_SA_STAGING": gha_sa,
        }
        if env_tier == "staging"
        else {
            "GCP_PROD_PROJECT_ID": project_id,
            "GCP_REGION": region,
            "WIF_PROVIDER_PROD": wif_provider,
            "WIF_SA_PROD": gha_sa,
        }
    )
    for name, value in gh_vars.items():
        run_cli(
            ["gh", "variable", "set", name, "--repo", github_repo, "--body", value],
            dry_run=dry_run,
        )


def provision_gcp_and_wif(args: argparse.Namespace) -> None:
    """Enables Google Cloud APIs, creates Artifact Registry, binds IAM & WIF."""
    project_id, region, env_tier, dry_run = (
        args.project,
        args.region,
        args.env,
        args.dry_run,
    )
    project_number = resolve_project_number(project_id, dry_run=dry_run)
    gha_sa = f"github-actions-cd@{project_id}.iam.gserviceaccount.com"
    compute_sa = f"{project_number}-compute@developer.gserviceaccount.com"
    cloudbuild_sa = f"{project_number}@cloudbuild.gserviceaccount.com"

    print(
        f"==> [1/4] Enabling Google Cloud APIs & Artifact Registry on {project_id}..."
    )
    run_cli(
        ["gcloud", "services", "enable", *REQUIRED_APIS, f"--project={project_id}"],
        dry_run=dry_run,
    )
    run_cli(
        [
            "gcloud",
            "iam",
            "service-accounts",
            "create",
            "github-actions-cd",
            f"--display-name=GitHub Actions {env_tier} CD",
            f"--project={project_id}",
        ],
        dry_run=dry_run,
        ignore_already_exists=True,
        retry_on=API_PROPAGATION_ERRORS,
    )
    run_cli(
        [
            "gcloud",
            "artifacts",
            "repositories",
            "create",
            "cloud-run-source-deploy",
            "--repository-format=docker",
            f"--location={region}",
            "--description=Cloud Run source deployment container repository",
            f"--project={project_id}",
        ],
        dry_run=dry_run,
        ignore_already_exists=True,
        retry_on=API_PROPAGATION_ERRORS,
    )

    print("==> [2/4] Granting Cloud Run runtime & Cloud Build IAM bindings...")
    for role in COMPUTE_SA_ROLES:
        _bind_project_role(
            project_id, f"serviceAccount:{compute_sa}", role, dry_run=dry_run
        )
    _bind_project_role(
        project_id,
        f"serviceAccount:{cloudbuild_sa}",
        "roles/run.admin",
        dry_run=dry_run,
        ignore_not_found=True,
    )
    _bind_sa_role(
        compute_sa,
        project_id,
        f"serviceAccount:{cloudbuild_sa}",
        "roles/iam.serviceAccountUser",
        dry_run=dry_run,
        ignore_not_found=True,
    )

    print(f"==> [3/4] Granting GitHub Actions CD service account roles ({gha_sa})...")
    for role in CD_SA_PROJECT_ROLES:
        _bind_project_role(
            project_id, f"serviceAccount:{gha_sa}", role, dry_run=dry_run
        )
    _bind_sa_role(
        compute_sa,
        project_id,
        f"serviceAccount:{gha_sa}",
        "roles/iam.serviceAccountUser",
        dry_run=dry_run,
    )
    _bind_sa_role(
        gha_sa,
        project_id,
        f"serviceAccount:{gha_sa}",
        "roles/iam.serviceAccountTokenCreator",
        dry_run=dry_run,
    )

    if args.repo:
        configure_wif_and_github_vars(
            env_tier=env_tier,
            project_id=project_id,
            project_number=project_number,
            region=region,
            gha_sa=gha_sa,
            github_repo=args.repo,
            dry_run=dry_run,
        )
    else:
        print(
            "==> [4/4] Skipped GitHub WIF (pass --repo OWNER/REPO to configure OIDC)."
        )
    print(f"Setup complete for {env_tier} ({project_id}).")


def build_parser() -> argparse.ArgumentParser:
    """Builds the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Provision Google Cloud APIs, least-privilege IAM, and GitHub Actions"
            " OIDC WIF."
        )
    )
    parser.add_argument("--env", choices=["staging", "prod"], default="staging")
    parser.add_argument(
        "--project", required=True, help="Target Google Cloud project ID."
    )
    parser.add_argument("--region", default="us-west1", help="Google Cloud region.")
    parser.add_argument("--repo", default="", help="GitHub repo (OWNER/REPO).")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print gcloud and gh commands without executing them.",
    )
    return parser


def main() -> None:
    """CLI entry point."""
    args = build_parser().parse_args()
    try:
        provision_gcp_and_wif(args)
    except RuntimeError as err:
        print(f"ERROR: {err}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
