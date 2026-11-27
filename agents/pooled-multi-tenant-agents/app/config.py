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
"""Tenant registry, agent entitlements, and role allowlists."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Protocol

SHARED_DIAGNOSTIC_AGENT = "cymbal_shared_diagnostic_agent"
REGULATORY_COMPLIANCE_AGENT = "finvault_regulatory_escalation_agent"

AGENT_SPIFFE_IDS: Mapping[str, str] = MappingProxyType(
    {
        SHARED_DIAGNOSTIC_AGENT: "spiffe://cymbal.example.com/ns/pooled/sa/cymbal-agent-shared",
        REGULATORY_COMPLIANCE_AGENT: (
            "spiffe://cymbal.example.com/ns/pooled/sa/cymbal-agent-compliance"
        ),
    }
)

ROLE_ALLOWED_SCOPES: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "sre_admin": frozenset({"2lo:cymbal.telemetry.read", "3lo:jira.incidents.write"}),
        "compliance_officer": frozenset({"2lo:cymbal.telemetry.read"}),
        "read_only_analyst": frozenset({"2lo:cymbal.telemetry.read"}),
    }
)

ROLE_ALLOWED_TOOLS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        "sre_admin": frozenset(
            {
                "query_telemetry",
                "execute_diagnostic_sandbox",
                "create_jira_incident",
                "update_incident_status",
                "query_compliance_audit",
            }
        ),
        "compliance_officer": frozenset({"query_telemetry", "query_compliance_audit"}),
        "read_only_analyst": frozenset({"query_telemetry"}),
    }
)

AGENT_ALLOWED_TOOLS: Mapping[str, frozenset[str]] = MappingProxyType(
    {
        SHARED_DIAGNOSTIC_AGENT: frozenset(
            {
                "query_telemetry",
                "execute_diagnostic_sandbox",
                "create_jira_incident",
                "update_incident_status",
            }
        ),
        REGULATORY_COMPLIANCE_AGENT: frozenset({"query_telemetry", "query_compliance_audit"}),
    }
)


class TenantEvictionHook(Protocol):
    """Protocol implemented by stateful components that support offboarding eviction."""

    def evict_tenant(self, tenant_id: str) -> None:
        """Purges cached state and credentials for an offboarded tenant."""


@dataclass(frozen=True)
class TenantPolicy:
    """Configuration record for one pooled tenant.

    Attributes:
      tenant_id: Unique tenant identifier bound 1:1 to an OIDC issuer.
      display_name: Human-readable tenant organization name.
      tier: Subscription tier (`enterprise` or `standard`).
      oidc_issuer: Corporate OIDC issuer URL.
      oidc_audience: Expected OIDC audience claim.
      service_account_email: Dedicated per-tenant Google Cloud service account.
      kms_key_name: Dedicated per-tenant Cloud KMS CMEK resource name.
      region: Enforced regional residency lock.
      memory_bank_instance: Target pooled or dedicated Memory Bank resource path.
      entitled_agents: Catalog agent identifiers allowed for this tenant.
      rpm_limit: Maximum requests per minute for this tenant.
      tpm_limit: Maximum tokens per minute for this tenant.
      thinking_budget_tokens: Upper bound on per-turn model thinking tokens.
      group_to_role: Mapping from corporate IdP group names to internal roles.
    """

    tenant_id: str
    display_name: str
    tier: str
    oidc_issuer: str
    oidc_audience: str
    service_account_email: str
    kms_key_name: str
    region: str
    memory_bank_instance: str
    entitled_agents: frozenset[str]
    rpm_limit: int
    tpm_limit: int
    thinking_budget_tokens: int
    group_to_role: Mapping[str, str] = field(default_factory=lambda: MappingProxyType({}))


DEFAULT_TENANT_POLICIES: Mapping[str, TenantPolicy] = MappingProxyType(
    {
        "tenant-finvault-alpha": TenantPolicy(
            tenant_id="tenant-finvault-alpha",
            display_name="FinVault Bank",
            tier="enterprise",
            oidc_issuer="https://finvault.okta.com/oauth2/default",
            oidc_audience="cymbal-cloudops-api",
            service_account_email="ct-finvault@cymbal-multitenancy-example.iam.gserviceaccount.com",
            kms_key_name=(
                "projects/cymbal-multitenancy-example/locations/us-central1/"
                "keyRings/cymbal-tenants/cryptoKeys/tenant-finvault-alpha"
            ),
            region="us-central1",
            memory_bank_instance=(
                "projects/cymbal-multitenancy-example/locations/us-central1/memoryBanks/pooled-us"
            ),
            entitled_agents=frozenset({SHARED_DIAGNOSTIC_AGENT, REGULATORY_COMPLIANCE_AGENT}),
            rpm_limit=120,
            tpm_limit=120_000,
            thinking_budget_tokens=4096,
            group_to_role=MappingProxyType(
                {
                    "finvault-sre-admins": "sre_admin",
                    "finvault-compliance": "compliance_officer",
                    "finvault-analysts": "read_only_analyst",
                }
            ),
        ),
        "tenant-retailstream-beta": TenantPolicy(
            tenant_id="tenant-retailstream-beta",
            display_name="RetailStream",
            tier="standard",
            oidc_issuer="https://login.microsoftonline.com/retailstream-tenant/v2.0",
            oidc_audience="cymbal-cloudops-api",
            service_account_email=(
                "ct-retailstream@cymbal-multitenancy-example.iam.gserviceaccount.com"
            ),
            kms_key_name=(
                "projects/cymbal-multitenancy-example/locations/us-central1/"
                "keyRings/cymbal-tenants/cryptoKeys/tenant-retailstream-beta"
            ),
            region="us-central1",
            memory_bank_instance=(
                "projects/cymbal-multitenancy-example/locations/us-central1/memoryBanks/pooled-us"
            ),
            entitled_agents=frozenset({SHARED_DIAGNOSTIC_AGENT}),
            rpm_limit=30,
            tpm_limit=30_000,
            thinking_budget_tokens=1024,
            group_to_role=MappingProxyType(
                {
                    "retailstream-sre": "sre_admin",
                    "retailstream-analysts": "read_only_analyst",
                }
            ),
        ),
        "tenant-eurobank-gamma": TenantPolicy(
            tenant_id="tenant-eurobank-gamma",
            display_name="EuroBank GmbH",
            tier="enterprise",
            oidc_issuer="https://eurobank.okta.eu/oauth2/default",
            oidc_audience="cymbal-cloudops-api",
            service_account_email="ct-eurobank@cymbal-multitenancy-example.iam.gserviceaccount.com",
            kms_key_name=(
                "projects/cymbal-multitenancy-example/locations/europe-west3/"
                "keyRings/cymbal-tenants/cryptoKeys/tenant-eurobank-gamma"
            ),
            region="europe-west3",
            memory_bank_instance=(
                "projects/cymbal-multitenancy-example/locations/europe-west3/"
                "memoryBanks/dedicated-eurobank"
            ),
            entitled_agents=frozenset({SHARED_DIAGNOSTIC_AGENT, REGULATORY_COMPLIANCE_AGENT}),
            rpm_limit=120,
            tpm_limit=120_000,
            thinking_budget_tokens=4096,
            group_to_role=MappingProxyType(
                {
                    "eurobank-sre": "sre_admin",
                    "eurobank-compliance": "compliance_officer",
                }
            ),
        ),
    }
)


class TenantDirectory:
    """Authoritative tenant policy directory with immediate revocation hooks."""

    def __init__(self, policies: Mapping[str, TenantPolicy] | None = None) -> None:
        """Initializes the directory with tenant policies and eviction hooks.

        Args:
          policies: Optional custom mapping from tenant_id to TenantPolicy. When
            None, loads DEFAULT_TENANT_POLICIES.
        """
        self._policies: dict[str, TenantPolicy] = dict(
            policies if policies is not None else DEFAULT_TENANT_POLICIES
        )
        self._revoked_tenants: set[str] = set()
        self._eviction_hooks: list[TenantEvictionHook] = []

    def register_eviction_hook(self, hook: TenantEvictionHook) -> None:
        """Registers a component to notify when a tenant is offboarded.

        Args:
          hook: Component implementing TenantEvictionHook.
        """
        self._eviction_hooks.append(hook)

    def get_policy_unfiltered(self, tenant_id: str) -> TenantPolicy | None:
        """Returns a TenantPolicy regardless of revocation status.

        Args:
          tenant_id: Tenant identifier to look up.

        Returns:
          The matching TenantPolicy, or None if tenant_id is unknown.
        """
        return self._policies.get(tenant_id)

    def get_active_policy(self, tenant_id: str) -> TenantPolicy:
        """Returns the active TenantPolicy for a non-revoked tenant.

        Args:
          tenant_id: Verified tenant identifier.

        Returns:
          The active TenantPolicy.

        Raises:
          PermissionError: If tenant_id is unknown or has been offboarded.
        """
        if tenant_id in self._revoked_tenants:
            raise PermissionError(f"Tenant '{tenant_id}' is offboarded/revoked.")
        policy = self._policies.get(tenant_id)
        if policy is None:
            raise PermissionError(f"Unknown tenant '{tenant_id}'.")
        return policy

    def resolve_by_issuer(self, issuer: str) -> TenantPolicy:
        """Resolves the unique active tenant bound 1:1 to an OIDC issuer.

        Args:
          issuer: Verified OIDC issuer URL from the corporate IdP token.

        Returns:
          The active TenantPolicy bound to issuer.

        Raises:
          PermissionError: If no active tenant matches issuer.
        """
        for policy in self._policies.values():
            if policy.oidc_issuer == issuer:
                return self.get_active_policy(policy.tenant_id)
        raise PermissionError(f"Untrusted OIDC issuer '{issuer}'.")

    def offboard_tenant(self, tenant_id: str) -> None:
        """Revokes a tenant and triggers all registered eviction hooks.

        Args:
          tenant_id: Tenant identifier to revoke.
        """
        self._revoked_tenants.add(tenant_id)
        for hook in self._eviction_hooks:
            hook.evict_tenant(tenant_id)

    def is_revoked(self, tenant_id: str) -> bool:
        """Returns True if tenant_id has been offboarded."""
        return tenant_id in self._revoked_tenants
