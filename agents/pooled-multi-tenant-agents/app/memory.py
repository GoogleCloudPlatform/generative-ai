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
"""CMEK AEAD session checkpoints and Memory Bank layered isolation controls."""

import hashlib
import hmac
import json
import os
import time
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app import config, egress, identity


def _build_session_aad(tenant_id: str, user_id: str, session_id: str, kms_key_name: str) -> bytes:
    """Builds AEAD associated data binding ciphertext to tenant, user, session, and key."""
    return f"{tenant_id}|{user_id}|{session_id}|{kms_key_name}".encode()


def _session_partition_key(tenant_id: str, user_id: str, session_id: str) -> str:
    """Returns the `{tenant_id}:{user_id}:{session_id}` document key."""
    return f"{tenant_id}:{user_id}:{session_id}"


def _validate_control1_scope(scope: Mapping[str, str]) -> tuple[tuple[str, str], ...]:
    """Rejects wildcards, empty values, or more than 5 scope keys (Control 1)."""
    if not scope or len(scope) > 5:
        raise PermissionError("Control 1 violation: Memory Bank scope must have 1 to 5 keys.")
    for key, value in scope.items():
        if not key or not value or "*" in value or "?" in value:
            raise PermissionError(
                f"Control 1 violation: wildcard or empty value rejected in scope key '{key}'."
            )
    return tuple(sorted(scope.items()))


class EncryptedSessionStore:
    """External stateless session store with per-tenant AEAD CMEK encryption."""

    def __init__(
        self,
        tenant_directory: config.TenantDirectory,
        guardrails: egress.EgressGuardrails | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initializes the local session store with a process-random master key.

        Args:
          tenant_directory: Authoritative TenantDirectory.
          guardrails: Optional EgressGuardrails for read-time screening; creates
            a default instance when None.
          clock: Injectable wall-clock function returning epoch seconds.
        """
        self._directory = tenant_directory
        self._guardrails = guardrails or egress.EgressGuardrails()
        self._clock = clock
        self._local_master_key = os.urandom(32)
        self._records: dict[str, tuple[bytes, bytes]] = {}
        self._disabled_kms_keys: set[str] = set()
        self._directory.register_eviction_hook(self)

    def is_kms_key_disabled(self, kms_key_name: str) -> bool:
        """Returns True if the tenant's KMS key has been disabled on offboarding."""
        return kms_key_name in self._disabled_kms_keys

    def save_turn(
        self,
        *,
        brokered_token: identity.BrokeredCloudToken,
        user_id: str,
        session_id: str,
        turns: Sequence[Mapping[str, str]],
    ) -> str:
        """Encrypts and checkpoints active session history under the tenant's CMEK.

        Args:
          brokered_token: Short-lived 2LO Google Cloud token from the broker.
          user_id: Verified user subject.
          session_id: Active conversation session identifier.
          turns: Sequence of role/content turn mappings.

        Returns:
          Partition key stored for the checkpoint.

        Raises:
          PermissionError: If the token is expired, the tenant is revoked, or
            the tenant's KMS key is disabled.
        """
        self._check_token_active(brokered_token)
        tenant_id = brokered_token.tenant_id
        dek = self._derive_tenant_dek(brokered_token.kms_key_name)
        nonce = os.urandom(12)
        aad = _build_session_aad(tenant_id, user_id, session_id, brokered_token.kms_key_name)
        plaintext = json.dumps([dict(turn) for turn in turns], separators=(",", ":")).encode(
            "utf-8"
        )
        ciphertext = AESGCM(dek).encrypt(nonce, plaintext, aad)
        doc_key = _session_partition_key(tenant_id, user_id, session_id)
        self._records[doc_key] = (nonce, ciphertext)
        return doc_key

    def load_turns(
        self,
        *,
        brokered_token: identity.BrokeredCloudToken,
        user_id: str,
        session_id: str,
    ) -> list[dict[str, str]]:
        """Decrypts and screens session history for the verified tenant and user.

        Args:
          brokered_token: Short-lived 2LO Google Cloud token from the broker.
          user_id: Verified user subject.
          session_id: Active conversation session identifier.

        Returns:
          Decrypted turn list, or an empty list for a new session.

        Raises:
          PermissionError: If the token is expired, the tenant is revoked, the
            KMS key is disabled, AEAD verification fails, or screening blocks
            stored text.
        """
        self._check_token_active(brokered_token)
        tenant_id = brokered_token.tenant_id
        doc_key = _session_partition_key(tenant_id, user_id, session_id)
        entry = self._records.get(doc_key)
        if entry is None:
            return []

        nonce, ciphertext = entry
        dek = self._derive_tenant_dek(brokered_token.kms_key_name)
        aad = _build_session_aad(tenant_id, user_id, session_id, brokered_token.kms_key_name)
        try:
            plaintext = AESGCM(dek).decrypt(nonce, ciphertext, aad).decode("utf-8")
        except InvalidTag as exc:
            raise PermissionError("Session AEAD integrity or key binding check failed.") from exc

        self._guardrails.screen_and_redact(plaintext)
        return list(json.loads(plaintext))

    def evict_tenant(self, tenant_id: str) -> None:
        """Disables the tenant's CMEK key and purges cached session records.

        Args:
          tenant_id: Offboarded tenant identifier.
        """
        prefix = f"{tenant_id}:"
        self._records = {
            key: value for key, value in self._records.items() if not key.startswith(prefix)
        }
        policy = self._directory.get_policy_unfiltered(tenant_id)
        if policy is not None:
            self._disabled_kms_keys.add(policy.kms_key_name)

    def _derive_tenant_dek(self, kms_key_name: str) -> bytes:
        """Derives a 256-bit DEK per KMS key via HMAC-SHA256 with the local master key."""
        if kms_key_name in self._disabled_kms_keys:
            raise PermissionError(f"Cloud KMS key '{kms_key_name}' is disabled.")
        return hmac.new(self._local_master_key, kms_key_name.encode(), hashlib.sha256).digest()

    def _check_token_active(self, brokered_token: identity.BrokeredCloudToken) -> None:
        """Rejects expired 2LO tokens and revoked tenants."""
        if brokered_token.expires_at <= self._clock():
            raise PermissionError("Brokered 2LO token has expired.")
        self._directory.get_active_policy(brokered_token.tenant_id)


@dataclass(frozen=True)
class MemoryRecord:
    """Single distilled semantic or episodic memory entry.

    Attributes:
      memory_id: Unique memory entry identifier.
      memory_bank_instance: Pooled or dedicated Memory Bank resource path.
      region: Google Cloud region holding this memory.
      scope: Sorted exact-match `(key, value)` scope tuples.
      fact: Distilled takeaway string.
    """

    memory_id: str
    memory_bank_instance: str
    region: str
    scope: tuple[tuple[str, str], ...]
    fact: str


class ScopedMemoryBank:
    """Local reference for Memory Bank enforcing Controls 1, 2, 3A, and 3B."""

    def __init__(
        self,
        tenant_directory: config.TenantDirectory,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initializes Memory Bank with synthetic prior incident recall.

        Args:
          tenant_directory: Authoritative TenantDirectory.
          clock: Injectable wall-clock function returning epoch seconds.
        """
        self._directory = tenant_directory
        self._clock = clock
        self._records: list[MemoryRecord] = [
            MemoryRecord(
                memory_id="mem-finvault-001",
                memory_bank_instance=(
                    "projects/cymbal-multitenancy-example/locations/us-central1/"
                    "memoryBanks/pooled-us"
                ),
                region="us-central1",
                scope=(
                    ("agent_id", "cymbal_shared_diagnostic_agent"),
                    ("lob", "retail_banking"),
                    ("tenant_id", "tenant-finvault-alpha"),
                    ("user_id", "priya@finvault.example.com"),
                ),
                fact=(
                    "Last month's payment-gateway outage was caused by AlloyDB connection-pool "
                    "exhaustion after a PgBouncer timeout change; Priya prefers Jira rollback "
                    "steps."
                ),
            ),
            MemoryRecord(
                memory_id="mem-retailstream-001",
                memory_bank_instance=(
                    "projects/cymbal-multitenancy-example/locations/us-central1/"
                    "memoryBanks/pooled-us"
                ),
                region="us-central1",
                scope=(
                    ("agent_id", "cymbal_shared_diagnostic_agent"),
                    ("lob", "ecommerce"),
                    ("tenant_id", "tenant-retailstream-beta"),
                    ("user_id", "alex@retailstream.example.com"),
                ),
                fact="Flash-sale Redis cluster requires read-replica pre-warming 30 minutes prior.",
            ),
        ]
        self._directory.register_eviction_hook(self)

    def retrieve(
        self,
        *,
        brokered_token: identity.BrokeredCloudToken,
        expected_agent_id: str,
        scope: Mapping[str, str],
        requested_region: str | None = None,
        top_k: int = 5,
    ) -> Sequence[MemoryRecord]:
        """Retrieves up to top_k memories matching the exact verified scope.

        Args:
          brokered_token: Short-lived 2LO token from the credential broker.
          expected_agent_id: Verified `agent_id` from `ctx+jwt`.
          scope: Exact-match scope mapping built from verified claims.
          requested_region: Optional region assertion; uses policy region when
            None.
          top_k: Maximum number of records to return.

        Returns:
          Sequence of matching MemoryRecord entries.

        Raises:
          PermissionError: If token expiry or Controls 1-3A fail.
        """
        canonical_scope, region, instance = self._enforce_controls(
            brokered_token=brokered_token,
            scope=scope,
            expected_agent_id=expected_agent_id,
            requested_region=requested_region,
        )
        matches = [
            record
            for record in self._records
            if record.memory_bank_instance == instance
            and record.region == region
            and record.scope == canonical_scope
        ]
        return matches[:top_k]

    def consolidate(
        self,
        *,
        brokered_token: identity.BrokeredCloudToken,
        expected_agent_id: str,
        scope: Mapping[str, str],
        distilled_fact: str,
        requested_region: str | None = None,
    ) -> MemoryRecord:
        """Consolidates a new distilled fact strictly inside the verified scope.

        Args:
          brokered_token: Short-lived 2LO token from the credential broker.
          expected_agent_id: Verified `agent_id` from `ctx+jwt`.
          scope: Exact-match scope mapping.
          distilled_fact: Compact takeaway string.
          requested_region: Optional region assertion; uses policy region when
            None.

        Returns:
          The persisted MemoryRecord.

        Raises:
          PermissionError: If token expiry or Controls 1-3A fail.
        """
        canonical_scope, region, instance = self._enforce_controls(
            brokered_token=brokered_token,
            scope=scope,
            expected_agent_id=expected_agent_id,
            requested_region=requested_region,
        )
        record = MemoryRecord(
            memory_id=f"mem-{brokered_token.tenant_id[:10]}-{len(self._records) + 1:03d}",
            memory_bank_instance=instance,
            region=region,
            scope=canonical_scope,
            fact=distilled_fact,
        )
        self._records.append(record)
        return record

    def evict_tenant(self, tenant_id: str) -> None:
        """Purges memories for an offboarded tenant.

        Args:
          tenant_id: Offboarded tenant identifier.
        """
        self._records = [
            record for record in self._records if dict(record.scope).get("tenant_id") != tenant_id
        ]

    def _enforce_controls(
        self,
        *,
        brokered_token: identity.BrokeredCloudToken,
        scope: Mapping[str, str],
        expected_agent_id: str,
        requested_region: str | None,
    ) -> tuple[tuple[tuple[str, str], ...], str, str]:
        """Enforces token expiry, Control 1 scope, Control 2 IAM CEL, and Controls 3A/3B."""
        if brokered_token.expires_at <= self._clock():
            raise PermissionError("Brokered 2LO token has expired.")
        canonical_scope = _validate_control1_scope(scope)
        if scope.get("tenant_id") != brokered_token.tenant_id:
            raise PermissionError(
                "403 PERMISSION_DENIED (Control 2 IAM CEL): "
                f"Service account '{brokered_token.service_account_email}' cannot access "
                f"tenant_id='{scope.get('tenant_id')}'."
            )
        if scope.get("agent_id") != expected_agent_id:
            raise PermissionError(
                "403 PERMISSION_DENIED (Control 2 IAM CEL): "
                f"agent_id='{scope.get('agent_id')}' does not match verified agent "
                f"'{expected_agent_id}'."
            )
        policy = self._directory.get_active_policy(brokered_token.tenant_id)
        if requested_region is not None and requested_region != policy.region:
            raise PermissionError(
                f"403 PERMISSION_DENIED (Control 3A Residency): tenant '{brokered_token.tenant_id}' "
                f"is locked to region '{policy.region}', cannot access '{requested_region}'."
            )
        return canonical_scope, policy.region, policy.memory_bank_instance
