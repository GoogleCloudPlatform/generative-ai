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
# pylint: disable=too-many-lines

"""Target Environment Server with Google Cloud Governance and Model Armor Ingress Shield."""

import asyncio
import importlib
import os
import threading
import time
import uuid
from collections.abc import AsyncIterator, Iterator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from pydantic import BaseModel, Field

from app.config import PROJECT_ID
from app.governance.audit_logger import CloudAuditLogger
from app.governance.kms_signer import CloudKmsSigner
from app.governance.model_armor import ModelArmorGuardrail
from app.governance.policy_controller import CloudPolicyController
from app.runtime_registry import register_platform_env
from app.target_env.cloud_telemetry import CloudTelemetryCollector
from app.target_env.cloudsql_service import CloudSqlDatabaseService
from app.target_env.memorystore_service import CloudMemorystoreService


class CheckoutRequest(BaseModel):
    """Request body for the governed /checkout endpoint."""

    cart_id: str = Field(..., json_schema_extra={"example": "cart_101"})
    items_count: int = Field(default=3, ge=1)
    customer_tier: str = Field(default="standard")
    auth_header: str | None = None


class TargetEnvironmentApp:  # pylint: disable=too-many-instance-attributes
    """Enterprise Target Infrastructure managed under Google Cloud Governance."""

    def __init__(self, project_id: str = PROJECT_ID):
        self.project_id = project_id
        self.cache = CloudMemorystoreService(max_keys=5)
        self.db = CloudSqlDatabaseService(max_connections=2, query_latency_ms=100.0)
        self.telemetry = CloudTelemetryCollector(
            cache_service=self.cache, db_service=self.db, project_id=project_id
        )

        # Governance & Security layers
        self.model_armor = ModelArmorGuardrail(project_id=project_id)
        self.kms_signer = CloudKmsSigner(project_id=project_id)
        self.policy_controller = CloudPolicyController()
        self.audit_logger = CloudAuditLogger(project_id=project_id)
        self._hitl_gate: Any | None = None
        self._principle_store: Any | None = None
        self._supervisor_runner: Any | None = None
        self._topology_mutator: Any | None = None
        # Guards lazy initialization (background warm-up thread vs. concurrent API requests)
        self._lazy_lock = threading.RLock()
        # Reset generation + lock: a long-running agent step that started before a reset must not
        # write its results (attach a limiter, publish a principle, rewire agents) after the reset.
        self._generation = 0
        self._state_lock = threading.RLock()

        # Dynamic patch reference (hotpatched by APEX Layer 1)
        # (TokenBucketRateLimiter / KmsSignatureEnvelope once attached, else None)
        self.rate_limiter: Any = None
        self.rate_limiter_signature: Any = None
        self.canary_enabled = False

        # Demo tracking state
        self.demo_state: dict[str, Any] = {
            "current_phase": 0,
            "status_message": "Ready: Baseline Infrastructure Nominal",
            "phase1": None,
            "phase2": None,
            "phase3": None,
            "phase4": None,
            "topology": ["SupervisorRouterAgent", "DiagnosticAgent"],
        }

        self.fastapi_app: FastAPI = FastAPI(
            title="Project Chrysalis: Agent Platform Environment",
            lifespan=self._lifespan,
        )
        self._register_routes()

    @asynccontextmanager
    async def _lifespan(self, _app: FastAPI) -> AsyncIterator[None]:
        """Server startup: pre-initialize lazily-loaded components in the background so the first
        UI click is fast (ADK agent graph, Agent Platform embedding client + seeded principle store,
        KMS key probe).
        """

        def _warm() -> None:
            try:
                importlib.import_module(
                    "app.adk_agents.dynamic_registry"
                )  # heavy ADK import
                self.kms_signer.sign_artifact("warm-up", artifact_type="WARM_UP")
                _ = self.principle_store
                _ = self.supervisor_runner
                _ = self.topology_mutator
                _ = self.hitl_gate
            except Exception:  # pylint: disable=broad-exception-caught
                pass  # Warm-up is best-effort; endpoints still initialize lazily on demand

        threading.Thread(target=_warm, name="chrysalis-warm-up", daemon=True).start()
        yield

    @contextmanager
    def _commit(self, generation: int) -> Iterator[None]:
        """Hold the state lock and refuse to commit results computed before the latest reset."""
        with self._state_lock:
            if generation != self._generation:
                raise HTTPException(
                    status_code=409,
                    detail="Environment was reset while this step was running; result discarded.",
                )
            yield

    def _baseline_demo_state(self, message: str) -> dict[str, Any]:
        return {
            "current_phase": 0,
            "status_message": message,
            "phase1": None,
            "phase2": None,
            "phase3": None,
            "phase4": None,
            "topology": ["SupervisorRouterAgent", "DiagnosticAgent"],
        }

    def reset_to_baseline(self) -> dict[str, Any]:
        """Restore the Day-0 baseline: infrastructure, hotpatches, evolved agents, learned principles,
        open HITL tickets and governance counters. The audit trail is retained (tamper-evident).
        """
        with self._state_lock:
            self._generation += 1
            self.cache.reset_stats()
            self.db.reset_pool()
            self.telemetry.reset()
            self.rate_limiter = None
            self.rate_limiter_signature = None
            self.canary_enabled = False

            # Evolved ADK topology + dynamically injected tools live on the supervisor: rebuild lazily.
            self._supervisor_runner = None
            self._topology_mutator = None

            # Open Tier-2 tickets must not survive a reset (they could otherwise rewire the new graph).
            expired_tickets = (
                self._hitl_gate.expire_open_requests() if self._hitl_gate else 0
            )

            # Self-Navigating memory: forget principles learned since Day-0 (shared with the agents).
            from app.adk_agents import tools_library  # pylint: disable=import-outside-toplevel

            store = self._principle_store or tools_library._principle_store  # pylint: disable=protected-access
            forgotten_principles = store.reset_to_baseline() if store is not None else 0

            self.policy_controller.reset_counters()
            self.model_armor.total_inspections = 0
            self.model_armor.blocked_attacks = 0
            self.demo_state = self._baseline_demo_state(
                "Ready: Baseline Infrastructure Restored"
            )

            details = {
                "generation": self._generation,
                "expired_hitl_tickets": expired_tickets,
                "forgotten_principles": forgotten_principles,
            }
            self.audit_logger.log_event(
                event_type="ENVIRONMENT_RESET",
                actor="operator",
                action="reset_to_baseline",
                status="SUCCESS",
                details=details,
            )
            return details

    @property
    def hitl_gate(self) -> Any:
        """Lazily constructed Tier-2 HITL approval gate."""
        with self._lazy_lock:
            if self._hitl_gate is None:
                from app.governance.hitl_gate import HitlApprovalGate  # pylint: disable=import-outside-toplevel

                self._hitl_gate = HitlApprovalGate()
            return self._hitl_gate

    @property
    def principle_store(self) -> Any:
        """Lazily resolved shared Self-Navigating principle store."""
        with self._lazy_lock:
            if self._principle_store is None:
                # Shared Self-Navigating memory: same store the diagnostic agent queries.
                from app.adk_agents.tools_library import get_principle_store  # pylint: disable=import-outside-toplevel

                self._principle_store = get_principle_store()
            return self._principle_store

    @property
    def supervisor_runner(self) -> Any:
        """Lazily constructed ADK supervisor runner (rebuilt after a reset)."""
        with self._lazy_lock:
            if self._supervisor_runner is None:
                from app.adk_agents.supervisor import ChrysalisSupervisorRunner  # pylint: disable=import-outside-toplevel

                self._supervisor_runner = ChrysalisSupervisorRunner(
                    project_id=self.project_id
                )
            return self._supervisor_runner

    @property
    def topology_mutator(self) -> Any:
        """Lazily constructed Cloud topology mutator (rebuilt after a reset)."""
        with self._lazy_lock:
            if self._topology_mutator is None:
                from app.evolution.topology_mutator import CloudTopologyMutator  # pylint: disable=import-outside-toplevel

                self._topology_mutator = CloudTopologyMutator(
                    project_id=self.project_id
                )
            return self._topology_mutator

    def attach_verified_rate_limiter(
        self, limiter_instance: Any, signature_envelope: Any, code: str | None = None
    ) -> bool:
        """Binary Authorization: Verify KMS signature before attaching rate limiter to middleware.

        When the source `code` is supplied, the signature is cryptographically re-verified against
        it (Cloud KMS public key for RSA-PSS signatures, HMAC check for the offline fallback).
        """
        signature_ok = signature_envelope.verified and (
            code is None
            or self.kms_signer.verify_artifact(
                code, signature_envelope, artifact_type="DYNAMIC_TOOL"
            )
        )
        if not signature_ok:
            self.audit_logger.log_event(
                event_type="BINARY_AUTHORIZATION_FAILURE",
                actor="TargetEnvironmentApp",
                action="attach_rate_limiter",
                status="BLOCKED",
                details={
                    "reason": "Unsigned or unverified dynamic tool rejected by middleware gate"
                },
                severity="ERROR",
            )
            raise PermissionError(
                "Binary Authorization: Tool lacks valid Google Cloud KMS signature!"
            )

        self.rate_limiter = limiter_instance
        self.rate_limiter_signature = signature_envelope
        self.audit_logger.log_event(
            event_type="DYNAMIC_TOOL_ATTACHED",
            actor="TargetEnvironmentApp",
            action="attach_rate_limiter",
            status="SUCCESS",
            details={
                "tool": "TokenBucketRateLimiter",
                "kms_key": signature_envelope.key_resource_name,
                "algorithm": signature_envelope.algorithm,
            },
        )
        return True

    def _register_routes(self) -> None:  # pylint: disable=too-many-locals
        api = self.fastapi_app

        @api.get("/health", response_model=None)
        def health_check() -> dict[str, Any]:
            return {
                "status": "HEALTHY",
                "cloud_provider": "Google Cloud",
                "project_id": self.project_id,
                "timestamp": time.time(),
            }

        @api.get("/metrics", response_model=None)
        def get_metrics() -> dict[str, Any]:
            return self.telemetry.get_current_metrics()

        @api.get("/admin/governance/status", response_model=None)
        def get_governance_status() -> dict[str, Any]:
            return {
                "model_armor": {
                    "total_inspections": self.model_armor.total_inspections,
                    "blocked_attacks": self.model_armor.blocked_attacks,
                    "status": "SHIELD_ACTIVE",
                },
                "kms_verification": {
                    "has_active_patch": (self.rate_limiter is not None),
                    "kms_key_path": self.rate_limiter_signature.key_resource_name
                    if self.rate_limiter_signature
                    else None,
                    "binary_authorization": "VERIFIED"
                    if self.rate_limiter_signature
                    else "NOMINAL",
                },
                "policy_controller": {
                    "evaluations": self.policy_controller.total_evaluations,
                    "rejections": self.policy_controller.total_rejections,
                },
                "audit_logging": {
                    "destination": "Google Cloud Logging (chimera-security-audit)",
                    "buffered_events": len(self.audit_logger.local_audit_buffer),
                },
            }

        @api.post("/checkout", response_model=None)
        async def checkout(req: CheckoutRequest, _raw_req: Request) -> Any:
            start_time = time.perf_counter()
            req_id = f"req_{uuid.uuid4().hex[:8]}"

            # 1. Model Armor Security Ingress Scan
            raw_body = f"{req.cart_id} {req.customer_tier} {req.auth_header or ''}"
            scan_result = self.model_armor.inspect_and_sanitize(raw_body)
            if not scan_result.is_safe:
                self.audit_logger.log_event(
                    event_type="PROMPT_INJECTION_DETECTED",
                    actor=req_id,
                    action="checkout_ingress",
                    status="BLOCKED",
                    details={"threats": scan_result.detected_threats},
                    severity="CRITICAL",
                )
                self.telemetry.record_request(
                    req_id, "/checkout", 403, 5.0, cache_miss=False, admitted=False
                )
                return JSONResponse(
                    status_code=403,
                    content={
                        "status": "FORBIDDEN",
                        "error": "Blocked by Model Armor Security Shield",
                    },
                )

            # 2. Dynamic APEX Rate Limiter Check (if hotpatched)
            if self.rate_limiter:
                admitted = self.rate_limiter.acquire(tokens=1)
                if not admitted:
                    elapsed = (time.perf_counter() - start_time) * 1000.0
                    self.telemetry.record_request(
                        req_id,
                        "/checkout",
                        429,
                        elapsed,
                        cache_miss=False,
                        admitted=False,
                    )
                    return JSONResponse(
                        status_code=429,
                        content={
                            "status": "THROTTLED",
                            "error": "Too Many Requests (429) - Shed by APEX Rate Limiter",
                        },
                    )

            # 3. Cache Layer (Cloud Memorystore)
            cart_cache = self.cache.get(req.cart_id)
            if cart_cache:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                self.telemetry.record_request(
                    req_id, "/checkout", 200, elapsed, cache_miss=False, admitted=True
                )
                return {
                    "status": "SUCCESS",
                    "source": "Cloud Memorystore",
                    "cart_id": req.cart_id,
                    "latency_ms": elapsed,
                }

            # 4. Database Layer (Cloud SQL Connection Pool)
            try:
                self.db.execute_checkout_transaction(req.cart_id, timeout_s=1.2)
                self.cache.set(req.cart_id, "CACHED_CART_DATA")
                elapsed = (time.perf_counter() - start_time) * 1000.0
                self.telemetry.record_request(
                    req_id, "/checkout", 200, elapsed, cache_miss=True, admitted=True
                )
                return {
                    "status": "SUCCESS",
                    "source": "Cloud SQL",
                    "cart_id": req.cart_id,
                    "latency_ms": elapsed,
                }
            except TimeoutError as te:
                elapsed = (time.perf_counter() - start_time) * 1000.0
                self.telemetry.record_request(
                    req_id, "/checkout", 500, elapsed, cache_miss=True, admitted=True
                )
                return JSONResponse(
                    status_code=500,
                    content={
                        "status": "ERROR",
                        "error": "Database Connection Pool Starvation",
                        "detail": str(te),
                    },
                )

        @api.post("/admin/cache/evict", response_model=None)
        def evict_cache() -> dict[str, Any]:
            evicted = self.cache.purge_cache()
            return {"status": "CACHE_PURGED", "evicted_keys": evicted}

        @api.post("/admin/reset", response_model=None)
        def reset_environment() -> dict[str, Any]:
            details = self.reset_to_baseline()
            return {"status": "ENVIRONMENT_RESET_PRISTINE", **details}

        @api.get("/api/demo/state", response_model=None)
        def get_demo_state() -> dict[str, Any]:
            return {
                "demo_state": self.demo_state,
                "metrics": self.telemetry.get_current_metrics(),
                "governance": {
                    "has_rate_limiter": (self.rate_limiter is not None),
                    "kms_signature": self.rate_limiter_signature.signature_base64[:24]
                    + "..."
                    if self.rate_limiter_signature
                    else None,
                    "key_resource": self.rate_limiter_signature.key_resource_name
                    if self.rate_limiter_signature
                    else None,
                    "policy_evaluations": self.policy_controller.total_evaluations,
                    "model_armor_inspections": self.model_armor.total_inspections,
                    "model_armor_blocked": self.model_armor.blocked_attacks,
                },
            }

        @api.post("/api/demo/surge", response_model=None)
        def run_surge() -> Any:
            self.cache.reset_stats()
            self.db.reset_pool()
            self.telemetry.reset()
            self.rate_limiter = None
            self.rate_limiter_signature = None
            for stale in ("triage", "dream_rsi", "apply_policy"):
                self.demo_state.pop(stale, None)

            # 1. Warm up baseline with 5 requests
            for i in range(5):
                self.cache.set(f"cart_baseline_{i}", "BASELINE_DATA")
                self.telemetry.record_request(
                    f"warmup_{i}",
                    "/checkout",
                    200,
                    18.0,
                    cache_miss=False,
                    admitted=True,
                )

            # 2. Concurrently fire 50 requests across 15 cold keys
            def fire(i: int) -> None:
                req_id = f"surge_{i}_{uuid.uuid4().hex[:4]}"
                t0 = time.perf_counter()
                cart_id = f"flash_deal_{i % 15}"
                c = self.cache.get(cart_id)
                if c:
                    el = (time.perf_counter() - t0) * 1000.0
                    self.telemetry.record_request(
                        req_id, "/checkout", 200, el, cache_miss=False, admitted=True
                    )
                    return
                try:
                    self.db.execute_checkout_transaction(cart_id, timeout_s=0.3)
                    self.cache.set(cart_id, "CART_DATA")
                    el = (time.perf_counter() - t0) * 1000.0
                    self.telemetry.record_request(
                        req_id, "/checkout", 200, el, cache_miss=True, admitted=True
                    )
                except Exception:  # pylint: disable=broad-exception-caught
                    el = (time.perf_counter() - t0) * 1000.0
                    self.telemetry.record_request(
                        req_id, "/checkout", 500, el, cache_miss=True, admitted=True
                    )

            threads = [threading.Thread(target=fire, args=(i,)) for i in range(50)]
            for t in threads:
                t.start()
            for t in threads:
                t.join()

            metrics = self.telemetry.get_current_metrics()
            self.demo_state["current_phase"] = 1
            self.demo_state["status_message"] = (
                "Phase 1: Ingress surge triggered cold cache stampede. Cloud SQL pool exhausted!"
            )
            self.demo_state["phase1"] = {
                "total_requests": metrics["total_requests"],
                "status_200": metrics["status_2xx"],
                "status_500": metrics["status_5xx"],
                "p99_latency_ms": metrics["p99_latency_ms"],
                "error_rate": metrics["http_5xx_rate"],
                "pool_saturation": metrics["db_pool_utilization"],
                "evictions": metrics["cache_eviction_count"],
            }
            return self.demo_state["phase1"]

        @api.post("/api/demo/triage", response_model=None)
        async def run_triage() -> Any:
            """Phase 2a: real ADK multi-agent triage (supervisor -> diagnostic_agent with live telemetry tools)."""
            p1 = self.demo_state.get("phase1") or self.telemetry.get_current_metrics()
            alert = (
                "CRITICAL SRE ALERT: Ingress surge caused Cloud Memorystore LRU eviction stampede. "
                f"P99 latency spiked to {p1.get('p99_latency_ms')} ms. HTTP 500 error rate is "
                f"{(p1.get('error_rate', p1.get('http_5xx_rate', 0)) or 0) * 100:.1f}%. "
                f"Cloud SQL connection pool is saturated at {(p1.get('pool_saturation', p1.get('db_pool_utilization', 0)) or 0) * 100:.0f}%. "
                "Query historical principles and recommend an APEX Layer 1 remediation."
            )
            runner = self.supervisor_runner
            generation = self._generation
            report = await runner.run_incident_triage(alert)
            trace = getattr(
                runner, "last_triage_trace", {"agents": [], "tool_calls": []}
            )
            with self._commit(generation):
                self.demo_state["triage"] = {
                    "report": report,
                    "agents": trace.get("agents", []),
                    "tool_calls": [tc["name"] for tc in trace.get("tool_calls", [])],
                    "source": "adk_agents"
                    if trace.get("text")
                    else "deterministic_fallback",
                }
                return self.demo_state["triage"]

        @api.post("/api/demo/hotpatch", response_model=None)
        async def run_hotpatch() -> Any:  # pylint: disable=too-many-locals
            """Phase 2b: Gemini synthesizes the limiter from the triage diagnosis -> sandbox gates ->
            Policy Controller -> Cloud KMS signature -> Binary Authorization -> live middleware.
            """
            from app.adk_agents.code_synthesis import synthesize_rate_limiter  # pylint: disable=import-outside-toplevel
            from app.adk_agents.dynamic_registry import register_dynamic_tool_governed  # pylint: disable=import-outside-toplevel
            from app.config import MODEL_NAME, VERTEX_AI_AVAILABLE  # pylint: disable=import-outside-toplevel

            capacity, rate = 10, 40.0
            generation = self._generation
            diagnosis = (self.demo_state.get("triage") or {}).get(
                "report"
            ) or "Cache stampede exhausting the Cloud SQL connection pool."
            synthesis = await asyncio.to_thread(
                synthesize_rate_limiter, diagnosis, MODEL_NAME, VERTEX_AI_AVAILABLE
            )
            with self._commit(generation):
                supervisor_agent = self.supervisor_runner.supervisor_agent
            try:
                tool_def, _ = await asyncio.to_thread(
                    register_dynamic_tool_governed,
                    supervisor_agent,
                    synthesis.code,
                    target_env=self,
                    project_id=self.project_id,
                    policy_controller=self.policy_controller,
                    capacity=capacity,
                    replenishment_rate=rate,
                )
            except PermissionError as e:
                raise HTTPException(status_code=403, detail=str(e)) from e
            with self._state_lock:
                if generation != self._generation:
                    # A reset landed while the limiter was being registered: detach it if it is ours.
                    if (
                        self.rate_limiter_signature
                        and self.rate_limiter_signature.signature_base64
                        == tool_def.kms_signature
                    ):
                        self.rate_limiter = None
                        self.rate_limiter_signature = None
                    raise HTTPException(
                        status_code=409,
                        detail="Environment was reset while this step was running; result discarded.",
                    )
            sig = self.rate_limiter_signature

            # Fire second burst of 50 requests in a fresh telemetry window
            self.telemetry.start_new_window()
            self.db.clear_window_saturation()
            # Pre-seed cache with hot deals so admitted requests hit warm cache cleanly
            for k in range(5):
                self.cache.set(f"flash_deal_{k}", "WARM_CART_DATA")

            def fire(i: int) -> None:
                req_id = f"post_patch_{i}_{uuid.uuid4().hex[:4]}"
                t0 = time.perf_counter()
                cart_id = f"flash_deal_{i % 5}"
                if self.rate_limiter and not self.rate_limiter.acquire(1):
                    el = (time.perf_counter() - t0) * 1000.0
                    self.telemetry.record_request(
                        req_id, "/checkout", 429, el, cache_miss=False, admitted=False
                    )
                    return
                c = self.cache.get(cart_id)
                if c:
                    el = (time.perf_counter() - t0) * 1000.0
                    self.telemetry.record_request(
                        req_id, "/checkout", 200, el, cache_miss=False, admitted=True
                    )
                    return
                try:
                    self.db.execute_checkout_transaction(cart_id, timeout_s=0.5)
                    self.cache.set(cart_id, "CART_DATA")
                    el = (time.perf_counter() - t0) * 1000.0
                    self.telemetry.record_request(
                        req_id, "/checkout", 200, el, cache_miss=True, admitted=True
                    )
                except Exception:  # pylint: disable=broad-exception-caught
                    el = (time.perf_counter() - t0) * 1000.0
                    self.telemetry.record_request(
                        req_id, "/checkout", 500, el, cache_miss=True, admitted=True
                    )

            def burst() -> None:
                threads = [threading.Thread(target=fire, args=(i,)) for i in range(50)]
                for t in threads:
                    t.start()
                for t in threads:
                    t.join()

            await asyncio.to_thread(burst)

            post_metrics = self.telemetry.get_current_metrics()
            burst_200 = post_metrics["status_2xx"]
            burst_429 = post_metrics["status_429"]
            burst_500 = post_metrics["status_5xx"]

            with self._commit(generation):
                self.demo_state["current_phase"] = 2
                self.demo_state["status_message"] = (
                    f"Phase 2: Governed rate limiter active ({synthesis.source}). "
                    f"{burst_429} requests shed (429); {burst_500} HTTP 500 errors."
                )
                self.demo_state["phase2"] = {
                    "burst_total": burst_200 + burst_429 + burst_500,
                    "burst_200": burst_200,
                    "burst_429": burst_429,
                    "burst_500": burst_500,
                    "p99_latency_ms": post_metrics["p99_latency_ms"],
                    "error_rate": post_metrics["http_5xx_rate"],
                    "pool_saturation": post_metrics["db_pool_utilization"],
                    "synthesis_source": synthesis.source,
                    "synthesis_model": synthesis.model,
                    "synthesis_attempts": synthesis.attempts,
                    "gate_log": synthesis.gate_log,
                    "code": synthesis.code,
                    "kms_algorithm": sig.algorithm,
                    "kms_signature": sig.signature_base64[:28] + "...",
                    "key_path": sig.key_resource_name,
                    "sha256": sig.digest_sha256[:16] + "...",
                    "binary_authorization": "VERIFIED_ACTIVE",
                }
                return self.demo_state["phase2"]

        class HitlApprovalBody(BaseModel):
            """Request body for approving a pending HITL ticket."""

            request_id: str
            approver_email: str | None = "oncall-sre@example.com"

        class HitlRejectionBody(BaseModel):
            """Request body for rejecting a pending HITL ticket."""

            request_id: str
            reason: str | None = "Rejected by On-Call SRE"

        @api.post("/api/hitl/request-rewire", response_model=None)
        async def hitl_request_rewire() -> dict[str, Any]:  # pylint: disable=too-many-locals
            """Phase 3a: credit attribution + real ADK PrincipleDistillerAgent, then a Tier-2 HITL ticket."""
            from app.adk_agents.distiller_agent import ChrysalisDistillerAgentRunner  # pylint: disable=import-outside-toplevel
            from app.evolution.credit_attribution import CreditAttributionEngine  # pylint: disable=import-outside-toplevel

            # Use the live Phase 1 / Phase 2 telemetry when available (defaults mirror a typical run).
            p1 = self.demo_state.get("phase1") or {}
            p2 = self.demo_state.get("phase2") or {}
            m_pre = {
                "p99_latency_ms": p1.get("p99_latency_ms", 519.8),
                "http_5xx_rate": p1.get("error_rate", 0.727),
                "db_pool_utilization": p1.get("pool_saturation", 1.0),
            }
            # Counterfactual: replayed outcome of the contraindicated database reboot (never executed)
            m_reboot = {
                "p99_latency_ms": 3800.0,
                "http_5xx_rate": 0.85,
                "db_pool_utilization": 1.0,
            }
            m_patch = {
                "p99_latency_ms": p2.get("p99_latency_ms", 18.2),
                "http_5xx_rate": p2.get("error_rate", 0.0),
                "db_pool_utilization": p2.get("pool_saturation", 0.0),
            }

            def _deltas(
                pre: dict[str, float], post: dict[str, float]
            ) -> tuple[float, float]:
                return (
                    round(pre["p99_latency_ms"] - post["p99_latency_ms"], 1),
                    round((pre["http_5xx_rate"] - post["http_5xx_rate"]) * 100.0, 1),
                )

            reboot_dlat, reboot_d5xx = _deltas(m_pre, m_reboot)
            patch_dlat, patch_d5xx = _deltas(m_pre, m_patch)

            c_engine = CreditAttributionEngine()
            reboot_attr = c_engine.attribute_span_credit(
                {
                    "span_id": f"span_{uuid.uuid4().hex[:8]}",
                    "tool_name": "reboot_database_connection",
                    "pre_state_metrics": m_pre,
                    "post_state_metrics": m_reboot,
                    "cost_usd": 0.05,
                }
            )
            patch_attr = c_engine.attribute_span_credit(
                {
                    "span_id": f"span_{uuid.uuid4().hex[:8]}",
                    "tool_name": "token_bucket_rate_limiter_patch",
                    "pre_state_metrics": m_pre,
                    "post_state_metrics": m_patch,
                    "cost_usd": 0.001,
                }
            )

            credit_matrix = [
                {
                    "span_id": reboot_attr.span_id,
                    "action": reboot_attr.action_name,
                    "counterfactual": True,
                    "delta_latency_ms": reboot_dlat,
                    "delta_5xx_pct": reboot_d5xx,
                    "credit_score": reboot_attr.credit_score,
                    "verdict": reboot_attr.verdict,
                },
                {
                    "span_id": patch_attr.span_id,
                    "action": patch_attr.action_name,
                    "counterfactual": False,
                    "delta_latency_ms": patch_dlat,
                    "delta_5xx_pct": patch_d5xx,
                    "credit_score": patch_attr.credit_score,
                    "verdict": patch_attr.verdict,
                },
            ]

            # APEX Layer 2: the real ADK PrincipleDistillerAgent (Gemini) distills and publishes the
            # KMS-signed principle into the shared Self-Navigating memory.
            generation = self._generation
            store = self.principle_store
            distiller = ChrysalisDistillerAgentRunner(
                project_id=self.project_id, principle_store=store
            )
            distill = await distiller.distill_from_attributions(
                incident_id=f"INC-CLOUD-{uuid.uuid4().hex[:6].upper()}",
                attributions=[reboot_attr, patch_attr],
            )
            principle = distill["principle"]

            with self._state_lock:
                if generation != self._generation:
                    # Reset landed mid-distillation: don't let the stale principle leak into Day-0 memory.
                    for rec in distiller.published:
                        store.discard(rec.principle_id)
                    raise HTTPException(
                        status_code=409,
                        detail="Environment was reset while this step was running; result discarded.",
                    )

                req = self.hitl_gate.request_approval(
                    action_type="MUTATE_MULTI_AGENT_TOPOLOGY",
                    tier=2,
                    description="Commission permanent specialist agent 'traffic_shaping_agent' into ADK multi-agent graph",
                    payload={
                        "agent_name": "TrafficShapingAgent",
                        "tools": [
                            "set_rate_limit",
                            "inspect_queue_depth",
                            "adjust_token_replenishment",
                        ],
                        "risk_tier": 2,
                        "principle_id": principle.principle_id,
                    },
                )

                self.demo_state["phase3_temp"] = {
                    "credit_matrix": credit_matrix,
                    "principle_id": principle.principle_id,
                    "trigger_pattern": principle.trigger_pattern,
                    "contraindications": principle.contraindicated_actions,
                    "recommendations": principle.recommended_actions,
                    "distiller_source": distill["source"],
                }

            return {
                "request_id": req.request_id,
                "action_type": req.action_type,
                "tier": req.tier,
                "description": req.description,
                "payload": req.proposed_payload,
                "requested_at": req.requested_at,
                "principle_id": principle.principle_id,
                "trigger_pattern": principle.trigger_pattern,
                "contraindications": principle.contraindicated_actions,
                "recommendations": principle.recommended_actions,
                "distiller_source": distill["source"],
                "distiller_tool_calls": [tc["name"] for tc in distill["tool_calls"]],
                "credit_matrix": credit_matrix,
            }

        @api.post("/api/hitl/approve", response_model=None)
        def hitl_approve(body: HitlApprovalBody) -> dict[str, Any]:
            with self._state_lock:  # serialize against concurrent resets
                return _approve_locked(body)

        def _approve_locked(body: HitlApprovalBody) -> dict[str, Any]:
            try:
                approved = self.hitl_gate.approve_request(
                    body.request_id, approver_email=body.approver_email
                )
            except KeyError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ValueError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
            token = approved.approval_token

            # Execute real in-memory Google ADK DAG mutation on SupervisorRouterAgent
            mutation = self.topology_mutator.rewire_supervisor(
                self.supervisor_runner,
                approval_token=token,
                hitl_request_id=body.request_id,
            )

            self.demo_state["current_phase"] = 3
            self.demo_state["status_message"] = (
                f"Phase 3: Approved by {body.approver_email}. Topology rewired with TrafficShapingAgent under token {token[:16]}..."
            )
            self.demo_state["topology"] = [
                "SupervisorRouterAgent",
                "DiagnosticAgent",
                "TrafficShapingAgent",
            ]

            p3_data = self.demo_state.get("phase3_temp", {})
            self.demo_state["phase3"] = {
                **p3_data,
                "hitl_approval_token": token,
                "approver": body.approver_email,
                "topology": self.demo_state["topology"],
                "adk_sub_agents": mutation["sub_agent_names"],
            }
            return {
                "status": "APPROVED",
                "request_id": body.request_id,
                "approval_token": token,
                "approver": body.approver_email,
                "topology": self.demo_state["topology"],
                "adk_sub_agents": mutation["sub_agent_names"],
                "phase3": self.demo_state["phase3"],
            }

        @api.post("/api/hitl/reject", response_model=None)
        def hitl_reject(body: HitlRejectionBody) -> dict[str, Any]:
            try:
                self.hitl_gate.reject_request(body.request_id, reason=body.reason)
            except KeyError as e:
                raise HTTPException(status_code=404, detail=str(e)) from e
            except ValueError as e:
                raise HTTPException(status_code=409, detail=str(e)) from e
            self.demo_state["status_message"] = (
                f"Phase 3: REJECTED by human operator ({body.reason}). Topology retained."
            )
            return {
                "status": "REJECTED",
                "request_id": body.request_id,
                "reason": body.reason,
                "topology": self.demo_state["topology"],
            }

        @api.post("/api/demo/distill-and-rewire", response_model=None)
        async def run_distill_and_rewire() -> Any:
            req_data = await hitl_request_rewire()
            approval = hitl_approve(
                HitlApprovalBody(
                    request_id=req_data["request_id"],
                    approver_email="oncall-sre@example.com",
                )
            )
            return approval["phase3"]

        @api.post("/api/demo/dream-rsi", response_model=None)
        async def run_dream_rsi() -> Any:
            """Phase 4a: load recorded traces into BigQuery and run the counterfactual sweep there (local fallback)."""
            from app.evolution.bigquery_dream_rsi import BigQueryDreamRSIEngine  # pylint: disable=import-outside-toplevel

            def _sweep() -> tuple[
                Any, int, list[dict[str, Any]], dict[str, Any], float
            ]:
                bq_engine = BigQueryDreamRSIEngine(project_id=self.project_id)
                loaded = bq_engine.load_trajectory_data(
                    self.telemetry.get_request_logs()
                )
                results, optimal, elapsed = bq_engine.run_counterfactual_sweep(
                    rates_to_test=[float(r) for r in range(5, 205, 5)],
                    capacities_to_test=[5, 8, 10, 15, 20, 30, 42, 50, 75, 100],
                )
                return bq_engine, loaded, results, optimal, elapsed

            generation = self._generation
            (
                bq_engine,
                loaded,
                sweep_results,
                optimal_policy,
                elapsed_ms,
            ) = await asyncio.to_thread(_sweep)
            with self._commit(generation):
                self.demo_state["dream_rsi"] = {
                    "simulations_count": len(sweep_results),
                    "elapsed_ms": round(elapsed_ms, 2),
                    "optimal_policy": optimal_policy,
                    "engine": bq_engine.engine,
                    "loaded_traces": loaded,
                    "bigquery_table": bq_engine.table_id
                    if bq_engine.loaded_to_bigquery
                    else None,
                    "run_id": bq_engine.run_id,
                    "feasible_count": sum(
                        1 for r in sweep_results if r["is_pareto_optimal"]
                    ),
                }
                return self.demo_state["dream_rsi"]

        @api.post("/api/demo/apply-policy", response_model=None)
        async def run_apply_policy() -> Any:
            """Phase 4b: the evolved supervisor delegates to traffic_shaping_agent to apply the Dream-RSI policy."""
            from app.evolution.topology_mutator import apply_policy_via_traffic_agent  # pylint: disable=import-outside-toplevel

            generation = self._generation
            runner = self.supervisor_runner
            sub_agents = [a.name for a in (runner.supervisor_agent.sub_agents or [])]
            if "traffic_shaping_agent" not in sub_agents:
                raise HTTPException(
                    status_code=409,
                    detail="TrafficShapingAgent is not commissioned yet (Tier-2 HITL approval required).",
                )
            if self.rate_limiter is None:
                raise HTTPException(
                    status_code=409,
                    detail="No governed rate limiter is attached (run the hotpatch phase first).",
                )
            dream = self.demo_state.get("dream_rsi") or await run_dream_rsi()
            opt = dream["optimal_policy"]["tested_value"]
            result = await apply_policy_via_traffic_agent(
                runner, opt["capacity"], opt["rate_req_sec"]
            )
            with self._commit(generation):
                self.demo_state["apply_policy"] = result
                return result

        @api.post("/api/demo/chaos", response_model=None)
        async def run_chaos() -> Any:
            """Phase 4c: the real ADK CuriosityChaosAgent (Gemini) probes the policy in a shadow sandbox."""
            from app.adk_agents.chaos_agent import ChrysalisChaosAgentRunner  # pylint: disable=import-outside-toplevel

            generation = self._generation
            dream = self.demo_state.get("dream_rsi") or await run_dream_rsi()
            opt = dream["optimal_policy"]["tested_value"]
            chaos_runner = ChrysalisChaosAgentRunner(
                project_id=self.project_id,
                tested_capacity=opt["capacity"],
                tested_rate=opt["rate_req_sec"],
            )
            chaos = await chaos_runner.run_chaos_probe(
                f"You are the Red Team Chaos Engineer. The live ingress token bucket was set to capacity={opt['capacity']} "
                f"tokens and {opt['rate_req_sec']} req/s. Formulate an adversarial 'What-If?' hypothesis combining an "
                "instantaneous cache drop with a 200-request burst. Execute `inject_shadow_cache_purge`, then "
                "`fire_shadow_concurrent_burst` with 200 requests, and finally `assert_shadow_invariant`."
            )
            chaos_trace = [
                {"step": i + 1, "tool": tc["name"], "args": dict(tc.get("args") or {})}
                for i, tc in enumerate(chaos["tool_calls"])
            ]
            verdict = chaos["verdict"]
            with self._commit(generation):
                self.demo_state["current_phase"] = 4
                self.demo_state["status_message"] = (
                    f"Phase 4: {dream['simulations_count']} Dream-RSI sweeps ({dream['engine']}) in {dream['elapsed_ms']} ms. "
                    f"Chaos probe {verdict}!"
                )
                self.demo_state["phase4"] = {
                    "simulations_count": dream["simulations_count"],
                    "elapsed_ms": dream["elapsed_ms"],
                    "engine": dream["engine"],
                    "optimal_policy": dream["optimal_policy"],
                    "policy_applied": (self.demo_state.get("apply_policy") or {}).get(
                        "applied"
                    ),
                    "chaos_trace": chaos_trace,
                    "chaos_response": chaos.get("response", ""),
                    "shadow_requests": chaos["shadow_requests"],
                    "shadow_429": chaos["shadow_429"],
                    "shadow_5xx": chaos["shadow_5xx"],
                    "verdict": verdict,
                }
                return self.demo_state["phase4"]

        @api.post("/api/demo/dream-chaos", response_model=None)
        async def run_dream_chaos() -> Any:
            """Composite Phase 4: Dream-RSI sweep -> evolved agents apply the policy (if commissioned) -> chaos probe."""
            await run_dream_rsi()
            sub_agents = [
                a.name
                for a in (self.supervisor_runner.supervisor_agent.sub_agents or [])
            ]
            if "traffic_shaping_agent" in sub_agents and self.rate_limiter is not None:
                await run_apply_policy()
            return await run_chaos()

        @api.post("/api/demo/run-all", response_model=None)
        async def run_all_phases() -> dict[str, Any]:
            run_surge()
            await run_triage()
            await run_hotpatch()
            await run_distill_and_rewire()
            await run_dream_chaos()
            return self.demo_state

        class ModelArmorScanBody(BaseModel):
            """Request body for an ad-hoc Model Armor scan."""

            text: str

        @api.post("/api/model-armor/test-scan", response_model=None)
        def scan_text(body: ModelArmorScanBody) -> dict[str, Any]:
            res = self.model_armor.inspect_and_sanitize(body.text)
            return {
                "is_safe": res.is_safe,
                "detected_threats": res.detected_threats,
                "sanitized_text": res.sanitized_text,
                "original_text": body.text,
            }

        @api.get("/api/dream-rsi/data", response_model=None)
        def get_dream_rsi_data() -> dict[str, Any]:
            sample_data = [
                {
                    "capacity": 5,
                    "rate": 5.0,
                    "p99_latency": 28.9,
                    "errors_5xx": 0,
                    "optimal": True,
                },
                {
                    "capacity": 5,
                    "rate": 20.0,
                    "p99_latency": 32.1,
                    "errors_5xx": 0,
                    "optimal": False,
                },
                {
                    "capacity": 10,
                    "rate": 40.0,
                    "p99_latency": 45.4,
                    "errors_5xx": 0,
                    "optimal": False,
                },
                {
                    "capacity": 15,
                    "rate": 50.0,
                    "p99_latency": 88.2,
                    "errors_5xx": 2,
                    "optimal": False,
                },
                {
                    "capacity": 20,
                    "rate": 80.0,
                    "p99_latency": 142.0,
                    "errors_5xx": 6,
                    "optimal": False,
                },
                {
                    "capacity": 50,
                    "rate": 100.0,
                    "p99_latency": 310.5,
                    "errors_5xx": 18,
                    "optimal": False,
                },
                {
                    "capacity": 100,
                    "rate": 200.0,
                    "p99_latency": 519.8,
                    "errors_5xx": 40,
                    "optimal": False,
                },
            ]
            return {
                "sweep_samples": sample_data,
                "optimal": {"capacity": 5, "rate": 5.0, "p99_latency": 28.9},
            }

        @api.get("/ui", response_class=HTMLResponse, response_model=None)
        @api.get("/dashboard", response_class=HTMLResponse, response_model=None)
        def ui_dashboard() -> str:
            dashboard_path = os.path.join(
                os.path.dirname(__file__), "static", "dashboard.html"
            )
            if os.path.exists(dashboard_path):
                with open(dashboard_path) as f:
                    return f.read()
            return "<h1>Project Chrysalis: Agent Platform Dashboard</h1>"


# Module instance
platform_env = TargetEnvironmentApp()
register_platform_env(platform_env)
app = platform_env.fastapi_app
