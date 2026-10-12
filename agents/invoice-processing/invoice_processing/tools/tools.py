"""Function tools for the Invoice Processing unified agent.

Combines inference tools (case discovery, pipeline execution) and
learning tools (case review, rule management, session logging).
"""

import ast
import json
import re
import sys
from pathlib import Path

# Resolve paths: tools.py -> tools/ -> invoice_processing/ (package root with data/ inside)
AGENT_PKG_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = AGENT_PKG_DIR / "data"
EXEMPLARY_DIR = AGENT_PKG_DIR / "exemplary_data"

# Ensure invoice_processing package and shared_libraries are importable
AGENT_ROOT = AGENT_PKG_DIR.parent  # invoice_processing/ (outer)
sys.path.insert(0, str(AGENT_ROOT))
sys.path.insert(0, str(AGENT_PKG_DIR / "shared_libraries"))

from ..core.case_loader import CaseLoaderAgent  # noqa: E402
from ..core.config import RULES_BOOK_PATH  # noqa: E402
from ..core.impact_assessor import ImpactAssessorAgent  # noqa: E402
from ..core.prompts import (  # noqa: E402
    RULE_DISCOVERY_SYSTEM_PROMPT,
    RULE_DISCOVERY_TASK_TEMPLATE,
    RULE_REVISION_TASK_TEMPLATE,
    extract_relevant_rules_book_sections,
)
from ..core.rule_writer import RuleWriterAgent  # noqa: E402
from ..core.safe_rule_orchestrator import SafeRuleOrchestrator  # noqa: E402
from ..core.session_logger import SessionLogger  # noqa: E402

# ---------------------------------------------------------------------------
# Module-level instances (singletons)
# ---------------------------------------------------------------------------

_case_loader = CaseLoaderAgent()
_impact_assessor = ImpactAssessorAgent()
_rule_writer = RuleWriterAgent()
_session_logger = SessionLogger()
_orchestrator = SafeRuleOrchestrator()


def _safe_json_loads(text) -> dict:
    """Parse JSON/dict input from LLM, handling all common formats."""
    # If already a dict/list (ADK may pass structured objects), return directly
    if isinstance(text, (dict, list)):
        return text
    if not isinstance(text, str):
        text = str(text)
    # Strip markdown code fences if present
    stripped = text.strip()
    if stripped.startswith("```"):
        lines = stripped.split("\n")
        # Remove first line (```json) and last line (```)
        lines = [line for line in lines[1:] if not line.strip().startswith("```")]
        stripped = "\n".join(lines).strip()
    # Try direct JSON parse
    try:
        return json.loads(stripped)
    except (json.JSONDecodeError, ValueError):
        pass
    # Fix unescaped backslashes (common LLM error)
    try:
        cleaned = re.sub(r'\\(?!["\\/bfnrtu])', r"\\\\", stripped)
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass
    # Try Python literal (single quotes, True/False/None)
    try:
        result = ast.literal_eval(stripped)
        if isinstance(result, (dict, list)):
            return result
    except (ValueError, SyntaxError):
        pass
    # Replace single quotes with double quotes
    try:
        cleaned = stripped.replace("'", '"')
        return json.loads(cleaned)
    except (json.JSONDecodeError, ValueError):
        pass
    raise ValueError(f"Could not parse input as JSON. Received: {text[:100]}...")


# ===========================================================================
# INFERENCE TOOLS
# ===========================================================================


def list_inference_cases() -> list[str]:
    """List all case IDs available for inference processing.

    Scans the exemplary_data/ directory for case folders that contain
    at least one PDF file (the input for the acting agent).

    Returns:
        Sorted list of case IDs (e.g., ["case_001", "case_002", ...]).
    """
    if not EXEMPLARY_DIR.exists():
        return []

    cases = []
    for folder in sorted(EXEMPLARY_DIR.iterdir()):
        if folder.is_dir() and any(folder.glob("*.pdf")):
            cases.append(folder.name)
    return cases


# ===========================================================================
# LEARNING TOOLS
# ===========================================================================


def list_cases() -> list[str]:
    """Return sorted list of all available case IDs.

    Scans agent_output/ for processed case folders.
    """
    return _case_loader.list_cases()


def load_case(case_id: str) -> dict:
    """Load all agent artifacts for a case and return structured summary.

    Args:
        case_id: The case identifier (folder name in data/agent_output/).

    Returns:
        dict with case_id, summary, decision, rejection_reason,
        rejection_phase, has_alf_output, and context.
    """
    case_data = _case_loader.run(case_id)
    _session_logger.log_case_loaded(case_id, case_data.summary)

    pp = case_data.postprocessing or {}
    inv_processing = pp.get("Invoice Processing", {})

    return {
        "case_id": case_data.case_id,
        "summary": case_data.summary,
        "decision": inv_processing.get("Invoice Status", "UNKNOWN"),
        "rejection_reason": inv_processing.get("Rejection Reason", ""),
        "rejection_phase": inv_processing.get("Rejection Phase", ""),
        "has_alf_output": case_data.alf_audit is not None,
        "context": case_data.context,
    }


def assess_impact(
    conditions_json: str, target_case_id: str, sample_size: str = "10"
) -> dict:
    """Evaluate proposed rule conditions against a sample of cases to detect unintended matches.

    The target case is always included. If total cases <= sample_size, all cases are evaluated.

    Args:
        conditions_json: JSON string of the conditions array from the proposed rule.
        target_case_id: The case ID the rule is intended to fix.
        sample_size: Max number of cases to evaluate (default 10). Set to a large number to evaluate all.

    Returns:
        dict with target_matched, collateral_matches, safe_cases, total_cases, sampled, sample_size, summary.
    """
    conditions = _safe_json_loads(conditions_json)
    report = _impact_assessor.run(
        conditions, target_case_id, sample_size=int(sample_size)
    )

    _session_logger.log_impact_assessed(
        report.summary,
        report.target_matched,
        len(report.collateral_matches),
        len(report.safe_cases),
        [m.case_id for m in report.collateral_matches],
    )

    return {
        "target_matched": report.target_matched,
        "collateral_matches": [
            {
                "case_id": m.case_id,
                "current_decision": m.decision,
                "rejection_reason": m.rejection_reason,
            }
            for m in report.collateral_matches
        ],
        "safe_cases": report.safe_cases,
        "total_cases": report.total_cases,
        "sampled": report.sampled,
        "sample_size": report.sample_size,
        "summary": report.summary,
    }


def validate_rule(rule_json: str) -> list[str]:
    """Validate rule schema against ALF requirements.

    Args:
        rule_json: JSON string of the rule dict.

    Returns:
        List of error strings. Empty list means the rule is valid.
    """
    return _rule_writer.validate_rule(_safe_json_loads(rule_json))


def check_conflicts(rule_json: str) -> list[str]:
    """Check for conflicts between proposed rule and existing rules.

    Args:
        rule_json: JSON string of the rule dict.

    Returns:
        List of warning strings. Empty list means no conflicts.
    """
    return _rule_writer.check_conflicts(_safe_json_loads(rule_json))


def write_rule(rule_json: str, mode: str = "add") -> dict:
    """Write a validated rule to rule_base.json.

    Args:
        rule_json: JSON string of the rule dict.
        mode: "add" for new rule, "update" to replace existing by ID.

    Returns:
        dict with success, rule_id, backup_path, total_rules, message.
    """
    result = _rule_writer.run(_safe_json_loads(rule_json), mode=mode)
    if result.success:
        _session_logger.log_rule_written(
            result.rule_id, result.backup_path, result.total_rules
        )
    return {
        "success": result.success,
        "rule_id": result.rule_id,
        "backup_path": result.backup_path,
        "total_rules": result.total_rules,
        "message": result.message,
    }


def delete_rule(rule_id: str) -> dict:
    """Delete a rule from rule_base.json by its ID.

    Creates a backup before deleting. The SME must confirm the deletion.

    Args:
        rule_id: The ALF rule ID to delete (e.g., "ALF-001").

    Returns:
        dict with success, rule_id, backup_path, total_rules, message.
    """
    result = _rule_writer.delete_rule(rule_id)
    if result.success:
        _session_logger.log_rule_written(
            result.rule_id, result.backup_path, result.total_rules
        )
    return {
        "success": result.success,
        "rule_id": result.rule_id,
        "backup_path": result.backup_path,
        "total_rules": result.total_rules,
        "message": result.message,
    }


def get_existing_rules() -> list[dict]:
    """Return all current ALF rules from rule_base.json."""
    return _rule_writer.get_existing_rules()


def get_existing_scopes() -> dict:
    """Return scope -> [rule_id, ...] mapping for mutual exclusion awareness."""
    return _rule_writer.get_existing_scopes()


def format_rule_display(rule_json: str) -> str:
    """Format a rule dict for human-readable display.

    Args:
        rule_json: JSON string of the rule dict.

    Returns:
        Formatted string for display to the SME.
    """
    try:
        rule_dict = _safe_json_loads(rule_json)
    except (json.JSONDecodeError, ValueError):
        return (
            "ERROR: Could not parse rule JSON. Please use get_existing_rules() "
            "to retrieve rules as structured data, then pass the JSON directly."
        )
    return _rule_writer.format_rule_display(rule_dict)


def get_next_rule_id() -> str:
    """Get the next available ALF rule ID (ALF-NNN format)."""
    return _rule_writer.next_rule_id()


def build_rule_discovery_context(case_id: str, sme_feedback: str) -> dict:
    """Build the complete context needed for LLM rule discovery.

    Args:
        case_id: The case identifier.
        sme_feedback: The SME's natural language description of what should change.

    Returns:
        dict with task_prompt and context fields for rule discovery.
    """
    case_data = _case_loader.run(case_id)
    _session_logger.log_sme_feedback(sme_feedback)

    pp = case_data.postprocessing or {}
    inv_processing = pp.get("Invoice Processing", {})
    failing_phase = inv_processing.get("Rejection Phase", "")
    agent_decision = inv_processing.get("Invoice Status", "UNKNOWN")
    rejection_reason = inv_processing.get("Rejection Reason", "")

    existing_rules = _rule_writer.get_existing_rules()
    existing_scopes = _rule_writer.get_existing_scopes()
    next_rule_id = _rule_writer.next_rule_id()

    rules_book_context = ""
    if RULES_BOOK_PATH.exists():
        rules_book_text = RULES_BOOK_PATH.read_text(encoding="utf-8")
        rules_book_context = extract_relevant_rules_book_sections(
            rules_book_text, failing_phase
        )

    validation_details = ""
    for phase_key in ["phase1", "phase2", "phase3", "phase4"]:
        phase_data = case_data.artifacts.get(phase_key, {})
        if phase_data and phase_data.get("validations"):
            validation_details += f"\n--- {phase_key.upper()} ---\n"
            for v in phase_data["validations"]:
                status = v.get("status", v.get("result", ""))
                step = v.get("step", v.get("step_name", ""))
                validation_details += f"  Step {step}: {status}\n"
                if v.get("rejection_template"):
                    validation_details += f"    Template: {v['rejection_template']}\n"

    invoice_json = json.dumps(
        case_data.context.get("invoice", {}), indent=2, default=str
    )[:3000]
    extraction_json = json.dumps(
        case_data.artifacts.get("extraction", {}), indent=2, default=str
    )[:3000]

    task_prompt = (
        RULE_DISCOVERY_SYSTEM_PROMPT
        + "\n\n"
        + RULE_DISCOVERY_TASK_TEMPLATE.format(
            sme_feedback=sme_feedback,
            case_id=case_id,
            agent_decision=agent_decision,
            rejection_reason=rejection_reason,
            failing_phase=failing_phase,
            case_summary=case_data.summary[:2000],
            validation_details=validation_details[:2000],
            invoice_json=invoice_json,
            extraction_json=extraction_json,
            existing_rules_json=json.dumps(existing_rules, indent=2, default=str)[
                :4000
            ],
            existing_scopes=json.dumps(existing_scopes, indent=2),
            rules_book_context=rules_book_context[:4000],
            next_rule_id=next_rule_id,
        )
    )

    return {
        "task_prompt": task_prompt,
        "case_id": case_id,
        "agent_decision": agent_decision,
        "rejection_reason": rejection_reason,
        "failing_phase": failing_phase,
        "next_rule_id": next_rule_id,
    }


def build_rule_revision_context(
    case_id: str,
    current_rule_json: str,
    revision_feedback: str,
    impact_summary: str,
) -> dict:
    """Build context for LLM rule revision.

    Args:
        case_id: The case identifier.
        current_rule_json: JSON string of the current proposed rule.
        revision_feedback: SME's revision request.
        impact_summary: Summary from the impact assessment.

    Returns:
        dict with task_prompt for rule revision.
    """
    case_data = _case_loader.run(case_id)
    _session_logger.log_sme_revision(revision_feedback)
    current_rule = _safe_json_loads(current_rule_json)

    invoice_json = json.dumps(
        case_data.context.get("invoice", {}), indent=2, default=str
    )[:3000]
    extraction_json = json.dumps(
        case_data.artifacts.get("extraction", {}), indent=2, default=str
    )[:3000]

    task_prompt = RULE_REVISION_TASK_TEMPLATE.format(
        revision_feedback=revision_feedback,
        current_rule_json=json.dumps(current_rule, indent=2),
        impact_summary=impact_summary,
        case_id=case_id,
        case_summary=case_data.summary[:2000],
        invoice_json=invoice_json,
        extraction_json=extraction_json,
        rule_id=current_rule.get("id", "ALF-???"),
    )

    return {
        "task_prompt": task_prompt,
        "case_id": case_id,
        "rule_id": current_rule.get("id"),
    }


def discover_safe_rule(case_id: str, sme_feedback: str) -> dict:
    """Generate a new ALF rule with automatic safety validation.

    This tool handles the full rule discovery pipeline:
    1. Generates a rule via LLM based on case data and SME feedback
    2. Validates the rule schema
    3. Assesses impact across all existing cases
    4. If collateral matches are found, automatically tightens conditions
       and re-assesses (up to 3 attempts)

    Args:
        case_id: The case identifier the rule is intended to fix.
        sme_feedback: The SME's natural language description of what should change.

    Returns:
        dict with: success, rule (dict), rule_json (string), display (formatted),
        impact (assessment results), attempts, revision_log, has_collateral,
        collateral_warning.
    """
    _session_logger.log_sme_feedback(sme_feedback)
    result = _orchestrator.discover(case_id, sme_feedback)
    if result.get("success"):
        _session_logger._add_event(
            "rule_discovered",
            {
                "case_id": case_id,
                "rule_id": result["rule"].get("id", "?"),
                "attempts": result["attempts"],
                "has_collateral": result["has_collateral"],
            },
        )
    return result


def revise_safe_rule(case_id: str, current_rule_json: str, sme_feedback: str) -> dict:
    """Revise a proposed rule based on SME feedback with automatic safety validation.

    Takes the SME's revision feedback, revises the rule via LLM, then runs
    the same safety loop as discover_safe_rule: validates, assesses impact,
    and auto-tightens if collateral is found.

    Args:
        case_id: The target case identifier.
        current_rule_json: JSON string of the current proposed rule to revise.
        sme_feedback: The SME's revision feedback describing what to change.

    Returns:
        Same format as discover_safe_rule.
    """
    current_rule = _safe_json_loads(current_rule_json)
    _session_logger.log_sme_revision(sme_feedback)
    result = _orchestrator.revise(case_id, current_rule, sme_feedback)
    if result.get("success"):
        _session_logger._add_event(
            "rule_revised",
            {
                "case_id": case_id,
                "rule_id": result["rule"].get("id", "?"),
                "attempts": result["attempts"],
                "has_collateral": result["has_collateral"],
            },
        )
    return result


def log_session_event(event_type: str, data_json: str = "{}") -> str:
    """Log an event to the session log for auditability.

    Args:
        event_type: The type of event to log.
        data_json: JSON string of event-specific data.

    Returns:
        Confirmation message.
    """
    _session_logger._add_event(event_type, _safe_json_loads(data_json))
    return f"Logged event: {event_type}"


def save_session() -> str:
    """Save the current session log and return the file path."""
    path = _session_logger.save()
    return f"Session saved: {path}" if path else "No session events to save."
