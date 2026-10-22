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

"""Project Chrysalis: End-to-End Autonomous Demonstration on Google Cloud Agent Platform.

Unifies:
1. Google Cloud Services: Cloud Memorystore (Redis), Cloud SQL, Cloud Logging, Cloud Monitoring, BigQuery, Agent Platform.
2. Google Cloud Governance: Model Armor, Cloud KMS Code Signing, Policy-as-Code Controller, HITL Dual-Custody.
3. Google ADK 2.0 Multi-Agent Framework: SupervisorRouterAgent, DiagnosticAgent, PrincipleDistillerAgent, CuriosityChaosAgent.
"""
import asyncio
import io
import os
import sys
import threading
import time
import uuid
from typing import cast

# Ensure import paths resolve. Google Cloud project / Agent Platform routing are configured in app.config
# ($GOOGLE_CLOUD_PROJECT, else Application Default Credentials / gcloud config).
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from app.config import PROJECT_ID, MODEL_NAME, VERTEX_AI_AVAILABLE  # noqa: E402  # pylint: disable=wrong-import-position
from app.target_env.server import platform_env  # noqa: E402  # pylint: disable=wrong-import-position
from app.adk_agents.supervisor import ChrysalisSupervisorRunner  # noqa: E402  # pylint: disable=wrong-import-position
from app.adk_agents.code_synthesis import synthesize_rate_limiter  # noqa: E402  # pylint: disable=wrong-import-position
from app.adk_agents.dynamic_registry import register_dynamic_tool_governed  # noqa: E402  # pylint: disable=wrong-import-position
from app.adk_agents.tools_library import get_principle_store  # noqa: E402  # pylint: disable=wrong-import-position
from app.evolution.credit_attribution import CreditAttributionEngine  # noqa: E402  # pylint: disable=wrong-import-position
from app.evolution.topology_mutator import CloudTopologyMutator, apply_policy_via_traffic_agent  # noqa: E402  # pylint: disable=wrong-import-position
from app.evolution.bigquery_dream_rsi import BigQueryDreamRSIEngine  # noqa: E402  # pylint: disable=wrong-import-position
from app.adk_agents.distiller_agent import ChrysalisDistillerAgentRunner  # noqa: E402  # pylint: disable=wrong-import-position
from app.adk_agents.chaos_agent import ChrysalisChaosAgentRunner  # noqa: E402  # pylint: disable=wrong-import-position
from app.governance.kms_signer import CloudKmsSigner  # noqa: E402  # pylint: disable=wrong-import-position
from app.governance.audit_logger import CloudAuditLogger  # noqa: E402  # pylint: disable=wrong-import-position


class Style:
    """ANSI terminal color / emphasis escape codes."""

    CYAN = "\033[96m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"
    RESET = "\033[0m"


def print_banner() -> None:
    """Print the demo banner (and an offline-mode notice when Agent Platform is unavailable)."""
    banner = f"""
{Style.CYAN}{Style.BOLD}========================================================================================
   PROJECT CHRYSALIS (GOOGLE CLOUD AGENT PLATFORM EDITION)
   Architecting Governed, Self-Evolving AI Agents on Gemini Enterprise Agent Platform
   Framework: Google ADK 2.0 | Model: Gemini 4.0 Argon | GCP: {PROJECT_ID}
   Governance: Model Armor | Cloud KMS | OPA Policy Controller | HITL Dual-Custody
========================================================================================{Style.RESET}"""
    print(banner)
    if not VERTEX_AI_AVAILABLE:
        print(f"{Style.YELLOW}   [Offline mode] No Google Cloud credentials found: ADK agents & cloud services use deterministic fallbacks.\n"
              f"   Run `gcloud auth application-default login` to enable live Gemini on Agent Platform.{Style.RESET}")


def print_phase_header(phase_num: int, title: str, subtitle: str) -> None:
    """Print a formatted header for a demo phase."""
    print(f"\n{Style.BOLD}----------------------------------------------------------------------------------------")
    print(f"[{Style.YELLOW}PHASE {phase_num}{Style.RESET}{Style.BOLD}] {title.upper()}")
    print(f"{Style.CYAN}>>> {subtitle}{Style.RESET}")
    print("----------------------------------------------------------------------------------------\n")


async def main() -> None:  # pylint: disable=too-many-locals,too-many-branches
    """Run the four-phase end-to-end Project Chrysalis demonstration."""
    print_banner()

    env = platform_env
    env.cache.reset_stats()
    env.db.reset_pool()
    env.telemetry.reset()
    env.rate_limiter = None
    env.rate_limiter_signature = None

    # Initialize Governance Control Plane
    # (Cloud KMS / Cloud Logging clients are initialized up front; the instances are not reused below.)
    CloudKmsSigner(project_id=PROJECT_ID)
    policy_controller = env.policy_controller  # shared with the server middleware & TrafficShapingAgent tools
    CloudAuditLogger(project_id=PROJECT_ID)

    # =========================================================================
    # PHASE 1: BLACK FRIDAY INGRESS SURGE (CLOUD MEMORYSTORE & CLOUD SQL)
    # =========================================================================
    print_phase_header(
        1,
        "Black Friday Surge on Cloud Memorystore & Cloud SQL",
        "Simulating cold-start cache stampede, connection starvation, and Cloud Logging streams",
    )

    print(f"{Style.CYAN}[>] Step 1.1: Pre-warming Cloud Memorystore cache with baseline shopping carts...{Style.RESET}")
    for i in range(5):
        cart_key = f"cart_prewarm_{i}"
        env.cache.set(cart_key, f"ITEM_DATA_{i}")
        env.telemetry.record_request(f"warm_{i}", "/checkout", 200, 18.0, cache_miss=False, admitted=True)

    base_m = env.telemetry.get_current_metrics()
    print(f"    Baseline: Latency={base_m['p99_latency_ms']}ms, Cache Hit Ratio={base_m['cache_hit_ratio']*100:.0f}%, 5xx Rate={base_m['http_5xx_rate']*100:.1f}%")

    print(f"\n{Style.RED}[!] Step 1.2: Triggering Black Friday 50-Request Concurrent Surge across 15 cold keys...{Style.RESET}")

    def fire_burst_request(req_id: int) -> None:
        cart_id = f"cart_burst_{req_id % (5 if env.rate_limiter else 15)}"
        t_start = time.perf_counter()

        # APEX Layer 1 Rate Limiter check (if attached)
        if env.rate_limiter:
            admitted = env.rate_limiter.acquire(tokens=1)
            if not admitted:
                elapsed = (time.perf_counter() - t_start) * 1000.0
                env.telemetry.record_request(f"req_{req_id}", "/checkout", 429, elapsed, cache_miss=False, admitted=False)
                return

        cart_val = env.cache.get(cart_id)
        if cart_val:
            elapsed = (time.perf_counter() - t_start) * 1000.0
            env.telemetry.record_request(f"req_{req_id}", "/checkout", 200, elapsed, cache_miss=False, admitted=True)
            return

        try:
            env.db.execute_checkout_transaction(cart_id, timeout_s=0.5)
            env.cache.set(cart_id, f"PAYLOAD_{req_id}")
            elapsed = (time.perf_counter() - t_start) * 1000.0
            env.telemetry.record_request(f"req_{req_id}", "/checkout", 200, elapsed, cache_miss=True, admitted=True)
        except TimeoutError:
            elapsed = (time.perf_counter() - t_start) * 1000.0
            env.telemetry.record_request(f"req_{req_id}", "/checkout", 500, elapsed, cache_miss=True, admitted=True)

    threads = []
    for i in range(50):
        t = threading.Thread(target=fire_burst_request, args=(i,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    stampede_metrics = env.telemetry.get_current_metrics()
    print(f"\n{Style.RED}{Style.BOLD}--- INCIDENT TELEMETRY SNAPSHOT (CLOUD MONITORING & LOGGING) ---{Style.RESET}")
    print(f"Total Concurrent Requests : {stampede_metrics['total_requests']}")
    print(f"HTTP 200 (Success)        : {stampede_metrics['status_2xx']}")
    print(f"HTTP 500 (Starvation)     : {Style.RED}{stampede_metrics['status_5xx']} ({stampede_metrics['http_5xx_rate']*100:.1f}%){Style.RESET}")
    print(f"P99 Ingress Latency       : {Style.RED}{stampede_metrics['p99_latency_ms']:.1f} ms{Style.RESET} (Target: 50.0 ms)")
    print(f"Cloud SQL Saturation      : {stampede_metrics['db_pool_utilization']*100:.0f}% (Semaphore Locked)")
    print(f"Memorystore Evictions     : {stampede_metrics['cache_eviction_count']} keys evicted under strict LRU")

    # =========================================================================
    # PHASE 2: ADK 2.0 TRIAGE, MODEL ARMOR & APEX LAYER 1 GOVERNED HOTPATCH
    # =========================================================================
    print_phase_header(
        2,
        "ADK 2.0 Fast Loop Triage & Governed APEX Layer 1 Hotpatch",
        "Model Armor, Self-Navigating guardrails, Cloud Policy Controller & Cloud KMS signing",
    )

    print(f"{Style.CYAN}[>] Step 2.1: Model Armor Ingress Scan & Dispatch to ADK 2.0 Supervisor Router Agent...{Style.RESET}")
    supervisor = ChrysalisSupervisorRunner(model_name=MODEL_NAME, project_id=PROJECT_ID)

    incident_alert = (
        f"CRITICAL SRE ALERT: Ingress surge caused Cloud Memorystore LRU eviction stampede. "
        f"P99 latency spiked to {stampede_metrics['p99_latency_ms']} ms. HTTP 500 error rate is {stampede_metrics['http_5xx_rate']*100:.1f}%. "
        f"Cloud SQL connection pool is saturated at {stampede_metrics['db_pool_utilization']*100:.0f}%. "
        f"Query historical principles and formulate an APEX Layer 1 hotpatch."
    )

    triage_response = await supervisor.run_incident_triage(incident_alert)
    print(f"\n{Style.GREEN}--- ADK 2.0 MULTI-AGENT DIAGNOSTIC REPORT ---{Style.RESET}")
    report_lines = [line for line in triage_response.strip().split("\n") if line.strip() and line.strip() != "---"]
    max_lines = 14
    for line in report_lines[:max_lines]:
        print(f"    {line}")
    if len(report_lines) > max_lines:
        print(f"    ... ({len(report_lines) - max_lines} more lines)")

    print(f"\n{Style.CYAN}[>] Step 2.2: Self-Navigating Memory Guardrail Check:{Style.RESET}")
    principle_store = get_principle_store()  # shared with the diagnostic & distiller agents
    historical_matches = principle_store.query_similar_principles("cache stampede database saturation", top_k=1)
    if historical_matches:
        top_p, _sim = historical_matches[0]
        print(f"    {Style.RED}{Style.BOLD}BLOCKING ACTION:{Style.RESET} Database Restart is strictly contraindicated!")
        print(f"    Reason: '{top_p.trigger_pattern}'")
        print(f"    Contraindications: {top_p.contraindicated_actions}")
        print(f"    Recommended      : {top_p.recommended_actions}")

    # Record simulated negative span
    span_db_reboot = {
        "span_id": f"span_{uuid.uuid4().hex[:8]}",
        "agent_name": "legacy_remediation_agent",
        "tool_name": "reboot_database_connections",
        "pre_state_metrics": stampede_metrics,
        "post_state_metrics": {
            "p99_latency_ms": 3800.0,
            "http_5xx_rate": 0.85,
            "db_pool_utilization": 1.0,
            "cache_hit_ratio": 0.0,
        },
        "cost_usd": 0.05,
        "execution_duration_ms": 1200.0,
    }
    env.telemetry.record_action_span(span_db_reboot)

    print(f"\n{Style.MAGENTA}[>] Step 2.3: APEX Layer 1: Gemini Tool Synthesis -> Sandbox Gates -> Policy -> Cloud KMS -> Binary Authorization...{Style.RESET}")
    synthesis = await asyncio.to_thread(synthesize_rate_limiter, triage_response, MODEL_NAME, VERTEX_AI_AVAILABLE)
    origin = (
        f"{Style.GREEN}Gemini-synthesized ({synthesis.model}, attempt {synthesis.attempts}){Style.RESET}"
        if synthesis.source == "gemini"
        else f"{Style.YELLOW}Reviewed reference template (Gemini unavailable or output rejected){Style.RESET}"
    )
    print(f"    Code Origin           : {origin}")
    for gate in synthesis.gate_log:
        print(f"    Verification Gate     : {gate}")
    code_lines = [ln for ln in synthesis.code.splitlines() if ln.strip()]
    print(f"    Synthesized Code      : {len(code_lines)} lines")
    for line in code_lines[:6]:
        print(f"      {Style.CYAN}{line}{Style.RESET}")
    if len(code_lines) > 6:
        print(f"      {Style.CYAN}...{Style.RESET}")

    tool_def, _dynamic_tool = register_dynamic_tool_governed(
        supervisor.supervisor_agent,
        code_string=synthesis.code,
        target_env=env,
        project_id=PROJECT_ID,
        policy_controller=policy_controller,
        capacity=10,
        replenishment_rate=40.0,
    )
    sig = env.rate_limiter_signature
    print(f"    AST Sandbox Policy    : {Style.GREEN}PASSED (import allow-list, no forbidden builtins / dunder access){Style.RESET}")
    print(f"    Cloud Policy Check    : {Style.GREEN}PASSED (capacity=10 <= 100, rate=40 req/s >= SLA floor 10){Style.RESET}")
    print(f"    Cloud KMS Signature   : {Style.GREEN}{sig.algorithm} {(tool_def.kms_signature or '')[:24]}...{Style.RESET}")
    print(f"    Binary Authorization  : {Style.GREEN}SIGNATURE RE-VERIFIED & ATTACHED TO SERVER MIDDLEWARE{Style.RESET}")

    print(f"\n{Style.CYAN}[>] Step 2.4: Firing second 50-request burst with Governed Rate Limiter ACTIVE...{Style.RESET}")
    env.telemetry.start_new_window()
    env.db.clear_window_saturation()
    for k in range(5):
        env.cache.set(f"cart_burst_{k}", f"WARM_PAYLOAD_{k}")

    threads = []
    for i in range(50):
        t = threading.Thread(target=fire_burst_request, args=(i + 50,))
        threads.append(t)
        t.start()
    for t in threads:
        t.join()

    post_metrics = env.telemetry.get_current_metrics()
    burst_200 = post_metrics['status_2xx']
    burst_429 = post_metrics['status_429']
    burst_500 = post_metrics['status_5xx']
    burst_total = burst_200 + burst_429 + burst_500
    err_color = Style.GREEN if burst_500 == 0 else Style.RED
    print(f"\n{Style.GREEN}{Style.BOLD}--- POST-PATCH RECOVERY SNAPSHOT (CLOUD MONITORING) ---{Style.RESET}")
    print(f"Total Requests in Burst   : {burst_total}")
    print(f"HTTP 200 (Admitted)       : {Style.GREEN}{burst_200}{Style.RESET}")
    print(f"HTTP 429 (Safely Shed)    : {Style.YELLOW}{burst_429}{Style.RESET}")
    print(f"HTTP 500 (Errors)         : {err_color}{burst_500} ({post_metrics['http_5xx_rate']*100:.1f}% in burst){Style.RESET}")
    print(f"P99 Ingress Latency       : {Style.GREEN}{post_metrics['p99_latency_ms']:.1f} ms{Style.RESET} (was {stampede_metrics['p99_latency_ms']:.1f} ms)")
    print(f"Cloud SQL Saturation      : {err_color}{post_metrics['db_pool_utilization']*100:.0f}% ({'zero starvation' if burst_500 == 0 else 'starvation persists'}){Style.RESET}")

    # Record positive span
    span_rate_limiter = {
        "span_id": f"span_{uuid.uuid4().hex[:8]}",
        "agent_name": "supervisor_router_agent",
        "tool_name": "token_bucket_rate_limiter_patch",
        "pre_state_metrics": stampede_metrics,
        "post_state_metrics": post_metrics,
        "cost_usd": 0.005,
        "execution_duration_ms": 45.0,
    }
    env.telemetry.record_action_span(span_rate_limiter)

    # =========================================================================
    # PHASE 3: AGENTEVOLVER CREDIT ATTRIBUTION & HITL TOPOLOGICAL EVOLUTION
    # =========================================================================
    print_phase_header(
        3,
        "AgentEvolver Credit Attribution & HITL Topological Evolution",
        "Mathematical Shapley attribution, KMS principle distillation, and Tier 2 Dual-Custody HITL gate",
    )

    print(f"{Style.CYAN}[>] Step 3.1: Computing Step-Level Credit Attribution Formula:{Style.RESET}")
    print("    H(S_t) = 0.35*min(L/200ms, 1) + 0.40*5xx + 0.25*U_pool")
    print("    C(a_t) = tanh(2.5 * (H_pre - H_post) - 1.0 * Cost)")
    engine = CreditAttributionEngine()
    spans = env.telemetry.get_action_spans()
    attributions = engine.attribute_trajectory_credits(spans)

    print("\n" + "=" * 104)
    print("AGENTEVOLVER FINE-GRAINED STEP CREDIT ATTRIBUTION MATRIX")
    print("=" * 104)
    print(f"{'Span ID':<13} | {'Tool / Action':<26} | {'Delta Latency':>13} | {'Delta 5xx':>9} | {'Delta H':>7} | {'Credit Score':>12} | {'Verdict'}")
    print("-" * 104)
    for span, a in zip(spans, attributions):
        # Positive deltas = improvement (latency / error rate reduced by the action)
        pre_m, post_m = span["pre_state_metrics"], span["post_state_metrics"]
        delta_lat = pre_m["p99_latency_ms"] - post_m["p99_latency_ms"]
        delta_5xx = (pre_m["http_5xx_rate"] - post_m["http_5xx_rate"]) * 100.0
        v_color = Style.GREEN if a.credit_score > 0 else Style.RED
        print(f"{a.span_id:<13} | {a.action_name[:26]:<26} | {delta_lat:>+10.1f} ms | {delta_5xx:>+8.1f}% | {a.health_delta:>+7.3f} | {v_color}{a.credit_score:>+12.2f}{Style.RESET} | {v_color}{a.verdict}{Style.RESET}")
    print("=" * 104)

    print(f"\n{Style.CYAN}[>] Step 3.2: APEX Layer 2 (Principle Distillation): Invoking ADK PrincipleDistillerAgent...{Style.RESET}")
    distiller = ChrysalisDistillerAgentRunner(model_name=MODEL_NAME, project_id=PROJECT_ID)
    distill_result = await distiller.distill_from_attributions(
        incident_id="INC-CLOUD-BF2026",
        attributions=attributions,
    )
    distilled_p = distill_result["principle"]
    print("    ADK Agent Dispatched  : principle_distiller_agent (Gemini 4.0 Argon)")
    print(f"    Executed Tool Calls   : {[t['name'] for t in distill_result['tool_calls']]}")
    if distilled_p:
        print(f"    Distilled Principle ID: {distilled_p.principle_id}")
        print(f"    Trigger Pattern       : {distilled_p.trigger_pattern}")
        print(f"    Contraindicated       : {distilled_p.contraindicated_actions}")
        print(f"    Recommended           : {distilled_p.recommended_actions}")
        print(f"    KMS Provenance Sig    : {distilled_p.kms_signature.signature_base64[:20]}...")

    print(f"\n{Style.BLUE}[>] Step 3.3: APEX Layer 3 (Topology Re-Wiring): Evaluating Tier 2 HITL Dual-Custody Gate...{Style.RESET}")
    mutator = CloudTopologyMutator(model_name=MODEL_NAME, project_id=PROJECT_ID)
    mutation_result = mutator.rewire_supervisor(supervisor)
    print(f"    HITL Dual-Custody Gate: {Style.GREEN}APPROVED (Token: {mutation_result['approval_token']}){Style.RESET}")
    print(f"    New Permanent Agent   : {mutation_result['new_agent_name']}")
    print(f"    Updated Sub-Agents    : {mutation_result['sub_agent_names']}")
    print("    Audit Log Status      : Streamed to Google Cloud Logging (chimera-security-audit)")

    # =========================================================================
    # PHASE 4: GOOGLE BIGQUERY DREAM-RSI & ADK CURIOSITY CHAOS AGENT
    # =========================================================================
    print_phase_header(
        4,
        "Google BigQuery Dream-RSI & Self-Questioning Verification",
        "Serverless parameter sweep across BigQuery traces; ADK Curiosity Chaos Agent",
    )

    print(f"{Style.CYAN}[>] Step 4.1: Exporting request execution traces to Google BigQuery dataset...{Style.RESET}")
    bq_engine = BigQueryDreamRSIEngine(project_id=PROJECT_ID)
    loaded_count = await asyncio.to_thread(bq_engine.load_trajectory_data, env.telemetry.get_request_logs())
    if bq_engine.loaded_to_bigquery:
        print(f"    BigQuery Load Job     : {Style.GREEN}Loaded {loaded_count} execution traces into '{bq_engine.table_id}' (run_id={bq_engine.run_id}){Style.RESET}")
    else:
        print(f"    BigQuery Load Job     : {Style.YELLOW}Dataset unavailable - {loaded_count} traces kept in the local replay buffer "
              f"(run scripts/setup_gcp.sh to provision BigQuery){Style.RESET}")

    print(f"\n{Style.CYAN}[>] Step 4.2: Running Dream-RSI Vectorized Counterfactual Policy Sweep (400 simulations)...{Style.RESET}")
    sweep_results, optimal_policy, elapsed_ms = await asyncio.to_thread(
        bq_engine.run_counterfactual_sweep,
        [float(r) for r in range(5, 205, 5)],
        [5, 8, 10, 15, 20, 30, 42, 50, 75, 100],
    )
    print(f"    Simulated Policies    : {len(sweep_results)} counterfactual runs completed in {elapsed_ms:.1f} ms")
    print(f"    Analytics Engine      : {bq_engine.engine}")
    print(f"\n{Style.GREEN}{Style.BOLD}--- DREAM-RSI OPTIMAL POLICY DISCOVERY ---{Style.RESET}")
    print(f"    Optimal Parameter     : {optimal_policy['tested_value']}")
    print(f"    Simulated P99 Latency : {optimal_policy['simulated_p99_latency_ms']:.1f} ms")
    print(f"    Simulated 5xx Count   : {optimal_policy['simulated_5xx_count']}")
    print(f"    Simulated DB Max Load : {optimal_policy['simulated_database_max_load']*100:.0f}%")

    opt_cap = optimal_policy["tested_value"].get("capacity", 10)
    opt_rate = optimal_policy["tested_value"].get("rate_req_sec", 40.0)
    print(f"\n{Style.BLUE}[>] Step 4.3: Evolved Topology in Action: Supervisor delegates policy rollout to TrafficShapingAgent...{Style.RESET}")
    applied = await apply_policy_via_traffic_agent(supervisor, opt_cap, opt_rate)
    a_color = Style.GREEN if applied["source"] == "adk_agents" else Style.YELLOW
    print(f"    Handled By            : {a_color}{' -> '.join(applied['agents']) or 'n/a'} ({applied['source']}){Style.RESET}")
    for tc in applied["tool_calls"]:
        print(f"    • ADK Tool Executed   : {Style.MAGENTA}{tc['agent']}.{tc['name']}{Style.RESET} {tc['args']}")
    print(f"    Live Rate Limiter     : capacity={applied['active_limiter']['capacity']}, rate={applied['active_limiter']['replenishment_rate']} req/s "
          f"({Style.GREEN + 'applied, policy-checked' if applied['applied'] else Style.RED + 'NOT applied'}{Style.RESET})")

    print(f"\n{Style.YELLOW}[>] Step 4.4: AgentEvolver Curiosity Engine: Dispatching ADK CuriosityChaosAgent...{Style.RESET}")
    chaos_runner = ChrysalisChaosAgentRunner(
        model_name=MODEL_NAME,
        project_id=PROJECT_ID,
        tested_capacity=opt_cap,
        tested_rate=opt_rate,
    )
    chaos_directive = (
        "You are the Red Team Chaos Engineer on Google Cloud Agent Platform. "
        "Formulate an adversarial 'What-If?' hypothesis combining an instantaneous cache drop with a 200-request burst. "
        "Execute `inject_shadow_cache_purge`, then `fire_shadow_concurrent_burst` with 200 requests, and finally `assert_shadow_invariant`."
    )
    print("    ADK Agent Dispatched  : curiosity_chaos_agent (Gemini 4.0 Argon)")
    chaos_result = await chaos_runner.run_chaos_probe(chaos_directive)

    print(f"\n{Style.CYAN}[>] Step 4.5: ADK Chaos Agent Autonomous Tool Execution Trace:{Style.RESET}")
    for tc in chaos_result["tool_calls"]:
        print(f"    • ADK Tool Executed   : {Style.MAGENTA}{tc['name']}{Style.RESET} {tc.get('args', {})}")
    verified = chaos_result["verdict"] == "VERIFIED_RESILIENT"
    v_color = Style.GREEN if verified else Style.RED
    print(f"    Shadow Probe Outcome  : {chaos_result['shadow_requests']} requests | "
          f"{chaos_result['shadow_429']} shed (429) | {v_color}{chaos_result['shadow_5xx']} errors (500){Style.RESET}")
    print(f"    Verification Result   : {v_color}{Style.BOLD}{chaos_result['verdict']}{Style.RESET}")

    eval_count = policy_controller.total_evaluations
    chaos_summary = (
        f"Autonomous shadow chaos probe verified zero HTTP 500 errors across {chaos_result['shadow_requests']} requests."
        if verified
        else f"Shadow chaos probe detected {chaos_result['shadow_5xx']} HTTP 500 errors: policy requires further tuning."
    )
    synth_summary = (
        f"Gemini-synthesized ({synthesis.model}) limiter passed sandbox gates"
        if synthesis.source == "gemini"
        else "Reference-template limiter (Gemini unavailable/rejected) passed sandbox gates"
    )
    kms_summary = (
        "signed with Cloud KMS (RSA-PSS) and re-verified against the KMS public key"
        if sig.algorithm != "HMAC_SHA256_KMS_DERIVED"
        else "signed with the local HMAC fallback (Cloud KMS key not provisioned - run scripts/setup_gcp.sh)"
    )
    rollout_summary = (
        "TrafficShapingAgent applied the Dream-RSI policy live (policy-checked)"
        if applied["source"] == "adk_agents"
        else "Dream-RSI policy applied via deterministic fallback (agents did not delegate)"
    )
    print(f"\n{Style.GREEN}{Style.BOLD}========================================================================================")
    print("   PROJECT CHRYSALIS: GOVERNED AGENT PLATFORM EVOLUTION COMPLETE")
    print("========================================================================================")
    print(f"• [APEX Layer 1]  : {synth_summary}; {kms_summary}.")
    print("• [Model Armor]   : Ingress prompt injection scanning & PII masking on every agent prompt.")
    print(f"• [Policy-as-Code]: SLA floor / capacity ceiling enforced ({eval_count} evaluation{'s' if eval_count != 1 else ''}).")
    print("• [HITL Gate]     : Dual-custody approval recorded before mutating the multi-agent graph.")
    print(f"• [APEX Layer 3]  : {rollout_summary}.")
    print(f"• [Dream-RSI]     : {len(sweep_results)} sweeps via {bq_engine.engine} in {elapsed_ms:.1f}ms (optimal: {optimal_policy['tested_value']}).")
    print(f"• [Curiosity Chaos]: {chaos_summary}{Style.RESET}\n")


if __name__ == "__main__":
    # Stream output line-by-line even when piped to a file / CI log
    cast(io.TextIOWrapper, sys.stdout).reconfigure(line_buffering=True)
    asyncio.run(main())
