# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""FastAPI HTTP boundary and AlloyDB PostgreSQL RLS DDL contract tests."""

import base64
import json
from pathlib import Path

import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

from app import config, identity
from app import main as app_main


def test_http_exchange_and_invoke_strip_forged_tenant_headers() -> None:
    runtime = app_main.PlatformRuntime()
    client = TestClient(app_main.create_app(runtime))
    dpop_key = ec.generate_private_key(ec.SECP256R1())
    idp_token = runtime.issue_synthetic_idp_token(
        issuer="https://finvault.okta.com/oauth2/default",
        subject="priya@finvault.example.com",
        groups=["finvault-sre-admins"],
        lob="retail_banking",
    )

    exchange_url = "http://testserver/api/v1/auth/exchange"
    exchange_response = client.post(
        "/api/v1/auth/exchange",
        json={"idp_token": idp_token},
        headers={
            "DPoP": identity.create_dpop_proof(dpop_key, http_method="POST", http_uri=exchange_url),
            "X-Tenant-ID": "tenant-retailstream-beta",
        },
    )
    assert exchange_response.status_code == 200
    access_token = exchange_response.json()["access_token"]
    assert exchange_response.json()["tenant_id"] == "tenant-finvault-alpha"

    invoke_url = "http://testserver/api/v1/agents/invoke"
    invoke_response = client.post(
        "/api/v1/agents/invoke",
        json={
            "agent_id": config.SHARED_DIAGNOSTIC_AGENT,
            "session_id": "sess-http-01",
            "prompt": "Check payment latency.",
        },
        headers={
            "Authorization": f"DPoP {access_token}",
            "DPoP": identity.create_dpop_proof(
                dpop_key,
                http_method="POST",
                http_uri=invoke_url,
                access_token=access_token,
            ),
            "X-Tenant-ID": "tenant-retailstream-beta",
        },
    )
    assert invoke_response.status_code == 200
    body = invoke_response.json()
    assert body["tenant_id"] == "tenant-finvault-alpha"
    assert body["telemetry_incident_ids"] == ["INC-FV-4012"]
    assert len(body["loaded_tenant_skills"]) == 2


def test_http_offboard_requires_admin_token_and_malformed_dpop_returns_401() -> None:
    runtime = app_main.PlatformRuntime(admin_token="test-admin-secret")
    client = TestClient(app_main.create_app(runtime))

    unauthenticated_response = client.post("/api/v1/tenants/tenant-finvault-alpha/offboard")
    assert unauthenticated_response.status_code == 403
    assert not runtime.tenant_directory.is_revoked("tenant-finvault-alpha")

    authenticated_response = client.post(
        "/api/v1/tenants/tenant-finvault-alpha/offboard",
        headers={"X-Platform-Admin-Token": "test-admin-secret"},
    )
    assert authenticated_response.status_code == 200
    assert runtime.tenant_directory.is_revoked("tenant-finvault-alpha")

    idp_token = runtime.issue_synthetic_idp_token(
        issuer="https://login.microsoftonline.com/retailstream-tenant/v2.0",
        subject="alex@retailstream.example.com",
        groups=["retailstream-sre"],
        lob="ecommerce",
    )
    encoded_header = base64.urlsafe_b64encode(
        json.dumps(
            {"typ": "dpop+jwt", "alg": "ES256", "jwk": {"kty": "EC", "crv": "P-256"}}
        ).encode()
    ).rstrip(b"=")
    encoded_payload = base64.urlsafe_b64encode(b"{}").rstrip(b"=")
    malformed_dpop = f"{encoded_header.decode()}.{encoded_payload.decode()}.sig"
    malformed_dpop_response = client.post(
        "/api/v1/auth/exchange",
        json={"idp_token": idp_token},
        headers={"DPoP": malformed_dpop},
    )
    assert malformed_dpop_response.status_code == 401


def test_alloydb_rls_schema_ddl_and_write_rbac_contract() -> None:
    schema_sql = (Path(__file__).resolve().parents[1] / "app/schema.sql").read_text(
        encoding="utf-8"
    )
    assert "NOBYPASSRLS" in schema_sql
    assert "ENABLE ROW LEVEL SECURITY" in schema_sql
    assert "FORCE ROW LEVEL SECURITY" in schema_sql
    assert "app.current_tenant_id" in schema_sql
    assert "app.current_user_role" in schema_sql
    assert "app.current_agent_id" in schema_sql
    assert "AS RESTRICTIVE" in schema_sql

    runtime = app_main.PlatformRuntime()
    readonly_context_token = runtime.context_signer.sign(
        tenant_id="tenant-finvault-alpha",
        user_id="analyst@finvault.example.com",
        user_role="read_only_analyst",
        agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        lob="retail_banking",
        scopes=("2lo:cymbal.telemetry.read",),
    )
    rows = runtime.alloydb_mcp.query_incidents(
        context_token=readonly_context_token,
        caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
    )
    assert [row.incident_id for row in rows] == ["INC-FV-4012"]

    with pytest.raises(PermissionError, match="Write RBAC policy denied"):
        runtime.alloydb_mcp.update_incident_summary(
            context_token=readonly_context_token,
            caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
            incident_id="INC-FV-4012",
            new_summary="Unauthorized edit",
        )
