#!/usr/bin/env python3
"""Adaptive Learning Framework (ALF) - Phase 1: Expert-Led Rule Evaluation Engine

This module implements a hybrid Deterministic + LLM correction layer that wraps
the Acting Agent (acting_agent). Rule CONDITIONS are evaluated deterministically.
When a rule fires, its ACTIONS are executed by calling Gemini Pro to continue the
processing pipeline from where the acting agent terminated early.

Architecture:
    ┌──────────────────────────────────────────────────────────┐
    │  Probabilistic Execution Zone (Acting Agent)             │
    │  Extraction → Validation → Transformation → Decision     │
    │  Output: Provisional JSON  (may terminate early)         │
    └─────────────────────┬────────────────────────────────────┘
                          │
                          ▼
    ┌──────────────────────────────────────────────────────────┐
    │  ALF Rule Evaluation Layer                               │
    │                                                          │
    │  1. Load Structured Rule Base (rule_base.json)           │
    │  2. DETERMINISTIC: Evaluate conditions against output    │
    │  3. LLM-DRIVEN: On match, call Gemini Pro to continue   │
    │     the remaining pipeline steps the agent skipped       │
    │  4. Produce complete Revised Output                      │
    │                                                          │
    │  Guarantees:                                             │
    │  - Conditions are deterministic (no LLM in matching)     │
    │  - Mutually Exclusive Matching (≤1 rule fires per scope) │
    │  - Actions completed by LLM (full pipeline continuation) │
    │  - Auditable (full trace + LLM prompt/response logged)   │
    └──────────────────────────────────────────────────────────┘

Usage:
    from alf_engine import ALFEngine

    engine = ALFEngine("rule_base.json")
    revised_output, audit_log = engine.evaluate(provisional_output, case_context)
"""

import argparse
import copy
import json
import logging
import os
import re
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

logger = logging.getLogger("ALF")

# Resolve paths: shared_libraries/ -> invoice_processing/ (package root with data/ inside)
SCRIPT_DIR = Path(__file__).parent  # shared_libraries/
AGENT_PKG_DIR = SCRIPT_DIR.parent  # invoice_processing/ package root
ALF_OUT_DIR = AGENT_PKG_DIR / "data" / "alf_output"

# Recipe root for .env resolution (holds .env / .env.example beside the package)
PROJECT_ROOT = AGENT_PKG_DIR.parent

# ---------------------------------------------------------------------------
# Master data loader (optional — provides domain-agnostic configuration)
# ---------------------------------------------------------------------------
sys.path.insert(0, str(SCRIPT_DIR))  # shared_libraries/ contains master_data_loader.py
try:
    from master_data_loader import load_master_data

    _MASTER_DATA = load_master_data()
except Exception:
    _MASTER_DATA = None

# Default artifact map (fallback when no master data)
_DEFAULT_ARTIFACT_MAP = {
    "classification": "01_classification.json",
    "extraction": "02_extraction.json",
    "phase1": "03_phase1_validation.json",
    "phase2": "04_phase2_validation.json",
    "phase3": "05_phase3_validation.json",
    "phase4": "06_phase4_validation.json",
    "transformer": "07_transformation.json",
    "decision": "08_decision.json",
    "audit_log": "09_audit_log.json",
}


def _get_artifact_map() -> dict:
    """Get artifact filename mapping from master data or fallback."""
    if _MASTER_DATA and _MASTER_DATA.get_agent_file_map():
        md_map = _MASTER_DATA.get_agent_file_map()
        result = {}
        for key, filename in md_map.items():
            # Normalize keys: master data uses "final_decision", ALF uses "decision"
            if key == "final_decision":
                result["decision"] = filename
            elif key == "transformation":
                result["transformer"] = filename
            elif key == "postprocessing":
                continue  # postprocessing handled separately
            else:
                result[key] = filename
        return result
    return _DEFAULT_ARTIFACT_MAP


# ============================================================================
# SCHEMA VERSION
# ============================================================================

SCHEMA_VERSION = "2.0.0"

SUPPORTED_CONDITION_OPERATORS = {
    "equals",  # Exact value match (case-insensitive for strings)
    "not_equals",  # Value does not match
    "contains",  # String contains substring (case-insensitive)
    "not_contains",  # String does not contain substring
    "in_list",  # Value is one of a list
    "not_in_list",  # Value is not in list
    "greater_than",  # Numeric comparison
    "less_than",  # Numeric comparison
    "greater_equal",  # Numeric comparison
    "less_equal",  # Numeric comparison
    "regex_match",  # Regex pattern match
    "is_true",  # Boolean true check
    "is_false",  # Boolean false check
    "is_null",  # None/null check
    "is_not_null",  # Not None/null check
    "starts_with",  # String starts with prefix
    "any_item_contains",  # Any item in array field contains substring
    "first_word_equals",  # First significant word of string matches
    "length_equals",  # String/array length equals
    "length_greater",  # String/array length greater than
    "length_less",  # String/array length less than
}

SUPPORTED_ACTION_TYPES = {
    # --- LLM-driven actions ---
    "llm_continue_processing",  # Call Gemini Pro to continue the full pipeline
    "llm_patch_fields",  # Call Gemini Pro to surgically correct specific fields
    # --- Deterministic actions (supplementary) ---
    "set_field",  # Set a field to a specific value
    "override_decision",  # Override the agent's final decision
    "override_validation",  # Override a specific validation step result
    "recalculate_field",  # Recalculate a derived field
    "add_to_list",  # Add a value to a list field
    "remove_from_list",  # Remove a value from a list field
    "set_nested_field",  # Set a deeply nested field using dot notation
    "conditional_set",  # Set field only if another condition holds
    "append_note",  # Append text to a notes/memo field
}

# ============================================================================
# LLM CONFIGURATION
# ============================================================================

# Google Cloud / Agent Platform (Vertex AI) config (mirrors acting_agent settings)
try:
    from dotenv import load_dotenv

    _env_file = PROJECT_ROOT / ".env"
    if _env_file.exists():
        load_dotenv(_env_file)
    else:
        load_dotenv()
except ImportError:
    pass


def _get_llm_project_id():
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        try:
            import google.auth

            _, project = google.auth.default()
        except Exception:
            pass
    return project


def _get_llm_location():
    return os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")


def _get_llm_model():
    return os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-pro")


def _get_llm_call_delay():
    return float(os.getenv("API_CALL_DELAY_SECONDS", "1.0"))


# ============================================================================
# CONDITION EVALUATOR
# ============================================================================


class ConditionEvaluator:
    """Evaluates structured conditions against case data.

    Each condition is a dict with:
      - field: JSON path to the field (dot notation, e.g., "invoice.vendor_name")
      - operator: One of SUPPORTED_CONDITION_OPERATORS
      - value: Expected value (operator-dependent)

    Conditions within a rule are AND-joined (all must be true).
    """

    @staticmethod
    def resolve_field(data: dict, field_path: str) -> Any:
        """Resolve a dot-notation field path against a nested dict.

        Examples:
            resolve_field({"a": {"b": 1}}, "a.b") → 1
            resolve_field({"items": [{"x": 1}]}, "items.0.x") → 1
        """
        current = data
        for part in field_path.split("."):
            if current is None:
                return None
            if isinstance(current, dict):
                current = current.get(part)
            elif isinstance(current, (list, tuple)):
                try:
                    idx = int(part)
                    current = current[idx] if idx < len(current) else None
                except (ValueError, IndexError):
                    return None
            else:
                return None
        return current

    @staticmethod
    def _resolve_dynamic_value(value: Any, data: dict) -> Any:
        """Resolve dynamic field references in condition values.

        If the value is a string matching the pattern _DYNAMIC_<field_path>_,
        resolve it to the actual value at that field path in the data context.

        Examples:
            "_DYNAMIC_preprocessing.vendor_name_" -> "GLOBAL FOOD EQUIPMENT"
            "_DYNAMIC_extraction.invoice.abn_"    -> "11089895732"
            "static value"                        -> "static value" (unchanged)
        """
        if not isinstance(value, str):
            return value
        if value.startswith("_DYNAMIC_") and value.endswith("_"):
            field_path = value[len("_DYNAMIC_") : -1]
            resolved = ConditionEvaluator.resolve_field(data, field_path)
            if resolved is not None:
                return resolved
            logger.warning(
                f"Dynamic value '{value}' resolved to None (field_path='{field_path}')"
            )
            return None
        return value

    @staticmethod
    def evaluate_single(data: dict, condition: dict) -> bool:
        """Evaluate a single condition against data.

        Args:
            data: The full case context (provisional output + intermediate artifacts)
            condition: A condition dict with field, operator, value keys

        Returns:
            True if the condition is satisfied
        """
        field_path = condition.get("field", "")
        operator = condition.get("operator", "")
        expected = condition.get("value")

        actual = ConditionEvaluator.resolve_field(data, field_path)

        # Resolve dynamic field references in expected value.
        # Values like "_DYNAMIC_preprocessing.vendor_name_" are resolved
        # to the actual value of that field path from the context data.
        expected = ConditionEvaluator._resolve_dynamic_value(expected, data)

        if operator not in SUPPORTED_CONDITION_OPERATORS:
            logger.warning(f"Unsupported operator: {operator}")
            return False

        try:
            return ConditionEvaluator._apply_operator(operator, actual, expected)
        except Exception as e:
            logger.warning(
                f"Condition evaluation error: {e} "
                f"(field={field_path}, op={operator}, "
                f"actual={actual}, expected={expected})"
            )
            return False

    @staticmethod
    def _apply_operator(operator: str, actual: Any, expected: Any) -> bool:
        """Core operator dispatch."""
        handler = _OPERATOR_DISPATCH.get(operator)
        if handler is not None:
            return handler(actual, expected)
        return False

    @staticmethod
    def evaluate_all(data: dict, conditions: list[dict]) -> tuple[bool, list[dict]]:
        """Evaluate all conditions (AND-joined).

        Returns:
            (all_passed, evaluation_details)
        """
        details = []
        all_passed = True

        for cond in conditions:
            passed = ConditionEvaluator.evaluate_single(data, cond)
            # Show the resolved expected value in the audit trace so
            # dynamic references (e.g. _DYNAMIC_preprocessing.vendor_name_)
            # display the actual resolved value rather than the placeholder.
            raw_expected = cond.get("value")
            resolved_expected = ConditionEvaluator._resolve_dynamic_value(
                raw_expected, data
            )
            details.append(
                {
                    "field": cond.get("field"),
                    "operator": cond.get("operator"),
                    "expected": resolved_expected,
                    "actual": ConditionEvaluator.resolve_field(
                        data, cond.get("field", "")
                    ),
                    "passed": passed,
                }
            )
            if not passed:
                all_passed = False

        return all_passed, details


# ---------------------------------------------------------------------------
# Operator handler functions for ConditionEvaluator._apply_operator dispatch
# ---------------------------------------------------------------------------


def _op_is_null(actual: Any, _expected: Any) -> bool:
    return actual is None


def _op_is_not_null(actual: Any, _expected: Any) -> bool:
    return actual is not None


def _op_is_true(actual: Any, _expected: Any) -> bool:
    return bool(actual) is True


def _op_is_false(actual: Any, _expected: Any) -> bool:
    return not bool(actual)


def _op_equals(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.strip().lower() == expected.strip().lower()
    return actual == expected


def _op_not_equals(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str) and isinstance(expected, str):
        return actual.strip().lower() != expected.strip().lower()
    return actual != expected


def _op_contains(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return str(expected).lower() in str(actual).lower()


def _op_not_contains(actual: Any, expected: Any) -> bool:
    if actual is None:
        return True
    return str(expected).lower() not in str(actual).lower()


def _op_starts_with(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return str(actual).lower().startswith(str(expected).lower())


def _op_in_list(actual: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        if isinstance(actual, str):
            return actual.lower() in [str(v).lower() for v in expected]
        return actual in expected
    return False


def _op_not_in_list(actual: Any, expected: Any) -> bool:
    if isinstance(expected, list):
        if isinstance(actual, str):
            return actual.lower() not in [str(v).lower() for v in expected]
        return actual not in expected
    return True


def _op_greater_than(actual: Any, expected: Any) -> bool:
    try:
        a = float(actual) if actual is not None else 0.0
        e = float(expected) if expected is not None else 0.0
        return a > e
    except (TypeError, ValueError):
        return False


def _op_less_than(actual: Any, expected: Any) -> bool:
    try:
        a = float(actual) if actual is not None else 0.0
        e = float(expected) if expected is not None else 0.0
        return a < e
    except (TypeError, ValueError):
        return False


def _op_greater_equal(actual: Any, expected: Any) -> bool:
    try:
        a = float(actual) if actual is not None else 0.0
        e = float(expected) if expected is not None else 0.0
        return a >= e
    except (TypeError, ValueError):
        return False


def _op_less_equal(actual: Any, expected: Any) -> bool:
    try:
        a = float(actual) if actual is not None else 0.0
        e = float(expected) if expected is not None else 0.0
        return a <= e
    except (TypeError, ValueError):
        return False


def _op_regex_match(actual: Any, expected: Any) -> bool:
    if actual is None:
        return False
    return bool(re.search(str(expected), str(actual), re.IGNORECASE))


def _op_any_item_contains(actual: Any, expected: Any) -> bool:
    if not isinstance(actual, list):
        return False
    search_patterns = str(expected).split("|")
    for item in actual:
        if isinstance(item, dict):
            text_values = [str(v).lower() for v in item.values()]
        else:
            text_values = [str(item).lower()]
        for text in text_values:
            for raw_pattern in search_patterns:
                normalized = raw_pattern.strip().lower()
                if not normalized:
                    continue
                # Support \b word boundaries via regex
                if "\\b" in normalized or "(" in normalized:
                    if re.search(normalized, text, re.IGNORECASE):
                        return True
                elif normalized in text:
                    return True
    return False


def _op_first_word_equals(actual: Any, expected: Any) -> bool:
    if actual is None or expected is None:
        return False
    skip = {
        "PTY",
        "LTD",
        "LIMITED",
        "THE",
        "A",
        "AN",
        "AND",
        "&",
        "P/L",
        "INC",
        "CORP",
        "OF",
    }
    actual_words = [w for w in str(actual).upper().split() if w not in skip]
    expected_words = [w for w in str(expected).upper().split() if w not in skip]
    if actual_words and expected_words:
        return actual_words[0] == expected_words[0]
    return False


def _op_length_equals(actual: Any, expected: Any) -> bool:
    return len(actual or []) == int(expected)


def _op_length_greater(actual: Any, expected: Any) -> bool:
    return len(actual or []) > int(expected)


def _op_length_less(actual: Any, expected: Any) -> bool:
    return len(actual or []) < int(expected)


_OPERATOR_DISPATCH: dict[str, Any] = {
    "is_null": _op_is_null,
    "is_not_null": _op_is_not_null,
    "is_true": _op_is_true,
    "is_false": _op_is_false,
    "equals": _op_equals,
    "not_equals": _op_not_equals,
    "contains": _op_contains,
    "not_contains": _op_not_contains,
    "starts_with": _op_starts_with,
    "in_list": _op_in_list,
    "not_in_list": _op_not_in_list,
    "greater_than": _op_greater_than,
    "less_than": _op_less_than,
    "greater_equal": _op_greater_equal,
    "less_equal": _op_less_equal,
    "regex_match": _op_regex_match,
    "any_item_contains": _op_any_item_contains,
    "first_word_equals": _op_first_word_equals,
    "length_equals": _op_length_equals,
    "length_greater": _op_length_greater,
    "length_less": _op_length_less,
}


# ============================================================================
# ACTION EXECUTOR
# ============================================================================


class ActionExecutor:
    """Executes actions on the provisional output.

    Supports two modes:
    - Deterministic: surgical field patches (set_field, append_note, etc.)
    - LLM-driven: calls Gemini Pro to continue the processing pipeline
      from where the acting agent terminated early.
    """

    @staticmethod
    def execute(output: dict, action: dict, context: dict | None = None) -> dict:
        """Execute a single action on the output.

        For llm_continue_processing, this delegates to LLMActionExecutor
        which calls Gemini Pro and returns the complete revised output.
        For deterministic actions, this patches fields in-place.

        Args:
            output: The provisional output dict (modified in-place)
            action: Action definition with type, target, value
            context: Full case context for reference

        Returns:
            Modified output dict
        """
        action_type = action.get("type", "")

        if action_type not in SUPPORTED_ACTION_TYPES:
            logger.warning(f"Unsupported action type: {action_type}")
            return output

        # LLM-driven actions: delegate to LLMActionExecutor
        if action_type == "llm_continue_processing":
            return LLMActionExecutor.execute(output, action, context)

        if action_type == "llm_patch_fields":
            return LLMActionExecutor.execute_patch(output, action, context)

        ActionExecutor._execute_deterministic(output, action, context)
        return output

    @staticmethod
    def _execute_deterministic(
        output: dict, action: dict, context: dict | None
    ) -> None:
        """Execute a deterministic (non-LLM) action on the output."""
        action_type = action.get("type", "")
        target = action.get("target", "")
        value = action.get("value")

        if action_type in ("set_field", "set_nested_field"):
            ActionExecutor._set_field(output, target, value)

        elif action_type == "override_decision":
            ActionExecutor._apply_override_decision(output, value)

        elif action_type == "override_validation":
            ActionExecutor._override_validation_step(output, action)

        elif action_type == "recalculate_field":
            ActionExecutor._recalculate(output, action, context)

        elif action_type == "add_to_list":
            ActionExecutor._add_to_list(output, target, value)

        elif action_type == "remove_from_list":
            ActionExecutor._remove_from_list(output, target, value)

        elif action_type == "append_note":
            current = ConditionEvaluator.resolve_field(output, target) or ""
            ActionExecutor._set_field(output, target, f"{current} {value}".strip())

        elif action_type == "conditional_set":
            sub_condition = action.get("condition", {})
            if ConditionEvaluator.evaluate_single(context or output, sub_condition):
                ActionExecutor._set_field(output, target, value)

    @staticmethod
    def _apply_override_decision(output: dict, value: Any) -> None:
        """Apply a decision override with corresponding status mapping."""
        ActionExecutor._set_field(output, "decision", value)
        status_map = {
            "ACCEPT": "Pending payment",
            "REJECT": "Rejected",
            "SET_ASIDE": "To verify",
            "CONTINUE": "To verify",
            "EMAIL_APPROVER": "To verify",
        }
        if value in status_map:
            ActionExecutor._set_field(
                output, "Invoice Processing.Invoice Status", status_map[value]
            )

    @staticmethod
    def _set_field(data: dict, field_path: str, value: Any):
        """Set a field value using dot-notation path."""
        parts = field_path.split(".")
        current = data

        for part in parts[:-1]:
            if part not in current or not isinstance(current.get(part), dict):
                current[part] = {}
            current = current[part]

        current[parts[-1]] = value

    @staticmethod
    def _override_validation_step(output: dict, action: dict):
        """Override a specific validation step in any phase artifact."""
        step_number = action.get("step")
        new_passed = action.get("passed")
        new_evidence = action.get("evidence", "")
        new_template = action.get("rejection_template")

        # Search through all phase validation artifacts
        for _key, value in output.items():
            if isinstance(value, dict) and "validations" in value:
                validations = value["validations"]
                if isinstance(validations, list):
                    for v in validations:
                        if isinstance(v, dict) and v.get("step") == step_number:
                            v["passed"] = new_passed
                            if new_evidence:
                                v["evidence"] = new_evidence
                            v["rejection_template"] = new_template
                            v["alf_override"] = True

    @staticmethod
    def _recalculate(output: dict, action: dict, context: dict):
        """Recalculate a derived field based on formula."""
        formula = action.get("formula", "")
        target = action.get("target", "")

        if formula == "sum_line_items_ex_gst":
            items = (
                ConditionEvaluator.resolve_field(context or output, "line_items_mapped")
                or []
            )
            total = sum(
                float(item.get("line_cost", "0").replace(",", ""))
                for item in items
                if isinstance(item, dict)
            )
            ActionExecutor._set_field(output, target, f"{total:,.2f}")

        elif formula == "invoice_total_minus_pretax":
            total = float(
                ConditionEvaluator.resolve_field(
                    output, "Invoice Details.Invoice Total"
                )
                or "0"
            )
            pretax = float(
                ConditionEvaluator.resolve_field(output, "Invoice Details.Pretax total")
                or "0"
            )
            ActionExecutor._set_field(output, target, f"{total - pretax:,.2f}")

    @staticmethod
    def _add_to_list(data: dict, field_path: str, value: Any):
        """Add a value to a list field."""
        current = ConditionEvaluator.resolve_field(data, field_path)
        if isinstance(current, list):
            current.append(value)
        else:
            ActionExecutor._set_field(data, field_path, [value])

    @staticmethod
    def _remove_from_list(data: dict, field_path: str, value: Any):
        """Remove a value from a list field."""
        current = ConditionEvaluator.resolve_field(data, field_path)
        if isinstance(current, list) and value in current:
            current.remove(value)


# ============================================================================
# LLM ACTION EXECUTOR
# ============================================================================

# System prompt instructing Gemini Pro how to continue the pipeline.
# This encodes the rules_book processing steps that the acting agent
# would have run if it hadn't terminated early.
LLM_CONTINUE_SYSTEM_PROMPT = """\
You are the ALF (Adaptive Learning Framework) Correction Agent for invoice processing.

CONTEXT:
The acting agent processed an invoice but terminated early due to a validation error
that has now been determined to be INCORRECT by a deterministic rule check.
Your job is to CONTINUE the processing pipeline from where it stopped and produce
the complete, corrected Postprocessing_Data.json output.

THE ACTING AGENT'S PIPELINE (9 agents):
  [1] Classifier       - Identify document types in PDFs
  [2] Extractor        - Extract invoice/WAF data from documents
  [3] Phase 1 Validator - Step 1.1: Extraction success, Step 1.2: Customer name, Step 1.3: Tax compliance, Step 1.4: WAF check, Step 1.5: Single invoice
  [4] Phase 2 Validator - Step 2.1: Line items present, Step 2.2: PO validation (if enabled)
  [5] Phase 3 Validator - Step 3.1: Duplicate detection (if enabled), Step 3.2: Tax ID checksum, Step 3.3: Future date check
  [6] Phase 4 Validator - Step 4.1: Total verification (informational), Step 4.2: Line sum validation, Step 4.3: WAF hours check (if WAF present)
  [7] Transformer      - Map line items to standard item codes
  [8] Output Generator  - Build Postprocessing_Data.json + decision
  [9] Audit Logger     - Log metrics

ITEM CODE MAPPING (for Transformer step):
  LABOUR     = Technician Labour (keywords: labour, labor, technician, installation)
  LABOUR_AH  = After Hours Labour (keywords: after hours, overtime, a/h)
  PARTS      = Parts/Materials/Components (keywords: parts, material, component, supply)
  FREIGHT    = Freight/Delivery (keywords: freight, delivery, shipping)
  TRAVEL     = Travel (keywords: travel, mileage, kilometre)
  CALLOUT    = Call Out Fee (keywords: call out, callout, attendance)
  HIRE       = Hire of Equipment (keywords: hire, rental)
  CLEANING   = Cleaning Services (keywords: cleaning, clean)
  OTHER      = Default (no keyword match)

TAX RATES:
  - AUD invoices: 10%
  - NZD invoices: 15%
  - USD invoices: 0%
  - EUR invoices: 20%

LINE ITEMS OUTPUT FORMAT:
Each line item must be a JSON object with these fields:
  line_number, item_code, description, quantity, unit_cost, line_cost, tax, tax_code

VALIDATION RULES TO APPLY (continue from where agent stopped):
  Step 2.1: Invoice charges must be itemized (line_items > 0)
  Step 3.2: Tax ID checksum validation (ABN mod 89)
  Step 3.3: Invoice date must not be in the future
  Step 4.1: Total = Subtotal + Tax (informational, tolerance $0.02)
  Step 4.2: Sum of line items = Subtotal (tolerance $1.00)
  Step 4.3: WAF hours >= invoice labour hours (tolerance 0.5 hours, if WAF present)

CRITICAL INSTRUCTIONS:
1. You receive the extraction data (invoice, WAF) and the correction context.
2. Run ALL remaining validation steps that the agent skipped.
3. Map ALL invoice line items to standard item codes.
4. Build the COMPLETE Postprocessing_Data.json output.
5. If all remaining validations pass -> Invoice Status = "Pending Payment"
6. If any remaining validation fails -> Invoice Status = "Rejected" with template
7. Return ONLY valid JSON. No markdown. No explanation. Just the JSON object.
"""

LLM_CONTINUE_TASK_TEMPLATE = """\
ALF CORRECTION RULE: {rule_id} - {rule_name}

CORRECTION CONTEXT:
{correction_context}

The acting agent terminated at: {resume_from}
The deterministic check has confirmed the agent's rejection was WRONG.
You must now continue processing from that point.

=== EXTRACTED INVOICE DATA ===
{invoice_json}

=== WORK AUTHORIZATION DATA ===
{waf_json}

=== AGENT'S PROVISIONAL OUTPUT (before correction) ===
{provisional_json}

=== ADDITIONAL CONTEXT ===
WAF count: {waf_count}
Has WAF: {has_waf}
Currency: {currency}

YOUR TASK:
1. Accept the correction (the rule's deterministic check is authoritative).
2. Continue the pipeline: run remaining validations, map line items to item codes.
3. If ALL remaining validations pass, set Invoice Status to "Pending Payment".
4. If any remaining validation FAILS, set Invoice Status to "Rejected" with the
   appropriate rejection template for the FIRST failing step.
5. Produce the COMPLETE Postprocessing_Data.json.

Return ONLY the JSON object. No markdown code blocks. No explanation.
Start with {{ and end with }}.
"""


# ============================================================================
# LLM PATCH PROMPTS (for llm_patch_fields action)
# ============================================================================

LLM_PATCH_SYSTEM_PROMPT = """\
You are the ALF (Adaptive Learning Framework) Surgical Correction Agent for invoice processing.

CONTEXT:
The acting agent completed processing an invoice and produced a full output.
However, specific fields in the output have been identified as incorrect by a
deterministic rule check. Your job is to determine the correct values for ONLY
the specified target fields based on the case data and correction context.

IMPORTANT:
- You are NOT regenerating the entire output.
- You are correcting ONLY the specified target fields.
- Return a JSON object with ONLY the target field paths as keys and their corrected values.
- Use the exact field path names provided in the target list.
- For array fields like "Line Items", return the complete corrected array.
- Leave all other fields in the output unchanged (they are NOT your concern).

ITEM CODE MAPPING (if line items need correction):
  LABOUR     = Technician Labour (keywords: labour, labor, technician, installation)
  LABOUR_AH  = After Hours Labour (keywords: after hours, overtime, a/h)
  PARTS      = Parts/Materials/Components (keywords: parts, material, component, supply)
  FREIGHT    = Freight/Delivery (keywords: freight, delivery, shipping)
  TRAVEL     = Travel (keywords: travel, mileage, kilometre)
  CALLOUT    = Call Out Fee (keywords: call out, callout, attendance)
  HIRE       = Hire of Equipment (keywords: hire, rental)
  CLEANING   = Cleaning Services (keywords: cleaning, clean)
  OTHER      = Default (no keyword match)

LINE ITEMS OUTPUT FORMAT (if line items need correction):
Each line item must be a JSON object with these fields:
  line_number, item_code, description, quantity, unit_cost, line_cost, tax, tax_code

Return ONLY valid JSON. No markdown. No explanation. Just the JSON object.
"""

LLM_PATCH_TASK_TEMPLATE = """\
ALF SURGICAL CORRECTION: {rule_id} - {rule_name}

CORRECTION CONTEXT:
{patch_context}

TARGET FIELDS TO CORRECT:
{target_fields_list}

CURRENT VALUES OF TARGET FIELDS:
{current_values_json}

=== EXTRACTED INVOICE DATA ===
{invoice_json}

=== WORK AUTHORIZATION DATA ===
{waf_json}

=== AGENT'S CURRENT OUTPUT (complete) ===
{current_output_json}

YOUR TASK:
1. Analyze the correction context and case data.
2. Determine the correct value for EACH target field listed above.
3. Return a JSON object with ONLY the target fields and their corrected values.

Example response format (for illustration only):
{{
  "Invoice Processing.Invoice Status": "Rejected",
  "Line Items": [...]
}}

Return ONLY the JSON object. No markdown code blocks. No explanation.
Start with {{ and end with }}.
"""


class LLMActionExecutor:
    """Executes rule actions by calling Gemini Pro.

    Supports two modes:
    - llm_continue_processing: Full pipeline continuation from a resume point.
      The LLM produces the entire revised Postprocessing_Data.json.
    - llm_patch_fields: Surgical field correction. The LLM produces only the
      corrected values for specific target fields, which are patched into
      the existing output.

    When a deterministic rule condition fires, this class:
    1. Builds a prompt with case data + correction context
    2. Calls Gemini Pro
    3. Parses the LLM response
    4. Returns revised output (full replacement or surgical patch)
    5. Logs the full prompt/response for auditability
    """

    _model = None  # Lazy-initialized Agent Platform (Vertex AI) model

    @classmethod
    def _get_model(cls):
        """Lazy-initialize the Agent Platform (Vertex AI) GenerativeModel."""
        if cls._model is None:
            try:
                from google.cloud import aiplatform
                from vertexai.generative_models import (
                    GenerationConfig,
                    GenerativeModel,
                )

                if not _get_llm_project_id():
                    raise ValueError(
                        "PROJECT_ID not set. Export it or add to .env file."
                    )
                aiplatform.init(
                    project=_get_llm_project_id(), location=_get_llm_location()
                )
                cls._model = GenerativeModel(
                    _get_llm_model(),
                    generation_config=GenerationConfig(temperature=0),
                )
                logger.info(
                    f"[LLM] Initialized {_get_llm_model()} "
                    f"(project={_get_llm_project_id()}, location={_get_llm_location()})"
                )
            except ImportError:
                raise ImportError(
                    "Agent Platform (Vertex AI) SDK required for LLM actions. Install with: "
                    "pip install google-cloud-aiplatform"
                ) from None
        return cls._model

    @staticmethod
    def execute(output: dict, action: dict, context: dict) -> dict:
        """Call Gemini Pro to continue processing and produce revised output.

        Args:
            output: Current provisional output dict
            action: The llm_continue_processing action definition containing:
                - resume_from: Which phase to resume from (e.g., "phase1", "phase3")
                - correction_context: Human-readable explanation of the correction
                - rule_id: The ALF rule that triggered this action
                - rule_name: Name of the rule for logging
            context: Full case context with extraction data, artifacts, etc.

        Returns:
            Revised output dict (complete Postprocessing_Data.json)
        """
        resume_from = action.get("resume_from", "phase1")
        correction_context = action.get("correction_context", "")
        rule_id = action.get("rule_id", "UNKNOWN")
        rule_name = action.get("rule_name", "")

        # Gather case data from context
        invoice = context.get("invoice", {})
        waf = context.get("work_authorization") or {}
        waf_count = context.get("waf_count", 0)
        has_waf = context.get("has_waf", False)
        currency = invoice.get("currency", "AUD")

        # Build the task prompt
        task_prompt = LLM_CONTINUE_TASK_TEMPLATE.format(
            rule_id=rule_id,
            rule_name=rule_name,
            correction_context=correction_context,
            resume_from=resume_from,
            invoice_json=json.dumps(invoice, indent=2, default=str),
            waf_json=json.dumps(waf, indent=2, default=str),
            provisional_json=json.dumps(output, indent=2, default=str),
            waf_count=waf_count,
            has_waf=has_waf,
            currency=currency,
        )

        full_prompt = f"{LLM_CONTINUE_SYSTEM_PROMPT}\n\n===TASK===\n{task_prompt}"

        # Call Gemini Pro
        logger.info(
            f"[LLM] Calling {_get_llm_model()} for {rule_id} (resume_from={resume_from})..."
        )
        start_time = time.time()

        try:
            model = LLMActionExecutor._get_model()
            response = model.generate_content(full_prompt)
            latency_ms = (time.time() - start_time) * 1000

            response_text = response.text.strip()

            # Parse JSON from response
            revised = LLMActionExecutor._parse_response(response_text)

            # Extract token usage
            usage = response.usage_metadata
            prompt_tokens = usage.prompt_token_count
            completion_tokens = usage.candidates_token_count

            logger.info(
                f"[LLM] {rule_id} completed in {latency_ms:.0f}ms "
                f"(prompt={prompt_tokens}, completion={completion_tokens})"
            )

            if _get_llm_call_delay() > 0:
                time.sleep(_get_llm_call_delay())

            # Store LLM metadata in output for audit
            revised["_alf_llm_metadata"] = {
                "rule_id": rule_id,
                "model": _get_llm_model(),
                "latency_ms": round(latency_ms, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "resume_from": resume_from,
            }

            return revised

        except Exception as e:
            logger.error(f"[LLM] {rule_id} failed: {e}")
            # On LLM failure, fall back to deterministic patch
            # (flip status + add error note)
            output.setdefault("Invoice Processing", {})["Invoice Status"] = "To verify"
            memo_key = output.setdefault("Notes and Texts", {})
            existing = memo_key.get("Asset specialist memo", "")
            memo_key["Asset specialist memo"] = (
                f"{existing} [{rule_id}] LLM continuation failed: {e}. "
                f"Manual review required."
            ).strip()
            output["_alf_llm_metadata"] = {
                "rule_id": rule_id,
                "model": _get_llm_model(),
                "error": str(e),
                "resume_from": resume_from,
                "fallback": "deterministic_set_aside",
            }
            return output

    @staticmethod
    def execute_patch(output: dict, action: dict, context: dict) -> dict:
        """Call Gemini Pro to surgically correct specific fields in the output.

        Unlike execute() which regenerates the entire Postprocessing_Data.json,
        this method asks the LLM to determine correct values for only the
        specified target fields, then patches them into the existing output.

        Args:
            output: Current complete output dict (all fields preserved)
            action: The llm_patch_fields action definition containing:
                - target_fields: List of field paths to correct (dot notation)
                - patch_context: Human-readable explanation of what's wrong
                - rule_id: The ALF rule that triggered this action
                - rule_name: Name of the rule for logging
            context: Full case context with extraction data, artifacts, etc.

        Returns:
            Output dict with only the target fields patched
        """
        target_fields = action.get("target_fields", [])
        patch_context = action.get("patch_context", "")
        rule_id = action.get("rule_id", "UNKNOWN")
        rule_name = action.get("rule_name", "")

        if not target_fields:
            logger.warning(f"[LLM-PATCH] {rule_id}: No target_fields specified")
            return output

        # Gather current values of target fields
        current_values = {}
        for field_path in target_fields:
            current_values[field_path] = ConditionEvaluator.resolve_field(
                output, field_path
            )

        # Gather case data from context
        invoice = context.get("invoice", {})
        waf = context.get("work_authorization") or {}

        # Build target fields list for prompt
        target_fields_list = "\n".join(f"  - {fp}" for fp in target_fields)

        # Build the task prompt
        task_prompt = LLM_PATCH_TASK_TEMPLATE.format(
            rule_id=rule_id,
            rule_name=rule_name,
            patch_context=patch_context,
            target_fields_list=target_fields_list,
            current_values_json=json.dumps(current_values, indent=2, default=str),
            invoice_json=json.dumps(invoice, indent=2, default=str),
            waf_json=json.dumps(waf, indent=2, default=str),
            current_output_json=json.dumps(output, indent=2, default=str),
        )

        full_prompt = f"{LLM_PATCH_SYSTEM_PROMPT}\n\n===TASK===\n{task_prompt}"

        # Call Gemini Pro
        logger.info(
            f"[LLM-PATCH] Calling {_get_llm_model()} for {rule_id} "
            f"(patching {len(target_fields)} fields)..."
        )
        start_time = time.time()

        try:
            model = LLMActionExecutor._get_model()
            response = model.generate_content(full_prompt)
            latency_ms = (time.time() - start_time) * 1000

            response_text = response.text.strip()

            # Parse JSON from response
            patches = LLMActionExecutor._parse_response(response_text)

            # Extract token usage
            usage = response.usage_metadata
            prompt_tokens = usage.prompt_token_count
            completion_tokens = usage.candidates_token_count

            logger.info(
                f"[LLM-PATCH] {rule_id} completed in {latency_ms:.0f}ms "
                f"(prompt={prompt_tokens}, completion={completion_tokens})"
            )

            if _get_llm_call_delay() > 0:
                time.sleep(_get_llm_call_delay())

            # Apply patches to output (surgical: only target fields changed)
            patched_output = copy.deepcopy(output)
            fields_patched = []

            for field_path in target_fields:
                if field_path in patches:
                    ActionExecutor._set_field(
                        patched_output, field_path, patches[field_path]
                    )
                    fields_patched.append(field_path)
                    logger.info(f"[LLM-PATCH]   Patched: {field_path}")
                else:
                    logger.warning(
                        f"[LLM-PATCH]   Field '{field_path}' not in LLM response"
                    )

            # Store LLM metadata in output for audit
            patched_output["_alf_llm_metadata"] = {
                "rule_id": rule_id,
                "action_type": "llm_patch_fields",
                "model": _get_llm_model(),
                "latency_ms": round(latency_ms, 2),
                "prompt_tokens": prompt_tokens,
                "completion_tokens": completion_tokens,
                "target_fields": target_fields,
                "fields_patched": fields_patched,
            }

            return patched_output

        except Exception as e:
            logger.error(f"[LLM-PATCH] {rule_id} failed: {e}")
            # On LLM failure, fall back: mark for manual review
            output.setdefault("Invoice Processing", {})["Invoice Status"] = "To verify"
            memo_key = output.setdefault("Notes and Texts", {})
            existing = memo_key.get("Asset specialist memo", "")
            memo_key["Asset specialist memo"] = (
                f"{existing} [{rule_id}] LLM patch failed: {e}. "
                f"Fields needing review: {', '.join(target_fields)}."
            ).strip()
            output["_alf_llm_metadata"] = {
                "rule_id": rule_id,
                "action_type": "llm_patch_fields",
                "model": _get_llm_model(),
                "error": str(e),
                "target_fields": target_fields,
                "fallback": "deterministic_set_aside",
            }
            return output

    @staticmethod
    def _parse_response(response_text: str) -> dict:
        """Parse the LLM response as JSON.
        Handles markdown code blocks and trailing text.
        """
        text = response_text.strip()
        text = LLMActionExecutor._strip_markdown_code_block(text)
        json_str = LLMActionExecutor._extract_json_object(text)

        # Fix trailing commas
        json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)
        return json.loads(json_str)

    @staticmethod
    def _strip_markdown_code_block(text: str) -> str:
        """Remove markdown code block fencing if present."""
        if not text.startswith("```"):
            return text
        lines = text.split("\n")
        json_lines = []
        in_block = False
        for line in lines:
            if line.strip().startswith("```"):
                if in_block:
                    break
                in_block = True
                continue
            if in_block:
                json_lines.append(line)
        if json_lines:
            return "\n".join(json_lines).strip()
        return text

    @staticmethod
    def _extract_json_object(text: str) -> str:
        """Find and extract the outermost JSON object from text."""
        start = text.find("{")
        if start == -1:
            raise ValueError("No JSON object found in LLM response")

        brace_count = 0
        end = -1
        for i in range(start, len(text)):
            if text[i] == "{":
                brace_count += 1
            elif text[i] == "}":
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break

        if end == -1:
            raise ValueError("Unclosed JSON object in LLM response")

        return text[start:end]


# ============================================================================
# RULE AGGREGATOR
# ============================================================================


class RuleAggregator:
    """Aggregates all matching rules into a unified RevisionPlan, then executes
    the plan in a deterministic order.

    Instead of applying rules one-by-one (which causes overwrite conflicts
    when multiple LLM actions fire), this class:

    1. COLLECT  - Evaluate all rules, collect matches (scope mutual exclusion)
    2. PLAN     - Categorize and merge matched actions into a RevisionPlan
    3. EXECUTE  - Run the plan: pipeline continuation → field patches → deterministic

    This guarantees at most 2 LLM calls per case (one for pipeline continuation,
    one for surgical patching) and eliminates overwrite conflicts.
    """

    # Resume point ordering (earlier = more work for LLM to redo)
    RESUME_ORDER: ClassVar[dict[str, int]] = {
        "phase2": 0,
        "phase3": 1,
        "phase4": 2,
        "transformer": 3,
    }

    # LLM action types (for categorization)
    LLM_ACTION_TYPES: ClassVar[set[str]] = {
        "llm_continue_processing",
        "llm_patch_fields",
    }

    @staticmethod
    def collect(rules: list, context: dict) -> tuple[list[tuple], list[dict], dict]:
        """Phase 1: Evaluate all rules and collect matches.

        Enforces scope-based mutual exclusion (at most one match per scope).
        Does NOT execute any actions.

        Args:
            rules: List of Rule objects (sorted by priority)
            context: Full case context for condition evaluation

        Returns:
            (matched_rules, all_traces, scope_matches)
            - matched_rules: list of (Rule, eval_details) tuples for matched rules
            - all_traces: list of trace dicts for every rule evaluated (for audit)
            - scope_matches: dict mapping scope -> rule_id that matched
        """
        # Group rules by scope for mutual exclusion
        scope_groups: dict[str, list] = {}
        for rule in rules:
            scope = rule.scope
            if scope not in scope_groups:
                scope_groups[scope] = []
            scope_groups[scope].append(rule)

        matched_rules = []
        all_traces = []
        scope_matches = {}

        for scope, scope_rules in scope_groups.items():
            scope_matched = False

            for rule in scope_rules:
                # Evaluate conditions
                all_passed, eval_details = ConditionEvaluator.evaluate_all(
                    context, rule.conditions
                )

                rule_trace = {
                    "rule_id": rule.id,
                    "rule_name": rule.name,
                    "scope": rule.scope,
                    "priority": rule.priority,
                    "conditions_evaluated": eval_details,
                    "matched": all_passed,
                    "applied": False,
                    "reason": None,
                }

                if all_passed:
                    if scope_matched:
                        rule_trace["reason"] = (
                            f"Skipped: another rule in scope '{scope}' already matched"
                        )
                        logger.info(
                            f"  [ALF] Rule {rule.id} matched but skipped "
                            f"(scope '{scope}' already has match)"
                        )
                    else:
                        scope_matched = True
                        matched_rules.append((rule, eval_details))
                        scope_matches[scope] = rule.id
                        rule_trace["applied"] = True
                        logger.info(f"  [ALF] Rule {rule.id} matched: {rule.name}")
                else:
                    rule_trace["reason"] = "Conditions not met"

                all_traces.append(rule_trace)

        return matched_rules, all_traces, scope_matches

    @staticmethod
    def build_plan(matched_rules: list[tuple]) -> dict:
        """Phase 2: Build a unified RevisionPlan from all matched rules.

        Categorizes matched actions into three tiers and merges same-tier
        actions to avoid conflicts:

        - pipeline_continuation: merged from all llm_continue_processing actions
          (earliest resume_from wins, correction contexts combined)
        - field_patches: merged from all llm_patch_fields actions
          (union of target_fields, patch contexts combined)
        - deterministic_edits: collected as-is from deterministic actions

        Args:
            matched_rules: list of (Rule, eval_details) tuples

        Returns:
            RevisionPlan dict with pipeline_continuation, field_patches,
            deterministic_edits keys
        """
        continuations, patches, deterministic = RuleAggregator._categorize_actions(
            matched_rules
        )

        merged_continuation = RuleAggregator._merge_continuations(continuations)
        merged_patches = RuleAggregator._merge_patches(patches)

        plan = {
            "pipeline_continuation": merged_continuation,
            "field_patches": merged_patches,
            "deterministic_edits": deterministic,
            "total_rules_aggregated": len(matched_rules),
            "execution_order": [],
        }

        # Build execution order for transparency
        RuleAggregator._build_execution_order(
            plan,
            merged_continuation,
            merged_patches,
            deterministic,
            continuations,
            patches,
        )

        return plan

    @staticmethod
    def _categorize_actions(
        matched_rules: list[tuple],
    ) -> tuple[list[dict], list[dict], list[dict]]:
        """Categorize matched rule actions into continuations, patches, and deterministic."""
        continuations: list[dict] = []
        patches: list[dict] = []
        deterministic: list[dict] = []

        for rule, _eval_details in matched_rules:
            for action in rule.actions:
                action_type = action.get("type", "")

                if action_type == "llm_continue_processing":
                    continuations.append(
                        {
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "resume_from": action.get("resume_from", "phase2"),
                            "correction_context": action.get("correction_context", ""),
                        }
                    )
                elif action_type == "llm_patch_fields":
                    patches.append(
                        {
                            "rule_id": rule.id,
                            "rule_name": rule.name,
                            "target_fields": action.get("target_fields", []),
                            "patch_context": action.get("patch_context", ""),
                        }
                    )
                else:
                    deterministic.append(
                        {
                            **action,
                            "source_rule": rule.id,
                        }
                    )

        return continuations, patches, deterministic

    @staticmethod
    def _merge_continuations(continuations: list[dict]) -> dict | None:
        """Merge multiple continuation actions into one (earliest resume_from wins)."""
        if not continuations:
            return None

        continuations.sort(
            key=lambda c: RuleAggregator.RESUME_ORDER.get(c["resume_from"], 99)
        )
        earliest = continuations[0]["resume_from"]

        combined_context_parts = []
        source_rules = []
        for c in continuations:
            source_rules.append(
                {
                    "rule_id": c["rule_id"],
                    "rule_name": c["rule_name"],
                    "original_resume_from": c["resume_from"],
                }
            )
            combined_context_parts.append(f"[{c['rule_id']}] {c['correction_context']}")

        return {
            "type": "llm_continue_processing",
            "resume_from": earliest,
            "correction_context": "\n\n".join(combined_context_parts),
            "source_rules": source_rules,
            "rules_merged": len(continuations),
        }

    @staticmethod
    def _merge_patches(patches: list[dict]) -> dict | None:
        """Merge multiple patch actions into one (union of target fields)."""
        if not patches:
            return None

        seen_fields: set[str] = set()
        all_target_fields: list[str] = []
        for p in patches:
            for field in p["target_fields"]:
                if field not in seen_fields:
                    seen_fields.add(field)
                    all_target_fields.append(field)

        combined_patch_parts = []
        source_rules = []
        for p in patches:
            source_rules.append(
                {
                    "rule_id": p["rule_id"],
                    "rule_name": p["rule_name"],
                }
            )
            combined_patch_parts.append(f"[{p['rule_id']}] {p['patch_context']}")

        return {
            "type": "llm_patch_fields",
            "target_fields": all_target_fields,
            "patch_context": "\n\n".join(combined_patch_parts),
            "source_rules": source_rules,
            "rules_merged": len(patches),
        }

    @staticmethod
    def _build_execution_order(
        plan: dict,
        merged_continuation: dict | None,
        merged_patches: dict | None,
        deterministic: list[dict],
        continuations: list[dict],
        patches: list[dict],
    ) -> None:
        """Populate the execution_order list in the plan for transparency."""
        if merged_continuation:
            plan["execution_order"].append(
                f"1. llm_continue_processing "
                f"(resume_from={merged_continuation['resume_from']}, "
                f"{len(continuations)} rules merged)"
            )
        if merged_patches:
            plan["execution_order"].append(
                f"{'2' if merged_continuation else '1'}. llm_patch_fields "
                f"({len(merged_patches['target_fields'])} fields, "
                f"{len(patches)} rules merged)"
            )
        if deterministic:
            step = len(plan["execution_order"]) + 1
            plan["execution_order"].append(
                f"{step}. deterministic_edits ({len(deterministic)} actions)"
            )

    @staticmethod
    def execute_plan(
        plan: dict, output: dict, context: dict
    ) -> tuple[dict, list[dict]]:
        """Phase 3: Execute the revision plan in deterministic order.

        Execution sequence:
        1. Pipeline continuation (one LLM call) - builds base output
        2. Surgical field patches (one LLM call) - fixes specific fields
        3. Deterministic edits (no LLM) - applies constant corrections

        Args:
            plan: RevisionPlan dict from build_plan()
            output: Current provisional output dict (deep copy)
            context: Full case context

        Returns:
            (revised_output, execution_log)
        """
        revised = output
        execution_log = []

        # --- Step 1: Pipeline continuation ---
        continuation = plan.get("pipeline_continuation")
        if continuation:
            logger.info(
                f"  [AGG] Executing pipeline continuation "
                f"(resume_from={continuation['resume_from']}, "
                f"{continuation['rules_merged']} rules merged)"
            )

            # Inject combined rule metadata
            action = {
                **continuation,
                "rule_id": "+".join(r["rule_id"] for r in continuation["source_rules"]),
                "rule_name": " + ".join(
                    r["rule_name"] for r in continuation["source_rules"]
                ),
            }

            before = copy.deepcopy(revised)
            revised = LLMActionExecutor.execute(revised, action, context)

            execution_log.append(
                {
                    "step": 1,
                    "action_type": "llm_continue_processing",
                    "resume_from": continuation["resume_from"],
                    "source_rules": [
                        r["rule_id"] for r in continuation["source_rules"]
                    ],
                    "rules_merged": continuation["rules_merged"],
                    "before_status": before.get("Invoice Processing", {}).get(
                        "Invoice Status"
                    ),
                    "after_status": revised.get("Invoice Processing", {}).get(
                        "Invoice Status"
                    ),
                }
            )

        # --- Step 2: Surgical field patches ---
        patches = plan.get("field_patches")
        if patches:
            logger.info(
                f"  [AGG] Executing surgical field patches "
                f"({len(patches['target_fields'])} fields, "
                f"{patches['rules_merged']} rules merged)"
            )

            action = {
                **patches,
                "rule_id": "+".join(r["rule_id"] for r in patches["source_rules"]),
                "rule_name": " + ".join(
                    r["rule_name"] for r in patches["source_rules"]
                ),
            }

            before_values = {
                fp: ConditionEvaluator.resolve_field(revised, fp)
                for fp in patches["target_fields"]
            }
            revised = LLMActionExecutor.execute_patch(revised, action, context)
            after_values = {
                fp: ConditionEvaluator.resolve_field(revised, fp)
                for fp in patches["target_fields"]
            }

            execution_log.append(
                {
                    "step": 2,
                    "action_type": "llm_patch_fields",
                    "target_fields": patches["target_fields"],
                    "source_rules": [r["rule_id"] for r in patches["source_rules"]],
                    "rules_merged": patches["rules_merged"],
                    "before_values": before_values,
                    "after_values": after_values,
                }
            )

        # --- Step 3: Deterministic edits ---
        det_edits = plan.get("deterministic_edits", [])
        if det_edits:
            logger.info(f"  [AGG] Executing {len(det_edits)} deterministic edits")

            for _i, action in enumerate(det_edits):
                target = action.get("target", "")
                before = (
                    ConditionEvaluator.resolve_field(revised, target)
                    if target
                    else None
                )
                revised = ActionExecutor.execute(revised, action, context)
                after = (
                    ConditionEvaluator.resolve_field(revised, target)
                    if target
                    else None
                )

                execution_log.append(
                    {
                        "step": 3,
                        "action_type": action.get("type"),
                        "target": target,
                        "source_rule": action.get("source_rule"),
                        "before": before,
                        "after": after,
                    }
                )

        return revised, execution_log


# ============================================================================
# RULE MODEL
# ============================================================================


class Rule:
    """Represents a single correction rule in the Structured Rule Base.

    A rule has:
      - id: Unique identifier (e.g., "ALF-001")
      - name: Human-readable name
      - description: Detailed explanation of what the rule corrects
      - scope: Which processing phase/agent this rule applies to
      - priority: Evaluation order (lower = evaluated first)
      - conditions: List of conditions (AND-joined) that must ALL be true
      - actions: List of deterministic actions to apply when conditions match
      - metadata: Origin, author, version, issue references
      - enabled: Whether the rule is active
    """

    def __init__(self, rule_dict: dict):
        self.id = rule_dict.get("id", "UNKNOWN")
        self.name = rule_dict.get("name", "")
        self.description = rule_dict.get("description", "")
        self.scope = rule_dict.get("scope", "global")
        self.priority = rule_dict.get("priority", 100)
        self.conditions = rule_dict.get("conditions", [])
        self.actions = rule_dict.get("actions", [])
        self.metadata = rule_dict.get("metadata", {})
        self.enabled = rule_dict.get("enabled", True)
        self.tags = rule_dict.get("tags", [])

    def __repr__(self):
        status = "ON" if self.enabled else "OFF"
        return (
            f"Rule({self.id}, scope={self.scope}, priority={self.priority}, {status})"
        )


# ============================================================================
# ALF ENGINE
# ============================================================================


class ALFEngine:
    """Adaptive Learning Framework Engine - Phase 1 (Expert-Led Correction).

    The engine loads a structured rule base and evaluates rules against
    the acting agent's provisional output. It applies deterministic
    corrections to produce a revised output.

    Design Principles:
      1. Mutually Exclusive Matching: At most ONE rule fires per scope
      2. Deterministic: No LLM calls, no randomness
      3. Auditable: Full evaluation trace for every rule
      4. Non-destructive: Original output preserved in audit log
      5. Priority-ordered: Rules evaluated in priority order within scope
    """

    def __init__(self, rule_base_path: str | Path | None = None):
        self.rules: list[Rule] = []
        self.schema_version = SCHEMA_VERSION
        self._rule_base_metadata = {}

        if rule_base_path:
            self.load_rule_base(rule_base_path)

    def load_rule_base(self, path: str | Path):
        """Load and validate the structured rule base from JSON.

        Args:
            path: Path to rule_base.json

        Raises:
            FileNotFoundError: If rule base file doesn't exist
            ValueError: If rule base schema is invalid
        """
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Rule base not found: {path}")

        with open(path, encoding="utf-8") as f:
            raw = json.load(f)

        # Validate schema
        self._validate_schema(raw)

        # Parse metadata
        self._rule_base_metadata = raw.get("metadata", {})

        # Parse rules
        self.rules = []
        for rule_dict in raw.get("rules", []):
            rule = Rule(rule_dict)
            if rule.enabled:
                self.rules.append(rule)

        # Sort by priority (lower = first)
        self.rules.sort(key=lambda r: r.priority)

        logger.info(
            f"Loaded {len(self.rules)} active rules from {path.name} "
            f"(schema v{raw.get('schema_version', 'unknown')})"
        )

    def _validate_schema(self, raw: dict):
        """Validate rule base JSON schema."""
        if "schema_version" not in raw:
            raise ValueError("Rule base missing 'schema_version' field")
        if "rules" not in raw:
            raise ValueError("Rule base missing 'rules' field")
        if not isinstance(raw["rules"], list):
            raise ValueError("'rules' must be a list")

        for i, rule in enumerate(raw["rules"]):
            self._validate_rule_structure(i, rule)
            self._validate_rule_conditions(rule)
            self._validate_rule_actions(rule)

    @staticmethod
    def _validate_rule_structure(index: int, rule: dict) -> None:
        """Validate that a rule has required top-level keys."""
        if "id" not in rule:
            raise ValueError(f"Rule at index {index} missing 'id'")
        if "conditions" not in rule:
            raise ValueError(f"Rule '{rule.get('id')}' missing 'conditions'")
        if "actions" not in rule:
            raise ValueError(f"Rule '{rule.get('id')}' missing 'actions'")

    @staticmethod
    def _validate_rule_conditions(rule: dict) -> None:
        """Validate all conditions in a rule."""
        for j, cond in enumerate(rule["conditions"]):
            if "field" not in cond:
                raise ValueError(f"Rule '{rule['id']}' condition {j} missing 'field'")
            if "operator" not in cond:
                raise ValueError(
                    f"Rule '{rule['id']}' condition {j} missing 'operator'"
                )
            op = cond["operator"]
            if op not in SUPPORTED_CONDITION_OPERATORS:
                raise ValueError(
                    f"Rule '{rule['id']}' condition {j}: unsupported operator '{op}'"
                )

    @staticmethod
    def _validate_rule_actions(rule: dict) -> None:
        """Validate all actions in a rule."""
        for j, act in enumerate(rule["actions"]):
            if "type" not in act:
                raise ValueError(f"Rule '{rule['id']}' action {j} missing 'type'")
            at = act["type"]
            if at not in SUPPORTED_ACTION_TYPES:
                raise ValueError(
                    f"Rule '{rule['id']}' action {j}: unsupported action type '{at}'"
                )

    def evaluate(
        self, provisional_output: dict, case_context: dict | None = None
    ) -> tuple[dict, dict]:
        """Evaluate all rules against the provisional output using the
        Collect -> Plan -> Execute pipeline.

        This is the main entry point for the Rule Evaluation Layer.

        Instead of applying rules one-by-one, this method:
        1. COLLECT: Evaluates all rules, collects matches (scope exclusion)
        2. PLAN: Merges matched actions into a unified RevisionPlan
        3. EXECUTE: Runs the plan in order (continuation → patches → deterministic)

        Args:
            provisional_output: The acting agent's provisional JSON output
            case_context: Extended context including intermediate artifacts,
                          raw PDF content, preprocessing data, etc.

        Returns:
            (revised_output, audit_log)
            - revised_output: The corrected output (or unchanged if no rules fired)
            - audit_log: Full evaluation trace for compliance/debugging
        """
        # Merge provisional output into context for field resolution
        context = {}
        if case_context:
            context.update(case_context)
        context["_provisional"] = provisional_output

        # Deep copy to avoid mutating original
        revised = copy.deepcopy(provisional_output)

        # ---- Phase 1: COLLECT ----
        matched_rules, all_traces, scope_matches = RuleAggregator.collect(
            self.rules, context
        )

        # Separate matched vs skipped/unmatched traces
        rules_applied_traces = [t for t in all_traces if t["applied"]]
        rules_skipped_traces = [t for t in all_traces if not t["applied"]]

        # ---- Phase 2: PLAN ----
        plan = RuleAggregator.build_plan(matched_rules)

        logger.info(
            f"  [ALF] Revision plan: "
            f"{plan['total_rules_aggregated']} rules aggregated, "
            f"execution order: {plan['execution_order']}"
        )

        # ---- Phase 3: EXECUTE ----
        execution_log = []
        if plan["total_rules_aggregated"] > 0:
            revised, execution_log = RuleAggregator.execute_plan(plan, revised, context)

        # Build audit log
        audit = {
            "alf_version": SCHEMA_VERSION,
            "rule_base_version": self._rule_base_metadata.get("version", "unknown"),
            "evaluation_timestamp": datetime.now().isoformat(),
            "total_rules_evaluated": len(all_traces),
            "rules_matched": len(matched_rules),
            "any_rules_fired": len(matched_rules) > 0,
            "rules_applied": rules_applied_traces,
            "rules_skipped": rules_skipped_traces,
            "scope_matches": scope_matches,
            "revision_plan": plan,
            "execution_log": execution_log,
            "original_decision": provisional_output.get("decision"),
            "revised_decision": revised.get("decision"),
        }

        return revised, audit

    def validate_rule_base_consistency(self) -> list[dict]:
        """Validate that the rule base is internally consistent.

        Checks:
        1. No duplicate rule IDs
        2. No conflicting rules within same scope (advisory)
        3. All field paths are syntactically valid
        4. Priority ordering is unambiguous within scope

        Returns:
            List of warning/error dicts
        """
        issues = []
        ids_seen = set()
        scope_priorities = {}

        for rule in self.rules:
            # Duplicate ID check
            if rule.id in ids_seen:
                issues.append(
                    {
                        "type": "error",
                        "rule_id": rule.id,
                        "message": f"Duplicate rule ID: {rule.id}",
                    }
                )
            ids_seen.add(rule.id)

            # Priority collision within scope
            key = (rule.scope, rule.priority)
            if key in scope_priorities:
                issues.append(
                    {
                        "type": "warning",
                        "rule_id": rule.id,
                        "message": (
                            f"Priority collision with rule "
                            f"'{scope_priorities[key]}' in scope '{rule.scope}' "
                            f"at priority {rule.priority}"
                        ),
                    }
                )
            scope_priorities[key] = rule.id

            # Validate field paths (basic syntax check)
            for cond in rule.conditions:
                field = cond.get("field", "")
                if not field or ".." in field or field.startswith("."):
                    issues.append(
                        {
                            "type": "error",
                            "rule_id": rule.id,
                            "message": f"Invalid field path: '{field}'",
                        }
                    )

        return issues

    def get_rules_by_scope(self, scope: str) -> list[Rule]:
        """Get all active rules for a specific scope."""
        return [r for r in self.rules if r.scope == scope]

    def get_rules_by_tag(self, tag: str) -> list[Rule]:
        """Get all active rules with a specific tag."""
        return [r for r in self.rules if tag in r.tags]

    def add_rule(self, rule_dict: dict):
        """Add a new rule to the engine (Phase 1: expert-defined).

        Args:
            rule_dict: Rule definition dict matching the schema

        Raises:
            ValueError: If rule ID already exists or schema invalid
        """
        existing_ids = {r.id for r in self.rules}
        new_id = rule_dict.get("id")
        if new_id in existing_ids:
            raise ValueError(f"Rule ID '{new_id}' already exists")

        rule = Rule(rule_dict)
        self.rules.append(rule)
        self.rules.sort(key=lambda r: r.priority)

    def save_rule_base(self, path: str | Path):
        """Save the current rule base to JSON.

        Args:
            path: Output file path
        """
        output = {
            "schema_version": SCHEMA_VERSION,
            "metadata": {
                **self._rule_base_metadata,
                "last_saved": datetime.now().isoformat(),
                "total_rules": len(self.rules),
            },
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "description": r.description,
                    "scope": r.scope,
                    "priority": r.priority,
                    "enabled": r.enabled,
                    "tags": r.tags,
                    "conditions": r.conditions,
                    "actions": r.actions,
                    "metadata": r.metadata,
                }
                for r in self.rules
            ],
        }

        with open(path, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)


# ============================================================================
# INTEGRATION ADAPTER
# ============================================================================


class ActingAgentAdapter:
    """Adapter to integrate ALF with the Acting Agent (acting_agent).

    This class bridges the gap between the acting agent's output format
    and the ALF engine's expected input format. It:
    1. Collects all intermediate artifacts from the acting agent
    2. Builds the case context for rule evaluation
    3. Applies revised output back to the acting agent's format
    """

    @staticmethod
    def build_case_context(
        output_folder: Path,
        extraction: dict | None = None,
        phase1: dict | None = None,
        phase2: dict | None = None,
        phase3: dict | None = None,
        phase4: dict | None = None,
        transformer: dict | None = None,
        exceptions: dict | None = None,
        postprocessing: dict | None = None,
    ) -> dict:
        """Build a unified case context from all agent artifacts.

        This flattens the multi-agent output into a single dict
        that the ALF engine can query with dot-notation paths.
        """
        context = {}

        # Load from output folder if individual dicts not provided
        ActingAgentAdapter._load_artifacts_from_folder(context, output_folder)

        # Override with explicitly provided dicts
        overrides = {
            "extraction": extraction,
            "phase1": phase1,
            "phase2": phase2,
            "phase3": phase3,
            "phase4": phase4,
            "transformer": transformer,
            "exceptions": exceptions,
            "postprocessing": postprocessing,
        }
        for key, value in overrides.items():
            if value:
                context[key] = value

        # Extract commonly-accessed fields to top level for convenience
        ActingAgentAdapter._promote_convenience_fields(context)

        return context

    @staticmethod
    def _load_artifacts_from_folder(context: dict, output_folder: Path) -> None:
        """Load agent artifacts from the output folder into context."""
        if not output_folder or not output_folder.exists():
            return
        artifact_map = _get_artifact_map()
        for key, filename in artifact_map.items():
            filepath = output_folder / filename
            if filepath.exists():
                try:
                    with open(filepath) as f:
                        context[key] = json.load(f)
                except json.JSONDecodeError:
                    context[key] = {}

    @staticmethod
    def _promote_convenience_fields(context: dict) -> None:
        """Promote commonly-accessed nested fields to the top level."""
        if "extraction" in context:
            ext = context["extraction"]
            context["invoice"] = ext.get("invoice", {})
            context["work_authorization"] = ext.get("work_authorization", {})
            context["has_waf"] = ext.get("waf_count", 0) > 0
            context["waf_count"] = ext.get("waf_count", 0)

        if "phase1" in context:
            context["decision_phase1"] = context["phase1"].get("decision")
            context["work_type"] = context["phase1"].get("work_type")

        if "phase2" in context:
            context["decision_phase2"] = context["phase2"].get("decision")

        if "phase3" in context:
            context["decision_phase3"] = context["phase3"].get("decision")

        if "phase4" in context:
            context["decision_phase4"] = context["phase4"].get("decision")

        if "transformer" in context:
            context["line_items_mapped"] = context["transformer"].get(
                "line_items_mapped", []
            )

    @staticmethod
    def apply_to_postprocessing(
        postprocessing: dict, revised_output: dict, audit_log: dict
    ) -> dict:
        """Apply ALF revisions back to the Postprocessing_Data.json format.

        When rules fired, the revised_output from evaluate() IS the complete
        corrected output - use it directly. When no rules fired, return the
        original unchanged.

        Args:
            postprocessing: Original Postprocessing_Data.json dict
            revised_output: ALF-revised output from evaluate()
            audit_log: ALF audit log for traceability

        Returns:
            Updated postprocessing dict with ALF corrections applied
        """
        if audit_log.get("any_rules_fired"):
            # Use the revised output directly - it already contains all
            # corrections from the RuleAggregator's execute_plan()
            result = copy.deepcopy(revised_output)

            # Add ALF audit trail to outcome message
            rules_applied = [r["rule_id"] for r in audit_log.get("rules_applied", [])]
            alf_note = f" [ALF corrections applied: {', '.join(rules_applied)}]"

            outcome = result.get("Outcome Message", {})
            if isinstance(outcome, dict):
                msg = outcome.get("Outcome Message", "")
                outcome["Outcome Message"] = msg + alf_note
            elif isinstance(outcome, str):
                result["Outcome Message"] = outcome + alf_note

            return result
        # No rules fired - return original unchanged
        return copy.deepcopy(postprocessing)


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================


def _snapshot_target(data: dict, action: dict) -> Any:
    """Capture the current value of an action's target field."""
    target = action.get("target", "")
    if target:
        return ConditionEvaluator.resolve_field(data, target)
    return None


def run_alf_on_case(
    rule_base_path: str | Path,
    output_folder: str | Path,
    postprocessing_path: str | Path | None = None,
    save_to_alf_out: bool = True,
    engine: "ALFEngine | None" = None,
) -> tuple[dict, dict]:
    """Run ALF on a single case and save revised output to ALF/out/{case_id}/.

    Args:
        rule_base_path: Path to rule_base.json
        output_folder: Path to the case's output folder (with agent artifacts)
        postprocessing_path: Optional path to Postprocessing_Data.json
        save_to_alf_out: If True, save revised output to ALF/out/{case_id}/
        engine: Optional pre-loaded ALFEngine (avoids re-loading for batch)

    Returns:
        (revised_postprocessing, audit_log)
    """
    output_folder = Path(output_folder)
    rule_base_path = Path(rule_base_path)

    # Load ALF engine (or reuse provided one)
    if engine is None:
        engine = ALFEngine(rule_base_path)

    # Build case context from artifacts
    context = ActingAgentAdapter.build_case_context(output_folder)

    # Load postprocessing data
    if postprocessing_path is None:
        postprocessing_path = output_folder / "Postprocessing_Data.json"

    postprocessing = {}
    pp_path = Path(postprocessing_path)
    if pp_path.exists():
        with open(pp_path) as f:
            postprocessing = json.load(f)

    # Merge postprocessing into context
    context["postprocessing"] = postprocessing
    context["decision"] = postprocessing.get("Invoice Processing", {}).get(
        "Invoice Status", ""
    )

    # Evaluate rules
    revised_output, audit_log = engine.evaluate(postprocessing, context)

    # Apply revisions
    revised_postprocessing = ActingAgentAdapter.apply_to_postprocessing(
        postprocessing, revised_output, audit_log
    )

    # Save to ALF/out/{case_id}/
    if save_to_alf_out:
        case_id = output_folder.name
        alf_case_dir = ALF_OUT_DIR / case_id
        alf_case_dir.mkdir(parents=True, exist_ok=True)

        # Save revised Postprocessing_Data.json
        revised_path = alf_case_dir / "Postprocessing_Data.json"
        with open(revised_path, "w", encoding="utf-8") as f:
            json.dump(revised_postprocessing, f, indent=2, ensure_ascii=False)

        # Save audit log
        audit_path = alf_case_dir / "alf_audit_log.json"
        with open(audit_path, "w", encoding="utf-8") as f:
            json.dump(audit_log, f, indent=2, ensure_ascii=False)

        logger.info(f"  Saved to {alf_case_dir}")

    return revised_postprocessing, audit_log


# ============================================================================
# CLI ENTRY POINT
# ============================================================================


def _parse_cli_args() -> argparse.Namespace:
    """Parse CLI arguments for the ALF engine."""
    parser = argparse.ArgumentParser(
        description="ALF Engine - Adaptive Learning Framework (Phase 1)"
    )
    parser.add_argument(
        "--rule-base",
        "-r",
        type=str,
        default=str(AGENT_PKG_DIR / "data" / "rule_base.json"),
        help="Path to rule_base.json (default: data/rule_base.json)",
    )
    parser.add_argument(
        "--case-dir",
        "-c",
        type=str,
        default=None,
        help="Path to a single case output folder",
    )
    parser.add_argument(
        "--batch-dir",
        "-b",
        type=str,
        default=None,
        help="Path to batch directory containing case folders "
        "(e.g., acting_agent/output)",
    )
    parser.add_argument(
        "--num-cases",
        "-n",
        type=int,
        default=None,
        help="Number of cases to process in batch mode (default: all)",
    )
    parser.add_argument(
        "--validate",
        "-v",
        action="store_true",
        help="Validate rule base consistency and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Evaluate rules but don't save output",
    )
    return parser.parse_args()


def _run_validate_mode(engine: ALFEngine) -> None:
    """Run rule base validation and print results."""
    issues = engine.validate_rule_base_consistency()
    if issues:
        print(f"\nFound {len(issues)} issue(s):")
        for issue in issues:
            print(f"  [{issue['type'].upper()}] {issue['rule_id']}: {issue['message']}")
    else:
        print("Rule base is consistent. No issues found.")


def _collect_case_folders(args: argparse.Namespace) -> list[Path] | None:
    """Collect case folders from CLI arguments. Returns None on error."""
    if args.case_dir:
        return [Path(args.case_dir)]
    if args.batch_dir:
        batch_path = Path(args.batch_dir)
        if not batch_path.exists():
            print(f"Error: Batch directory not found: {batch_path}")
            return None
        folders = sorted(
            [d for d in batch_path.iterdir() if d.is_dir()],
            key=lambda x: x.name,
        )
        if args.num_cases:
            folders = folders[: args.num_cases]
        return folders
    print("Error: Provide either --case-dir or --batch-dir")
    return None


def _process_case(
    idx: int,
    total: int,
    case_dir: Path,
    rule_base_path: Path,
    engine: ALFEngine,
    dry_run: bool,
    stats: dict,
) -> None:
    """Process a single case directory and update stats."""
    case_id = case_dir.name
    pp_path = case_dir / "Postprocessing_Data.json"

    if not pp_path.exists():
        print(f"[{idx}/{total}] {case_id}: No Postprocessing_Data.json - skipping")
        return

    revised, audit = run_alf_on_case(
        rule_base_path=rule_base_path,
        output_folder=case_dir,
        save_to_alf_out=(not dry_run),
        engine=engine,
    )

    rules_applied = [r["rule_id"] for r in audit.get("rules_applied", [])]

    if rules_applied:
        stats["rules_fired"] += len(rules_applied)
        stats["cases_corrected"].append({"case_id": case_id, "rules": rules_applied})
        alf_case_dir = ALF_OUT_DIR / case_id
        print(
            f"[{idx}/{total}] {case_id}: "
            f"CORRECTED [{', '.join(rules_applied)}]"
            f"{'' if dry_run else f' -> {alf_case_dir}'}"
        )
    else:
        stats["no_change"] += 1
        if not dry_run:
            _save_unchanged_case(case_id, revised, audit)
        print(f"[{idx}/{total}] {case_id}: no rules fired (unchanged)")


def _save_unchanged_case(case_id: str, revised: dict, audit: dict) -> None:
    """Save unchanged case output to ALF output directory."""
    alf_case_dir = ALF_OUT_DIR / case_id
    alf_case_dir.mkdir(parents=True, exist_ok=True)
    with open(alf_case_dir / "Postprocessing_Data.json", "w", encoding="utf-8") as f:
        json.dump(revised, f, indent=2, ensure_ascii=False)
    with open(alf_case_dir / "alf_audit_log.json", "w", encoding="utf-8") as f:
        json.dump(audit, f, indent=2, ensure_ascii=False)


def _print_batch_summary(stats: dict, dry_run: bool) -> None:
    """Print batch processing summary."""
    print(f"\n{'=' * 70}")
    print("ALF BATCH SUMMARY")
    print(f"{'=' * 70}")
    print(f"Total cases processed: {stats['total']}")
    print(f"Cases corrected:       {len(stats['cases_corrected'])}")
    print(f"Cases unchanged:       {stats['no_change']}")
    print(f"Total rules fired:     {stats['rules_fired']}")

    if stats["cases_corrected"]:
        print("\nCorrected cases:")
        for cc in stats["cases_corrected"]:
            print(f"  {cc['case_id']}: {', '.join(cc['rules'])}")

    if not dry_run:
        print(f"\nRevised output saved to: {ALF_OUT_DIR}")


def main():
    """CLI entry point for running ALF on cases."""
    args = _parse_cli_args()

    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )

    rule_base_path = Path(args.rule_base)
    engine = ALFEngine(rule_base_path)

    if args.validate:
        _run_validate_mode(engine)
        return

    case_folders = _collect_case_folders(args)
    if case_folders is None:
        return

    # Print header
    print(f"\n{'=' * 70}")
    print("ALF Engine - Phase 1 Evaluation")
    print(f"{'=' * 70}")
    print(f"Rule base:  {rule_base_path}")
    print(f"Output dir: {ALF_OUT_DIR}")
    print(f"Rules loaded: {len(engine.rules)}")
    print(f"Cases to process: {len(case_folders)}")
    print(f"Dry run: {args.dry_run}")
    print()

    stats = {
        "total": len(case_folders),
        "rules_fired": 0,
        "no_change": 0,
        "cases_corrected": [],
    }

    for idx, case_dir in enumerate(case_folders, 1):
        _process_case(
            idx,
            len(case_folders),
            case_dir,
            rule_base_path,
            engine,
            args.dry_run,
            stats,
        )

    _print_batch_summary(stats, args.dry_run)

    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
