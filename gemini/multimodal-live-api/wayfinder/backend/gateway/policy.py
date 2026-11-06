# Copyright 2026 Google LLC
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

"""Access policy: API key + origin allowlist.

`evaluate()` is the single decision point for inbound connections, so it can
be replaced with a managed gateway later without touching the server.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from ..config import get_api_keys, get_auth_enabled, get_self_origin


@dataclass
class PolicyDecision:
    """Outcome of a policy check, with the resolved tenant when allowed."""

    allowed: bool
    reason: str
    tenant_id: str = ""
    metadata: dict = field(default_factory=dict)

    @classmethod
    def allow(cls, reason: str, tenant_id: str = "", **meta: object) -> PolicyDecision:
        """Builds an allowing decision for `tenant_id`."""
        return cls(allowed=True, reason=reason, tenant_id=tenant_id, metadata=meta)

    @classmethod
    def deny(cls, reason: str, **meta: object) -> PolicyDecision:
        """Builds a denying decision with a reason."""
        return cls(allowed=False, reason=reason, metadata=meta)


def evaluate(  # pylint: disable=too-many-return-statements  # one early return per rule
    origin: str, api_key: str | None
) -> PolicyDecision:
    """Decide whether an inbound request from `origin` is allowed.

    `origin` must be the hostname from the browser's `Origin` header (see
    `server.request_origin_host`), not a value the page claims.
    """
    if not get_auth_enabled():
        return PolicyDecision.allow("auth_disabled")

    self_origin = get_self_origin()
    if self_origin and origin == self_origin:
        return PolicyDecision.allow("same_origin")

    if not api_key:
        return PolicyDecision.deny("missing_api_key")

    key_config = get_api_keys().get(api_key)
    if not key_config:
        return PolicyDecision.deny("invalid_api_key")

    tenant_id = key_config.get("name", "")
    allowed_origins = key_config.get("origins", [])

    if "*" in allowed_origins:
        return PolicyDecision.allow("wildcard_origin", tenant_id=tenant_id)
    if origin in allowed_origins:
        return PolicyDecision.allow("origin_match", tenant_id=tenant_id)

    bare = origin[4:] if origin.startswith("www.") else None
    if bare and bare in allowed_origins:
        return PolicyDecision.allow("origin_match_bare", tenant_id=tenant_id)
    if not origin.startswith("www.") and ("www." + origin) in allowed_origins:
        return PolicyDecision.allow("origin_match_www", tenant_id=tenant_id)

    return PolicyDecision.deny("origin_not_allowed")
