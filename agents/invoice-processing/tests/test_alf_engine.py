"""Tests for ALFEngine -- schema validation, consistency, rule management."""

import json
import sys
import tempfile
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from invoice_processing.shared_libraries.alf_engine import (
    SUPPORTED_ACTION_TYPES,
    SUPPORTED_CONDITION_OPERATORS,
    ALFEngine,
    Rule,
    RuleAggregator,
)

_MIN_CONDITION_OPERATORS = 19
_MIN_ACTION_TYPES = 10
_EXPECTED_RULE_COUNT = 2

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


class TestConstants:
    def test_supported_operators_is_set(self):
        assert isinstance(SUPPORTED_CONDITION_OPERATORS, set)
        assert len(SUPPORTED_CONDITION_OPERATORS) >= _MIN_CONDITION_OPERATORS

    def test_key_operators_present(self):
        for op in [
            "equals",
            "contains",
            "regex_match",
            "greater_than",
            "is_null",
            "in_list",
            "any_item_contains",
            "first_word_equals",
        ]:
            assert op in SUPPORTED_CONDITION_OPERATORS

    def test_supported_actions_is_set(self):
        assert isinstance(SUPPORTED_ACTION_TYPES, set)
        assert len(SUPPORTED_ACTION_TYPES) >= _MIN_ACTION_TYPES

    def test_key_actions_present(self):
        for action in [
            "override_decision",
            "set_field",
            "llm_continue_processing",
            "llm_patch_fields",
            "append_note",
            "add_to_list",
        ]:
            assert action in SUPPORTED_ACTION_TYPES


# ---------------------------------------------------------------------------
# ALFEngine -- load and validate
# ---------------------------------------------------------------------------

MINIMAL_RULE_BASE = {
    "schema_version": "2.0.0",
    "metadata": {"total_rules": 1},
    "rules": [
        {
            "id": "ALF-001",
            "name": "Test",
            "scope": "test_scope",
            "priority": 50,
            "enabled": True,
            "conditions": [
                {"field": "decision", "operator": "equals", "value": "REJECT"}
            ],
            "actions": [{"type": "override_decision", "value": "ACCEPT"}],
        }
    ],
}


def _write_rule_base(data: dict) -> Path:
    """Write rule base to temp file and return path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(data, tmp, indent=2)
    tmp.close()
    return Path(tmp.name)


class TestALFEngineLoad:
    def test_load_valid_rule_base(self):
        path = _write_rule_base(MINIMAL_RULE_BASE)
        try:
            engine = ALFEngine(rule_base_path=path)
            assert len(engine.rules) == 1
            assert engine.rules[0].id == "ALF-001"
        finally:
            path.unlink()

    def test_load_empty_rules(self):
        data = {
            "schema_version": "2.0.0",
            "metadata": {"total_rules": 0},
            "rules": [],
        }
        path = _write_rule_base(data)
        try:
            engine = ALFEngine(rule_base_path=path)
            assert len(engine.rules) == 0
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# Schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_valid_schema_passes(self):
        path = _write_rule_base(MINIMAL_RULE_BASE)
        try:
            engine = ALFEngine(rule_base_path=path)
            # A valid schema loads its rules without raising.
            assert len(engine.rules) == 1
        finally:
            path.unlink()

    def test_missing_schema_version_raises(self):
        data = {"rules": []}
        path = _write_rule_base(data)
        try:
            with pytest.raises(ValueError, match="schema_version"):
                ALFEngine(rule_base_path=path)
        finally:
            path.unlink()

    def test_missing_rules_key_raises(self):
        data = {"schema_version": "2.0.0"}
        path = _write_rule_base(data)
        try:
            with pytest.raises(ValueError, match="'rules'"):
                ALFEngine(rule_base_path=path)
        finally:
            path.unlink()

    def test_rule_missing_id_raises(self):
        data = {
            "schema_version": "2.0.0",
            "rules": [
                {
                    "name": "No ID",
                    "conditions": [{"field": "x", "operator": "equals", "value": "y"}],
                    "actions": [{"type": "set_field"}],
                }
            ],
        }
        path = _write_rule_base(data)
        try:
            with pytest.raises(ValueError, match="id"):
                ALFEngine(rule_base_path=path)
        finally:
            path.unlink()

    def test_invalid_operator_raises(self):
        data = {
            "schema_version": "2.0.0",
            "rules": [
                {
                    "id": "ALF-001",
                    "conditions": [
                        {"field": "x", "operator": "INVALID_OP", "value": "y"}
                    ],
                    "actions": [{"type": "set_field"}],
                }
            ],
        }
        path = _write_rule_base(data)
        try:
            with pytest.raises(ValueError, match="operator"):
                ALFEngine(rule_base_path=path)
        finally:
            path.unlink()

    def test_invalid_action_type_raises(self):
        data = {
            "schema_version": "2.0.0",
            "rules": [
                {
                    "id": "ALF-001",
                    "conditions": [{"field": "x", "operator": "equals", "value": "y"}],
                    "actions": [{"type": "teleport"}],
                }
            ],
        }
        path = _write_rule_base(data)
        try:
            with pytest.raises(ValueError, match="action"):
                ALFEngine(rule_base_path=path)
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# Rule queries
# ---------------------------------------------------------------------------


class TestRuleQueries:
    def setup_method(self):
        self.path = _write_rule_base(MINIMAL_RULE_BASE)
        self.engine = ALFEngine(rule_base_path=self.path)

    def teardown_method(self):
        self.path.unlink()

    def test_get_rules_by_scope(self):
        rules = self.engine.get_rules_by_scope("test_scope")
        assert len(rules) == 1

    def test_get_rules_by_scope_empty(self):
        rules = self.engine.get_rules_by_scope("nonexistent")
        assert len(rules) == 0

    def test_get_rules_by_tag(self):
        # Add a rule with tags
        self.engine.add_rule(
            {
                "id": "ALF-002",
                "name": "Tagged",
                "tags": ["phase1", "override"],
                "conditions": [{"field": "x", "operator": "equals", "value": "y"}],
                "actions": [{"type": "set_field"}],
            }
        )
        rules = self.engine.get_rules_by_tag("phase1")
        assert len(rules) == 1
        assert rules[0].id == "ALF-002"

    def test_add_rule(self):
        self.engine.add_rule(
            {
                "id": "ALF-003",
                "name": "New",
                "conditions": [{"field": "x", "operator": "equals", "value": "y"}],
                "actions": [{"type": "set_field"}],
            }
        )
        assert len(self.engine.rules) == _EXPECTED_RULE_COUNT

    def test_add_duplicate_id_raises(self):
        with pytest.raises(ValueError, match="ALF-001"):
            self.engine.add_rule(
                {
                    "id": "ALF-001",
                    "name": "Dup",
                    "conditions": [],
                    "actions": [],
                }
            )


# ---------------------------------------------------------------------------
# Consistency validation
# ---------------------------------------------------------------------------


class TestConsistencyValidation:
    def test_clean_rule_base(self):
        path = _write_rule_base(MINIMAL_RULE_BASE)
        try:
            engine = ALFEngine(rule_base_path=path)
            issues = engine.validate_rule_base_consistency()
            assert len(issues) == 0
        finally:
            path.unlink()

    def test_duplicate_id_detected(self):
        data = {
            "schema_version": "2.0.0",
            "rules": [
                {
                    "id": "ALF-001",
                    "conditions": [{"field": "x", "operator": "equals", "value": "y"}],
                    "actions": [{"type": "set_field"}],
                },
                {
                    "id": "ALF-001",
                    "conditions": [{"field": "a", "operator": "equals", "value": "b"}],
                    "actions": [{"type": "set_field"}],
                },
            ],
        }
        path = _write_rule_base(data)
        try:
            engine = ALFEngine(rule_base_path=path)
            issues = engine.validate_rule_base_consistency()
            assert any("duplicate" in str(i).lower() for i in issues)
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# Save rule base
# ---------------------------------------------------------------------------


class TestSaveRuleBase:
    def test_save_and_reload(self):
        path = _write_rule_base(MINIMAL_RULE_BASE)
        try:
            engine = ALFEngine(rule_base_path=path)
            engine.add_rule(
                {
                    "id": "ALF-002",
                    "name": "Second",
                    "conditions": [{"field": "x", "operator": "equals", "value": "y"}],
                    "actions": [{"type": "set_field"}],
                }
            )

            out_path = path.parent / "test_save_output.json"
            engine.save_rule_base(out_path)

            with open(out_path) as f:
                saved = json.load(f)
            assert len(saved["rules"]) == _EXPECTED_RULE_COUNT
            assert saved["schema_version"] == "2.0.0"
            out_path.unlink()
        finally:
            path.unlink()


# ---------------------------------------------------------------------------
# RuleAggregator.collect -- scope mutual exclusion
# ---------------------------------------------------------------------------


class TestRuleAggregatorCollect:
    def test_single_rule_matches(self):
        rules = [
            {
                "id": "ALF-001",
                "name": "R1",
                "scope": "scope_a",
                "priority": 50,
                "enabled": True,
                "conditions": [
                    {
                        "field": "decision",
                        "operator": "equals",
                        "value": "REJECT",
                    }
                ],
                "actions": [{"type": "override_decision", "value": "ACCEPT"}],
            }
        ]
        context = {"decision": "REJECT"}
        rule_objects = [Rule(r) for r in rules]
        matched, _audit, _ = RuleAggregator.collect(rule_objects, context)
        assert len(matched) == 1

    def test_scope_mutual_exclusion(self):
        """Only the first matching rule in a scope should fire (first-match-wins)."""
        rules = [
            {
                "id": "ALF-001",
                "name": "First rule",
                "scope": "same_scope",
                "priority": 50,
                "enabled": True,
                "conditions": [{"field": "x", "operator": "equals", "value": "yes"}],
                "actions": [{"type": "set_field"}],
            },
            {
                "id": "ALF-002",
                "name": "Second rule same scope",
                "scope": "same_scope",
                "priority": 60,
                "enabled": True,
                "conditions": [{"field": "x", "operator": "equals", "value": "yes"}],
                "actions": [{"type": "set_field"}],
            },
        ]
        context = {"x": "yes"}
        rule_objects = [Rule(r) for r in rules]
        matched, _, _ = RuleAggregator.collect(rule_objects, context)
        assert len(matched) == 1
        matched_id = matched[0][0].id
        assert matched_id == "ALF-001"  # first match wins within scope

    def test_disabled_rule_filtered_at_load(self):
        """Disabled rules are filtered out during ALFEngine load, not in collect."""
        data = {
            "schema_version": "2.0.0",
            "rules": [
                {
                    "id": "ALF-001",
                    "scope": "s",
                    "priority": 50,
                    "enabled": False,
                    "conditions": [
                        {"field": "x", "operator": "equals", "value": "yes"}
                    ],
                    "actions": [{"type": "set_field"}],
                },
                {
                    "id": "ALF-002",
                    "scope": "s2",
                    "priority": 50,
                    "enabled": True,
                    "conditions": [
                        {"field": "x", "operator": "equals", "value": "yes"}
                    ],
                    "actions": [{"type": "set_field"}],
                },
            ],
        }
        path = _write_rule_base(data)
        try:
            engine = ALFEngine(rule_base_path=path)
            # Only the enabled rule should be loaded
            assert len(engine.rules) == 1
            assert engine.rules[0].id == "ALF-002"
        finally:
            path.unlink()
