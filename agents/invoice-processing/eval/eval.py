#!/usr/bin/env python3
"""Schema-Driven Evaluation Script for Document Processing Agents

Two-layer evaluation:
  1. Deterministic — field-by-field comparison (instant, reproducible, zero cost)
  2. LLM-as-judge — single Gemini call per case producing a holistic alignment verdict

All field paths, section names, comparison groups, and status mappings are read
from master_data.yaml (or .json) — making this evaluator domain-agnostic.

The LLM layer is optional (--skip-llm to disable) and produces one of:
  - ALIGNED:           Agent output matches ground truth in all material respects
  - PARTIALLY_ALIGNED: Correct decision but some field differences
  - NOT_ALIGNED:       Wrong decision or critical data errors

Usage:
    # Full evaluation (deterministic + LLM)
    python eval.py --ground-truth "exemplary_data" --agent-output output

    # With explicit master data file
    python eval.py --ground-truth "exemplary_data" --agent-output output \
        --master-data ../invoice_processing/shared_libraries/invoice_master_data.yaml

    # Deterministic only (no LLM, no cost)
    python eval.py --ground-truth "exemplary_data" --agent-output output --skip-llm

    # Single case
    python eval.py --ground-truth "exemplary_data" --agent-output output --case case_001

    # Custom financial tolerance (default: $0.02)
    python eval.py --ground-truth "exemplary_data" --agent-output output --tolerance 0.05
"""

import argparse
import json
import os
import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

# Optional LLM imports — only needed when --skip-llm is NOT set
_LLM_AVAILABLE = False
try:
    from dotenv import load_dotenv
    from google.cloud import aiplatform
    from vertexai.generative_models import GenerativeModel

    _LLM_AVAILABLE = True
except ImportError:
    pass

# Resolve: eval/ -> invoice-processing/ (recipe root) -> invoice_processing/
# (the package, which holds data/ and exemplary_data/). Relative --ground-truth
# / --agent-output paths and the eval_results output dir all resolve under the
# package, matching invoice_processing/core/config.py.
SCRIPT_DIR = Path(__file__).resolve().parent
RECIPE_ROOT = SCRIPT_DIR.parent
PROJECT_ROOT = RECIPE_ROOT / "invoice_processing"

# Master data loader — provides domain-agnostic configuration
sys.path.insert(0, str(PROJECT_ROOT / "shared_libraries"))
from master_data_loader import MasterData, load_master_data  # noqa: E402

# ============================================================================
# CONFIGURATION
# ============================================================================
EVAL_OUTPUT_DIR = PROJECT_ROOT / "data" / "eval_results"

# Default financial tolerance for amount comparisons
DEFAULT_TOLERANCE = 0.02


# LLM configuration (only used when LLM evaluation is enabled)
def _init_llm() -> Optional["GenerativeModel"]:
    """Initialize LLM model. Returns None if unavailable."""
    if not _LLM_AVAILABLE:
        return None

    # Load .env from project root
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        env_file = SCRIPT_DIR / ".env"
    if env_file.exists():
        load_dotenv(env_file)
    else:
        load_dotenv()

    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    model_name = os.getenv("MODEL_NAME", "gemini-3.5-flash")

    if not project_id:
        return None

    aiplatform.init(project=project_id, location=location)
    return GenerativeModel(model_name)


# Hardcoded fallback — used only when no master data is provided
_FALLBACK_STATUS_TO_DECISION = {
    "pending payment": "ACCEPT",
    "rejected": "REJECT",
    "to verify": "SET_ASIDE",
}


# ============================================================================
# COMPARISON FUNCTIONS
# ============================================================================


def parse_amount(value: str) -> float | None:
    """Parse a formatted amount string like '1,100.00' into a float."""
    if value is None:
        return None
    try:
        return float(str(value).replace(",", "").strip())
    except (ValueError, TypeError):
        return None


def amounts_match(gt_val: str, agent_val: str, tolerance: float) -> bool:
    """Check if two amount strings match within tolerance."""
    gt = parse_amount(gt_val)
    agent = parse_amount(agent_val)
    if gt is None and agent is None:
        return True
    if gt is None or agent is None:
        return False
    return abs(gt - agent) <= tolerance


def normalize_string(val: str | None) -> str:
    """Normalize a string for comparison (lowercase, strip, collapse whitespace)."""
    if val is None:
        return ""
    return " ".join(str(val).strip().lower().split())


def status_to_decision(status: str, mapping: dict[str, str] | None = None) -> str:
    """Map Invoice Status to decision class using master data or fallback."""
    if mapping is None:
        mapping = _FALLBACK_STATUS_TO_DECISION
    return mapping.get(normalize_string(status), "UNKNOWN")


def parse_line_items(line_items_field: Any) -> list[dict]:
    """Parse the Line Items field (stored as JSON string in the schema)."""
    if line_items_field is None:
        return []
    if isinstance(line_items_field, list):
        return line_items_field
    if isinstance(line_items_field, str):
        try:
            parsed = json.loads(line_items_field)
            return parsed if isinstance(parsed, list) else []
        except (json.JSONDecodeError, TypeError):
            return []
    return []


def compare_decision(gt: dict, agent: dict, master: MasterData | None = None) -> dict:
    """Compare the processing decision (ACCEPT/REJECT/SET_ASIDE).

    Reads the decision field path and status-to-decision mapping from master data.
    Falls back to hardcoded "Invoice Processing.Invoice Status" if no master data.
    """
    if master:
        decision_path = master.get_eval_decision_path()
        status_mapping = master.get_eval_status_to_decision()
    else:
        decision_path = "Invoice Processing.Invoice Status"
        status_mapping = _FALLBACK_STATUS_TO_DECISION

    # Resolve the decision path (e.g., "Invoice Processing.Invoice Status")
    parts = decision_path.split(".")
    gt_status = gt
    agent_status = agent
    for part in parts:
        gt_status = (
            (gt_status or {}).get(part, "") if isinstance(gt_status, dict) else ""
        )
        agent_status = (
            (agent_status or {}).get(part, "") if isinstance(agent_status, dict) else ""
        )

    gt_decision = status_to_decision(gt_status, status_mapping)
    agent_decision = status_to_decision(agent_status, status_mapping)

    match = gt_decision == agent_decision

    return {
        "ground_truth_status": gt_status,
        "agent_status": agent_status,
        "ground_truth_decision": gt_decision,
        "agent_decision": agent_decision,
        "match": match,
    }


def compare_financials(gt: dict, agent: dict, tolerance: float) -> dict:
    """Compare financial amounts (total, pretax, tax)."""
    gt_details = gt.get("Invoice Details") or {}
    agent_details = agent.get("Invoice Details") or {}

    fields = {
        "Invoice Total": ("Invoice Total", tolerance),
        "Pretax Total": ("Pretax Total", tolerance),
        "Tax Amount": ("Tax Amount", tolerance),
    }

    results = {}
    all_match = True

    for label, (field_name, tol) in fields.items():
        gt_val = gt_details.get(field_name, "")
        agent_val = agent_details.get(field_name, "")
        match = amounts_match(gt_val, agent_val, tol)
        if not match:
            all_match = False

        results[label] = {
            "ground_truth": gt_val,
            "agent": agent_val,
            "match": match,
        }

    # Currency
    gt_currency = gt_details.get("Currency", "")
    agent_currency = agent_details.get("Currency", "")
    currency_match = normalize_string(gt_currency) == normalize_string(agent_currency)
    results["Currency"] = {
        "ground_truth": gt_currency,
        "agent": agent_currency,
        "match": currency_match,
    }
    if not currency_match:
        all_match = False

    results["all_match"] = all_match
    return results


def compare_vendor(gt: dict, agent: dict) -> dict:
    """Compare vendor information."""
    gt_vendor = gt.get("Vendor Information") or {}
    agent_vendor = agent.get("Vendor Information") or {}

    # Vendor name — normalized comparison
    gt_name = normalize_string(gt_vendor.get("Vendor Name", ""))
    agent_name = normalize_string(agent_vendor.get("Vendor Name", ""))
    name_match = gt_name == agent_name

    # Tax ID — exact after stripping whitespace
    gt_tax_id = str(gt_vendor.get("Tax ID", "")).replace(" ", "").strip()
    agent_tax_id = str(agent_vendor.get("Tax ID", "")).replace(" ", "").strip()
    tax_id_match = gt_tax_id == agent_tax_id

    return {
        "Vendor Name": {
            "ground_truth": gt_vendor.get("Vendor Name", ""),
            "agent": agent_vendor.get("Vendor Name", ""),
            "match": name_match,
        },
        "Tax ID": {
            "ground_truth": gt_vendor.get("Tax ID", ""),
            "agent": agent_vendor.get("Tax ID", ""),
            "match": tax_id_match,
        },
        "all_match": name_match and tax_id_match,
    }


def compare_header(gt: dict, agent: dict) -> dict:
    """Compare invoice header fields (number, date)."""
    gt_details = gt.get("Invoice Details") or {}
    agent_details = agent.get("Invoice Details") or {}

    results = {}
    all_match = True

    for field in ["Vendor Invoice", "Invoice Date"]:
        gt_val = str(gt_details.get(field, "")).strip()
        agent_val = str(agent_details.get(field, "")).strip()
        match = normalize_string(gt_val) == normalize_string(agent_val)
        if not match:
            all_match = False
        results[field] = {
            "ground_truth": gt_val,
            "agent": agent_val,
            "match": match,
        }

    results["all_match"] = all_match
    return results


def compare_field_group(
    gt: dict, agent: dict, group_config: dict, tolerance: float
) -> dict:
    """Generic field group comparison driven by eval_schema.comparison_groups.

    This is the schema-driven replacement for compare_financials, compare_vendor,
    and compare_header. Each group config specifies the section name and a list of
    fields with their comparison type ("amount" or "string").
    """
    section = group_config.get("section", "")
    gt_section = gt.get(section) or {}
    agent_section = agent.get(section) or {}

    results = {}
    all_match = True

    for field in group_config.get("fields", []):
        field_name = field["name"]
        field_type = field.get("type", "string")

        gt_val = str(gt_section.get(field_name, "")).strip()
        agent_val = str(agent_section.get(field_name, "")).strip()

        if field_type == "amount":
            match = amounts_match(gt_val, agent_val, tolerance)
        else:
            match = normalize_string(gt_val) == normalize_string(agent_val)

        if not match:
            all_match = False

        results[field_name] = {
            "ground_truth": gt_val,
            "agent": agent_val,
            "match": match,
        }

    results["all_match"] = all_match
    return results


def _compare_per_line_fields(
    gt_items: list[dict],
    agent_items: list[dict],
    per_line_fields: list[str],
    per_line_types: dict[str, str],
    tolerance: float,
) -> list[dict]:
    """Compare individual line items field by field, returning a list of diffs."""
    line_diffs = []
    gt_sorted = sorted(gt_items, key=lambda x: x.get("line_number", 0))
    agent_sorted = sorted(agent_items, key=lambda x: x.get("line_number", 0))

    for gt_line, agent_line in zip(gt_sorted, agent_sorted, strict=False):
        diffs = {}
        for field_name in per_line_fields:
            gt_val = str(gt_line.get(field_name, "")).strip()
            agent_val = str(agent_line.get(field_name, "")).strip()

            if per_line_types.get(field_name) == "amount":
                match = amounts_match(gt_val, agent_val, tolerance)
            else:
                match = normalize_string(gt_val) == normalize_string(agent_val)

            if not match:
                diffs[field_name] = {"ground_truth": gt_val, "agent": agent_val}

        if diffs:
            line_diffs.append(
                {
                    "line_number": gt_line.get("line_number"),
                    "differences": diffs,
                }
            )
    return line_diffs


def compare_line_items_generic(
    gt: dict, agent: dict, group_config: dict, tolerance: float
) -> dict:
    """Schema-driven line item comparison using per_line_fields from master data."""
    source_key = group_config.get("source", "Line Items")
    per_line_fields = [f["name"] for f in group_config.get("per_line_fields", [])]
    per_line_types = {
        f["name"]: f.get("type", "string")
        for f in group_config.get("per_line_fields", [])
    }

    gt_items = parse_line_items(gt.get(source_key))
    agent_items = parse_line_items(agent.get(source_key))

    gt_count = len(gt_items)
    agent_count = len(agent_items)
    count_match = gt_count == agent_count

    # Compare item codes (if item_code is in per_line_fields)
    code_field = "item_code" if "item_code" in per_line_fields else None
    if code_field:
        gt_codes = sorted([item.get(code_field, "UNKNOWN") for item in gt_items])
        agent_codes = sorted([item.get(code_field, "UNKNOWN") for item in agent_items])
        codes_match = gt_codes == agent_codes
    else:
        gt_codes = []
        agent_codes = []
        codes_match = True

    # Compare totals for amount fields
    amount_fields = [f for f in per_line_fields if per_line_types.get(f) == "amount"]
    total_checks = {}
    for af in amount_fields:
        gt_total = sum(parse_amount(item.get(af, "0")) or 0 for item in gt_items)
        agent_total = sum(parse_amount(item.get(af, "0")) or 0 for item in agent_items)
        total_checks[af] = {
            "ground_truth": f"{gt_total:.2f}",
            "agent": f"{agent_total:.2f}",
            "match": abs(gt_total - agent_total) <= tolerance,
        }

    # Per-line comparison (by line_number if counts match)
    line_diffs = (
        _compare_per_line_fields(
            gt_items, agent_items, per_line_fields, per_line_types, tolerance
        )
        if count_match
        else []
    )

    all_match = (
        count_match
        and codes_match
        and all(tc["match"] for tc in total_checks.values())
        and len(line_diffs) == 0
    )

    result = {
        "count": {
            "ground_truth": gt_count,
            "agent": agent_count,
            "match": count_match,
        },
        "line_diffs": line_diffs,
        "all_match": all_match,
    }
    if code_field:
        result["item_codes"] = {
            "ground_truth": gt_codes,
            "agent": agent_codes,
            "match": codes_match,
        }
    for af, tc in total_checks.items():
        result[f"total_{af}"] = tc

    return result


def compare_line_items(gt: dict, agent: dict, tolerance: float) -> dict:
    """Compare line items between ground truth and agent output (legacy fallback)."""
    gt_items = parse_line_items(gt.get("Line Items"))
    agent_items = parse_line_items(agent.get("Line Items"))

    gt_count = len(gt_items)
    agent_count = len(agent_items)
    count_match = gt_count == agent_count

    # Compare item codes
    gt_codes = sorted([item.get("item_code", "UNKNOWN") for item in gt_items])
    agent_codes = sorted([item.get("item_code", "UNKNOWN") for item in agent_items])
    codes_match = gt_codes == agent_codes

    # Compare total line cost
    gt_total = sum(parse_amount(item.get("line_cost", "0")) or 0 for item in gt_items)
    agent_total = sum(
        parse_amount(item.get("line_cost", "0")) or 0 for item in agent_items
    )
    total_match = abs(gt_total - agent_total) <= tolerance

    # Compare total tax
    gt_tax = sum(parse_amount(item.get("tax", "0")) or 0 for item in gt_items)
    agent_tax = sum(parse_amount(item.get("tax", "0")) or 0 for item in agent_items)
    tax_match = abs(gt_tax - agent_tax) <= tolerance

    # Per-line comparison (by line_number if counts match)
    line_diffs = []
    if count_match:
        # Sort both by line_number
        gt_sorted = sorted(gt_items, key=lambda x: x.get("line_number", 0))
        agent_sorted = sorted(agent_items, key=lambda x: x.get("line_number", 0))

        for gt_line, agent_line in zip(gt_sorted, agent_sorted, strict=False):
            diffs = {}
            for field in [
                "item_code",
                "description",
                "quantity",
                "unit_cost",
                "line_cost",
                "tax",
                "tax_code",
            ]:
                gt_val = str(gt_line.get(field, "")).strip()
                agent_val = str(agent_line.get(field, "")).strip()

                if field in ["line_cost", "unit_cost", "tax", "quantity"]:
                    match = amounts_match(gt_val, agent_val, tolerance)
                else:
                    match = normalize_string(gt_val) == normalize_string(agent_val)

                if not match:
                    diffs[field] = {"ground_truth": gt_val, "agent": agent_val}

            if diffs:
                line_diffs.append(
                    {
                        "line_number": gt_line.get("line_number"),
                        "differences": diffs,
                    }
                )

    all_match = (
        count_match
        and codes_match
        and total_match
        and tax_match
        and len(line_diffs) == 0
    )

    return {
        "count": {
            "ground_truth": gt_count,
            "agent": agent_count,
            "match": count_match,
        },
        "item_codes": {
            "ground_truth": gt_codes,
            "agent": agent_codes,
            "match": codes_match,
        },
        "total_line_cost": {
            "ground_truth": f"{gt_total:.2f}",
            "agent": f"{agent_total:.2f}",
            "match": total_match,
        },
        "total_tax": {
            "ground_truth": f"{gt_tax:.2f}",
            "agent": f"{agent_tax:.2f}",
            "match": tax_match,
        },
        "line_diffs": line_diffs,
        "all_match": all_match,
    }


# ============================================================================
# LLM-AS-JUDGE EVALUATION
# ============================================================================

LLM_EVAL_PROMPT_TEMPLATE = """You are evaluating a {domain_name} agent's output against ground truth.

Compare these two JSON documents and produce a holistic alignment verdict.

===GROUND TRUTH===
{ground_truth}

===AGENT OUTPUT===
{agent_output}

===DETERMINISTIC MISMATCHES ALREADY DETECTED===
{mismatches}

VERDICT CRITERIA:

ALIGNED — Agent output matches ground truth in all material respects.
  The processing decision is correct. Financial amounts match. Vendor info matches.
  Minor formatting differences (commas, whitespace, date format) are acceptable.
  Outcome message timestamp/wording differences are acceptable.

PARTIALLY_ALIGNED — The processing decision (accept/reject) is correct, but
  there are differences in non-critical fields such as line item descriptions,
  item code classifications, or minor amount rounding.

NOT_ALIGNED — The processing decision is wrong (accepted when should reject
  or vice versa), OR there are critical financial errors (wrong totals, wrong
  tax amounts), OR vendor identification is wrong.

Respond with ONLY valid JSON, no markdown:
{{
  "verdict": "ALIGNED" or "PARTIALLY_ALIGNED" or "NOT_ALIGNED",
  "reason": "One sentence explaining the verdict"
}}"""


def llm_evaluate(
    model: "GenerativeModel",
    ground_truth: dict,
    agent_output: dict,
    mismatches: list[str],
    domain_name: str = "invoice processing",
) -> dict | None:
    """Run a single LLM call to get holistic alignment verdict."""
    prompt = LLM_EVAL_PROMPT_TEMPLATE.format(
        domain_name=domain_name,
        ground_truth=json.dumps(ground_truth, indent=2),
        agent_output=json.dumps(agent_output, indent=2),
        mismatches="\n".join(f"- {m}" for m in mismatches)
        if mismatches
        else "None detected",
    )

    try:
        response = model.generate_content(prompt)
        text = response.text.strip()

        # Strip markdown code fences if present
        if text.startswith("```"):
            match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
            if match:
                text = match.group(1).strip()

        result = json.loads(text)

        # Validate verdict value
        verdict = result.get("verdict", "").upper()
        if verdict not in ("ALIGNED", "PARTIALLY_ALIGNED", "NOT_ALIGNED"):
            result["verdict"] = "NOT_ALIGNED"
            result["reason"] = (
                result.get("reason", "")
                + f" (original verdict '{verdict}' was invalid)"
            )

        return result

    except Exception as e:
        return {"verdict": "ERROR", "reason": str(e)}


# ============================================================================
# CASE EVALUATION
# ============================================================================


def _run_comparison_groups(
    gt: dict, agent: dict, master: MasterData, tolerance: float
) -> dict[str, dict]:
    """Run all schema-driven comparison groups and return results keyed by group ID."""
    group_results = {}
    for group in master.get_eval_comparison_groups():
        group_id = group.get("id", "")
        if group.get("type", "") == "array":
            group_results[group_id] = compare_line_items_generic(
                gt, agent, group, tolerance
            )
        else:
            group_results[group_id] = compare_field_group(gt, agent, group, tolerance)
    return group_results


def _collect_schema_mismatches(
    decision: dict, group_results: dict[str, dict]
) -> list[str]:
    """Collect mismatch descriptions from schema-driven comparison results."""
    mismatches = []
    if not decision["match"]:
        mismatches.append(
            f"Decision: {decision['ground_truth_decision']} vs {decision['agent_decision']}"
        )
    for _group_id, result in group_results.items():
        if result.get("all_match"):
            continue
        for key, val in result.items():
            if isinstance(val, dict) and "match" in val and not val["match"]:
                mismatches.append(
                    f"{key}: {val.get('ground_truth', '?')} vs {val.get('agent', '?')}"
                )
    return mismatches


def _evaluate_schema_driven(
    case_id: str,
    gt: dict,
    agent: dict,
    decision: dict,
    master: MasterData,
    tolerance: float,
) -> dict:
    """Evaluate a case using schema-driven comparison groups from master data."""
    group_results = _run_comparison_groups(gt, agent, master, tolerance)
    mismatches = _collect_schema_mismatches(decision, group_results)

    all_correct = decision["match"] and all(
        r.get("all_match", True) for r in group_results.values()
    )

    result_dict = {
        "case_id": case_id,
        "status": "PASS" if all_correct else "FAIL",
        "all_correct": all_correct,
        "decision": decision,
        "mismatches": mismatches,
    }
    for gid, result in group_results.items():
        result_dict[gid] = result

    # Keep backward-compatible keys for the standard invoice groups
    for compat_key in ("financials", "vendor", "header", "line_items"):
        if compat_key in group_results:
            result_dict[compat_key] = group_results[compat_key]

    return result_dict


def _evaluate_legacy(
    case_id: str,
    gt: dict,
    agent: dict,
    decision: dict,
    tolerance: float,
) -> dict:
    """Evaluate a case using hardcoded invoice-specific comparators (legacy fallback)."""
    financials = compare_financials(gt, agent, tolerance)
    vendor = compare_vendor(gt, agent)
    header = compare_header(gt, agent)
    line_items = compare_line_items(gt, agent, tolerance)

    all_correct = (
        decision["match"]
        and financials["all_match"]
        and vendor["all_match"]
        and header["all_match"]
        and line_items["all_match"]
    )

    mismatches = _collect_legacy_mismatches(
        decision, financials, vendor, header, line_items
    )

    return {
        "case_id": case_id,
        "status": "PASS" if all_correct else "FAIL",
        "all_correct": all_correct,
        "decision": decision,
        "financials": financials,
        "vendor": vendor,
        "header": header,
        "line_items": line_items,
        "mismatches": mismatches,
    }


def _collect_field_mismatches(section: dict, labels: list[str]) -> list[str]:
    """Collect mismatch strings for a list of field labels from a comparison section."""
    mismatches = []
    for label in labels:
        if not section[label]["match"]:
            mismatches.append(
                f"{label}: {section[label]['ground_truth']} vs {section[label]['agent']}"
            )
    return mismatches


def _collect_line_item_mismatches(line_items: dict) -> list[str]:
    """Collect mismatch strings from line item comparison results."""
    mismatches = []
    if not line_items["count"]["match"]:
        mismatches.append(
            f"Line item count: {line_items['count']['ground_truth']} vs {line_items['count']['agent']}"
        )
    if not line_items["item_codes"]["match"]:
        mismatches.append("Item codes differ")
    if not line_items["total_line_cost"]["match"]:
        mismatches.append(
            f"Line cost total: {line_items['total_line_cost']['ground_truth']} vs {line_items['total_line_cost']['agent']}"
        )
    return mismatches


def _collect_legacy_mismatches(
    decision: dict,
    financials: dict,
    vendor: dict,
    header: dict,
    line_items: dict,
) -> list[str]:
    """Collect mismatch descriptions from legacy comparator results."""
    mismatches = []
    if not decision["match"]:
        mismatches.append(
            f"Decision: {decision['ground_truth_decision']} vs {decision['agent_decision']}"
        )
    mismatches.extend(
        _collect_field_mismatches(
            financials,
            ["Invoice Total", "Pretax Total", "Tax Amount", "Currency"],
        )
    )
    mismatches.extend(_collect_field_mismatches(vendor, ["Vendor Name", "Tax ID"]))
    mismatches.extend(
        _collect_field_mismatches(header, ["Vendor Invoice", "Invoice Date"])
    )
    mismatches.extend(_collect_line_item_mismatches(line_items))
    return mismatches


def evaluate_case(
    case_id: str,
    gt_file: Path,
    agent_file: Path,
    tolerance: float,
    llm_model: Any | None = None,
    master: MasterData | None = None,
) -> dict:
    """Evaluate a single case by comparing ground truth and agent output.

    When master data is provided, uses schema-driven comparison groups.
    Otherwise falls back to the hardcoded invoice-specific comparators.
    """
    # Load files
    try:
        gt = json.loads(gt_file.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "case_id": case_id,
            "status": "ERROR",
            "error": f"Failed to load ground truth: {e}",
        }

    try:
        agent = json.loads(agent_file.read_text(encoding="utf-8"))
    except Exception as e:
        return {
            "case_id": case_id,
            "status": "ERROR",
            "error": f"Failed to load agent output: {e}",
        }

    # Decision comparison (always schema-driven when master data available)
    decision = compare_decision(gt, agent, master)

    # Field group comparisons — schema-driven or legacy fallback
    if master:
        result_dict = _evaluate_schema_driven(
            case_id, gt, agent, decision, master, tolerance
        )
    else:
        result_dict = _evaluate_legacy(case_id, gt, agent, decision, tolerance)

    # LLM alignment verdict (optional)
    llm_verdict = None
    if llm_model is not None:
        domain_name = master.display_name if master else "invoice processing"
        llm_verdict = llm_evaluate(
            llm_model, gt, agent, result_dict["mismatches"], domain_name
        )
    result_dict["llm_verdict"] = llm_verdict

    return result_dict


# ============================================================================
# AGGREGATE STATISTICS
# ============================================================================


def _compute_decision_matrix(evaluated: list[dict]) -> dict[str, int]:
    """Compute the confusion matrix for accept/reject decisions."""
    matrix = {"TP": 0, "FP": 0, "FN": 0, "TN": 0}
    for r in evaluated:
        gt_d = r["decision"]["ground_truth_decision"]
        ag_d = r["decision"]["agent_decision"]
        if gt_d == "ACCEPT" and ag_d == "ACCEPT":
            matrix["TP"] += 1
        elif gt_d == "REJECT" and ag_d == "REJECT":
            matrix["TN"] += 1
        elif gt_d == "REJECT" and ag_d == "ACCEPT":
            matrix["FP"] += 1
        elif gt_d == "ACCEPT" and ag_d == "REJECT":
            matrix["FN"] += 1
    return matrix


def _compute_group_and_field_stats_schema(
    evaluated: list[dict], master: MasterData, total: int
) -> tuple:
    """Compute group-level and field-level accuracy using schema-driven config."""
    group_accuracy = {}
    field_stats = {}

    for group in master.get_eval_comparison_groups():
        group_id = group.get("id", "")
        group_display = group.get("display_name", group_id)
        group_type = group.get("type", "")

        correct = sum(
            1 for r in evaluated if r.get(group_id, {}).get("all_match", True)
        )
        group_accuracy[group_id] = {
            "display_name": group_display,
            "correct": correct,
            "total": total,
            "accuracy": correct / total,
        }

        if group_type != "array":
            for field in group.get("fields", []):
                fname = field["name"]
                fc = sum(
                    1
                    for r in evaluated
                    if r.get(group_id, {}).get(fname, {}).get("match", True)
                )
                field_stats[fname] = {
                    "correct": fc,
                    "total": total,
                    "accuracy": fc / total,
                }

    return group_accuracy, field_stats


def _compute_group_and_field_stats_legacy(evaluated: list[dict], total: int) -> tuple:
    """Compute group-level and field-level accuracy using legacy hardcoded fields."""
    group_accuracy = {}
    field_stats = {}

    for group_key in ["financials", "vendor", "header", "line_items"]:
        correct = sum(
            1 for r in evaluated if r.get(group_key, {}).get("all_match", True)
        )
        group_accuracy[group_key] = {
            "display_name": group_key.replace("_", " ").title(),
            "correct": correct,
            "total": total,
            "accuracy": correct / total,
        }

    legacy_field_groups = [
        (
            "financials",
            ["Invoice Total", "Pretax Total", "Tax Amount", "Currency"],
        ),
        ("vendor", ["Vendor Name", "Tax ID"]),
        ("header", ["Vendor Invoice", "Invoice Date"]),
    ]
    for section_key, fields in legacy_field_groups:
        for field in fields:
            correct = sum(
                1
                for r in evaluated
                if r.get(section_key, {}).get(field, {}).get("match", True)
            )
            field_stats[field] = {
                "correct": correct,
                "total": total,
                "accuracy": correct / total,
            }

    return group_accuracy, field_stats


def _compute_llm_stats(evaluated: list[dict]) -> dict | None:
    """Compute LLM alignment statistics from evaluation results."""
    llm_results = [
        r
        for r in evaluated
        if r.get("llm_verdict") and r["llm_verdict"].get("verdict") != "ERROR"
    ]
    if not llm_results:
        return None

    verdict_counts = {"ALIGNED": 0, "PARTIALLY_ALIGNED": 0, "NOT_ALIGNED": 0}
    for r in llm_results:
        v = r["llm_verdict"]["verdict"]
        if v in verdict_counts:
            verdict_counts[v] += 1
    llm_total = len(llm_results)
    return {
        "total_judged": llm_total,
        "aligned": verdict_counts["ALIGNED"],
        "partially_aligned": verdict_counts["PARTIALLY_ALIGNED"],
        "not_aligned": verdict_counts["NOT_ALIGNED"],
        "alignment_rate": verdict_counts["ALIGNED"] / llm_total,
        "partial_or_better_rate": (
            verdict_counts["ALIGNED"] + verdict_counts["PARTIALLY_ALIGNED"]
        )
        / llm_total,
    }


def compute_aggregate_stats(
    results: list[dict], master: MasterData | None = None
) -> dict:
    """Compute aggregate statistics across all evaluated cases.

    When master data is provided, dynamically computes per-group and per-field
    accuracy from eval_schema.comparison_groups instead of hardcoded field names.
    """
    evaluated = [r for r in results if r.get("status") != "ERROR"]
    errors = [r for r in results if r.get("status") == "ERROR"]

    if not evaluated:
        return {"total": len(results), "evaluated": 0, "errors": len(errors)}

    total = len(evaluated)
    passed = sum(1 for r in evaluated if r["all_correct"])

    decision_correct = sum(1 for r in evaluated if r["decision"]["match"])
    decision_matrix = _compute_decision_matrix(evaluated)

    if master:
        group_accuracy, field_stats = _compute_group_and_field_stats_schema(
            evaluated, master, total
        )
    else:
        group_accuracy, field_stats = _compute_group_and_field_stats_legacy(
            evaluated, total
        )

    llm_stats = _compute_llm_stats(evaluated)

    return {
        "total": len(results),
        "evaluated": total,
        "errors": len(errors),
        "passed": passed,
        "failed": total - passed,
        "pass_rate": passed / total,
        "decision_accuracy": decision_correct / total,
        "decision_matrix": decision_matrix,
        "group_accuracy": group_accuracy,
        "field_stats": field_stats,
        "llm_alignment": llm_stats,
    }


def _print_decision_stats(stats: dict) -> None:
    """Print decision accuracy and confusion matrix metrics."""
    print(f"\n  DECISION ACCURACY: {stats['decision_accuracy']:.1%}")
    dm = stats["decision_matrix"]
    print(f"    TP={dm['TP']}  FP={dm['FP']}  FN={dm['FN']}  TN={dm['TN']}")
    if dm["TP"] + dm["FP"] > 0:
        precision = dm["TP"] / (dm["TP"] + dm["FP"])
        print(f"    Precision: {precision:.3f}")
    if dm["TP"] + dm["FN"] > 0:
        recall = dm["TP"] / (dm["TP"] + dm["FN"])
        print(f"    Recall:    {recall:.3f}")
    if dm["TP"] + dm["FP"] > 0 and dm["TP"] + dm["FN"] > 0:
        f1 = (
            2 * precision * recall / (precision + recall)
            if (precision + recall) > 0
            else 0
        )
        print(f"    F1 Score:  {f1:.3f}")


def _print_group_and_field_accuracy(stats: dict) -> None:
    """Print group-level and field-level accuracy sections."""
    group_acc = stats.get("group_accuracy", {})
    if group_acc:
        print("\n  GROUP ACCURACY:")
        for group_id, gstat in group_acc.items():
            display = gstat.get("display_name", group_id)
            print(f"    {display:24s} {gstat['accuracy']:.1%}")
    elif "financial_accuracy" in stats:
        print(f"\n  FINANCIAL ACCURACY: {stats['financial_accuracy']:.1%}")
        print(f"  VENDOR ACCURACY:    {stats['vendor_accuracy']:.1%}")
        print(f"  LINE ITEM ACCURACY: {stats['line_item_accuracy']:.1%}")

    print("\n  FIELD-LEVEL ACCURACY:")
    for field, fstat in stats["field_stats"].items():
        bar = "#" * int(fstat["accuracy"] * 20)
        print(
            f"    {field:20s} {fstat['correct']:3d}/{fstat['total']:3d}  {fstat['accuracy']:.1%}  {bar}"
        )


def _print_llm_and_case_details(stats: dict, results: list[dict]) -> None:
    """Print LLM alignment stats, failed cases, and error cases."""
    llm = stats.get("llm_alignment")
    if llm:
        print("\n  LLM ALIGNMENT (Gemini judge):")
        print(f"    ALIGNED:           {llm['aligned']}/{llm['total_judged']}")
        print(
            f"    PARTIALLY_ALIGNED: {llm['partially_aligned']}/{llm['total_judged']}"
        )
        print(f"    NOT_ALIGNED:       {llm['not_aligned']}/{llm['total_judged']}")
        print(f"    Alignment rate:    {llm['alignment_rate']:.1%}")
        print(f"    Partial+ rate:     {llm['partial_or_better_rate']:.1%}")

        not_aligned = [
            r
            for r in results
            if r.get("llm_verdict", {}).get("verdict") == "NOT_ALIGNED"
        ]
        if not_aligned:
            print("\n    NOT_ALIGNED cases:")
            for r in not_aligned:
                reason = r["llm_verdict"].get("reason", "")
                print(f"      {r['case_id']}: {reason}")

    failed = [r for r in results if r.get("status") == "FAIL"]
    if failed:
        print("\n  FAILED CASES:")
        for r in failed:
            print(f"    {r['case_id']}:")
            for m in r["mismatches"]:
                print(f"      - {m}")

    error_cases = [r for r in results if r.get("status") == "ERROR"]
    if error_cases:
        print("\n  ERROR CASES:")
        for r in error_cases:
            print(f"    {r['case_id']}: {r.get('error', 'Unknown error')}")


def print_report(stats: dict, results: list[dict]) -> None:
    """Print evaluation report to console."""
    print()
    print("=" * 70)
    print("EVALUATION REPORT")
    print("=" * 70)

    if stats["evaluated"] == 0:
        print(f"\nNo cases evaluated. {stats['errors']} error(s).")
        return

    total = stats["evaluated"]

    print(f"\n  Cases:    {stats['evaluated']} evaluated, {stats['errors']} errors")
    print(f"  Passed:   {stats['passed']}/{total} ({stats['pass_rate']:.1%})")
    print(f"  Failed:   {stats['failed']}/{total}")

    _print_decision_stats(stats)
    _print_group_and_field_accuracy(stats)
    _print_llm_and_case_details(stats, results)

    print()
    print("=" * 70)


# ============================================================================
# MAIN
# ============================================================================


def _parse_args() -> argparse.Namespace:
    """Parse and return command-line arguments."""
    parser = argparse.ArgumentParser(
        description="Schema-driven evaluation of document processing agents against ground truth"
    )
    parser.add_argument(
        "--ground-truth",
        "-g",
        type=str,
        required=True,
        help='Directory containing ground truth case folders (e.g., "exemplary_data")',
    )
    parser.add_argument(
        "--agent-output",
        "-a",
        type=str,
        required=True,
        help='Directory containing agent output case folders (e.g., "output")',
    )
    parser.add_argument(
        "--master-data",
        "-m",
        type=str,
        default=None,
        help="Path to master_data.yaml or .json (auto-detected if not provided)",
    )
    parser.add_argument(
        "--case",
        "-c",
        type=str,
        default=None,
        help="Evaluate a single case by folder name (e.g., case_001)",
    )
    parser.add_argument(
        "--num-cases",
        "-n",
        type=int,
        default=0,
        help="Limit number of cases to evaluate (0 = all)",
    )
    parser.add_argument(
        "--tolerance",
        "-t",
        type=float,
        default=DEFAULT_TOLERANCE,
        help=f"Financial amount tolerance in dollars (default: {DEFAULT_TOLERANCE})",
    )
    parser.add_argument(
        "--output",
        "-o",
        type=str,
        default=None,
        help="Output file for evaluation results JSON",
    )
    parser.add_argument(
        "--skip-llm",
        action="store_true",
        help="Skip LLM alignment evaluation (deterministic only, no cost)",
    )
    return parser.parse_args()


def _load_master(master_data_path: str | None) -> MasterData | None:
    """Load master data, returning None with a warning on failure."""
    try:
        return load_master_data(master_data_path)
    except FileNotFoundError:
        print("  Warning: Master data file not found. Using legacy comparators.")
    except Exception as e:
        print(f"  Warning: Failed to load master data ({e}). Using legacy comparators.")
    return None


def _resolve_directories(args: argparse.Namespace) -> tuple:
    """Resolve and validate ground truth and agent output directories."""
    gt_dir = Path(args.ground_truth)
    if not gt_dir.is_absolute():
        gt_dir = PROJECT_ROOT / gt_dir

    agent_dir = Path(args.agent_output)
    if not agent_dir.is_absolute():
        if (PROJECT_ROOT / agent_dir).exists():
            agent_dir = PROJECT_ROOT / agent_dir
        else:
            agent_dir = SCRIPT_DIR / agent_dir

    if not gt_dir.exists():
        print(f"Error: Ground truth directory not found: {gt_dir}")
        sys.exit(1)
    if not agent_dir.exists():
        print(f"Error: Agent output directory not found: {agent_dir}")
        sys.exit(1)

    return gt_dir, agent_dir


def _collect_case_ids(
    args: argparse.Namespace, gt_dir: Path, agent_dir: Path
) -> list[str]:
    """Collect and return the list of case IDs to evaluate."""
    if args.case:
        case_ids = [args.case]
    else:
        gt_cases = {d.name for d in gt_dir.iterdir() if d.is_dir()}
        agent_cases = {d.name for d in agent_dir.iterdir() if d.is_dir()}
        common = sorted(gt_cases & agent_cases)

        if not common:
            print("No matching case folders found between:")
            print(f"  Ground truth: {gt_dir} ({len(gt_cases)} folders)")
            print(f"  Agent output: {agent_dir} ({len(agent_cases)} folders)")
            if gt_cases - agent_cases:
                print(f"  In ground truth only: {sorted(gt_cases - agent_cases)[:5]}")
            if agent_cases - gt_cases:
                print(f"  In agent output only: {sorted(agent_cases - gt_cases)[:5]}")
            sys.exit(1)

        case_ids = common

    if args.num_cases > 0:
        case_ids = case_ids[: args.num_cases]

    return case_ids


def _run_evaluation_loop(
    case_ids: list[str],
    gt_dir: Path,
    agent_dir: Path,
    tolerance: float,
    llm_model: Any | None,
    master: MasterData | None,
) -> list[dict]:
    """Run evaluation on each case and return the list of results."""
    results = []
    for idx, case_id in enumerate(case_ids, 1):
        gt_file = gt_dir / case_id / "Postprocessing_Data.json"
        agent_file = agent_dir / case_id / "Postprocessing_Data.json"

        if not gt_file.exists():
            results.append(
                {
                    "case_id": case_id,
                    "status": "ERROR",
                    "error": "Ground truth file not found",
                }
            )
            print(f"  [{idx}/{len(case_ids)}] {case_id}: ERROR (no ground truth)")
            continue
        if not agent_file.exists():
            results.append(
                {
                    "case_id": case_id,
                    "status": "ERROR",
                    "error": "Agent output file not found",
                }
            )
            print(f"  [{idx}/{len(case_ids)}] {case_id}: ERROR (no agent output)")
            continue

        result = evaluate_case(
            case_id, gt_file, agent_file, tolerance, llm_model, master
        )
        results.append(result)

        # evaluate_case returns only case_id/status/error when a file fails to
        # load (bad JSON), so it has no "all_correct" key on that path.
        if result.get("status") == "ERROR":
            print(
                f"  [{idx}/{len(case_ids)}] {case_id}: ERROR "
                f"({result.get('error', 'unknown error')})"
            )
            continue

        status_icon = "PASS" if result["all_correct"] else "FAIL"
        llm_tag = ""
        if result.get("llm_verdict"):
            llm_tag = f" [{result['llm_verdict']['verdict']}]"
        detail = ""
        if not result["all_correct"]:
            detail = f"  ({', '.join(result['mismatches'][:2])})"
        print(f"  [{idx}/{len(case_ids)}] {case_id}: {status_icon}{llm_tag}{detail}")

    return results


def _save_results(
    args: argparse.Namespace,
    stats: dict,
    results: list[dict],
    gt_dir: Path,
    agent_dir: Path,
    llm_model: Any | None,
    master: MasterData | None,
) -> None:
    """Save evaluation results to a JSON file."""
    if args.output:
        output_file = Path(args.output)
        output_file.parent.mkdir(parents=True, exist_ok=True)
    else:
        EVAL_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        output_file = EVAL_OUTPUT_DIR / f"eval_{timestamp}.json"

    output_json = {
        "timestamp": datetime.now().isoformat(),
        "config": {
            "domain": master.domain if master else "invoice_processing",
            "display_name": master.display_name if master else "Invoice Processing",
            "master_data": str(master.source_path)
            if master and master.source_path
            else None,
            "ground_truth_dir": str(gt_dir),
            "agent_output_dir": str(agent_dir),
            "tolerance": args.tolerance,
            "llm_judge": llm_model is not None,
        },
        "statistics": stats,
        "results": results,
    }

    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(output_json, f, indent=2, ensure_ascii=False)

    print(f"Results saved to: {output_file}")


def main():
    args = _parse_args()

    master = _load_master(args.master_data)

    gt_dir, agent_dir = _resolve_directories(args)

    case_ids = _collect_case_ids(args, gt_dir, agent_dir)

    # Initialize LLM if needed
    llm_model = None
    if not args.skip_llm:
        llm_model = _init_llm()
        if llm_model is None:
            print(
                "\n  Warning: LLM unavailable (missing packages or PROJECT_ID). "
                "Running deterministic only."
            )
            print("  Install: pip install google-cloud-aiplatform python-dotenv")

    domain_name = master.display_name if master else "Invoice Processing"
    print("=" * 70)
    print(f"{domain_name.upper()} AGENT EVALUATION")
    print("=" * 70)
    print(f"  Ground truth: {gt_dir}")
    print(f"  Agent output: {agent_dir}")
    if master:
        print(f"  Master data:  {master.source_path}")
    print(f"  Cases:        {len(case_ids)}")
    print(f"  Tolerance:    ${args.tolerance}")
    print(f"  LLM judge:    {'enabled' if llm_model else 'disabled'}")

    results = _run_evaluation_loop(
        case_ids, gt_dir, agent_dir, args.tolerance, llm_model, master
    )

    stats = compute_aggregate_stats(results, master)
    print_report(stats, results)

    _save_results(args, stats, results, gt_dir, agent_dir, llm_model, master)


if __name__ == "__main__":
    main()
