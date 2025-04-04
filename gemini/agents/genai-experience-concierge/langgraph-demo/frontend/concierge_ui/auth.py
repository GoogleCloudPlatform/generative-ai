# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Auth utilities for authenticating to Google Cloud services."""

from concierge_ui import remote_settings as settings
from google import auth
from google.auth import compute_engine, impersonated_credentials
from google.auth.transport import requests


def get_auth_headers(agent_config: settings.RemoteAgentConfig) -> dict[str, str]:
    """
    Retrieves authentication headers for making requests to a remote agent.
    """
    if not agent_config.fetch_id_token:
        return {}

    target_audience = f"{agent_config.base_url.scheme}://{agent_config.base_url.host}"

    if agent_config.target_principal:
        token = fetch_impersonated_id_token_credentials(
            target_audience=target_audience,
            target_principal=agent_config.target_principal,
        ).token
    else:
        token = fetch_gce_id_token_credentials(target_audience=target_audience).token

    headers = {"Authorization": f"Bearer {token}"}

    return headers


def fetch_gce_id_token_credentials(
    target_audience: str | None = None,
) -> compute_engine.IDTokenCredentials:
    """
    Fetches ID token credentials from the Google Compute Engine metadata server.
    """
    request = requests.Request()
    creds = compute_engine.IDTokenCredentials(
        request,
        target_audience=target_audience,
        use_metadata_identity_endpoint=True,
    )
    creds.refresh(request)

    return creds


def fetch_impersonated_id_token_credentials(
    target_principal: str,
    target_audience: str | None = None,
) -> impersonated_credentials.IDTokenCredentials:
    """
    Fetches ID token credentials for an impersonated user.
    """
    request = requests.Request()

    source_credentials, _ = auth.default()
    source_credentials.refresh(request)

    target_credentials = impersonated_credentials.Credentials(
        source_credentials=source_credentials,
        target_principal=target_principal,
        target_scopes=["https://www.googleapis.com/auth/cloud-platform"],
    )
    target_credentials.refresh(request)

    token_credentials = impersonated_credentials.IDTokenCredentials(
        target_credentials=target_credentials,
        target_audience=target_audience,
    )
    token_credentials.refresh(request)

    return token_credentials
