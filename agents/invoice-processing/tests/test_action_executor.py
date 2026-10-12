"""Tests for ActionExecutor -- deterministic action execution."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from invoice_processing.shared_libraries.alf_engine import ActionExecutor

_TEST_VALUE = 42

# ---------------------------------------------------------------------------
# _set_field
# ---------------------------------------------------------------------------


class TestSetField:
    def test_simple_field(self):
        data = {}
        ActionExecutor._set_field(data, "status", "ACCEPT")
        assert data["status"] == "ACCEPT"

    def test_nested_field_creates_intermediates(self):
        data = {}
        ActionExecutor._set_field(data, "a.b.c", _TEST_VALUE)
        assert data["a"]["b"]["c"] == _TEST_VALUE

    def test_overwrite_existing(self):
        data = {"decision": "REJECT"}
        ActionExecutor._set_field(data, "decision", "ACCEPT")
        assert data["decision"] == "ACCEPT"

    def test_nested_overwrite(self):
        data = {"Invoice Details": {"Invoice Status": "Rejected"}}
        ActionExecutor._set_field(
            data, "Invoice Details.Invoice Status", "Pending payment"
        )
        assert data["Invoice Details"]["Invoice Status"] == "Pending payment"


# ---------------------------------------------------------------------------
# override_decision
# ---------------------------------------------------------------------------


class TestOverrideDecision:
    def test_override_accept(self):
        output = {"decision": "REJECT"}
        action = {"type": "override_decision", "value": "ACCEPT"}
        result = ActionExecutor.execute(output, action)
        assert result["decision"] == "ACCEPT"
        assert result["Invoice Processing"]["Invoice Status"] == "Pending payment"

    def test_override_reject(self):
        output = {"decision": "ACCEPT"}
        action = {"type": "override_decision", "value": "REJECT"}
        result = ActionExecutor.execute(output, action)
        assert result["decision"] == "REJECT"
        assert result["Invoice Processing"]["Invoice Status"] == "Rejected"

    def test_override_set_aside(self):
        output = {"decision": "REJECT"}
        action = {"type": "override_decision", "value": "SET_ASIDE"}
        result = ActionExecutor.execute(output, action)
        assert result["decision"] == "SET_ASIDE"
        assert result["Invoice Processing"]["Invoice Status"] == "To verify"


# ---------------------------------------------------------------------------
# set_field / set_nested_field
# ---------------------------------------------------------------------------


class TestSetFieldAction:
    def test_set_field(self):
        output = {"notes": ""}
        action = {
            "type": "set_field",
            "target": "notes",
            "value": "Updated by ALF",
        }
        result = ActionExecutor.execute(output, action)
        assert result["notes"] == "Updated by ALF"

    def test_set_nested_field(self):
        output = {"invoice": {"vendor": "old"}}
        action = {
            "type": "set_nested_field",
            "target": "invoice.vendor",
            "value": "new",
        }
        result = ActionExecutor.execute(output, action)
        assert result["invoice"]["vendor"] == "new"


# ---------------------------------------------------------------------------
# append_note
# ---------------------------------------------------------------------------


class TestAppendNote:
    def test_append_to_existing(self):
        output = {"notes": "Original note."}
        action = {
            "type": "append_note",
            "target": "notes",
            "value": "ALF correction applied.",
        }
        result = ActionExecutor.execute(output, action)
        assert result["notes"] == "Original note. ALF correction applied."

    def test_append_to_empty(self):
        output = {}
        action = {
            "type": "append_note",
            "target": "notes",
            "value": "First note.",
        }
        result = ActionExecutor.execute(output, action)
        assert result["notes"] == "First note."


# ---------------------------------------------------------------------------
# add_to_list / remove_from_list
# ---------------------------------------------------------------------------


class TestListActions:
    def test_add_to_existing_list(self):
        output = {"tags": ["phase1", "phase2"]}
        action = {
            "type": "add_to_list",
            "target": "tags",
            "value": "alf_corrected",
        }
        result = ActionExecutor.execute(output, action)
        assert "alf_corrected" in result["tags"]

    def test_add_to_nonexistent_creates_list(self):
        output = {}
        action = {"type": "add_to_list", "target": "tags", "value": "new_tag"}
        result = ActionExecutor.execute(output, action)
        assert result["tags"] == ["new_tag"]

    def test_remove_from_list(self):
        output = {"tags": ["a", "b", "c"]}
        action = {"type": "remove_from_list", "target": "tags", "value": "b"}
        result = ActionExecutor.execute(output, action)
        assert "b" not in result["tags"]
        assert result["tags"] == ["a", "c"]

    def test_remove_missing_value_is_noop(self):
        output = {"tags": ["a", "b"]}
        action = {"type": "remove_from_list", "target": "tags", "value": "z"}
        result = ActionExecutor.execute(output, action)
        assert result["tags"] == ["a", "b"]


# ---------------------------------------------------------------------------
# override_validation
# ---------------------------------------------------------------------------


class TestOverrideValidation:
    def test_override_phase_validation_step(self):
        output = {
            "phase4": {
                "validations": [
                    {
                        "step": 1,
                        "passed": True,
                        "evidence": "",
                        "rejection_template": None,
                    },
                    {
                        "step": 2,
                        "passed": False,
                        "evidence": "mismatch",
                        "rejection_template": "calc error",
                    },
                ]
            }
        }
        action = {
            "type": "override_validation",
            "step": 2,
            "passed": True,
            "evidence": "ALF override: false positive",
            "rejection_template": None,
        }
        result = ActionExecutor.execute(output, action)
        step2 = result["phase4"]["validations"][1]
        assert step2["passed"] is True
        assert step2["evidence"] == "ALF override: false positive"
        assert step2["rejection_template"] is None
        assert step2["alf_override"] is True


# ---------------------------------------------------------------------------
# conditional_set
# ---------------------------------------------------------------------------


class TestConditionalSet:
    def test_condition_met(self):
        output = {"decision": "REJECT", "reason": ""}
        context = {"decision": "REJECT"}
        action = {
            "type": "conditional_set",
            "target": "reason",
            "value": "overridden",
            "condition": {
                "field": "decision",
                "operator": "equals",
                "value": "REJECT",
            },
        }
        result = ActionExecutor.execute(output, action, context)
        assert result["reason"] == "overridden"

    def test_condition_not_met(self):
        output = {"decision": "ACCEPT", "reason": ""}
        context = {"decision": "ACCEPT"}
        action = {
            "type": "conditional_set",
            "target": "reason",
            "value": "overridden",
            "condition": {
                "field": "decision",
                "operator": "equals",
                "value": "REJECT",
            },
        }
        result = ActionExecutor.execute(output, action, context)
        assert result["reason"] == ""


# ---------------------------------------------------------------------------
# recalculate_field
# ---------------------------------------------------------------------------


class TestRecalculateField:
    def test_sum_line_items(self):
        output = {}
        context = {
            "line_items_mapped": [
                {"description": "Item A", "line_cost": "100.00"},
                {"description": "Item B", "line_cost": "250.50"},
            ]
        }
        action = {
            "type": "recalculate_field",
            "formula": "sum_line_items_ex_gst",
            "target": "totals.subtotal",
        }
        result = ActionExecutor.execute(output, action, context)
        assert result["totals"]["subtotal"] == "350.50"

    def test_invoice_total_minus_pretax(self):
        output = {
            "Invoice Details": {
                "Invoice Total": "1100.00",
                "Pretax total": "1000.00",
            }
        }
        action = {
            "type": "recalculate_field",
            "formula": "invoice_total_minus_pretax",
            "target": "Invoice Details.GST Amount",
        }
        result = ActionExecutor.execute(output, action)
        assert result["Invoice Details"]["GST Amount"] == "100.00"


# ---------------------------------------------------------------------------
# Unsupported action type
# ---------------------------------------------------------------------------


class TestUnsupportedAction:
    def test_unsupported_action_returns_output_unchanged(self):
        output = {"decision": "REJECT"}
        action = {"type": "nonexistent_action"}
        result = ActionExecutor.execute(output, action)
        assert result == {"decision": "REJECT"}
