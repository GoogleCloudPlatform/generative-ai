"""Tests for ConditionEvaluator -- all 21 operators and field resolution."""

import sys
from pathlib import Path
from typing import ClassVar

# Add parent package to path so imports work without installing
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from invoice_processing.shared_libraries.alf_engine import (
    ConditionEvaluator,
)

_TEST_VALUE = 42
_TEST_ARRAY_VALUE = 10
_TEST_SECOND_ARRAY_VALUE = 20
_EXPECTED_CONDITION_COUNT = 2

# ---------------------------------------------------------------------------
# resolve_field
# ---------------------------------------------------------------------------


class TestResolveField:
    def test_simple_key(self):
        assert ConditionEvaluator.resolve_field({"a": 1}, "a") == 1

    def test_nested_key(self):
        data = {"a": {"b": {"c": _TEST_VALUE}}}
        assert ConditionEvaluator.resolve_field(data, "a.b.c") == _TEST_VALUE

    def test_missing_key_returns_none(self):
        assert ConditionEvaluator.resolve_field({"a": 1}, "b") is None

    def test_missing_nested_key(self):
        assert ConditionEvaluator.resolve_field({"a": {"b": 1}}, "a.x") is None

    def test_array_index(self):
        data = {"items": [{"x": _TEST_ARRAY_VALUE}, {"x": _TEST_SECOND_ARRAY_VALUE}]}
        assert ConditionEvaluator.resolve_field(data, "items.0.x") == _TEST_ARRAY_VALUE
        assert (
            ConditionEvaluator.resolve_field(data, "items.1.x")
            == _TEST_SECOND_ARRAY_VALUE
        )

    def test_array_index_out_of_bounds(self):
        data = {"items": [1]}
        assert ConditionEvaluator.resolve_field(data, "items.5") is None

    def test_none_intermediate(self):
        data = {"a": None}
        assert ConditionEvaluator.resolve_field(data, "a.b") is None

    def test_non_dict_intermediate(self):
        data = {"a": "string_value"}
        assert ConditionEvaluator.resolve_field(data, "a.b") is None

    def test_empty_data(self):
        assert ConditionEvaluator.resolve_field({}, "anything") is None


# ---------------------------------------------------------------------------
# _resolve_dynamic_value
# ---------------------------------------------------------------------------


class TestResolveDynamicValue:
    def test_static_string_unchanged(self):
        result = ConditionEvaluator._resolve_dynamic_value("hello", {})
        assert result == "hello"

    def test_non_string_unchanged(self):
        assert ConditionEvaluator._resolve_dynamic_value(_TEST_VALUE, {}) == _TEST_VALUE
        assert ConditionEvaluator._resolve_dynamic_value(None, {}) is None

    def test_dynamic_resolved(self):
        data = {"vendor": {"name": "Acme Corp"}}
        result = ConditionEvaluator._resolve_dynamic_value(
            "_DYNAMIC_vendor.name_", data
        )
        assert result == "Acme Corp"

    def test_dynamic_unresolved_returns_none(self):
        result = ConditionEvaluator._resolve_dynamic_value(
            "_DYNAMIC_missing.field_", {}
        )
        assert result is None


# ---------------------------------------------------------------------------
# _apply_operator -- all 21 operators
# ---------------------------------------------------------------------------


class TestApplyOperator:
    # -- Null checks --
    def test_is_null_true(self):
        assert ConditionEvaluator._apply_operator("is_null", None, None) is True

    def test_is_null_false(self):
        assert ConditionEvaluator._apply_operator("is_null", "x", None) is False

    def test_is_not_null_true(self):
        assert ConditionEvaluator._apply_operator("is_not_null", "x", None) is True

    def test_is_not_null_false(self):
        assert ConditionEvaluator._apply_operator("is_not_null", None, None) is False

    # -- Boolean checks --
    def test_is_true(self):
        assert ConditionEvaluator._apply_operator("is_true", True, None) is True
        assert ConditionEvaluator._apply_operator("is_true", 1, None) is True
        assert ConditionEvaluator._apply_operator("is_true", "yes", None) is True

    def test_is_false(self):
        assert ConditionEvaluator._apply_operator("is_false", False, None) is True
        assert ConditionEvaluator._apply_operator("is_false", 0, None) is True
        assert ConditionEvaluator._apply_operator("is_false", "", None) is True
        assert ConditionEvaluator._apply_operator("is_false", None, None) is True

    # -- Equals --
    def test_equals_string_case_insensitive(self):
        assert ConditionEvaluator._apply_operator("equals", "REJECT", "reject") is True
        assert (
            ConditionEvaluator._apply_operator("equals", " Accept ", "accept") is True
        )

    def test_equals_numeric(self):
        assert ConditionEvaluator._apply_operator("equals", 42, 42) is True
        assert ConditionEvaluator._apply_operator("equals", 42, 43) is False

    def test_not_equals(self):
        assert ConditionEvaluator._apply_operator("not_equals", "a", "b") is True
        assert ConditionEvaluator._apply_operator("not_equals", "a", "a") is False

    # -- Contains --
    def test_contains(self):
        assert (
            ConditionEvaluator._apply_operator(
                "contains", "different company found", "different company"
            )
            is True
        )
        assert (
            ConditionEvaluator._apply_operator("contains", "all good", "error") is False
        )

    def test_contains_case_insensitive(self):
        assert (
            ConditionEvaluator._apply_operator(
                "contains", "Different Company", "different company"
            )
            is True
        )

    def test_contains_none_actual(self):
        assert ConditionEvaluator._apply_operator("contains", None, "x") is False

    def test_not_contains(self):
        assert (
            ConditionEvaluator._apply_operator("not_contains", "hello world", "error")
            is True
        )
        assert (
            ConditionEvaluator._apply_operator("not_contains", "has error", "error")
            is False
        )

    def test_not_contains_none_actual(self):
        assert ConditionEvaluator._apply_operator("not_contains", None, "x") is True

    # -- Starts with --
    def test_starts_with(self):
        assert (
            ConditionEvaluator._apply_operator("starts_with", "ACME Corp", "acme")
            is True
        )
        assert (
            ConditionEvaluator._apply_operator("starts_with", "Global Ltd", "acme")
            is False
        )

    def test_starts_with_none(self):
        assert ConditionEvaluator._apply_operator("starts_with", None, "x") is False

    # -- In list --
    def test_in_list(self):
        assert (
            ConditionEvaluator._apply_operator(
                "in_list", "REJECT", ["ACCEPT", "REJECT"]
            )
            is True
        )

    def test_in_list_case_insensitive(self):
        assert (
            ConditionEvaluator._apply_operator(
                "in_list", "reject", ["ACCEPT", "REJECT"]
            )
            is True
        )

    def test_in_list_not_found(self):
        assert (
            ConditionEvaluator._apply_operator(
                "in_list", "PENDING", ["ACCEPT", "REJECT"]
            )
            is False
        )

    def test_in_list_not_a_list(self):
        assert ConditionEvaluator._apply_operator("in_list", "x", "not a list") is False

    def test_not_in_list(self):
        assert (
            ConditionEvaluator._apply_operator(
                "not_in_list", "PENDING", ["ACCEPT", "REJECT"]
            )
            is True
        )
        assert (
            ConditionEvaluator._apply_operator(
                "not_in_list", "ACCEPT", ["ACCEPT", "REJECT"]
            )
            is False
        )

    # -- Numeric comparisons --
    def test_greater_than(self):
        assert ConditionEvaluator._apply_operator("greater_than", 10, 5) is True
        assert ConditionEvaluator._apply_operator("greater_than", 5, 10) is False

    def test_less_than(self):
        assert ConditionEvaluator._apply_operator("less_than", 3, 10) is True
        assert ConditionEvaluator._apply_operator("less_than", 10, 3) is False

    def test_greater_equal(self):
        assert ConditionEvaluator._apply_operator("greater_equal", 10, 10) is True
        assert ConditionEvaluator._apply_operator("greater_equal", 9, 10) is False

    def test_less_equal(self):
        assert ConditionEvaluator._apply_operator("less_equal", 10, 10) is True
        assert ConditionEvaluator._apply_operator("less_equal", 11, 10) is False

    def test_numeric_with_strings(self):
        assert (
            ConditionEvaluator._apply_operator("greater_than", "100.50", "50.25")
            is True
        )

    def test_numeric_non_numeric_returns_false(self):
        assert ConditionEvaluator._apply_operator("greater_than", "abc", 5) is False

    # -- Regex --
    def test_regex_match(self):
        assert (
            ConditionEvaluator._apply_operator(
                "regex_match", "Acme Pty Ltd", r"(?i)^acme\s+pty\s+ltd$"
            )
            is True
        )

    def test_regex_no_match(self):
        assert (
            ConditionEvaluator._apply_operator(
                "regex_match", "Global Corp", r"(?i)^acme\s+pty\s+ltd$"
            )
            is False
        )

    def test_regex_none_actual(self):
        assert ConditionEvaluator._apply_operator("regex_match", None, r".*") is False

    # -- any_item_contains --
    def test_any_item_contains_dict_items(self):
        items = [
            {"description": "Office Supplies", "amount": "50.00"},
            {"description": "Labour charge", "amount": "200.00"},
        ]
        assert (
            ConditionEvaluator._apply_operator("any_item_contains", items, "labour")
            is True
        )
        assert (
            ConditionEvaluator._apply_operator("any_item_contains", items, "shipping")
            is False
        )

    def test_any_item_contains_string_items(self):
        items = ["apple", "banana", "cherry"]
        assert (
            ConditionEvaluator._apply_operator("any_item_contains", items, "ban")
            is True
        )

    def test_any_item_contains_not_a_list(self):
        assert (
            ConditionEvaluator._apply_operator("any_item_contains", "not a list", "x")
            is False
        )

    def test_any_item_contains_pipe_separated(self):
        items = [{"desc": "widget"}, {"desc": "gadget"}]
        assert (
            ConditionEvaluator._apply_operator(
                "any_item_contains", items, "widget|sprocket"
            )
            is True
        )
        assert (
            ConditionEvaluator._apply_operator(
                "any_item_contains", items, "sprocket|doohickey"
            )
            is False
        )

    # -- first_word_equals --
    def test_first_word_equals_simple(self):
        assert (
            ConditionEvaluator._apply_operator(
                "first_word_equals", "Acme Corp", "Acme Ltd"
            )
            is True
        )

    def test_first_word_equals_skips_articles(self):
        assert (
            ConditionEvaluator._apply_operator(
                "first_word_equals", "The Acme Corp", "Acme Ltd"
            )
            is True
        )

    def test_first_word_equals_skips_pty_ltd(self):
        assert (
            ConditionEvaluator._apply_operator(
                "first_word_equals", "Pty Ltd Acme", "Acme Corp"
            )
            is True
        )

    def test_first_word_equals_none(self):
        assert (
            ConditionEvaluator._apply_operator("first_word_equals", None, "Acme")
            is False
        )

    def test_first_word_equals_different(self):
        assert (
            ConditionEvaluator._apply_operator(
                "first_word_equals", "Global Corp", "Acme Corp"
            )
            is False
        )

    # -- Length checks --
    def test_length_equals(self):
        assert ConditionEvaluator._apply_operator("length_equals", [1, 2, 3], 3) is True
        assert ConditionEvaluator._apply_operator("length_equals", [1, 2], 3) is False

    def test_length_greater(self):
        assert (
            ConditionEvaluator._apply_operator("length_greater", [1, 2, 3], 2) is True
        )
        assert ConditionEvaluator._apply_operator("length_greater", [1], 2) is False

    def test_length_less(self):
        assert ConditionEvaluator._apply_operator("length_less", [1], 2) is True
        assert ConditionEvaluator._apply_operator("length_less", [1, 2, 3], 2) is False

    def test_length_with_none(self):
        assert ConditionEvaluator._apply_operator("length_equals", None, 0) is True


# ---------------------------------------------------------------------------
# evaluate_single
# ---------------------------------------------------------------------------


class TestEvaluateSingle:
    def test_full_condition_match(self):
        data = {"decision_phase1": "REJECT"}
        condition = {
            "field": "decision_phase1",
            "operator": "equals",
            "value": "REJECT",
        }
        assert ConditionEvaluator.evaluate_single(data, condition) is True

    def test_unsupported_operator(self):
        condition = {"field": "x", "operator": "INVALID_OP", "value": "y"}
        assert ConditionEvaluator.evaluate_single({"x": "y"}, condition) is False

    def test_dynamic_value_in_condition(self):
        data = {"vendor": "Acme", "match_field": "Acme"}
        condition = {
            "field": "vendor",
            "operator": "equals",
            "value": "_DYNAMIC_match_field_",
        }
        assert ConditionEvaluator.evaluate_single(data, condition) is True


# ---------------------------------------------------------------------------
# evaluate_all
# ---------------------------------------------------------------------------


class TestEvaluateAll:
    def test_all_pass(self):
        data = {"decision": "REJECT", "vendor": "Acme"}
        conditions = [
            {"field": "decision", "operator": "equals", "value": "REJECT"},
            {"field": "vendor", "operator": "contains", "value": "Acme"},
        ]
        passed, details = ConditionEvaluator.evaluate_all(data, conditions)
        assert passed is True
        assert len(details) == _EXPECTED_CONDITION_COUNT
        assert all(d["passed"] for d in details)

    def test_one_fails(self):
        data = {"decision": "ACCEPT", "vendor": "Acme"}
        conditions = [
            {"field": "decision", "operator": "equals", "value": "REJECT"},
            {"field": "vendor", "operator": "contains", "value": "Acme"},
        ]
        passed, details = ConditionEvaluator.evaluate_all(data, conditions)
        assert passed is False
        assert details[0]["passed"] is False
        assert details[1]["passed"] is True

    def test_empty_conditions(self):
        passed, details = ConditionEvaluator.evaluate_all({}, [])
        assert passed is True
        assert details == []


# ---------------------------------------------------------------------------
# Real ALF-001 rule scenario
# ---------------------------------------------------------------------------


class TestALF001Scenario:
    """Test the actual ALF-001 rule conditions from rule_base.json."""

    ALF_001_CONDITIONS: ClassVar[list[dict[str, str]]] = [
        {
            "field": "decision_phase1",
            "operator": "equals",
            "value": "REJECT",
        },
        {
            "field": "phase1.rejection_template",
            "operator": "contains",
            "value": "different company",
        },
        {
            "field": "invoice.customer_name",
            "operator": "regex_match",
            "value": r"(?i)^acme\s+pty\s+ltd$",
        },
    ]

    def test_case_004_matches(self):
        """case_004: Acme Pty Ltd rejected for wrong customer -- should match."""
        data = {
            "decision_phase1": "REJECT",
            "phase1": {"rejection_template": "Invoice addressed to different company"},
            "invoice": {"customer_name": "Acme Pty Ltd"},
        }
        passed, _ = ConditionEvaluator.evaluate_all(data, self.ALF_001_CONDITIONS)
        assert passed is True

    def test_case_001_no_match(self):
        """case_001: Rejected for GST, not customer name -- should not match."""
        data = {
            "decision_phase1": "REJECT",
            "phase1": {"rejection_template": "GST calculation error"},
            "invoice": {"customer_name": "ACME Corp"},
        }
        passed, _ = ConditionEvaluator.evaluate_all(data, self.ALF_001_CONDITIONS)
        assert passed is False

    def test_case_002_no_match(self):
        """case_002: Accepted invoice -- should not match (not rejected)."""
        data = {
            "decision_phase1": "ACCEPT",
            "phase1": {},
            "invoice": {"customer_name": "ACME Corp"},
        }
        passed, _ = ConditionEvaluator.evaluate_all(data, self.ALF_001_CONDITIONS)
        assert passed is False
