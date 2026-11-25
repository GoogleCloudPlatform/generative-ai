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
"""Automated cross-tenant breach verification suite aligned with Part 2 blog."""

import pytest
from cryptography.hazmat.primitives.asymmetric import ec

from app import config, egress, identity
from app import main as app_main

EXCHANGE_URI = "https://cymbal.example.com/api/v1/auth/exchange"
INVOKE_URI = "https://cymbal.example.com/api/v1/agents/invoke"


def _mint_priya_context(
    runtime: app_main.PlatformRuntime,
) -> tuple[str, str, ec.EllipticCurvePrivateKey]:
    """Completes Priya's FinVault Okta SSO -> DPoP exchange -> ctx+jwt flow."""
    dpop_key = ec.generate_private_key(ec.SECP256R1())
    idp_token = runtime.issue_synthetic_idp_token(
        issuer="https://finvault.okta.com/oauth2/default",
        subject="priya@finvault.example.com",
        groups=["finvault-sre-admins"],
        lob="retail_banking",
    )
    session = runtime.ingress_gateway.exchange_idp_token(
        idp_jwt=idp_token,
        dpop_proof=identity.create_dpop_proof(dpop_key, http_method="POST", http_uri=EXCHANGE_URI),
        http_uri=EXCHANGE_URI,
    )
    context_token = runtime.ingress_gateway.authorize_and_mint_context_token(
        gateway_access_token=session.access_token,
        dpop_proof=identity.create_dpop_proof(
            dpop_key,
            http_method="POST",
            http_uri=INVOKE_URI,
            access_token=session.access_token,
        ),
        http_method="POST",
        http_uri=INVOKE_URI,
        agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        requested_scopes=("2lo:cymbal.telemetry.read", "3lo:jira.incidents.write"),
    )
    return session.access_token, context_token, dpop_key


def test_priya_end_to_end_six_checkpoints() -> None:
    runtime = app_main.PlatformRuntime()
    _, context_token, _ = _mint_priya_context(runtime)

    result = runtime.orchestrator.run_turn(
        context_token=context_token,
        caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
        session_id="sess-priya-01",
        prompt="Is this payment-API spike like last month's outage? Open a Jira ticket.",
        diagnostic_script="print('checking pgbouncer pool wait queue')",
        create_jira_ticket=True,
    )

    assert result.tenant_id == "tenant-finvault-alpha"
    assert result.model_name == "gemini-4-carbon"
    assert result.telemetry_incident_ids == ("INC-FV-4012",)
    assert len(result.recalled_memories) == 1
    assert "AlloyDB connection-pool" in result.recalled_memories[0]
    assert result.jira_ticket_id is not None and result.jira_ticket_id.startswith("FINV-")
    assert "[REDACTED_IBAN]" in result.redactions_applied
    assert "DE89370400440532013000" not in result.response_text
    assert len(result.loaded_tenant_skills) == 2


def test_cross_tenant_idp_issuer_claim_spoofing_and_scope_escalation_blocked() -> None:
    runtime = app_main.PlatformRuntime()
    dpop_key = ec.generate_private_key(ec.SECP256R1())
    idp_token = runtime.issue_synthetic_idp_token(
        issuer="https://finvault.okta.com/oauth2/default",
        subject="analyst@finvault.example.com",
        groups=["finvault-analysts"],
    )
    with pytest.raises(PermissionError, match="conflicts with verified issuer tenant"):
        runtime.ingress_gateway.exchange_idp_token(
            idp_jwt=idp_token,
            dpop_proof=identity.create_dpop_proof(
                dpop_key, http_method="POST", http_uri=EXCHANGE_URI
            ),
            http_uri=EXCHANGE_URI,
            claimed_tenant_id="tenant-retailstream-beta",
        )

    session = runtime.ingress_gateway.exchange_idp_token(
        idp_jwt=idp_token,
        dpop_proof=identity.create_dpop_proof(dpop_key, http_method="POST", http_uri=EXCHANGE_URI),
        http_uri=EXCHANGE_URI,
    )
    context_token = runtime.ingress_gateway.authorize_and_mint_context_token(
        gateway_access_token=session.access_token,
        dpop_proof=identity.create_dpop_proof(
            dpop_key,
            http_method="POST",
            http_uri=INVOKE_URI,
            access_token=session.access_token,
        ),
        http_method="POST",
        http_uri=INVOKE_URI,
        agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        requested_scopes=("2lo:cymbal.telemetry.read", "3lo:jira.incidents.write", "admin:super"),
    )
    verified = runtime.context_verifier.verify(context_token)
    assert verified.scopes == ("2lo:cymbal.telemetry.read",)


def test_stolen_dpop_token_with_wrong_key_and_replay_blocked() -> None:
    runtime = app_main.PlatformRuntime()
    access_token, _, priya_dpop_key = _mint_priya_context(runtime)
    attacker_dpop_key = ec.generate_private_key(ec.SECP256R1())

    with pytest.raises(PermissionError, match="thumbprint does not match"):
        runtime.ingress_gateway.authorize_and_mint_context_token(
            gateway_access_token=access_token,
            dpop_proof=identity.create_dpop_proof(
                attacker_dpop_key,
                http_method="POST",
                http_uri=INVOKE_URI,
                access_token=access_token,
            ),
            http_method="POST",
            http_uri=INVOKE_URI,
            agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        )

    reused_proof = identity.create_dpop_proof(
        priya_dpop_key,
        http_method="POST",
        http_uri=INVOKE_URI,
        access_token=access_token,
    )
    runtime.ingress_gateway.authorize_and_mint_context_token(
        gateway_access_token=access_token,
        dpop_proof=reused_proof,
        http_method="POST",
        http_uri=INVOKE_URI,
        agent_id=config.SHARED_DIAGNOSTIC_AGENT,
    )
    with pytest.raises(PermissionError, match="replay detected"):
        runtime.ingress_gateway.authorize_and_mint_context_token(
            gateway_access_token=access_token,
            dpop_proof=reused_proof,
            http_method="POST",
            http_uri=INVOKE_URI,
            agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        )


def test_standard_tier_blocked_from_enterprise_compliance_agent() -> None:
    runtime = app_main.PlatformRuntime()
    retailstream_dpop_key = ec.generate_private_key(ec.SECP256R1())
    retailstream_idp_token = runtime.issue_synthetic_idp_token(
        issuer="https://login.microsoftonline.com/retailstream-tenant/v2.0",
        subject="alex@retailstream.example.com",
        groups=["retailstream-sre"],
        lob="ecommerce",
    )
    retailstream_session = runtime.ingress_gateway.exchange_idp_token(
        idp_jwt=retailstream_idp_token,
        dpop_proof=identity.create_dpop_proof(
            retailstream_dpop_key, http_method="POST", http_uri=EXCHANGE_URI
        ),
        http_uri=EXCHANGE_URI,
    )
    with pytest.raises(PermissionError, match="not entitled to agent"):
        runtime.ingress_gateway.authorize_and_mint_context_token(
            gateway_access_token=retailstream_session.access_token,
            dpop_proof=identity.create_dpop_proof(
                retailstream_dpop_key,
                http_method="POST",
                http_uri=INVOKE_URI,
                access_token=retailstream_session.access_token,
            ),
            http_method="POST",
            http_uri=INVOKE_URI,
            agent_id=config.REGULATORY_COMPLIANCE_AGENT,
        )


def test_layer3_spiffe_mismatch_and_coworker_3lo_isolation() -> None:
    runtime = app_main.PlatformRuntime()
    _, priya_context_token, _ = _mint_priya_context(runtime)

    with pytest.raises(PermissionError, match="Layer 3 workload identity mismatch"):
        runtime.vault_broker.mint_2lo_cloud_token(
            context_token=priya_context_token,
            caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.REGULATORY_COMPLIANCE_AGENT],
        )

    coworker_context_token = runtime.context_signer.sign(
        tenant_id="tenant-finvault-alpha",
        user_id="bob@finvault.example.com",
        user_role="sre_admin",
        agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        lob="retail_banking",
        scopes=("3lo:jira.incidents.write",),
    )
    with pytest.raises(PermissionError, match="No 3LO 'jira' grant"):
        runtime.vault_broker.checkout_3lo_saas_token(
            context_token=coworker_context_token,
            caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
            provider="jira",
            required_scope="3lo:jira.incidents.write",
        )


@pytest.mark.parametrize(
    "malicious_script",
    [
        "fetch('http://169.254.169.254/computeMetadata/v1/')",
        "addr = 'http://0xa9fea9fe/computeMetadata/v1/'",
        "import os; print(os.environ)",
        "import urllib.request; urllib.request.urlopen('https://example.com')",
    ],
)
def test_sandbox_blocks_metadata_ssrf_and_egress(malicious_script: str) -> None:
    runtime = app_main.PlatformRuntime()
    with pytest.raises(PermissionError, match="Sandbox policy blocked"):
        runtime.sandbox_runner.execute_diagnostic_script(
            tenant_id="tenant-finvault-alpha",
            user_id="priya@finvault.example.com",
            session_id="sess-breach",
            script_code=malicious_script,
        )


def test_memory_bank_controls_1_2_3a_3b_and_expired_token() -> None:
    runtime = app_main.PlatformRuntime()
    _, priya_context_token, _ = _mint_priya_context(runtime)
    cloud_token = runtime.vault_broker.mint_2lo_cloud_token(
        context_token=priya_context_token,
        caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
    )

    expired_token = identity.BrokeredCloudToken(
        access_token=cloud_token.access_token,
        service_account_email=cloud_token.service_account_email,
        kms_key_name=cloud_token.kms_key_name,
        tenant_id=cloud_token.tenant_id,
        scope=cloud_token.scope,
        expires_at=1.0,
    )
    with pytest.raises(PermissionError, match="expired"):
        runtime.memory_bank.retrieve(
            brokered_token=expired_token,
            expected_agent_id=config.SHARED_DIAGNOSTIC_AGENT,
            scope={
                "tenant_id": "tenant-finvault-alpha",
                "lob": "retail_banking",
                "user_id": "priya@finvault.example.com",
                "agent_id": config.SHARED_DIAGNOSTIC_AGENT,
            },
        )

    with pytest.raises(PermissionError, match="Control 1 violation"):
        runtime.memory_bank.retrieve(
            brokered_token=cloud_token,
            expected_agent_id=config.SHARED_DIAGNOSTIC_AGENT,
            scope={
                "tenant_id": "tenant-finvault-alpha",
                "lob": "*",
                "user_id": "priya@finvault.example.com",
                "agent_id": config.SHARED_DIAGNOSTIC_AGENT,
            },
        )

    with pytest.raises(PermissionError, match="Control 2 IAM CEL"):
        runtime.memory_bank.retrieve(
            brokered_token=cloud_token,
            expected_agent_id=config.SHARED_DIAGNOSTIC_AGENT,
            scope={
                "tenant_id": "tenant-retailstream-beta",
                "lob": "ecommerce",
                "user_id": "alex@retailstream.example.com",
                "agent_id": config.SHARED_DIAGNOSTIC_AGENT,
            },
        )

    with pytest.raises(PermissionError, match="Control 3A Residency"):
        runtime.memory_bank.retrieve(
            brokered_token=cloud_token,
            expected_agent_id=config.SHARED_DIAGNOSTIC_AGENT,
            scope={
                "tenant_id": "tenant-finvault-alpha",
                "lob": "retail_banking",
                "user_id": "priya@finvault.example.com",
                "agent_id": config.SHARED_DIAGNOSTIC_AGENT,
            },
            requested_region="europe-west3",
        )

    eurobank_context_token = runtime.context_signer.sign(
        tenant_id="tenant-eurobank-gamma",
        user_id="lena@eurobank.example.eu",
        user_role="sre_admin",
        agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        lob="sepa_payments",
        scopes=("2lo:cymbal.telemetry.read",),
    )
    eurobank_cloud_token = runtime.vault_broker.mint_2lo_cloud_token(
        context_token=eurobank_context_token,
        caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
    )
    saved = runtime.memory_bank.consolidate(
        brokered_token=eurobank_cloud_token,
        expected_agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        scope={
            "tenant_id": "tenant-eurobank-gamma",
            "lob": "sepa_payments",
            "user_id": "lena@eurobank.example.eu",
            "agent_id": config.SHARED_DIAGNOSTIC_AGENT,
        },
        distilled_fact="EU SEPA settlement timeout mitigated.",
        requested_region="europe-west3",
    )
    assert "dedicated-eurobank" in saved.memory_bank_instance
    assert saved.region == "europe-west3"


def test_noisy_neighbor_quota_bulkhead_and_immediate_offboarding() -> None:
    runtime = app_main.PlatformRuntime()
    for _ in range(30):
        runtime.quota_bulkhead.consume(tenant_id="tenant-retailstream-beta", estimated_tokens=100)

    with pytest.raises(egress.QuotaExceededError):
        runtime.quota_bulkhead.consume(tenant_id="tenant-retailstream-beta", estimated_tokens=100)

    finvault_quota = runtime.quota_bulkhead.consume(
        tenant_id="tenant-finvault-alpha",
        estimated_tokens=500,
    )
    assert finvault_quota["rpm_remaining"] == 119

    _, priya_context_token, _ = _mint_priya_context(runtime)
    policy = runtime.tenant_directory.get_active_policy("tenant-finvault-alpha")
    runtime.vault_broker.mint_2lo_cloud_token(
        context_token=priya_context_token,
        caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
    )
    runtime.tenant_directory.offboard_tenant("tenant-finvault-alpha")
    assert runtime.session_store.is_kms_key_disabled(policy.kms_key_name)
    with pytest.raises(PermissionError, match="revoked"):
        runtime.vault_broker.mint_2lo_cloud_token(
            context_token=priya_context_token,
            caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
        )
