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
"""FastAPI Ingress Gateway and agent turn invocation HTTP boundary."""

import hmac
import os
import secrets
import time
from collections.abc import Sequence
from dataclasses import asdict
from typing import Any

import jwt
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi import FastAPI, Header, HTTPException, Request
from pydantic import BaseModel, Field

from app import config, data, egress, identity, memory, orchestrator


class AuthExchangeRequest(BaseModel):
    """Request payload for IdP-to-DPoP token exchange."""

    idp_token: str = Field(..., min_length=10)
    claimed_tenant_id: str | None = None


class InvokeAgentRequest(BaseModel):
    """Request payload for invoking a catalog agent through the gateway."""

    agent_id: str = Field(default=config.SHARED_DIAGNOSTIC_AGENT)
    session_id: str = Field(default="sess-priya-001")
    prompt: str = Field(..., min_length=1)
    diagnostic_script: str | None = None
    create_jira_ticket: bool = False
    requested_region: str | None = None
    requested_scopes: list[str] = Field(
        default_factory=lambda: ["2lo:cymbal.telemetry.read", "3lo:jira.incidents.write"]
    )


class PlatformRuntime:
    """Wires pooled subsystems into one testable runtime container."""

    def __init__(self, admin_token: str | None = None) -> None:
        """Initializes all subsystems with synthetic IdP keys for local runs.

        Args:
          admin_token: Optional control-plane token for `/offboard`. When None,
            reads `CYMBAL_PLATFORM_ADMIN_TOKEN` or generates a random token.
        """
        self.admin_token = (
            admin_token
            or os.environ.get("CYMBAL_PLATFORM_ADMIN_TOKEN")
            or secrets.token_urlsafe(32)
        )
        self.tenant_directory = config.TenantDirectory()
        self.idp_signing_keys: dict[str, ec.EllipticCurvePrivateKey] = {
            policy.oidc_issuer: ec.generate_private_key(ec.SECP256R1())
            for policy in config.DEFAULT_TENANT_POLICIES.values()
        }
        self.context_signer = identity.ContextTokenSigner()
        self.context_verifier = identity.ContextTokenVerifier(
            public_keys={self.context_signer.key_id: self.context_signer.public_key},
            revoked_check=self.tenant_directory.is_revoked,
        )
        self.ingress_gateway = identity.IngressGateway(
            tenant_directory=self.tenant_directory,
            context_signer=self.context_signer,
            idp_public_keys={
                issuer: key.public_key() for issuer, key in self.idp_signing_keys.items()
            },
        )
        self.vault_broker = identity.VaultCredentialBroker(
            tenant_directory=self.tenant_directory,
            context_verifier=self.context_verifier,
        )
        self.vault_broker.register_user_3lo_grant(
            identity.UserOAuthGrant(
                tenant_id="tenant-finvault-alpha",
                user_id="priya@finvault.example.com",
                provider="jira",
                scope="3lo:jira.incidents.write",
                token_value="jira-3lo-priya-finvault-handle",
            )
        )
        self.sandbox_runner = orchestrator.IsolatedSandboxRunner()
        self.tenant_directory.register_eviction_hook(self.sandbox_runner)
        self.skill_loader = orchestrator.DynamicSkillLoader()
        self.guardrails = egress.EgressGuardrails()
        self.session_store = memory.EncryptedSessionStore(self.tenant_directory, self.guardrails)
        self.memory_bank = memory.ScopedMemoryBank(self.tenant_directory)
        self.quota_bulkhead = egress.TenantQuotaBulkhead(self.tenant_directory)
        self.model_router = egress.GovernedGeminiRouter()
        self.alloydb_mcp = data.AlloyDBTelemetryMCPServer(self.context_verifier)
        self.saas_client = data.DelegatedSaaSClient(self.vault_broker, self.guardrails)
        self.orchestrator = orchestrator.StatelessTurnOrchestrator(
            tenant_directory=self.tenant_directory,
            context_verifier=self.context_verifier,
            vault_broker=self.vault_broker,
            sandbox_runner=self.sandbox_runner,
            skill_loader=self.skill_loader,
            session_store=self.session_store,
            memory_bank=self.memory_bank,
            guardrails=self.guardrails,
            quota_bulkhead=self.quota_bulkhead,
            model_router=self.model_router,
            alloydb_mcp=self.alloydb_mcp,
            saas_client=self.saas_client,
        )

    def verify_admin_token(self, provided_token: str | None) -> bool:
        """Verifies control-plane admin credentials in constant time.

        Args:
          provided_token: Value from `X-Platform-Admin-Token`, or None.

        Returns:
          True if provided_token matches `self.admin_token`.
        """
        if not provided_token:
            return False
        return hmac.compare_digest(provided_token, self.admin_token)

    def issue_synthetic_idp_token(
        self,
        *,
        issuer: str,
        subject: str,
        groups: Sequence[str],
        lob: str = "retail_banking",
    ) -> str:
        """Signs a synthetic corporate OIDC token for local demo and tests.

        Args:
          issuer: Corporate OIDC issuer URL configured in DEFAULT_TENANT_POLICIES.
          subject: User subject identifier.
          groups: Corporate IdP group memberships.
          lob: Line-of-business claim value.

        Returns:
          Compact ES256-signed OIDC JWT string.
        """
        now = int(time.time())
        return jwt.encode(
            {
                "iss": issuer,
                "aud": "cymbal-cloudops-api",
                "sub": subject,
                "groups": list(groups),
                "lob": lob,
                "iat": now,
                "exp": now + 600,
            },
            self.idp_signing_keys[issuer],
            algorithm="ES256",
        )


def create_app(runtime: PlatformRuntime | None = None) -> FastAPI:
    """Creates the FastAPI application wired to a PlatformRuntime instance.

    Args:
      runtime: Optional pre-configured PlatformRuntime; creates a new instance
        when None.

    Returns:
      Configured FastAPI application.
    """
    active_runtime = runtime or PlatformRuntime()
    application = FastAPI(
        title="Cymbal CloudOps Pooled Multi-Tenant Agent Gateway",
        version="0.3.0",
    )
    application.state.runtime = active_runtime

    @application.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @application.post("/api/v1/auth/exchange")
    def auth_exchange(payload: AuthExchangeRequest, request: Request) -> dict[str, Any]:
        sanitized_headers = identity.sanitize_inbound_headers(dict(request.headers))
        dpop_header = sanitized_headers.get("dpop")
        if not dpop_header:
            raise HTTPException(status_code=401, detail="Missing DPoP proof header.")
        http_uri = str(request.url).split("?", 1)[0]
        try:
            session_token = active_runtime.ingress_gateway.exchange_idp_token(
                idp_jwt=payload.idp_token,
                dpop_proof=dpop_header,
                http_uri=http_uri,
                claimed_tenant_id=payload.claimed_tenant_id,
            )
        except PermissionError as exc:
            raise HTTPException(status_code=401, detail=str(exc)) from exc
        return asdict(session_token)

    @application.post("/api/v1/agents/invoke")
    def invoke_agent(payload: InvokeAgentRequest, request: Request) -> dict[str, Any]:
        sanitized_headers = identity.sanitize_inbound_headers(dict(request.headers))
        authorization = sanitized_headers.get("authorization")
        dpop_header = sanitized_headers.get("dpop")
        if not authorization or not authorization.startswith("DPoP "):
            raise HTTPException(status_code=401, detail="Authorization must use 'DPoP <token>'.")
        if not dpop_header:
            raise HTTPException(status_code=401, detail="Missing DPoP proof header.")

        gateway_token = authorization.removeprefix("DPoP ").strip()
        http_uri = str(request.url).split("?", 1)[0]
        try:
            context_token = active_runtime.ingress_gateway.authorize_and_mint_context_token(
                gateway_access_token=gateway_token,
                dpop_proof=dpop_header,
                http_method="POST",
                http_uri=http_uri,
                agent_id=payload.agent_id,
                requested_scopes=tuple(payload.requested_scopes),
            )
            caller_spiffe = config.AGENT_SPIFFE_IDS.get(payload.agent_id, "")
            result = active_runtime.orchestrator.run_turn(
                context_token=context_token,
                caller_spiffe_id=caller_spiffe,
                session_id=payload.session_id,
                prompt=payload.prompt,
                diagnostic_script=payload.diagnostic_script,
                create_jira_ticket=payload.create_jira_ticket,
                requested_region=payload.requested_region,
            )
        except egress.QuotaExceededError as exc:
            raise HTTPException(
                status_code=429,
                detail=str(exc),
                headers={"Retry-After": str(exc.retry_after_seconds)},
            ) from exc
        except PermissionError as exc:
            status_code = 401 if "DPoP" in str(exc) or "access token" in str(exc) else 403
            raise HTTPException(status_code=status_code, detail=str(exc)) from exc
        return asdict(result)

    @application.post("/api/v1/tenants/{tenant_id}/offboard")
    def offboard_tenant(
        tenant_id: str,
        x_admin_token: str | None = Header(default=None, alias="X-Platform-Admin-Token"),
    ) -> dict[str, str]:
        if not active_runtime.verify_admin_token(x_admin_token):
            raise HTTPException(status_code=403, detail="Platform admin credentials required.")
        active_runtime.tenant_directory.offboard_tenant(tenant_id)
        return {"status": "offboarded", "tenant_id": tenant_id}

    return application


app = create_app()
