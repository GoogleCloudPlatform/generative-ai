"""Invoice Processing -- Unified ADK Agent: Inference + Learning

A single LlmAgent that supports two modes:
  1. Inference -- runs the full Acting -> Investigation -> ALF pipeline
  2. Learning -- SME-driven rule review and creation

Usage:
    adk web invoice_processing
"""

import json
import os
import shutil
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

# Resolve paths: agent.py -> invoice_processing/ (package root with data/ inside)
AGENT_PKG_DIR = Path(__file__).resolve().parent
DATA_DIR = AGENT_PKG_DIR / "data"
EXEMPLARY_DIR = AGENT_PKG_DIR / "exemplary_data"

# Project root for .env resolution (contrib/python/invoice-processing/)
PROJECT_ROOT = AGENT_PKG_DIR.parent

# Ensure invoice_processing package is importable
sys.path.insert(0, str(AGENT_PKG_DIR.parent))

from google.adk.agents import LlmAgent  # noqa: E402
from google.genai import types  # noqa: E402

from .prompt import INVOICE_PROCESSING_INSTRUCTION  # noqa: E402
from .shared_libraries.acting.general_invoice_agent import (  # noqa: E402
    process_invoice,
)
from .shared_libraries.alf_engine import (  # noqa: E402
    ALFEngine,
    ActingAgentAdapter,
)
from .shared_libraries.investigation.investigate_agent_reconst import (  # noqa: E402
    BypassDetector,
    DataSourceValidator,
    LLMRulesValidatorReconstructed,
    PerGroupValidator,
    ReconstructedRulesExtractor,
    RuleDiscoveryEngine,
    ToleranceExtractor,
    investigate_agent_case,
    load_agent_case_data,
)
from .tools.tools import (  # noqa: E402
    assess_impact,
    build_rule_discovery_context,
    build_rule_revision_context,
    check_conflicts,
    delete_rule,
    discover_safe_rule,
    format_rule_display,
    get_existing_rules,
    get_existing_scopes,
    get_next_rule_id,
    list_cases,
    list_inference_cases,
    load_case,
    log_session_event,
    revise_safe_rule,
    save_session,
    validate_rule,
    write_rule,
)

# ============================================================================
# Investigation lazy initialization
# ============================================================================


@dataclass
class _InvestigationState:
    """Holds mutable singletons for lazy investigation initialization."""

    initialized: bool = False
    llm_validator: object = field(default=None)
    data_source_validator: object = field(default=None)
    bypass_detector: object = field(default=None)
    tolerance_extractor: object = field(default=None)
    per_group_validator: object = field(default=None)
    rule_discovery: object = field(default=None)


_investigation_state = _InvestigationState()


def _ensure_investigation_initialized():
    """Lazy-initialize all investigation validators and rule discovery."""
    if _investigation_state.initialized:
        return

    rules_book_path = DATA_DIR / "reconstructed_rules_book.md"
    if not rules_book_path.exists():
        raise FileNotFoundError(
            f"Rules book not found: {rules_book_path}. "
            "The agent requires reconstructed_rules_book.md in data/."
        )

    rules_content = rules_book_path.read_text(encoding="utf-8")

    _investigation_state.rule_discovery = RuleDiscoveryEngine(rules_content)
    _investigation_state.rule_discovery.discover_rules()

    rules_extractor = ReconstructedRulesExtractor(rules_content)

    _investigation_state.data_source_validator = DataSourceValidator(
        rule_discovery=_investigation_state.rule_discovery,
    )
    _investigation_state.bypass_detector = BypassDetector(
        rules_extractor=rules_extractor,
        rule_discovery=_investigation_state.rule_discovery,
    )
    _investigation_state.tolerance_extractor = ToleranceExtractor(
        rules_extractor=rules_extractor,
        rule_discovery=_investigation_state.rule_discovery,
    )

    _investigation_state.llm_validator = LLMRulesValidatorReconstructed(
        rules_extractor=rules_extractor,
    )
    _investigation_state.per_group_validator = PerGroupValidator()

    _investigation_state.initialized = True


# ============================================================================
# FunctionTool: run_inference -- helper functions
# ============================================================================


def _run_acting_stage(case_id, stages):
    """Run the Acting Agent stage and return (acting_result, error_response).

    Returns:
        tuple: (acting_result dict, error_response dict or None)
    """
    source_folder = EXEMPLARY_DIR / case_id
    if not source_folder.exists():
        return None, {
            "status": "ERROR",
            "error": f"Source folder not found: {source_folder}",
            "stages": stages,
        }

    # Clean up previous run output to avoid stale data
    agent_output_dir = DATA_DIR / "agent_output" / case_id
    alf_output_dir = DATA_DIR / "alf_output" / case_id
    if agent_output_dir.exists():
        shutil.rmtree(agent_output_dir)
    if alf_output_dir.exists():
        shutil.rmtree(alf_output_dir)

    try:
        acting_result = process_invoice(source_folder)
    except Exception as e:
        return None, {
            "status": "ERROR",
            "error": f"Acting Agent error: {e}",
            "stages": stages,
        }

    return acting_result, None


def _build_acting_stage_result(acting_result, stages, pipeline_start, case_id):
    """Process acting result, update stages, and return error response if needed.

    Returns:
        tuple: (acting_decision, error_response or None)
    """
    acting_decision = acting_result.get("decision", "ERROR")
    acting_time = acting_result.get("processing_time", 0)

    stages["acting"] = {
        "decision": acting_decision,
        "processing_time": acting_time,
        "output_folder": str(acting_result.get("output_folder", "")),
        "rejection_phase": acting_result.get("phase"),
    }

    print(f"  Acting Agent: {acting_decision} (took {acting_time:.1f}s)")

    if acting_decision == "ERROR":
        return acting_decision, {
            "status": "ERROR",
            "error": acting_result.get("error", "Unknown acting agent error"),
            "stages": stages,
            "acting_decision": "ERROR",
            "final_output": str(DATA_DIR / "agent_output" / case_id),
            "pipeline_time": (
                datetime.now(timezone.utc) - pipeline_start
            ).total_seconds(),
        }

    return acting_decision, None


def _run_investigation_stage(
    case_id, stages, pipeline_start, acting_decision, total_stages
):
    """Run the Investigation Agent stage.

    Returns:
        tuple: (compliance_score, overall_compliance, stop_response or None)
    """
    print(f"\nStage 2/{total_stages}: Running Investigation Agent...")

    try:
        _ensure_investigation_initialized()

        case_data = load_agent_case_data(case_id)
        discovered_rules = _investigation_state.rule_discovery.discovered_rules

        investigation = investigate_agent_case(
            case_id,
            case_data,
            _investigation_state.llm_validator,
            _investigation_state.data_source_validator,
            _investigation_state.bypass_detector,
            _investigation_state.tolerance_extractor,
            _investigation_state.per_group_validator,
            discovered_rules,
        )

        compliance_score = investigation.compliance_score
        overall_compliance = investigation.overall_rule_compliance

        stages["investigation"] = {
            "compliance": overall_compliance,
            "score": compliance_score,
            "is_rejected": investigation.is_rejected,
            "rejection_justified": investigation.rejection_justified,
            "data_source_compliance": investigation.data_source_compliance,
            "layer3_violations": investigation.layer3_violations,
            "summary": investigation.summary,
        }

    except Exception as e:
        print(f"  WARNING: Investigation failed: {e}")
        print("  Treating as INCONCLUSIVE -- continuing to ALF.")
        compliance_score = 0.0
        overall_compliance = "INCONCLUSIVE"
        stages["investigation"] = {
            "compliance": "INCONCLUSIVE",
            "score": 0.0,
            "error": str(e),
        }

    print(f"  Investigation: {overall_compliance} (score: {compliance_score:.1f}%)")

    # Gate: stop on MAJOR_VIOLATION
    if overall_compliance == "MAJOR_VIOLATION":
        pipeline_time = (datetime.now(timezone.utc) - pipeline_start).total_seconds()
        print("\n  PIPELINE STOPPED: MAJOR_VIOLATION (compliance < 60%)")
        return (
            compliance_score,
            overall_compliance,
            {
                "status": "STOPPED",
                "reason": "MAJOR_VIOLATION -- acting agent output did not pass quality validation. ALF corrections were NOT applied.",
                "stages": stages,
                "acting_decision": acting_decision,
                "investigation_compliance": overall_compliance,
                "investigation_score": compliance_score,
                "alf_revised": False,
                "alf_rules_matched": 0,
                "final_output": str(DATA_DIR / "agent_output" / case_id),
                "pipeline_time": pipeline_time,
            },
        )

    return compliance_score, overall_compliance, None


def _run_alf_stage(
    case_id,
    stages,
    pipeline_start,
    acting_decision,
    overall_compliance,
    compliance_score,
    total_stages,
    skip_inv,
):
    """Run the ALF Agent stage and return the final pipeline result dict."""
    alf_stage_num = 2 if skip_inv else 3
    print(f"\nStage {alf_stage_num}/{total_stages}: Running ALF Agent...")

    rule_base_path = DATA_DIR / "rule_base.json"
    output_folder = DATA_DIR / "agent_output" / case_id

    try:
        alf_engine = ALFEngine(rule_base_path)
    except Exception as e:
        pipeline_time = (datetime.now(timezone.utc) - pipeline_start).total_seconds()
        stages["alf"] = {"error": str(e), "revised": False}
        return {
            "status": "COMPLETED",
            "stages": stages,
            "acting_decision": acting_decision,
            "investigation_compliance": overall_compliance,
            "investigation_score": compliance_score,
            "alf_revised": False,
            "alf_rules_matched": 0,
            "alf_error": str(e),
            "final_output": str(output_folder),
            "pipeline_time": pipeline_time,
        }

    # Build case context from agent artifacts
    case_context = ActingAgentAdapter.build_case_context(output_folder)

    # Load provisional output
    postprocessing_path = output_folder / "Postprocessing_Data.json"
    if not postprocessing_path.exists():
        pipeline_time = (datetime.now(timezone.utc) - pipeline_start).total_seconds()
        return {
            "status": "ERROR",
            "error": f"Postprocessing_Data.json not found in {output_folder}",
            "stages": stages,
            "pipeline_time": pipeline_time,
        }

    with open(postprocessing_path) as f:
        provisional_output = json.load(f)

    # Run ALF Collect-Plan-Execute pipeline
    revised_output, audit_log = alf_engine.evaluate(provisional_output, case_context)

    any_rules_fired = audit_log.get("any_rules_fired", False)
    rules_matched = audit_log.get("rules_matched", 0)
    matched_ids = [r.get("rule_id", "?") for r in audit_log.get("rules_applied", [])]

    original_decision, revised_decision, final_output = _save_alf_output(
        any_rules_fired,
        rules_matched,
        matched_ids,
        revised_output,
        audit_log,
        provisional_output,
        case_id,
        output_folder,
    )

    stages["alf"] = {
        "revised": any_rules_fired,
        "rules_evaluated": audit_log.get("total_rules_evaluated", 0),
        "rules_matched": rules_matched,
        "matched_rule_ids": matched_ids,
        "original_decision": original_decision,
        "revised_decision": revised_decision,
    }

    pipeline_time = (datetime.now(timezone.utc) - pipeline_start).total_seconds()

    print(f"\n{'=' * 60}")
    print(f"PIPELINE COMPLETED in {pipeline_time:.1f}s")
    print(f"  Acting: {acting_decision}")
    print(f"  Investigation: {overall_compliance} ({compliance_score:.1f}%)")
    print(f"  ALF: {'Revised' if any_rules_fired else 'No changes'}")
    print(f"  Final output: {final_output}")
    print(f"{'=' * 60}\n")

    return {
        "status": "COMPLETED",
        "stages": stages,
        "acting_decision": acting_decision,
        "investigation_compliance": overall_compliance,
        "investigation_score": compliance_score,
        "alf_revised": any_rules_fired,
        "alf_rules_matched": rules_matched,
        "alf_matched_ids": matched_ids,
        "original_decision": original_decision,
        "revised_decision": revised_decision,
        "final_output": final_output,
        "pipeline_time": pipeline_time,
    }


def _save_alf_output(
    any_rules_fired,
    rules_matched,
    matched_ids,
    revised_output,
    audit_log,
    provisional_output,
    case_id,
    output_folder,
):
    """Save ALF output files if rules fired and return decision info.

    Returns:
        tuple: (original_decision, revised_decision, final_output)
    """
    original_decision = provisional_output.get("Invoice Processing", {}).get(
        "Invoice Status"
    )

    if any_rules_fired:
        alf_output_dir = DATA_DIR / "alf_output" / case_id
        alf_output_dir.mkdir(parents=True, exist_ok=True)

        with open(alf_output_dir / "Postprocessing_Data.json", "w") as f:
            json.dump(revised_output, f, indent=2, default=str)

        with open(alf_output_dir / "alf_audit_log.json", "w") as f:
            json.dump(audit_log, f, indent=2, default=str)

        final_output = str(alf_output_dir)
        revised_decision = revised_output.get("Invoice Processing", {}).get(
            "Invoice Status"
        )
        print(f"  ALF: {rules_matched} rules applied ({', '.join(matched_ids)})")
        print(f"  Decision: {original_decision} -> {revised_decision}")
    else:
        final_output = str(output_folder)
        revised_decision = original_decision
        print(
            f"  ALF: {audit_log.get('total_rules_evaluated', 0)} rules evaluated, no rules matched -- output unchanged"
        )

    return original_decision, revised_decision, final_output


# ============================================================================
# FunctionTool: run_inference
# ============================================================================


def run_inference(case_id: str, skip_investigation: str = "false") -> dict:
    """Run the inference pipeline for a case.

    By default runs all three stages: Acting -> Investigation -> ALF.
    Set skip_investigation to "true" to skip the Investigation stage,
    running only Acting -> ALF (faster, but no compliance validation).

    Args:
        case_id: The case identifier (e.g., "case_001"). Must exist in
                 exemplary_data/ with at least one PDF file.
        skip_investigation: "true" to skip Investigation stage (default "false").

    Returns:
        dict with keys:
            - status: "COMPLETED" | "STOPPED" | "ERROR"
            - stages: dict with results for each completed stage
            - acting_decision: "ACCEPT" | "REJECT" | "ERROR"
            - investigation_compliance: str (e.g., "FULLY_COMPLIANT") or "SKIPPED"
            - investigation_score: float (0-100)
            - alf_revised: bool
            - alf_rules_matched: int
            - final_output: str (path to final output)
            - pipeline_time: float (seconds)
    """
    pipeline_start = datetime.now(timezone.utc)
    stages = {}

    # ================================================================
    # STAGE 1: ACTING AGENT
    # ================================================================
    print(f"\n{'=' * 60}")
    print(f"INFERENCE PIPELINE: {case_id}")
    print(f"{'=' * 60}")
    _skip_inv = skip_investigation.lower() == "true"
    total_stages = 2 if _skip_inv else 3
    print(f"\nStage 1/{total_stages}: Running Acting Agent...")

    acting_result, error_response = _run_acting_stage(case_id, stages)
    if error_response is not None:
        return error_response

    acting_decision, error_response = _build_acting_stage_result(
        acting_result,
        stages,
        pipeline_start,
        case_id,
    )
    if error_response is not None:
        return error_response

    # ================================================================
    # STAGE 2: INVESTIGATION AGENT (optional)
    # ================================================================
    if _skip_inv:
        print("\n  Investigation: SKIPPED (skip_investigation=true)")
        compliance_score = 0.0
        overall_compliance = "SKIPPED"
        stages["investigation"] = {"compliance": "SKIPPED", "score": 0.0}
    else:
        compliance_score, overall_compliance, stop_response = _run_investigation_stage(
            case_id,
            stages,
            pipeline_start,
            acting_decision,
            total_stages,
        )
        if stop_response is not None:
            return stop_response

    # ================================================================
    # STAGE 3: ALF AGENT
    # ================================================================
    return _run_alf_stage(
        case_id,
        stages,
        pipeline_start,
        acting_decision,
        overall_compliance,
        compliance_score,
        total_stages,
        _skip_inv,
    )


# ============================================================================
# Root ADK Agent
# ============================================================================

root_agent = LlmAgent(
    name="invoice_processing",
    model=os.environ.get("MODEL_NAME", "gemini-3.5-flash"),
    generate_content_config=types.GenerateContentConfig(temperature=0),
    instruction=INVOICE_PROCESSING_INSTRUCTION,
    tools=[
        # Inference tools
        list_inference_cases,
        run_inference,
        # Learning tools (primary)
        list_cases,
        load_case,
        discover_safe_rule,
        revise_safe_rule,
        # Learning tools (manual)
        assess_impact,
        validate_rule,
        check_conflicts,
        write_rule,
        delete_rule,
        get_existing_rules,
        get_existing_scopes,
        format_rule_display,
        get_next_rule_id,
        build_rule_discovery_context,
        build_rule_revision_context,
        log_session_event,
        save_session,
    ],
)
