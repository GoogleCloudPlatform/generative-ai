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
"""Stateless turn orchestrator, dynamic skills, and local sandbox simulator."""

import re
from dataclasses import dataclass

from app import config, data, egress, identity, memory

SHARED_BASELINE_SKILLS: tuple[str, ...] = (
    "baseline/latency_triage: Correlate p99 latency spikes with connection-pool saturation.",
    "baseline/rollback_checklist: Verify canary error rate before proposing rollback.",
)

_BLOCKED_SANDBOX_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("metadata_ip", re.compile(r"169\.254\.169\.254")),
    ("metadata_host", re.compile(r"metadata\.google\.internal", re.IGNORECASE)),
    ("metadata_hex_ip", re.compile(r"0x0*a9fea9fe", re.IGNORECASE)),
    ("metadata_decimal_ip", re.compile(r"\b2852039166\b")),
    (
        "credential_env_probe",
        re.compile(r"(?:GOOGLE_APPLICATION_CREDENTIALS|os\.environ|subprocess)"),
    ),
    ("direct_egress", re.compile(r"(?:urllib\.request|requests\.|httpx\.|socket\.connect|curl\s)")),
)


@dataclass(frozen=True)
class TenantSkillBundle:
    """Per-turn skills split into shared baseline and per-tenant custom tiers.

    Attributes:
      shared_baseline: Provider-authored runbooks cached in the static prefix.
      tenant_custom: Tenant-owned runbooks injected post-prefix.
      storage_prefix: Tenant-isolated Cloud Storage prefix for custom skills.
    """

    shared_baseline: tuple[str, ...]
    tenant_custom: tuple[str, ...]
    storage_prefix: str


class DynamicSkillLoader:
    """Loads per-tenant custom skills strictly under a verified 2LO token."""

    def __init__(self) -> None:
        """Initializes isolated per-tenant custom runbooks."""
        self._tenant_skills: dict[str, tuple[str, ...]] = {
            "tenant-finvault-alpha": (
                "finvault/sec_17a4_escalation: Mask PAN/IBAN before Jira ticket creation.",
                (
                    "finvault/payment_pool_runbook: Check AlloyDB max_connections and "
                    "PgBouncer wait queue."
                ),
            ),
            "tenant-retailstream-beta": (
                "retailstream/pos_redis_runbook: Check flash-sale cart cache eviction rate.",
            ),
            "tenant-eurobank-gamma": (
                "eurobank/gdpr_residency_runbook: Keep all diagnostic artifacts in europe-west3.",
            ),
        }

    def load_for_turn(self, brokered_token: identity.BrokeredCloudToken) -> TenantSkillBundle:
        """Loads shared baseline and per-tenant custom skills for one turn.

        Args:
          brokered_token: Short-lived 2LO Google Cloud token from the broker.

        Returns:
          TenantSkillBundle with static baseline and post-prefix tenant skills.
        """
        tenant_id = brokered_token.tenant_id
        return TenantSkillBundle(
            shared_baseline=SHARED_BASELINE_SKILLS,
            tenant_custom=self._tenant_skills.get(tenant_id, ()),
            storage_prefix=f"gs://cymbal-runbooks/{tenant_id}/skills/",
        )


@dataclass(frozen=True)
class SandboxExecutionResult:
    """Structured output returned from the local sandbox policy simulator.

    Attributes:
      sandbox_id: Ephemeral per-session sandbox identifier.
      tenant_id: Verified tenant identifier.
      user_id: Verified user subject.
      stdout: Simulated diagnostic screening summary.
      egress_mode: Network egress policy (`NO_DIRECT_EGRESS`).
      credentials_mounted: Whether any credentials are mounted (False).
    """

    sandbox_id: str
    tenant_id: str
    user_id: str
    stdout: str
    egress_mode: str
    credentials_mounted: bool


class IsolatedSandboxRunner:
    """Local policy simulator for ephemeral per-session sandboxes."""

    def __init__(self, ttl_seconds: int = 120) -> None:
        """Initializes the sandbox simulator with an ephemeral TTL.

        Args:
          ttl_seconds: Simulated sandbox lifetime in seconds.
        """
        self._ttl_seconds = ttl_seconds
        self._active_sandboxes: dict[str, set[str]] = {}

    def execute_diagnostic_script(
        self,
        *,
        tenant_id: str,
        user_id: str,
        session_id: str,
        script_code: str,
        staged_log_summary: str = "",
    ) -> SandboxExecutionResult:
        """Screens script_code for SSRF/credential probes and returns a summary.

        Args:
          tenant_id: Verified tenant identifier.
          user_id: Verified user subject.
          session_id: Active investigation session identifier.
          script_code: Untrusted diagnostic script proposed by the agent.
          staged_log_summary: Sanitized log summary staged by the orchestrator.

        Returns:
          SandboxExecutionResult with simulated output and policy metadata.

        Raises:
          PermissionError: If script_code matches a blocked SSRF, credential,
            or direct-egress pattern.
        """
        for rule_name, pattern in _BLOCKED_SANDBOX_PATTERNS:
            if pattern.search(script_code):
                raise PermissionError(
                    f"Sandbox policy blocked '{rule_name}': zero credentials and no direct egress."
                )

        sandbox_id = f"sbx-{tenant_id[:12]}-{session_id[:8]}"
        self._active_sandboxes.setdefault(tenant_id, set()).add(sandbox_id)

        line_count = len([line for line in staged_log_summary.splitlines() if line.strip()])
        stdout = (
            f"[local-sandbox-sim id={sandbox_id} ttl={self._ttl_seconds}s] "
            f"Screened script ({len(script_code)} chars) against {line_count} staged log line(s)."
        )
        return SandboxExecutionResult(
            sandbox_id=sandbox_id,
            tenant_id=tenant_id,
            user_id=user_id,
            stdout=stdout,
            egress_mode="NO_DIRECT_EGRESS",
            credentials_mounted=False,
        )

    def evict_tenant(self, tenant_id: str) -> None:
        """Purges active sandbox registrations for an offboarded tenant.

        Args:
          tenant_id: Offboarded tenant identifier.
        """
        self._active_sandboxes.pop(tenant_id, None)


@dataclass(frozen=True)
class TurnResult:
    """Complete auditable result of one stateless multi-tenant agent turn.

    Attributes:
      tenant_id: Verified tenant identifier.
      user_id: Verified user subject.
      user_role: Mapped intra-tenant RBAC role.
      agent_id: Invoked catalog agent identifier.
      session_id: Conversation session identifier.
      entitled_tools: Tools allowed by the Tenant ∩ Role ∩ Agent intersection.
      loaded_tenant_skills: Per-tenant custom skills injected post-prefix.
      model_name: Selected Gemini model identifier.
      prefix_cache_key: Shared provider-only prefix cache key.
      recalled_memories: Distilled facts recalled from Memory Bank.
      telemetry_incident_ids: Incident IDs returned by AlloyDB RLS queries.
      sandbox_stdout: Output from the local sandbox policy simulator.
      jira_ticket_id: Created Jira ticket key, or None if no ticket was opened.
      redactions_applied: Unique DLP redaction labels applied during the turn.
      response_text: Final synthesized assistant response.
    """

    tenant_id: str
    user_id: str
    user_role: str
    agent_id: str
    session_id: str
    entitled_tools: tuple[str, ...]
    loaded_tenant_skills: tuple[str, ...]
    model_name: str
    prefix_cache_key: str
    recalled_memories: tuple[str, ...]
    telemetry_incident_ids: tuple[str, ...]
    sandbox_stdout: str
    jira_ticket_id: str | None
    redactions_applied: tuple[str, ...]
    response_text: str


class StatelessTurnOrchestrator:
    """Stateless turn orchestrator with zero standing tenant credentials."""

    def __init__(
        self,
        *,
        tenant_directory: config.TenantDirectory,
        context_verifier: identity.ContextTokenVerifier,
        vault_broker: identity.VaultCredentialBroker,
        sandbox_runner: IsolatedSandboxRunner,
        skill_loader: DynamicSkillLoader,
        session_store: memory.EncryptedSessionStore,
        memory_bank: memory.ScopedMemoryBank,
        guardrails: egress.EgressGuardrails,
        quota_bulkhead: egress.TenantQuotaBulkhead,
        model_router: egress.GovernedGeminiRouter,
        alloydb_mcp: data.AlloyDBTelemetryMCPServer,
        saas_client: data.DelegatedSaaSClient,
    ) -> None:
        """Initializes the orchestrator with externalized subsystem handles."""
        self._directory = tenant_directory
        self._verifier = context_verifier
        self._vault = vault_broker
        self._sandbox = sandbox_runner
        self._skills = skill_loader
        self._sessions = session_store
        self._memory_bank = memory_bank
        self._guardrails = guardrails
        self._quota = quota_bulkhead
        self._router = model_router
        self._alloydb = alloydb_mcp
        self._saas = saas_client

    def run_turn(
        self,
        *,
        context_token: str,
        caller_spiffe_id: str,
        session_id: str,
        prompt: str,
        diagnostic_script: str | None = None,
        create_jira_ticket: bool = False,
        requested_region: str | None = None,
    ) -> TurnResult:
        """Executes one stateless turn across all six security checkpoints.

        Args:
          context_token: ES256-signed `ctx+jwt` from the Ingress Gateway.
          caller_spiffe_id: Workload SPIFFE mTLS identity of the calling agent.
          session_id: Conversation session identifier.
          prompt: User diagnostic prompt.
          diagnostic_script: Optional untrusted script for the sandbox
            simulator; skipped when None.
          create_jira_ticket: If True, opens a redacted 3LO Jira ticket.
          requested_region: Optional region lock assertion; uses the tenant's
            configured region when None.

        Returns:
          TurnResult with audit metadata and synthesized response text.

        Raises:
          PermissionError: If token, entitlement, guardrail, sandbox, or memory
            isolation checks fail.
          QuotaExceededError: If the tenant exceeds its per-minute RPM or TPM
            quota.
        """
        verified = self._verifier.verify(context_token)
        policy = self._directory.get_active_policy(verified.tenant_id)

        self._quota.consume(tenant_id=verified.tenant_id, estimated_tokens=500)
        screened_prompt = self._guardrails.screen_and_redact(prompt)

        role_tools = config.ROLE_ALLOWED_TOOLS.get(verified.user_role, frozenset())
        agent_tools = config.AGENT_ALLOWED_TOOLS.get(verified.agent_id, frozenset())
        entitled_tools = tuple(sorted(role_tools & agent_tools))

        cloud_token = self._vault.mint_2lo_cloud_token(
            context_token=context_token,
            caller_spiffe_id=caller_spiffe_id,
            required_scope="2lo:cymbal.telemetry.read",
        )

        prior_turns = self._sessions.load_turns(
            brokered_token=cloud_token,
            user_id=verified.user_id,
            session_id=session_id,
        )
        skill_bundle = self._skills.load_for_turn(cloud_token)

        memory_scope = {
            "tenant_id": verified.tenant_id,
            "lob": verified.lob,
            "user_id": verified.user_id,
            "agent_id": verified.agent_id,
        }
        recalled_records = self._memory_bank.retrieve(
            brokered_token=cloud_token,
            expected_agent_id=verified.agent_id,
            scope=memory_scope,
            requested_region=requested_region,
            top_k=5,
        )
        recalled_facts = [record.fact for record in recalled_records]

        incidents = self._alloydb.query_incidents(
            context_token=context_token,
            caller_spiffe_id=caller_spiffe_id,
            limit=5,
        )
        raw_telemetry = "; ".join(
            f"{row.incident_id} ({row.service_name} {row.severity}): {row.summary}"
            for row in incidents
        )
        screened_telemetry = self._guardrails.screen_and_redact(raw_telemetry)

        sandbox_stdout = "No sandbox script executed."
        if diagnostic_script is not None:
            if "execute_diagnostic_sandbox" not in entitled_tools:
                raise PermissionError(
                    f"Role '{verified.user_role}' / agent '{verified.agent_id}' is not entitled "
                    "to invoke execute_diagnostic_sandbox."
                )
            sandbox_result = self._sandbox.execute_diagnostic_script(
                tenant_id=verified.tenant_id,
                user_id=verified.user_id,
                session_id=session_id,
                script_code=diagnostic_script,
                staged_log_summary=screened_telemetry.sanitized_text,
            )
            sandbox_stdout = sandbox_result.stdout

        jira_ticket_id: str | None = None
        all_redactions = list(
            screened_prompt.redactions_applied + screened_telemetry.redactions_applied
        )
        if create_jira_ticket:
            if "create_jira_incident" not in entitled_tools:
                raise PermissionError("Caller is not entitled to invoke create_jira_incident.")
            receipt = self._saas.create_jira_incident(
                context_token=context_token,
                caller_spiffe_id=caller_spiffe_id,
                summary=f"[{policy.display_name}] Payment latency investigation",
                description=f"{raw_telemetry} | {sandbox_stdout}",
            )
            jira_ticket_id = receipt.ticket_id
            all_redactions.extend(receipt.redactions_applied)

        model_decision = self._router.generate(
            policy=policy,
            user_prompt=screened_prompt.sanitized_text,
            tenant_skills=skill_bundle.tenant_custom,
            recalled_memories=recalled_facts,
            telemetry_summary=screened_telemetry.sanitized_text,
            sandbox_stdout=sandbox_stdout,
            jira_ticket_id=jira_ticket_id,
        )

        updated_turns = [
            *prior_turns,
            {"role": "user", "content": screened_prompt.sanitized_text},
            {"role": "assistant", "content": model_decision.response_text},
        ]
        self._sessions.save_turn(
            brokered_token=cloud_token,
            user_id=verified.user_id,
            session_id=session_id,
            turns=updated_turns,
        )
        self._memory_bank.consolidate(
            brokered_token=cloud_token,
            expected_agent_id=verified.agent_id,
            scope=memory_scope,
            distilled_fact=(
                f"Turn summary ({session_id}): {screened_telemetry.sanitized_text[:120]}"
            ),
            requested_region=requested_region,
        )

        return TurnResult(
            tenant_id=verified.tenant_id,
            user_id=verified.user_id,
            user_role=verified.user_role,
            agent_id=verified.agent_id,
            session_id=session_id,
            entitled_tools=entitled_tools,
            loaded_tenant_skills=skill_bundle.tenant_custom,
            model_name=model_decision.model_name,
            prefix_cache_key=model_decision.prefix_cache_key,
            recalled_memories=tuple(recalled_facts),
            telemetry_incident_ids=tuple(row.incident_id for row in incidents),
            sandbox_stdout=sandbox_stdout,
            jira_ticket_id=jira_ticket_id,
            redactions_applied=tuple(dict.fromkeys(all_redactions)),
            response_text=model_decision.response_text,
        )
