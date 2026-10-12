"""Safe Rule Orchestrator

Programmatic safety loop for rule discovery and revision.
Generates rules via LLM, then automatically validates, assesses impact,
and auto-tightens conditions if collateral matches are found.

Enforces the safety loop in code (not prompt instructions) so it cannot
be skipped by the LLM agent.
"""

import json
import logging

from .case_loader import CaseLoaderAgent
from .impact_assessor import ImpactAssessorAgent
from .rule_discoverer import RuleDiscovererAgent
from .rule_writer import RuleWriterAgent

logger = logging.getLogger("LearningAgent.SafeRuleOrchestrator")

MAX_SAFETY_ATTEMPTS = 3
DEFAULT_SAMPLE_SIZE = 10


class SafeRuleOrchestrator:
    """Orchestrates rule discovery/revision with automatic safety validation.

    Both discover() and revise() run the same safety loop:
      generate/revise → validate → assess impact → if collateral, auto-tighten → repeat
    """

    def __init__(self):
        self._discoverer = RuleDiscovererAgent()
        self._writer = RuleWriterAgent()
        self._impact = ImpactAssessorAgent()
        self._loader = CaseLoaderAgent()

    def _format_collateral_info(self, collateral_matches: list) -> str:
        """Format collateral match details for the revision prompt."""
        lines = []
        for m in collateral_matches:
            lines.append(
                f"- {m.case_id}: current decision={m.decision}, "
                f"rejection_reason={m.rejection_reason or '(none)'}"
            )
        return "\n".join(lines)

    def _run_safety_loop(
        self,
        case_id: str,
        initial_rule: dict,
        sample_size: int = DEFAULT_SAMPLE_SIZE,
    ) -> dict:
        """Run validate → impact → auto-tighten loop on a rule.

        Args:
            case_id: The target case ID.
            initial_rule: The rule dict to validate and assess.
            sample_size: Number of cases to sample for impact assessment.

        Returns:
            dict with: rule, impact, attempts, revision_log, success, etc.
        """
        case_data = self._loader.run(case_id)
        rule_dict = initial_rule
        revision_log = []
        impact_report = None

        for attempt in range(MAX_SAFETY_ATTEMPTS):
            # Validate schema
            errors = self._writer.validate_rule(rule_dict)
            if errors:
                revision_log.append(
                    {
                        "attempt": attempt + 1,
                        "issue": "validation_errors",
                        "errors": errors,
                    }
                )
                # Try to fix via revision
                proposed = self._discoverer.revise(
                    case_data,
                    rule_dict,
                    f"Fix these schema validation errors: {'; '.join(errors)}",
                    "",
                )
                if not proposed.success:
                    return self._error_result(
                        rule_dict,
                        revision_log,
                        f"Failed to fix validation errors after revision: {proposed.parse_errors}",
                    )
                rule_dict = proposed.rule_dict
                continue

            # Assess impact
            conditions = rule_dict.get("conditions", [])
            impact_report = self._impact.run(conditions, case_id, sample_size)

            # Check: does the rule match the target case?
            if not impact_report.target_matched:
                revision_log.append(
                    {
                        "attempt": attempt + 1,
                        "issue": "target_not_matched",
                    }
                )
                proposed = self._discoverer.revise(
                    case_data,
                    rule_dict,
                    "CRITICAL: The rule does NOT match the target case. "
                    "The conditions are too narrow. Broaden them so the "
                    "target case matches while remaining conservative.",
                    impact_report.summary,
                )
                if not proposed.success:
                    return self._error_result(
                        rule_dict,
                        revision_log,
                        f"Failed to broaden conditions: {proposed.parse_errors}",
                    )
                rule_dict = proposed.rule_dict
                continue

            # Check: any collateral matches?
            if not impact_report.collateral_matches:
                # Safe — no collateral
                break

            # Collateral found — auto-tighten
            collateral_info = self._format_collateral_info(
                impact_report.collateral_matches
            )
            collateral_ids = [m.case_id for m in impact_report.collateral_matches]
            revision_log.append(
                {
                    "attempt": attempt + 1,
                    "issue": "collateral_matches",
                    "collateral_cases": collateral_ids,
                }
            )
            logger.info(
                f"Attempt {attempt + 1}: collateral matches {collateral_ids}, "
                f"auto-tightening conditions"
            )

            proposed = self._discoverer.revise(
                case_data,
                rule_dict,
                f"The rule has UNINTENDED collateral matches on these cases:\n"
                f"{collateral_info}\n\n"
                f"Tighten the conditions to EXCLUDE these cases while still "
                f"matching the target case {case_id}. Add more specific "
                f"conditions (e.g. vendor name, amount range, specific "
                f"rejection template text, service category).",
                impact_report.summary,
            )
            if not proposed.success:
                # Can't auto-tighten — return with warning
                revision_log.append(
                    {
                        "attempt": attempt + 1,
                        "issue": "auto_tighten_failed",
                        "errors": proposed.parse_errors,
                    }
                )
                break
            rule_dict = proposed.rule_dict

        # Build final result
        display = self._writer.format_rule_display(rule_dict)
        has_collateral = bool(impact_report and impact_report.collateral_matches)

        impact_dict = {}
        if impact_report:
            impact_dict = {
                "target_matched": impact_report.target_matched,
                "collateral_matches": [
                    {
                        "case_id": m.case_id,
                        "current_decision": m.decision,
                        "rejection_reason": m.rejection_reason,
                    }
                    for m in impact_report.collateral_matches
                ],
                "safe_cases": impact_report.safe_cases,
                "total_cases": impact_report.total_cases,
                "sampled": impact_report.sampled,
                "sample_size": impact_report.sample_size,
                "summary": impact_report.summary,
            }

        return {
            "success": True,
            "rule": rule_dict,
            "rule_json": json.dumps(rule_dict, indent=2, default=str),
            "display": display,
            "impact": impact_dict,
            "attempts": attempt + 1,
            "revision_log": revision_log,
            "has_collateral": has_collateral,
            "collateral_warning": (
                f"WARNING: {len(impact_report.collateral_matches)} collateral "
                f"match(es) remain after {attempt + 1} auto-tighten attempts. "
                f"SME review required."
                if has_collateral
                else ""
            ),
        }

    def _error_result(self, rule_dict: dict, revision_log: list, error: str) -> dict:
        """Build an error result."""
        return {
            "success": False,
            "rule": rule_dict,
            "rule_json": json.dumps(rule_dict, indent=2, default=str),
            "display": "",
            "impact": {},
            "attempts": len(revision_log),
            "revision_log": revision_log,
            "has_collateral": False,
            "error": error,
        }

    def discover(
        self,
        case_id: str,
        sme_feedback: str,
        sample_size: int = DEFAULT_SAMPLE_SIZE,
    ) -> dict:
        """Generate a new safe ALF rule.

        1. Loads case data and generates a rule via LLM
        2. Runs safety loop: validate → assess impact → auto-tighten
        3. Returns vetted rule with impact report and revision log

        Args:
            case_id: The target case identifier.
            sme_feedback: SME's natural language description of what should change.
            sample_size: Number of cases to sample for impact assessment.

        Returns:
            dict with: success, rule, rule_json, display, impact,
                       attempts, revision_log, has_collateral, collateral_warning
        """
        case_data = self._loader.run(case_id)

        # Step 1: Generate initial rule
        proposed = self._discoverer.run(case_data, sme_feedback)
        if not proposed.success:
            return {
                "success": False,
                "error": f"Rule generation failed: {proposed.parse_errors}",
                "rule": proposed.rule_dict,
                "rule_json": json.dumps(proposed.rule_dict, indent=2, default=str),
                "display": "",
                "impact": {},
                "attempts": 0,
                "revision_log": [],
                "has_collateral": False,
            }

        # Step 2: Safety loop
        return self._run_safety_loop(case_id, proposed.rule_dict, sample_size)

    def revise(
        self,
        case_id: str,
        current_rule: dict,
        sme_feedback: str,
        sample_size: int = DEFAULT_SAMPLE_SIZE,
    ) -> dict:
        """Revise a rule based on SME feedback, then run safety loop.

        1. Revises the rule via LLM using SME feedback
        2. Runs the same safety loop: validate → assess impact → auto-tighten
        3. Returns vetted revised rule

        Args:
            case_id: The target case identifier.
            current_rule: The current proposed rule dict to revise.
            sme_feedback: SME's revision feedback.
            sample_size: Number of cases to sample for impact assessment.

        Returns:
            Same format as discover().
        """
        case_data = self._loader.run(case_id)

        # Step 1: Revise based on SME feedback
        proposed = self._discoverer.revise(case_data, current_rule, sme_feedback, "")
        if not proposed.success:
            return {
                "success": False,
                "error": f"Rule revision failed: {proposed.parse_errors}",
                "rule": proposed.rule_dict,
                "rule_json": json.dumps(proposed.rule_dict, indent=2, default=str),
                "display": "",
                "impact": {},
                "attempts": 0,
                "revision_log": [],
                "has_collateral": False,
            }

        # Step 2: Safety loop on the revised rule
        return self._run_safety_loop(case_id, proposed.rule_dict, sample_size)
