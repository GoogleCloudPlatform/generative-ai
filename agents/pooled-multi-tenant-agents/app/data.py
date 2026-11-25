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
"""AlloyDB RLS MCP adapter and delegated 3LO Jira client."""

from collections.abc import Sequence
from dataclasses import dataclass

from app import config, egress, identity

ALLOWED_READ_ROLES = frozenset({"sre_admin", "compliance_officer", "read_only_analyst"})
ALLOWED_WRITE_ROLES = frozenset({"sre_admin"})


def _tenant_ticket_prefix(tenant_id: str) -> str:
    """Derives a 4-letter Jira project prefix from a tenant identifier."""
    parts = [part for part in tenant_id.split("-") if part and part != "tenant"]
    label = parts[0] if parts else tenant_id
    return label[:4].upper()


@dataclass(frozen=True)
class IncidentRow:
    """One row from the `tenant_incidents` table in AlloyDB for PostgreSQL.

    Attributes:
      incident_id: Primary key incident identifier.
      tenant_id: Owning tenant identifier.
      service_name: Affected service name.
      severity: Incident severity label (for example, `SEV1`).
      summary: Incident description text.
    """

    incident_id: str
    tenant_id: str
    service_name: str
    severity: str
    summary: str


class AlloyDBTelemetryMCPServer:
    """Local reference MCP server mirroring `app/schema.sql` fail-closed RLS."""

    def __init__(self, context_verifier: identity.ContextTokenVerifier) -> None:
        """Initializes the MCP server with synthetic tenant incident rows.

        Args:
          context_verifier: Public-key-only `ctx+jwt` verifier.
        """
        self._verifier = context_verifier
        self._rows: list[IncidentRow] = [
            IncidentRow(
                incident_id="INC-FV-4012",
                tenant_id="tenant-finvault-alpha",
                service_name="payment-api",
                severity="SEV1",
                summary=(
                    "p99 latency spiked to 4.2s; PgBouncer pool wait queue saturated "
                    "(customer IBAN DE89370400440532013000 in debug payload)."
                ),
            ),
            IncidentRow(
                incident_id="INC-RS-9001",
                tenant_id="tenant-retailstream-beta",
                service_name="checkout-cart-redis",
                severity="SEV2",
                summary="Flash-sale cache evictions elevated on shard 3.",
            ),
            IncidentRow(
                incident_id="INC-EB-7701",
                tenant_id="tenant-eurobank-gamma",
                service_name="sepa-settlement-api",
                severity="SEV2",
                summary="EU settlement queue delay in europe-west3.",
            ),
        ]

    def query_incidents(
        self,
        *,
        context_token: str,
        caller_spiffe_id: str,
        limit: int = 10,
    ) -> Sequence[IncidentRow]:
        """Queries `tenant_incidents` under fail-closed RLS and RBAC claims.

        Args:
          context_token: Gateway-signed `ctx+jwt`.
          caller_spiffe_id: Calling agent workload SPIFFE identity.
          limit: Maximum rows to return, ordered by `incident_id`.

        Returns:
          Sequence of tenant-scoped IncidentRow entries.

        Raises:
          PermissionError: If `ctx+jwt` or SPIFFE verification fails.
        """
        tenant_id, user_role, agent_id = self._verify_mcp_caller(context_token, caller_spiffe_id)
        if (
            not tenant_id
            or user_role not in ALLOWED_READ_ROLES
            or agent_id not in config.AGENT_SPIFFE_IDS
        ):
            return []

        scoped = [row for row in self._rows if row.tenant_id == tenant_id]
        scoped.sort(key=lambda row: row.incident_id)
        return scoped[:limit]

    def update_incident_summary(
        self,
        *,
        context_token: str,
        caller_spiffe_id: str,
        incident_id: str,
        new_summary: str,
    ) -> IncidentRow:
        """Updates an incident summary under the restrictive write RBAC policy.

        Args:
          context_token: Gateway-signed `ctx+jwt`.
          caller_spiffe_id: Calling agent workload SPIFFE identity.
          incident_id: Target incident identifier.
          new_summary: Replacement summary text.

        Returns:
          The updated IncidentRow.

        Raises:
          PermissionError: If write RBAC denies the update or the row is not
            visible to the verified tenant.
        """
        tenant_id, user_role, agent_id = self._verify_mcp_caller(context_token, caller_spiffe_id)
        if user_role not in ALLOWED_WRITE_ROLES or agent_id != config.SHARED_DIAGNOSTIC_AGENT:
            raise PermissionError(
                f"Write RBAC policy denied UPDATE for role='{user_role}', agent='{agent_id}'."
            )

        for row_index, row in enumerate(self._rows):
            if row.incident_id == incident_id and row.tenant_id == tenant_id:
                updated = IncidentRow(
                    incident_id=row.incident_id,
                    tenant_id=row.tenant_id,
                    service_name=row.service_name,
                    severity=row.severity,
                    summary=new_summary,
                )
                self._rows[row_index] = updated
                return updated
        raise PermissionError(f"Incident '{incident_id}' not visible under tenant '{tenant_id}'.")

    def _verify_mcp_caller(self, context_token: str, caller_spiffe_id: str) -> tuple[str, str, str]:
        """Re-verifies `ctx+jwt` and SPIFFE workload identity independently."""
        verified = self._verifier.verify(context_token)
        expected_spiffe = config.AGENT_SPIFFE_IDS.get(verified.agent_id)
        if expected_spiffe is None or caller_spiffe_id != expected_spiffe:
            raise PermissionError("MCP server rejected mismatched SPIFFE workload identity.")
        return verified.tenant_id, verified.user_role, verified.agent_id


@dataclass(frozen=True)
class SanitizedTicketReceipt:
    """Receipt returned after creating a redacted external Jira ticket.

    Attributes:
      ticket_id: Created ticket identifier.
      tenant_id: Tenant owning the ticket.
      acted_as_user: Delegated 3LO user subject.
      redacted_description: Ticket text after egress redaction.
      redactions_applied: Placeholder labels applied during screening.
    """

    ticket_id: str
    tenant_id: str
    acted_as_user: str
    redacted_description: str
    redactions_applied: tuple[str, ...]


class DelegatedSaaSClient:
    """Executes user-delegated 3LO Jira actions through egress guardrails."""

    def __init__(
        self,
        vault_broker: identity.VaultCredentialBroker,
        guardrails: egress.EgressGuardrails,
    ) -> None:
        """Initializes the delegated SaaS client.

        Args:
          vault_broker: Out-of-process credential broker.
          guardrails: Egress injection and PII/PCI screener.
        """
        self._vault = vault_broker
        self._guardrails = guardrails
        self._ticket_counter = 100

    def create_jira_incident(
        self,
        *,
        context_token: str,
        caller_spiffe_id: str,
        summary: str,
        description: str,
    ) -> SanitizedTicketReceipt:
        """Checks out the caller's 3LO Jira grant, redacts PII, and opens a ticket.

        Args:
          context_token: Gateway-signed `ctx+jwt`.
          caller_spiffe_id: Calling workload SPIFFE identity.
          summary: Ticket title.
          description: Diagnostic body screened before egress.

        Returns:
          SanitizedTicketReceipt confirming delegated creation and redactions.

        Raises:
          PermissionError: If 3LO checkout or egress screening fails.
        """
        grant = self._vault.checkout_3lo_saas_token(
            context_token=context_token,
            caller_spiffe_id=caller_spiffe_id,
            provider="jira",
            required_scope="3lo:jira.incidents.write",
        )
        screened_summary = self._guardrails.screen_and_redact(summary)
        screened_body = self._guardrails.screen_and_redact(description)
        self._ticket_counter += 1
        prefix = _tenant_ticket_prefix(grant.tenant_id)
        return SanitizedTicketReceipt(
            ticket_id=f"{prefix}-{self._ticket_counter}",
            tenant_id=grant.tenant_id,
            acted_as_user=grant.user_id,
            redacted_description=f"{screened_summary.sanitized_text}: {screened_body.sanitized_text}",
            redactions_applied=screened_summary.redactions_applied
            + screened_body.redactions_applied,
        )
