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
"""Interactive walkthrough of the Part 2 Pooled Architecture blog.

Runs Priya's 6-checkpoint incident investigation for FinVault Bank, followed by
6 cross-tenant breach checks verifying each isolation boundary fails closed.

Usage:
  uv run python demo.py
"""

from cryptography.hazmat.primitives.asymmetric import ec

from app import config, identity
from app import main as app_main

_EXCHANGE_URI = "https://cymbal.example.com/api/v1/auth/exchange"
_INVOKE_URI = "https://cymbal.example.com/api/v1/agents/invoke"


def run_walkthrough() -> None:
    """Runs Priya's 6-checkpoint flow and 6 cross-tenant breach checks."""
    runtime = app_main.PlatformRuntime()
    priya_dpop_key = ec.generate_private_key(ec.SECP256R1())

    print("=== Part 2 Pooled Architecture: Priya's 6-Checkpoint End-to-End Trace ===")
    priya_idp_token = runtime.issue_synthetic_idp_token(
        issuer="https://finvault.okta.com/oauth2/default",
        subject="priya@finvault.example.com",
        groups=["finvault-sre-admins"],
        lob="retail_banking",
    )
    gateway_session = runtime.ingress_gateway.exchange_idp_token(
        idp_jwt=priya_idp_token,
        dpop_proof=identity.create_dpop_proof(
            priya_dpop_key, http_method="POST", http_uri=_EXCHANGE_URI
        ),
        http_uri=_EXCHANGE_URI,
    )
    print(f"[Checkpoint 1] Verified FinVault Okta SSO -> DPoP jkt={gateway_session.jkt[:12]}...")

    context_token = runtime.ingress_gateway.authorize_and_mint_context_token(
        gateway_access_token=gateway_session.access_token,
        dpop_proof=identity.create_dpop_proof(
            priya_dpop_key,
            http_method="POST",
            http_uri=_INVOKE_URI,
            access_token=gateway_session.access_token,
        ),
        http_method="POST",
        http_uri=_INVOKE_URI,
        agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        requested_scopes=("2lo:cymbal.telemetry.read", "3lo:jira.incidents.write"),
    )
    print("[Checkpoint 2] Signed ES256 ctx+jwt locking Tenant ∩ User ∩ Agent.")

    turn = runtime.orchestrator.run_turn(
        context_token=context_token,
        caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
        session_id="sess-priya-payment-outage",
        prompt="Is this payment-API latency spike like last month's outage? Open a Jira ticket.",
        diagnostic_script="print('p99_wait_ms=4200')",
        create_jira_ticket=True,
    )
    print(f"[Checkpoints 3-6] Model={turn.model_name} | PrefixCache={turn.prefix_cache_key}")
    print(f"  AlloyDB RLS incidents : {turn.telemetry_incident_ids}")
    print(f"  Memory Bank recalled  : {len(turn.recalled_memories)} record(s)")
    print(f"  Loaded tenant skills  : {len(turn.loaded_tenant_skills)} runbook(s)")
    print(f"  Sandbox sim output    : {turn.sandbox_stdout}")
    print(f"  3LO Jira ticket       : {turn.jira_ticket_id} (DLP={turn.redactions_applied})")

    print("\n=== 6 Automated Cross-Tenant Breach Checks ===")
    checks: list[tuple[str, str]] = []

    attacker_dpop_key = ec.generate_private_key(ec.SECP256R1())
    try:
        runtime.ingress_gateway.authorize_and_mint_context_token(
            gateway_access_token=gateway_session.access_token,
            dpop_proof=identity.create_dpop_proof(
                attacker_dpop_key,
                http_method="POST",
                http_uri=_INVOKE_URI,
                access_token=gateway_session.access_token,
            ),
            http_method="POST",
            http_uri=_INVOKE_URI,
            agent_id=config.SHARED_DIAGNOSTIC_AGENT,
        )
    except PermissionError as exc:
        checks.append(("1. Stolen DPoP token with wrong key", f"BLOCKED ({exc})"))

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
            retailstream_dpop_key, http_method="POST", http_uri=_EXCHANGE_URI
        ),
        http_uri=_EXCHANGE_URI,
    )
    try:
        runtime.ingress_gateway.authorize_and_mint_context_token(
            gateway_access_token=retailstream_session.access_token,
            dpop_proof=identity.create_dpop_proof(
                retailstream_dpop_key,
                http_method="POST",
                http_uri=_INVOKE_URI,
                access_token=retailstream_session.access_token,
            ),
            http_method="POST",
            http_uri=_INVOKE_URI,
            agent_id=config.REGULATORY_COMPLIANCE_AGENT,
        )
    except PermissionError as exc:
        checks.append(("2. Standard tenant invokes Enterprise agent", f"BLOCKED ({exc})"))

    try:
        runtime.vault_broker.mint_2lo_cloud_token(
            context_token=context_token,
            caller_spiffe_id="spiffe://cymbal.example.com/ns/pooled/sa/rogue-container",
        )
    except PermissionError as exc:
        checks.append(("3. Rogue container SPIFFE spoof at Vault", f"BLOCKED ({exc})"))

    try:
        runtime.sandbox_runner.execute_diagnostic_script(
            tenant_id="tenant-finvault-alpha",
            user_id="priya@finvault.example.com",
            session_id="sess-breach",
            script_code="url = 'http://0xa9fea9fe/computeMetadata/v1/'",
        )
    except PermissionError as exc:
        checks.append(("4. Sandbox hex metadata SSRF probe", f"BLOCKED ({exc})"))

    cloud_token = runtime.vault_broker.mint_2lo_cloud_token(
        context_token=context_token,
        caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
    )
    try:
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
    except PermissionError as exc:
        checks.append(("5. Memory Bank cross-tenant IAM CEL read", f"BLOCKED ({exc})"))

    runtime.tenant_directory.offboard_tenant("tenant-finvault-alpha")
    try:
        runtime.vault_broker.mint_2lo_cloud_token(
            context_token=context_token,
            caller_spiffe_id=config.AGENT_SPIFFE_IDS[config.SHARED_DIAGNOSTIC_AGENT],
        )
    except PermissionError as exc:
        checks.append(("6. Post-offboarding token reuse", f"BLOCKED ({exc})"))

    for label, status in checks:
        print(f"  [PASS] {label}: {status}")
    if len(checks) != 6:
        raise RuntimeError(f"Expected 6 blocked breach checks, got {len(checks)}.")


def main() -> None:
    """CLI entry point for the interactive walkthrough."""
    run_walkthrough()


if __name__ == "__main__":
    main()
