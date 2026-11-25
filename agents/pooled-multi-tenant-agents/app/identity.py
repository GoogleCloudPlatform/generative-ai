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
"""Identity, Ingress Gateway, RFC 9449 DPoP, ctx+jwt, and Vault broker."""

import base64
import hashlib
import json
import time
import uuid
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

import jwt
from cryptography.hazmat.primitives.asymmetric import ec

from app import config

CONTEXT_TOKEN_TYPE = "ctx+jwt"
CONTEXT_TOKEN_ISSUER = "cymbal-ingress-gateway"
CONTEXT_TOKEN_AUDIENCE = "cymbal-agent-runtime"
MAX_CONTEXT_TOKEN_TTL_SECONDS = 300

UNTRUSTED_IDENTITY_HEADERS = frozenset(
    {"x-tenant-id", "x-user-id", "x-user-role", "x-agent-id", "x-cymbal-tenant"}
)


def sanitize_inbound_headers(headers: Mapping[str, str]) -> dict[str, str]:
    """Strips untrusted caller-supplied identity headers and normalizes keys.

    Args:
      headers: Raw inbound HTTP header mapping.

    Returns:
      Lowercase-keyed dictionary with spoofable tenant/user/agent headers removed.
    """
    return {
        header_name.lower(): header_value
        for header_name, header_value in headers.items()
        if header_name.lower() not in UNTRUSTED_IDENTITY_HEADERS
    }


def compute_jwk_thumbprint(public_jwk: Mapping[str, str]) -> str:
    """Computes the RFC 7638 SHA-256 JWK thumbprint for an EC P-256 public key.

    Args:
      public_jwk: Public JWK dictionary with `crv`, `kty`, `x`, and `y`.

    Returns:
      Base64url-encoded SHA-256 thumbprint without padding.
    """
    canonical = json.dumps(
        {
            "crv": public_jwk["crv"],
            "kty": public_jwk["kty"],
            "x": public_jwk["x"],
            "y": public_jwk["y"],
        },
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return base64.urlsafe_b64encode(hashlib.sha256(canonical).digest()).rstrip(b"=").decode("ascii")


def create_dpop_proof(
    private_key: ec.EllipticCurvePrivateKey,
    *,
    http_method: str,
    http_uri: str,
    access_token: str | None = None,
    jti: str | None = None,
    iat: int | None = None,
) -> str:
    """Creates an ES256 RFC 9449 DPoP proof JWT for a client request.

    Args:
      private_key: Client's ephemeral EC P-256 private key.
      http_method: HTTP method (for example, `POST`).
      http_uri: Target URL without query string or fragment.
      access_token: Optional gateway access token for `ath` binding; omitted
        during initial token exchange.
      jti: Optional explicit proof ID; generated with UUID4 when None.
      iat: Optional issued-at epoch seconds; uses current wall clock when None.

    Returns:
      Compact ES256 DPoP proof JWT string.
    """
    public_jwk = json.loads(jwt.algorithms.ECAlgorithm.to_jwk(private_key.public_key()))
    payload: dict[str, object] = {
        "htm": http_method.upper(),
        "htu": http_uri,
        "iat": int(time.time()) if iat is None else iat,
        "jti": jti or str(uuid.uuid4()),
    }
    if access_token is not None:
        digest = hashlib.sha256(access_token.encode("ascii")).digest()
        payload["ath"] = base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")
    return jwt.encode(
        payload,
        private_key,
        algorithm="ES256",
        headers={"typ": "dpop+jwt", "jwk": public_jwk},
    )


class DPoPVerifier:
    """Verifies RFC 9449 EC P-256 DPoP proofs with single-use replay protection."""

    def __init__(self, max_age_seconds: int = 60, clock: Callable[[], float] = time.time) -> None:
        """Initializes the verifier with a bounded replay cache.

        Args:
          max_age_seconds: Maximum allowed age of a DPoP proof `iat` claim.
          clock: Injectable wall-clock function returning epoch seconds.
        """
        self._max_age_seconds = max_age_seconds
        self._clock = clock
        self._seen_jtis: dict[str, float] = {}

    def verify_proof(
        self,
        proof_jwt: str,
        *,
        expected_method: str,
        expected_uri: str,
        expected_jkt: str | None = None,
        access_token: str | None = None,
    ) -> str:
        """Verifies a DPoP proof and returns its RFC 7638 JWK thumbprint.

        Args:
          proof_jwt: Raw `DPoP` header value.
          expected_method: Expected HTTP method (`htm`).
          expected_uri: Expected HTTP URI (`htu`).
          expected_jkt: Optional expected `cnf.jkt` thumbprint; skipped when None.
          access_token: Optional access token for `ath` verification; skipped when
            None.

        Returns:
          Verified RFC 7638 JWK thumbprint.

        Raises:
          PermissionError: If the proof is malformed, invalid, mismatched, or
            replayed.
        """
        try:
            header = jwt.get_unverified_header(proof_jwt)
        except jwt.PyJWTError as exc:
            raise PermissionError("Malformed DPoP proof header.") from exc

        if header.get("typ") != "dpop+jwt" or header.get("alg") != "ES256":
            raise PermissionError("DPoP proof must use ES256 and typ='dpop+jwt'.")

        public_jwk = header.get("jwk")
        if (
            not isinstance(public_jwk, dict)
            or public_jwk.get("kty") != "EC"
            or public_jwk.get("crv") != "P-256"
        ):
            raise PermissionError("DPoP header must contain an EC P-256 public JWK.")
        if "d" in public_jwk:
            raise PermissionError("DPoP JWK must not contain private key material.")

        try:
            public_key = jwt.algorithms.ECAlgorithm.from_jwk(json.dumps(public_jwk))
            claims = jwt.decode(
                proof_jwt,
                public_key,
                algorithms=["ES256"],
                options={"require": ["htm", "htu", "iat", "jti"]},
            )
            issued_at = float(claims["iat"])
            key_thumbprint = compute_jwk_thumbprint(public_jwk)
        except (jwt.PyJWTError, ValueError, TypeError, KeyError) as exc:
            raise PermissionError(f"Invalid DPoP proof: {exc}") from exc

        if str(claims["htm"]).upper() != expected_method.upper():
            raise PermissionError("DPoP HTTP method mismatch.")
        if str(claims["htu"]) != expected_uri:
            raise PermissionError("DPoP HTTP URI mismatch.")

        now = self._clock()
        if abs(now - issued_at) > self._max_age_seconds:
            raise PermissionError("DPoP proof outside allowed clock window.")

        if expected_jkt is not None and key_thumbprint != expected_jkt:
            raise PermissionError("DPoP key thumbprint does not match token binding.")

        if access_token is not None:
            expected_access_token_hash = (
                base64.urlsafe_b64encode(hashlib.sha256(access_token.encode("ascii")).digest())
                .rstrip(b"=")
                .decode("ascii")
            )
            if claims.get("ath") != expected_access_token_hash:
                raise PermissionError("DPoP access token hash mismatch.")

        expired_jtis = [
            seen_jti
            for seen_jti, recorded_at in self._seen_jtis.items()
            if now - recorded_at > self._max_age_seconds
        ]
        for expired_jti in expired_jtis:
            del self._seen_jtis[expired_jti]

        proof_jti = str(claims["jti"])
        if proof_jti in self._seen_jtis:
            raise PermissionError("DPoP proof replay detected.")
        self._seen_jtis[proof_jti] = now
        return key_thumbprint


@dataclass(frozen=True)
class VerifiedContext:
    """Cryptographically verified Tenant ∩ User ∩ Agent identity envelope.

    Attributes:
      tenant_id: Verified tenant identifier.
      user_id: Verified user subject.
      user_role: Mapped intra-tenant RBAC role.
      agent_id: Entitled catalog agent identifier.
      lob: Line-of-business scope label.
      scopes: Granted 2LO and 3LO capability scopes.
      jti: Unique JWT identifier.
      exp: Expiration epoch timestamp in seconds.
    """

    tenant_id: str
    user_id: str
    user_role: str
    agent_id: str
    lob: str
    scopes: tuple[str, ...]
    jti: str
    exp: int


class ContextTokenSigner:
    """Signs short-lived ES256 `ctx+jwt` tokens inside the Ingress Gateway."""

    def __init__(
        self,
        private_key: ec.EllipticCurvePrivateKey | None = None,
        key_id: str = "kms-p256-v1",
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initializes the signer with an EC P-256 private key.

        Args:
          private_key: Optional EC P-256 private key; generated when None.
          key_id: Key identifier written into the JWT `kid` header.
          clock: Injectable wall-clock function returning epoch seconds.
        """
        self._private_key = private_key or ec.generate_private_key(ec.SECP256R1())
        self._key_id = key_id
        self._clock = clock

    @property
    def key_id(self) -> str:
        """Active signing key identifier."""
        return self._key_id

    @property
    def public_key(self) -> ec.EllipticCurvePublicKey:
        """Public key exported for verification-only downstream services."""
        return self._private_key.public_key()

    def sign(
        self,
        *,
        tenant_id: str,
        user_id: str,
        user_role: str,
        agent_id: str,
        lob: str,
        scopes: Sequence[str],
        ttl_seconds: int = MAX_CONTEXT_TOKEN_TTL_SECONDS,
    ) -> str:
        """Mints a short-lived ES256 `ctx+jwt` envelope.

        Args:
          tenant_id: Verified tenant identifier.
          user_id: Verified user subject.
          user_role: Mapped intra-tenant RBAC role.
          agent_id: Entitled catalog agent identifier.
          lob: Line-of-business scope label.
          scopes: Granted capability scopes.
          ttl_seconds: Requested TTL, clamped to MAX_CONTEXT_TOKEN_TTL_SECONDS.

        Returns:
          Compact ES256-signed JWT string.
        """
        now = int(self._clock())
        clamped_ttl = max(1, min(ttl_seconds, MAX_CONTEXT_TOKEN_TTL_SECONDS))
        payload = {
            "iss": CONTEXT_TOKEN_ISSUER,
            "aud": CONTEXT_TOKEN_AUDIENCE,
            "sub": user_id,
            "tenant_id": tenant_id,
            "user_role": user_role,
            "agent_id": agent_id,
            "lob": lob,
            "scope": list(scopes),
            "iat": now,
            "exp": now + clamped_ttl,
            "jti": str(uuid.uuid4()),
        }
        return jwt.encode(
            payload,
            self._private_key,
            algorithm="ES256",
            headers={"typ": CONTEXT_TOKEN_TYPE, "kid": self._key_id},
        )


class ContextTokenVerifier:
    """Public-key-only `ctx+jwt` verifier used by downstream services."""

    def __init__(
        self,
        public_keys: Mapping[str, ec.EllipticCurvePublicKey],
        revoked_check: Callable[[str], bool] | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initializes the verifier with trusted public keys only.

        Args:
          public_keys: Mapping from `kid` to EC P-256 public key.
          revoked_check: Optional callback returning True if a tenant is revoked;
            revocation checks are skipped when None.
          clock: Injectable wall-clock function returning epoch seconds.
        """
        self._public_keys = dict(public_keys)
        self._revoked_check = revoked_check
        self._clock = clock

    def verify(self, token: str) -> VerifiedContext:
        """Verifies ES256 signature, `typ`, claims, expiry, and revocation.

        Args:
          token: Compact JWT string received from the Ingress Gateway.

        Returns:
          VerifiedContext with immutable identity claims.

        Raises:
          PermissionError: If signature, header, expiry, or revocation fails.
        """
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise PermissionError("Malformed context token header.") from exc

        if header.get("alg") != "ES256" or header.get("typ") != CONTEXT_TOKEN_TYPE:
            raise PermissionError("Context token must use ES256 and typ='ctx+jwt'.")

        key_id = header.get("kid")
        public_key = self._public_keys.get(key_id) if isinstance(key_id, str) else None
        if public_key is None:
            raise PermissionError(f"Unknown context token key id '{key_id}'.")

        try:
            claims = jwt.decode(
                token,
                public_key,
                algorithms=["ES256"],
                audience=CONTEXT_TOKEN_AUDIENCE,
                issuer=CONTEXT_TOKEN_ISSUER,
                options={"require": ["sub", "tenant_id", "user_role", "agent_id", "exp", "jti"]},
                leeway=0,
            )
        except jwt.PyJWTError as exc:
            raise PermissionError(f"Invalid context token: {exc}") from exc

        if int(claims["exp"]) <= int(self._clock()):
            raise PermissionError("Context token expired.")

        tenant_id = str(claims["tenant_id"])
        if self._revoked_check is not None and self._revoked_check(tenant_id):
            raise PermissionError(f"Tenant '{tenant_id}' has been revoked.")

        raw_scopes = claims.get("scope", [])
        scopes = tuple(str(item) for item in raw_scopes) if isinstance(raw_scopes, list) else ()
        return VerifiedContext(
            tenant_id=tenant_id,
            user_id=str(claims["sub"]),
            user_role=str(claims["user_role"]),
            agent_id=str(claims["agent_id"]),
            lob=str(claims.get("lob", "default")),
            scopes=scopes,
            jti=str(claims["jti"]),
            exp=int(claims["exp"]),
        )


@dataclass(frozen=True)
class GatewaySessionToken:
    """Short-lived DPoP-bound token issued after corporate SSO exchange.

    Attributes:
      access_token: Compact ES256 gateway access token (`typ=at+jwt`).
      tenant_id: Verified tenant identifier.
      user_id: Verified user subject.
      user_role: Mapped intra-tenant role.
      lob: Line-of-business label.
      jkt: Bound RFC 7638 client DPoP key thumbprint.
      expires_at: Expiration epoch timestamp in seconds.
    """

    access_token: str
    tenant_id: str
    user_id: str
    user_role: str
    lob: str
    jkt: str
    expires_at: int


class IngressGateway:
    """Pooled Ingress Gateway enforcing issuer-bound SSO, DPoP, and `ctx+jwt`."""

    def __init__(
        self,
        tenant_directory: config.TenantDirectory,
        context_signer: ContextTokenSigner,
        idp_public_keys: Mapping[str, ec.EllipticCurvePublicKey],
        dpop_verifier: DPoPVerifier | None = None,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initializes the Ingress Gateway.

        Args:
          tenant_directory: Authoritative TenantDirectory with revocation state.
          context_signer: Gateway-only ES256 `ctx+jwt` signer.
          idp_public_keys: Mapping from corporate OIDC issuer URL to public key.
          dpop_verifier: Optional DPoPVerifier; creates a default instance when
            None.
          clock: Injectable wall-clock function returning epoch seconds.
        """
        self._directory = tenant_directory
        self._context_signer = context_signer
        self._idp_public_keys = dict(idp_public_keys)
        self._dpop = dpop_verifier or DPoPVerifier(clock=clock)
        self._clock = clock
        self._gateway_key = ec.generate_private_key(ec.SECP256R1())

    def exchange_idp_token(
        self,
        *,
        idp_jwt: str,
        dpop_proof: str,
        http_uri: str,
        claimed_tenant_id: str | None = None,
    ) -> GatewaySessionToken:
        """Validates a corporate IdP OIDC token and mints a DPoP-bound token.

        Args:
          idp_jwt: Signed OIDC token from the tenant's corporate IdP.
          dpop_proof: Client's RFC 9449 DPoP proof for the exchange endpoint.
          http_uri: Exchange endpoint URI (`htu`).
          claimed_tenant_id: Optional caller-supplied tenant ID; rejected if it
            conflicts with the issuer-bound tenant.

        Returns:
          GatewaySessionToken bound to the client's DPoP key thumbprint.

        Raises:
          PermissionError: If issuer, signature, role mapping, tenant claim, or
            DPoP verification fails.
        """
        try:
            unverified = jwt.decode(idp_jwt, options={"verify_signature": False})
        except jwt.PyJWTError as exc:
            raise PermissionError("Malformed IdP token.") from exc

        issuer = str(unverified.get("iss", ""))
        policy = self._directory.resolve_by_issuer(issuer)
        idp_public_key = self._idp_public_keys.get(issuer)
        if idp_public_key is None:
            raise PermissionError(f"No verification key configured for issuer '{issuer}'.")

        try:
            claims = jwt.decode(
                idp_jwt,
                idp_public_key,
                algorithms=["ES256"],
                audience=policy.oidc_audience,
                issuer=policy.oidc_issuer,
                options={"require": ["sub", "iss", "aud", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise PermissionError(f"IdP token signature verification failed: {exc}") from exc

        if claimed_tenant_id is not None and claimed_tenant_id != policy.tenant_id:
            raise PermissionError(
                f"Caller tenant '{claimed_tenant_id}' conflicts with verified issuer tenant "
                f"'{policy.tenant_id}'."
            )

        groups = claims.get("groups", [])
        mapped_role = None
        if isinstance(groups, list):
            for group in groups:
                if str(group) in policy.group_to_role:
                    mapped_role = policy.group_to_role[str(group)]
                    break
        if mapped_role is None:
            raise PermissionError("No corporate IdP group maps to an authorized tenant role.")

        key_thumbprint = self._dpop.verify_proof(
            dpop_proof,
            expected_method="POST",
            expected_uri=http_uri,
        )
        now = int(self._clock())
        expires_at = now + 900
        lob = str(claims.get("lob", "core_ops"))
        gateway_payload = {
            "iss": CONTEXT_TOKEN_ISSUER,
            "aud": "cymbal-gateway-api",
            "sub": str(claims["sub"]),
            "tenant_id": policy.tenant_id,
            "user_role": mapped_role,
            "lob": lob,
            "cnf": {"jkt": key_thumbprint},
            "iat": now,
            "exp": expires_at,
            "jti": str(uuid.uuid4()),
        }
        access_token = jwt.encode(
            gateway_payload,
            self._gateway_key,
            algorithm="ES256",
            headers={"typ": "at+jwt"},
        )
        return GatewaySessionToken(
            access_token=access_token,
            tenant_id=policy.tenant_id,
            user_id=str(claims["sub"]),
            user_role=mapped_role,
            lob=lob,
            jkt=key_thumbprint,
            expires_at=expires_at,
        )

    def authorize_and_mint_context_token(
        self,
        *,
        gateway_access_token: str,
        dpop_proof: str,
        http_method: str,
        http_uri: str,
        agent_id: str,
        requested_scopes: Sequence[str] = ("2lo:cymbal.telemetry.read",),
    ) -> str:
        """Verifies gateway token and DPoP proof, intersects scopes, and signs `ctx+jwt`.

        Args:
          gateway_access_token: DPoP-bound access token (`typ=at+jwt`).
          dpop_proof: Single-use DPoP proof bound to this request.
          http_method: Request HTTP method.
          http_uri: Request HTTP URI.
          agent_id: Target catalog agent identifier.
          requested_scopes: Requested capability scopes to intersect with role
            entitlements.

        Returns:
          ES256-signed short-lived `ctx+jwt` string.

        Raises:
          PermissionError: If token, DPoP binding, tenant status, or agent
            entitlement checks fail.
        """
        try:
            header = jwt.get_unverified_header(gateway_access_token)
            if header.get("typ") != "at+jwt":
                raise PermissionError("Gateway access token must use typ='at+jwt'.")
            claims = jwt.decode(
                gateway_access_token,
                self._gateway_key.public_key(),
                algorithms=["ES256"],
                audience="cymbal-gateway-api",
                issuer=CONTEXT_TOKEN_ISSUER,
                options={"require": ["sub", "tenant_id", "user_role", "cnf", "exp"]},
            )
        except jwt.PyJWTError as exc:
            raise PermissionError(f"Invalid gateway access token: {exc}") from exc

        confirmation_claim = claims.get("cnf")
        expected_jkt = (
            confirmation_claim.get("jkt") if isinstance(confirmation_claim, dict) else None
        )
        if not isinstance(expected_jkt, str):
            raise PermissionError("Gateway token missing DPoP cnf.jkt binding.")

        self._dpop.verify_proof(
            dpop_proof,
            expected_method=http_method,
            expected_uri=http_uri,
            expected_jkt=expected_jkt,
            access_token=gateway_access_token,
        )

        tenant_id = str(claims["tenant_id"])
        policy = self._directory.get_active_policy(tenant_id)
        if agent_id not in policy.entitled_agents:
            raise PermissionError(
                f"Tenant '{tenant_id}' ({policy.tier} tier) is not entitled to agent '{agent_id}'."
            )

        user_role = str(claims["user_role"])
        allowed_scopes = config.ROLE_ALLOWED_SCOPES.get(user_role, frozenset())
        granted_scopes = tuple(scope for scope in requested_scopes if scope in allowed_scopes)
        return self._context_signer.sign(
            tenant_id=tenant_id,
            user_id=str(claims["sub"]),
            user_role=user_role,
            agent_id=agent_id,
            lob=str(claims.get("lob", "core_ops")),
            scopes=granted_scopes,
        )


@dataclass(frozen=True)
class BrokeredCloudToken:
    """Short-lived 2LO Google Cloud token scoped to one tenant service account.

    Attributes:
      access_token: Opaque 2LO bearer token handle.
      service_account_email: Impersonated per-tenant service account email.
      kms_key_name: Tenant Cloud KMS CMEK resource name.
      tenant_id: Verified tenant identifier.
      scope: Granted 2LO capability scope.
      expires_at: Expiration epoch timestamp in seconds.
    """

    access_token: str
    service_account_email: str
    kms_key_name: str
    tenant_id: str
    scope: str
    expires_at: float


@dataclass(frozen=True)
class UserOAuthGrant:
    """User-bound 3LO external SaaS OAuth grant stored inside the broker.

    Attributes:
      tenant_id: Tenant identifier owning this grant partition.
      user_id: Consented user subject.
      provider: External SaaS provider name (for example, `jira`).
      scope: Granted 3LO OAuth scope.
      token_value: Opaque delegated token handle.
    """

    tenant_id: str
    user_id: str
    provider: str
    scope: str
    token_value: str


class VaultCredentialBroker:
    """Out-of-process credential broker enforcing Tenant ∩ User ∩ Agent."""

    def __init__(
        self,
        tenant_directory: config.TenantDirectory,
        context_verifier: ContextTokenVerifier,
        token_ttl_seconds: int = 300,
        clock: Callable[[], float] = time.time,
    ) -> None:
        """Initializes the broker and registers it for offboarding eviction.

        Args:
          tenant_directory: Authoritative TenantDirectory.
          context_verifier: Public-key-only `ctx+jwt` verifier.
          token_ttl_seconds: Lifetime for brokered 2LO tokens.
          clock: Injectable wall-clock function returning epoch seconds.
        """
        self._directory = tenant_directory
        self._verifier = context_verifier
        self._token_ttl_seconds = token_ttl_seconds
        self._clock = clock
        self._cloud_token_cache: dict[tuple[str, str, str], BrokeredCloudToken] = {}
        self._user_oauth_vault: dict[tuple[str, str, str, str], UserOAuthGrant] = {}
        self._directory.register_eviction_hook(self)

    def register_user_3lo_grant(self, grant: UserOAuthGrant) -> None:
        """Stores a user-consented 3LO grant partitioned by tenant and user.

        Args:
          grant: UserOAuthGrant to store.
        """
        self._user_oauth_vault[(grant.tenant_id, grant.user_id, grant.provider, grant.scope)] = (
            grant
        )

    def evict_tenant(self, tenant_id: str) -> None:
        """Purges all cached 2LO tokens and 3LO grants for an offboarded tenant.

        Args:
          tenant_id: Offboarded tenant identifier.
        """
        self._cloud_token_cache = {
            key: value for key, value in self._cloud_token_cache.items() if key[0] != tenant_id
        }
        self._user_oauth_vault = {
            key: value for key, value in self._user_oauth_vault.items() if key[0] != tenant_id
        }

    def mint_2lo_cloud_token(
        self,
        *,
        context_token: str,
        caller_spiffe_id: str,
        required_scope: str = "2lo:cymbal.telemetry.read",
    ) -> BrokeredCloudToken:
        """Mints or returns a cached short-lived 2LO per-tenant cloud token.

        Args:
          context_token: Gateway-signed `ctx+jwt`.
          caller_spiffe_id: Calling workload SPIFFE mTLS identity.
          required_scope: Required 2LO capability scope.

        Returns:
          BrokeredCloudToken scoped to the tenant's service account and KMS key.

        Raises:
          PermissionError: If any of the three identity layers fails.
        """
        verified = self._verify_three_layer_lock(context_token, caller_spiffe_id, required_scope)
        policy = self._directory.get_active_policy(verified.tenant_id)
        cache_key = (verified.tenant_id, verified.agent_id, required_scope)
        now = self._clock()
        cached = self._cloud_token_cache.get(cache_key)
        if cached is not None and cached.expires_at > now + 15:
            return cached

        digest = hashlib.sha256(
            f"{policy.service_account_email}:{verified.agent_id}:{required_scope}:{int(now)}".encode()
        ).hexdigest()[:24]
        brokered = BrokeredCloudToken(
            access_token=f"sts-2lo-{verified.tenant_id}-{digest}",
            service_account_email=policy.service_account_email,
            kms_key_name=policy.kms_key_name,
            tenant_id=verified.tenant_id,
            scope=required_scope,
            expires_at=now + self._token_ttl_seconds,
        )
        self._cloud_token_cache[cache_key] = brokered
        return brokered

    def checkout_3lo_saas_token(
        self,
        *,
        context_token: str,
        caller_spiffe_id: str,
        provider: str,
        required_scope: str,
    ) -> UserOAuthGrant:
        """Checks out a user-bound 3LO SaaS OAuth grant.

        Args:
          context_token: Gateway-signed `ctx+jwt`.
          caller_spiffe_id: Calling workload SPIFFE mTLS identity.
          provider: External SaaS provider name.
          required_scope: Required 3LO scope.

        Returns:
          The caller's matching UserOAuthGrant.

        Raises:
          PermissionError: If identity checks fail or no matching grant exists.
        """
        verified = self._verify_three_layer_lock(context_token, caller_spiffe_id, required_scope)
        key = (verified.tenant_id, verified.user_id, provider, required_scope)
        grant = self._user_oauth_vault.get(key)
        if grant is None:
            raise PermissionError(
                f"No 3LO '{provider}' grant for user '{verified.user_id}' in tenant "
                f"'{verified.tenant_id}' with scope '{required_scope}'."
            )
        return grant

    def _verify_three_layer_lock(
        self, context_token: str, caller_spiffe_id: str, required_scope: str
    ) -> VerifiedContext:
        """Verifies Tenant ∩ User ∩ Agent before any cache lookup or minting."""
        verified = self._verifier.verify(context_token)
        policy = self._directory.get_active_policy(verified.tenant_id)
        if verified.agent_id not in policy.entitled_agents:
            raise PermissionError(
                f"Agent '{verified.agent_id}' is not entitled for tenant '{verified.tenant_id}'."
            )
        expected_spiffe = config.AGENT_SPIFFE_IDS.get(verified.agent_id)
        if expected_spiffe is None or caller_spiffe_id != expected_spiffe:
            raise PermissionError(
                f"Layer 3 workload identity mismatch: caller '{caller_spiffe_id}' "
                f"cannot impersonate agent '{verified.agent_id}'."
            )
        if required_scope not in verified.scopes:
            raise PermissionError(f"Context token lacks required scope '{required_scope}'.")
        return verified
