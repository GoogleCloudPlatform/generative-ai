"""Tests for ImpactAssessorAgent -- impact analysis logic."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from invoice_processing.core.impact_assessor import (
    CaseMatch,
    ImpactAssessorAgent,
    ImpactReport,
    _truncate,
)

_SMALL_CASE_COUNT = 5
_LARGE_CASE_COUNT = 50
_DEFAULT_SAMPLE_SIZE = 10
_SMALL_SAMPLE_SIZE = 5
_EXPECTED_SAFE_ALL = 4
_EXPECTED_SAFE_SAMPLED = 9
_EXACT_SAMPLE_COUNT = 10

# ---------------------------------------------------------------------------
# _truncate helper
# ---------------------------------------------------------------------------


class TestTruncate:
    def test_short_string_unchanged(self):
        assert _truncate("hello") == "hello"

    def test_long_string_truncated(self):
        long = "a" * 100
        result = _truncate(long, max_len=10)
        assert result == "a" * 10 + "..."

    def test_exact_length(self):
        assert _truncate("12345", max_len=5) == "12345"

    def test_non_string_converted(self):
        assert _truncate(42) == "42"
        assert _truncate(None) == "None"


# ---------------------------------------------------------------------------
# _get_case_summary
# ---------------------------------------------------------------------------


class TestGetCaseSummary:
    def setup_method(self):
        self.agent = ImpactAssessorAgent.__new__(ImpactAssessorAgent)

    def test_phase1_reject(self):
        context = {
            "phase1": {
                "decision": "REJECT",
                "rejection_template": "wrong company",
            },
            "phase2": {},
        }
        decision, reason = self.agent._get_case_summary(context)
        assert decision == "REJECT"
        assert reason == "wrong company"

    def test_phase4_set_aside(self):
        context = {
            "phase1": {"decision": "ACCEPT"},
            "phase2": {"decision": "ACCEPT"},
            "phase3": {"decision": "ACCEPT"},
            "phase4": {
                "decision": "SET_ASIDE",
                "rejection_template": "needs review",
            },
        }
        decision, reason = self.agent._get_case_summary(context)
        assert decision == "SET_ASIDE"
        assert reason == "needs review"

    def test_all_accept_falls_through(self):
        context = {
            "phase1": {"decision": "ACCEPT"},
            "phase2": {"decision": "ACCEPT"},
            "phase3": {"decision": "ACCEPT"},
            "phase4": {"decision": "ACCEPT"},
            "decision": {"decision": "ACCEPT"},
        }
        decision, reason = self.agent._get_case_summary(context)
        assert decision == "ACCEPT"
        assert reason == ""

    def test_empty_context(self):
        decision, reason = self.agent._get_case_summary({})
        assert decision == "ACCEPT"  # fallback from empty decision dict
        assert reason == ""


# ---------------------------------------------------------------------------
# _build_summary
# ---------------------------------------------------------------------------


class TestBuildSummary:
    def setup_method(self):
        self.agent = ImpactAssessorAgent.__new__(ImpactAssessorAgent)

    def test_safe_report(self):
        report = ImpactReport(
            target_case_id="case_004",
            target_matched=True,
            collateral_matches=[],
            safe_cases=["case_001", "case_002", "case_003"],
            total_cases=4,
        )
        summary = self.agent._build_summary(report)
        assert "safe to apply" in summary.lower()
        assert "case_004" in summary
        assert "MATCH (target)" in summary

    def test_target_not_matched_warning(self):
        report = ImpactReport(
            target_case_id="case_004",
            target_matched=False,
            collateral_matches=[],
            safe_cases=["case_001"],
            total_cases=2,
        )
        summary = self.agent._build_summary(report)
        assert "WARNING" in summary
        assert "does NOT match" in summary

    def test_collateral_matches_warning(self):
        report = ImpactReport(
            target_case_id="case_004",
            target_matched=True,
            collateral_matches=[
                CaseMatch(
                    case_id="case_001",
                    matched=True,
                    condition_details=[
                        {
                            "field": "decision",
                            "operator": "equals",
                            "actual": "REJECT",
                            "passed": True,
                        }
                    ],
                    decision="REJECT",
                    rejection_reason="GST error",
                )
            ],
            safe_cases=[],
            total_cases=2,
        )
        summary = self.agent._build_summary(report)
        assert "WARNING" in summary
        assert "1 other case(s)" in summary
        assert "case_001" in summary


# ---------------------------------------------------------------------------
# run (with mocked contexts)
# ---------------------------------------------------------------------------


class TestImpactAssessorRun:
    def test_target_matches_no_collateral(self):
        agent = ImpactAssessorAgent.__new__(ImpactAssessorAgent)
        agent._loader = MagicMock()
        agent._contexts_cache = {}

        contexts = {
            "case_004": {
                "decision_phase1": "REJECT",
                "phase1": {
                    "decision": "REJECT",
                    "rejection_template": "different company",
                },
                "invoice": {"customer_name": "Acme Pty Ltd"},
            },
            "case_001": {
                "decision_phase1": "REJECT",
                "phase1": {
                    "decision": "REJECT",
                    "rejection_template": "GST error",
                },
                "invoice": {"customer_name": "ACME Corp"},
            },
            "case_002": {
                "decision_phase1": "ACCEPT",
                "phase1": {"decision": "ACCEPT"},
                "invoice": {"customer_name": "ACME Corp"},
            },
        }

        with patch.object(agent, "_load_all_contexts", return_value=contexts):
            conditions = [
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
            report = agent.run(conditions, target_case_id="case_004")

        assert report.target_matched is True
        assert len(report.collateral_matches) == 0
        assert "case_001" in report.safe_cases or "case_002" in report.safe_cases
        assert "safe to apply" in report.summary.lower()


# ---------------------------------------------------------------------------
# Sampling behaviour
# ---------------------------------------------------------------------------


def _make_contexts(n: int) -> dict[str, dict]:
    """Generate n fake case contexts. case_target is always the target."""
    contexts = {}
    contexts["case_target"] = {
        "decision_phase1": "REJECT",
        "phase1": {"decision": "REJECT", "rejection_template": "target reason"},
    }
    for i in range(n - 1):
        contexts[f"case_{i:04d}"] = {
            "decision_phase1": "ACCEPT",
            "phase1": {"decision": "ACCEPT"},
        }
    return contexts


class TestSampling:
    def _make_agent(self, contexts):
        agent = ImpactAssessorAgent.__new__(ImpactAssessorAgent)
        agent._loader = MagicMock()
        agent._contexts_cache = contexts
        return agent

    def test_no_sampling_when_fewer_than_sample_size(self):
        contexts = _make_contexts(_SMALL_CASE_COUNT)
        agent = self._make_agent(contexts)
        conditions = [
            {
                "field": "decision_phase1",
                "operator": "equals",
                "value": "REJECT",
            }
        ]

        report = agent.run(conditions, "case_target", sample_size=_DEFAULT_SAMPLE_SIZE)

        assert report.sampled is False
        assert report.total_cases == _SMALL_CASE_COUNT
        assert report.sample_size == _SMALL_CASE_COUNT
        # All non-target cases should be in safe_cases
        assert len(report.safe_cases) == _EXPECTED_SAFE_ALL
        assert "Scanning 5 cases" in report.summary

    def test_sampling_when_more_than_sample_size(self):
        contexts = _make_contexts(_LARGE_CASE_COUNT)
        agent = self._make_agent(contexts)
        conditions = [
            {
                "field": "decision_phase1",
                "operator": "equals",
                "value": "REJECT",
            }
        ]

        report = agent.run(conditions, "case_target", sample_size=_DEFAULT_SAMPLE_SIZE)

        assert report.sampled is True
        assert report.total_cases == _LARGE_CASE_COUNT
        assert report.sample_size == _DEFAULT_SAMPLE_SIZE
        # Only 9 non-target cases should be evaluated (10 - 1 target)
        assert len(report.safe_cases) == _EXPECTED_SAFE_SAMPLED
        assert "Sampled 10 of 50" in report.summary
        assert "NOTE:" in report.summary

    def test_target_always_included_in_sample(self):
        contexts = _make_contexts(100)
        agent = self._make_agent(contexts)
        conditions = [
            {
                "field": "decision_phase1",
                "operator": "equals",
                "value": "REJECT",
            }
        ]

        report = agent.run(conditions, "case_target", sample_size=_SMALL_SAMPLE_SIZE)

        assert report.target_matched is True
        assert report.sample_size == _SMALL_SAMPLE_SIZE

    def test_sampling_summary_includes_note(self):
        contexts = _make_contexts(20)
        agent = self._make_agent(contexts)
        conditions = [
            {
                "field": "decision_phase1",
                "operator": "equals",
                "value": "ACCEPT",
            }
        ]

        report = agent.run(conditions, "case_target", sample_size=_SMALL_SAMPLE_SIZE)

        assert report.sampled is True
        assert "NOTE: Only 5 of 20 cases" in report.summary
        assert "larger sample_size" in report.summary

    def test_exact_sample_size_no_sampling(self):
        contexts = _make_contexts(10)
        agent = self._make_agent(contexts)
        conditions = [
            {
                "field": "decision_phase1",
                "operator": "equals",
                "value": "REJECT",
            }
        ]

        report = agent.run(conditions, "case_target", sample_size=_EXACT_SAMPLE_COUNT)

        assert report.sampled is False
        assert report.sample_size == _EXACT_SAMPLE_COUNT
