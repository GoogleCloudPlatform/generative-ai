"""Tests for RuleWriterAgent -- validation, conflicts, ID generation, formatting."""

import json
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import invoice_processing.core.rule_writer as rw_module
from invoice_processing.core.rule_writer import RuleWriterAgent

_EXPECTED_RULE_COUNT = 2


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_RULE_BASE = {
    "schema_version": "2.0.0",
    "metadata": {"total_rules": 1},
    "rules": [
        {
            "id": "ALF-001",
            "name": "Test Rule",
            "scope": "customer_entity_validation",
            "priority": 50,
            "conditions": [
                {"field": "decision", "operator": "equals", "value": "REJECT"}
            ],
            "actions": [{"type": "override_decision", "value": "ACCEPT"}],
        }
    ],
}

VALID_RULE = {
    "id": "ALF-002",
    "name": "New Rule",
    "scope": "calculation_validation",
    "priority": 60,
    "conditions": [
        {"field": "decision_phase4", "operator": "equals", "value": "REJECT"},
        {
            "field": "phase4.rejection_template",
            "operator": "contains",
            "value": "false positive",
        },
    ],
    "actions": [{"type": "override_decision", "value": "ACCEPT"}],
    "metadata": {"severity": "HIGH", "root_cause": "Test"},
}


def _make_agent_with_rule_base(rule_base_dict: dict) -> RuleWriterAgent:
    """Create a RuleWriterAgent with a temp rule base file."""
    agent = RuleWriterAgent()
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False, encoding="utf-8"
    )
    json.dump(rule_base_dict, tmp, indent=2)
    tmp.close()
    return agent, Path(tmp.name)


# ---------------------------------------------------------------------------
# validate_rule
# ---------------------------------------------------------------------------


class TestValidateRule:
    def setup_method(self):
        self.agent = RuleWriterAgent()

    def test_valid_rule_no_errors(self):
        errors = self.agent.validate_rule(VALID_RULE)
        assert errors == []

    def test_missing_id(self):
        rule = {k: v for k, v in VALID_RULE.items() if k != "id"}
        errors = self.agent.validate_rule(rule)
        assert any("'id'" in e for e in errors)

    def test_missing_name(self):
        rule = {k: v for k, v in VALID_RULE.items() if k != "name"}
        errors = self.agent.validate_rule(rule)
        assert any("'name'" in e for e in errors)

    def test_missing_conditions(self):
        rule = {k: v for k, v in VALID_RULE.items() if k != "conditions"}
        errors = self.agent.validate_rule(rule)
        assert any("'conditions'" in e for e in errors)

    def test_missing_actions(self):
        rule = {k: v for k, v in VALID_RULE.items() if k != "actions"}
        errors = self.agent.validate_rule(rule)
        assert any("'actions'" in e for e in errors)

    def test_unsupported_operator(self):
        rule = {
            **VALID_RULE,
            "conditions": [{"field": "x", "operator": "FAKE_OP", "value": "y"}],
        }
        errors = self.agent.validate_rule(rule)
        assert any("unsupported operator" in e for e in errors)

    def test_unsupported_action_type(self):
        rule = {
            **VALID_RULE,
            "actions": [{"type": "teleport_data"}],
        }
        errors = self.agent.validate_rule(rule)
        assert any("unsupported type" in e for e in errors)

    def test_condition_missing_field(self):
        rule = {
            **VALID_RULE,
            "conditions": [{"operator": "equals", "value": "x"}],
        }
        errors = self.agent.validate_rule(rule)
        assert any("missing 'field'" in e for e in errors)

    def test_condition_missing_operator(self):
        rule = {
            **VALID_RULE,
            "conditions": [{"field": "x", "value": "y"}],
        }
        errors = self.agent.validate_rule(rule)
        assert any("missing 'operator'" in e for e in errors)

    def test_action_missing_type(self):
        rule = {
            **VALID_RULE,
            "actions": [{"value": "something"}],
        }
        errors = self.agent.validate_rule(rule)
        assert any("missing 'type'" in e for e in errors)


# ---------------------------------------------------------------------------
# check_conflicts
# ---------------------------------------------------------------------------


class TestCheckConflicts:
    def test_duplicate_id_warning(self):
        agent, tmp_path = _make_agent_with_rule_base(SAMPLE_RULE_BASE)
        with patch("invoice_processing.core.config.RULE_BASE_PATH", tmp_path):
            with patch.object(
                type(agent), "load_rule_base", return_value=SAMPLE_RULE_BASE
            ):
                rule = {**VALID_RULE, "id": "ALF-001"}  # duplicate
                with patch.object(
                    agent,
                    "get_existing_rules",
                    return_value=SAMPLE_RULE_BASE["rules"],
                ):
                    warnings = agent.check_conflicts(rule)
        assert any("already exists" in w for w in warnings)
        tmp_path.unlink(missing_ok=True)

    def test_priority_collision_warning(self):
        agent = RuleWriterAgent()
        rule = {
            **VALID_RULE,
            "scope": "customer_entity_validation",
            "priority": 50,
        }
        with patch.object(
            agent, "get_existing_rules", return_value=SAMPLE_RULE_BASE["rules"]
        ):
            warnings = agent.check_conflicts(rule)
        assert any("Priority collision" in w for w in warnings)

    def test_scope_mutual_exclusion_warning(self):
        agent = RuleWriterAgent()
        rule = {**VALID_RULE, "scope": "customer_entity_validation"}
        with patch.object(
            agent, "get_existing_rules", return_value=SAMPLE_RULE_BASE["rules"]
        ):
            warnings = agent.check_conflicts(rule)
        assert any("mutual exclusion" in w for w in warnings)

    def test_no_conflicts_different_scope(self):
        agent = RuleWriterAgent()
        with patch.object(
            agent, "get_existing_rules", return_value=SAMPLE_RULE_BASE["rules"]
        ):
            warnings = agent.check_conflicts(VALID_RULE)
        # Should only have no duplicate/priority warnings
        assert not any("already exists" in w for w in warnings)
        assert not any("Priority collision" in w for w in warnings)


# ---------------------------------------------------------------------------
# next_rule_id
# ---------------------------------------------------------------------------


class TestNextRuleId:
    def test_increments_from_existing(self):
        agent = RuleWriterAgent()
        with patch.object(
            agent, "get_existing_rules", return_value=SAMPLE_RULE_BASE["rules"]
        ):
            assert agent.next_rule_id() == "ALF-002"

    def test_starts_at_001_when_empty(self):
        agent = RuleWriterAgent()
        with patch.object(agent, "get_existing_rules", return_value=[]):
            assert agent.next_rule_id() == "ALF-001"

    def test_handles_multiple_rules(self):
        rules = [
            {"id": "ALF-001"},
            {"id": "ALF-005"},
            {"id": "ALF-003"},
        ]
        agent = RuleWriterAgent()
        with patch.object(agent, "get_existing_rules", return_value=rules):
            assert agent.next_rule_id() == "ALF-006"

    def test_handles_malformed_ids(self):
        rules = [{"id": "ALF-001"}, {"id": "BAD"}, {"id": "ALF-xyz"}]
        agent = RuleWriterAgent()
        with patch.object(agent, "get_existing_rules", return_value=rules):
            assert agent.next_rule_id() == "ALF-002"


# ---------------------------------------------------------------------------
# format_rule_display
# ---------------------------------------------------------------------------


class TestFormatRuleDisplay:
    def test_includes_key_fields(self):
        agent = RuleWriterAgent()
        output = agent.format_rule_display(VALID_RULE)
        assert "ALF-002" in output
        assert "New Rule" in output
        assert "calculation_validation" in output
        assert "60" in output
        assert "Conditions:" in output
        assert "Actions:" in output

    def test_includes_metadata(self):
        agent = RuleWriterAgent()
        output = agent.format_rule_display(VALID_RULE)
        assert "Severity: HIGH" in output
        assert "Root cause: Test" in output

    def test_handles_missing_metadata(self):
        rule = {k: v for k, v in VALID_RULE.items() if k != "metadata"}
        agent = RuleWriterAgent()
        output = agent.format_rule_display(rule)
        assert "Conditions:" in output  # still works


# ---------------------------------------------------------------------------
# run (write rule to file)
# ---------------------------------------------------------------------------


class TestRunWriteRule:
    def _make_tmp_rule_base(self):
        """Write SAMPLE_RULE_BASE to a temp file and return path."""
        f = tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        )
        json.dump(SAMPLE_RULE_BASE, f, indent=2)
        f.close()
        return Path(f.name)

    def _cleanup(self, tmp_path):
        tmp_path.unlink(missing_ok=True)
        for bak in tmp_path.parent.glob(f"{tmp_path.stem}*.bak.*"):
            bak.unlink(missing_ok=True)

    def test_add_rule_success(self):
        tmp_path = self._make_tmp_rule_base()
        try:
            original = rw_module.RULE_BASE_PATH
            rw_module.RULE_BASE_PATH = tmp_path
            try:
                agent = RuleWriterAgent()
                result = agent.run(VALID_RULE, mode="add")

                assert result.success is True
                assert result.rule_id == "ALF-002"
                assert result.mode == "add"
                assert result.total_rules == _EXPECTED_RULE_COUNT

                # Verify file contents
                with open(tmp_path) as f:
                    saved = json.load(f)
                assert len(saved["rules"]) == _EXPECTED_RULE_COUNT
                assert saved["rules"][1]["id"] == "ALF-002"
            finally:
                rw_module.RULE_BASE_PATH = original
        finally:
            self._cleanup(tmp_path)

    def test_add_duplicate_id_fails(self):
        tmp_path = self._make_tmp_rule_base()
        try:
            original = rw_module.RULE_BASE_PATH
            rw_module.RULE_BASE_PATH = tmp_path
            try:
                dup_rule = {**VALID_RULE, "id": "ALF-001"}
                agent = RuleWriterAgent()
                result = agent.run(dup_rule, mode="add")
                assert result.success is False
                assert "already exists" in result.message
            finally:
                rw_module.RULE_BASE_PATH = original
        finally:
            self._cleanup(tmp_path)

    def test_validation_failure_prevents_write(self):
        agent = RuleWriterAgent()
        bad_rule = {"id": "ALF-999"}  # missing name, conditions, actions
        result = agent.run(bad_rule, mode="add")
        assert result.success is False
        assert "Validation errors" in result.message
