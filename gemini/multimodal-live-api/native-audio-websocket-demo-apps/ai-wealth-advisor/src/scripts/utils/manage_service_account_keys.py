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


"""
Run this first for a project created in Argolis, which by defualt, disables service account key creation:
    gcloud org-policies delete iam.disaeServiceAccountKeyCreation --organization=307923223344
"""

import typer

from common import run_gcloud_command
from rich.console import Console

# # Add src directory to path to allow for absolute imports from the project root.
# sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# from backend.settings import get_application_settings

# backend.app_settings = get_application_settings()
app = typer.Typer()
console = Console()


# def create_key(project_id: str, account: str) -> types.ServiceAccountKey:
#     """
#     Creates a key for a service account.

#     project_id: ID or number of the Google Cloud project you want to use.
#     account: ID or email which is unique identifier of the service account.
#     """
#     iam_admin_client = iam_admin_v1.IAMClient()
#     request = types.CreateServiceAccountKeyRequest()
#     request.name = f"projects/{project_id}/serviceAccounts/{account}"

#     key = iam_admin_client.create_service_account_key(request=request)
#     console.log(f"Successfully created key: {key.name}\n\n")
#     console.log("Key JSON (save this, it cannot be retrieved later):\n\n")
#     console.log(f"Decoded key:\n {key.private_key_data.decode('utf-8')}")
#     json_key_data = json.loads(key.private_key_data)
#     console.log(f"JSON loaded key:\n {json_key_data}\n\n")
#     console.log(f"JSON loaded key ID:\n {json_key_data['private_key_id']}")
#     return key


@app.command()
def create(
    project_id: str = typer.Option("my-project-id", "--project-id", "-p", help="ID of the GCP Project"),
    account_id: str = typer.Option("my-srvc-acct-id", "--account-id", "-a", help="ID of the service account"),
    output_file: str = typer.Option(
        "service_account_key.json", "--output-file", "-o", help="Path to save the key file"
    ),
):
    """Creates a service account key."""
    service_account_email = f"{account_id}@{project_id}.iam.gserviceaccount.com"
    console.log(f"Creating a new key for service account '{service_account_email}' in project '{project_id}'...")
    # key = create_key(project_id, service_account_email)
    # if key:
    #     console.log(f"[green]Key created successfully and saved to '{output_file}'.[/green]")
    # else:
    #     console.log(f"[red]Failed to create key for {service_account_email}[/red]")
    command = [
        "gcloud",
        "iam",
        "service-accounts",
        "keys",
        "create",
        output_file,
        f"--iam-account={service_account_email}",
        f"--project={project_id}",
    ]
    if run_gcloud_command(command):
        console.log(f"[green]Key created successfully and saved to '{output_file}'.[/green]")
    else:
        console.log(f"[red]Failed to create key for {service_account_email}[/red]")


if __name__ == "__main__":
    app()


# def create_key(project_id: str, account: str) -> types.ServiceAccountKey:
#     """
#     Creates a key for a service account.

#     project_id: ID or number of the Google Cloud project you want to use.
#     account: ID or email which is unique identifier of the service account.
#     """
#     logging.info(f"Creating a new key for service account '{account}' in project '{project_id}'...")
#     iam_admin_client = iam_admin_v1.IAMClient()
#     request = types.CreateServiceAccountKeyRequest()
#     request.name = f"projects/{project_id}/serviceAccounts/{account}"

#     key = iam_admin_client.create_service_account_key(request=request)
#     logging.info(f"Successfully created key: {key.name}")
#     logging.info("Key JSON (save this, it cannot be retrieved later):")
#     logging.info(key.private_key_data.decode("utf-8"))
#     json_key_data = json.loads(key.private_key_data)
#     logging.info(f"JSON loaded key: {json_key_data}")
#     logging.info(f"JSON loaded key ID: {json_key_data['private_key_id']}")
#     return key


# def delete_key(project_id: str, account: str, key_id: str) -> None:
#     """Deletes a key for a service account.

#     project_id: ID or number of the Google Cloud project you want to use.
#     account: ID or email which is unique identifier of the service account.
#     key_id: unique ID of the key.
#     """
#     logging.info(f"Deleting key '{key_id}' for service account '{account}' in project '{project_id}'...")
#     iam_admin_client = iam_admin_v1.IAMClient()
#     request = types.DeleteServiceAccountKeyRequest()
#     request.name = f"projects/{project_id}/serviceAccounts/{account}/keys/{key_id}"

#     iam_admin_client.delete_service_account_key(request=request)
#     logging.info(f"Successfully deleted key: {key_id}")


# def list_keys(project_id: str, account: str) -> List[iam_admin_v1.ServiceAccountKey]:
#     """Lists keys for a service account.

#     project_id: ID or number of the Google Cloud project you want to use.
#     account: ID or email which is unique identifier of the service account.
#     """
#     logging.info(f"Listing keys for service account '{account}' in project '{project_id}'...")
#     iam_admin_client = iam_admin_v1.IAMClient()
#     request = types.ListServiceAccountKeysRequest()
#     request.name = f"projects/{project_id}/serviceAccounts/{account}"

#     response = iam_admin_client.list_service_account_keys(request=request)
#     keys = response.keys
#     if keys:
#         logging.info(f"Found {len(list(keys))} key(s):")
#         for key in keys:
#             print(f"  - {key.name}")
#     else:
#         logging.info("No keys found for this service account.")
#     return keys  # type: ignore


# def get_service_account_key(project_id: str, account: str, key_id: str) -> None:
#     """
#     Gets a service account key's metadata and returns it as a JSON object.

#     project_id: ID or number of the Google Cloud project you want to use.
#     account: ID or email which is unique identifier of the service account.
#     key_id: unique ID of the key.
#     """
#     logging.info(f"Getting key '{key_id}' for service account '{account}' in project '{project_id}'...")
#     iam_admin_client = iam_admin_v1.IAMClient()

#     # Get the service account to retrieve the client_id (unique_id) and client_email
#     sa_request = types.GetServiceAccountRequest()
#     sa_request.name = f"projects/{project_id}/serviceAccounts/{account}"
#     service_account = iam_admin_client.get_service_account(request=sa_request)

#     # Get the service account key
#     key_request = types.GetServiceAccountKeyRequest()
#     key_request.name = f"projects/{project_id}/serviceAccounts/{account}/keys/{key_id}"
#     key = iam_admin_client.get_service_account_key(request=key_request)

#     key_json = {
#         "type": "service_account",
#         "project_id": project_id,
#         "private_key_id": key_id,
#         "private_key": "Private key data is not available for existing keys.",
#         "client_email": service_account.email,
#         "client_id": service_account.unique_id,
#         "auth_uri": "https://accounts.google.com/o/oauth2/auth",
#         "token_uri": "https://oauth2.googleapis.com/token",
#         "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
#         "client_x509_cert_url": f"https://www.googleapis.com/robot/v1/metadata/x509/{service_account.email.replace('@', '%40')}",
#         "universe_domain": "googleapis.com",
#     }

#     logging.info(f"Successfully retrieved key: {key.name}")
#     print(json.dumps(key_json, indent=2))


# def main():
#     """
#     Main function to parse arguments and orchestrate service account key management.
#     """
#     parser = argparse.ArgumentParser(
#         description="Manage GCP Service Account Keys.",
#         formatter_class=argparse.RawTextHelpFormatter,
#     )
#     subparsers = parser.add_subparsers(dest="command", required=True)

#     ##################
#     # Create command #
#     ##################
#     parser_create = subparsers.add_parser("create", help="Create a new service account key.")
#     parser_create.add_argument(
#         "--project_id",
#         default=app_settings.vertex_ai.google_cloud_project,
#         required=True,
#         help="The ID of your Google Cloud project.",
#     )
#     parser_create.add_argument(
#         "--account",
#         default=app_settings.service_account_email,
#         required=True,
#         help="The ID or email of the service account.",
#     )

#     ##################
#     # Delete command #
#     ##################
#     parser_delete = subparsers.add_parser("delete", help="Delete a service account key.")
#     parser_delete.add_argument(
#         "--project_id",
#         default=app_settings.vertex_ai.google_cloud_project,
#         required=True,
#         help="The ID of your Google Cloud project.",
#     )
#     parser_delete.add_argument(
#         "--account",
#         default=app_settings.service_account_email,
#         required=True,
#         help="The ID or email of the service account.",
#     )
#     parser_delete.add_argument("--key_id", required=True, help="The ID of the key to delete.")

#     ################
#     # List command #
#     ################
#     parser_list = subparsers.add_parser("list", help="List service account keys.")
#     parser_list.add_argument(
#         "--project_id",
#         default=app_settings.vertex_ai.google_cloud_project,
#         required=True,
#         help="The ID of your Google Cloud project.",
#     )
#     parser_list.add_argument(
#         "--account",
#         default=app_settings.service_account_email,
#         required=True,
#         help="The ID or email of the service account.",
#     )

#     ###############
#     # Get command #
#     ###############
#     parser_get = subparsers.add_parser("get", help="Get a service account key.")
#     parser_get.add_argument(
#         "--project_id",
#         default=app_settings.vertex_ai.google_cloud_project,
#         required=True,
#         help="The ID of your Google Cloud project.",
#     )
#     parser_get.add_argument(
#         "--account",
#         default=app_settings.service_account_email,
#         required=True,
#         help="The ID or email of the service account.",
#     )
#     parser_get.add_argument("--key_id", required=True, help="The ID of the key to get.")

#     args = parser.parse_args()

#     try:
#         if args.command == "create":
#             create_key(args.project_id, args.account)
#         elif args.command == "delete":
#             delete_key(args.project_id, args.account, args.key_id)
#         elif args.command == "list":
#             list_keys(args.project_id, args.account)
#         elif args.command == "get":
#             get_service_account_key(args.project_id, args.account, args.key_id)
#         logging.info("Script finished.")
#     except Exception as e:
#         logging.error(f"An error occurred: {e}")
#         sys.exit(1)


# if __name__ == "__main__":
#     main()
