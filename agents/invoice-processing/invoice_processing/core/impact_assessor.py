"""Impact Assessor Sub-Agent

Evaluates proposed rule conditions against a sample of existing case outputs
to identify unintended matches before a rule is committed.

Uses ALF engine's ConditionEvaluator for guaranteed consistency.

ADK-transferable: single run() entry point, structured I/O.
"""

import random
from dataclasses import dataclass, field

from ..shared_libraries.alf_engine import ConditionEvaluator
from .case_loader import CaseLoaderAgent

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CaseMatch:
    """One case's match result."""

    case_id: str
    matched: bool
    condition_details: list = field(default_factory=list)
    decision: str = ""  # current agent decision for this case
    rejection_reason: str = ""  # current rejection reason


@dataclass
class ImpactReport:
    """Structured output from ImpactAssessorAgent."""

    target_case_id: str
    target_matched: bool
    collateral_matches: list[CaseMatch] = field(default_factory=list)
    safe_cases: list[str] = field(default_factory=list)
    total_cases: int = 0
    sampled: bool = False
    sample_size: int = 0
    summary: str = ""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class ImpactAssessorAgent:
    """Sub-agent: Evaluates proposed conditions against all cases.

    Deterministic - no LLM calls. Uses ALF ConditionEvaluator directly.
    """

    def __init__(self):
        self._loader = CaseLoaderAgent()
        self._contexts_cache: dict[str, dict] = {}

    def _load_all_contexts(self) -> dict[str, dict]:
        """Load and cache flattened context for every case."""
        if self._contexts_cache:
            return self._contexts_cache

        case_ids = self._loader.list_cases()
        for cid in case_ids:
            try:
                case_data = self._loader.run(cid)
                self._contexts_cache[cid] = case_data.context
            except Exception:
                pass  # skip broken cases

        return self._contexts_cache

    def _get_case_summary(self, context: dict) -> tuple[str, str]:
        """Extract decision and rejection reason from context."""
        # Find the terminal decision
        for phase_key in ["phase1", "phase2", "phase3", "phase4"]:
            phase = context.get(phase_key, {})
            decision = phase.get("decision", "")
            if decision in ("REJECT", "SET_ASIDE", "EMAIL_APPROVER"):
                rejection = phase.get("rejection_template", "")
                return decision, rejection

        # If no phase rejected, check final decision
        final = context.get("decision", {})
        return final.get("final_decision", "ACCEPT"), ""

    def run(
        self,
        conditions: list[dict],
        target_case_id: str,
        sample_size: int = 10,
    ) -> ImpactReport:
        """Evaluate conditions against a sample of cases.

        Args:
            conditions: List of condition dicts (ALF rule conditions format).
            target_case_id: The case the SME is working on (should match).
            sample_size: Max number of cases to evaluate. The target case is
                always included. If total cases <= sample_size, all are evaluated.

        Returns:
            ImpactReport with target match status, collateral matches, and safe count.
        """
        all_contexts = self._load_all_contexts()

        # Determine which cases to evaluate
        all_case_ids = list(all_contexts.keys())
        if len(all_case_ids) > sample_size:
            # Always include target; randomly sample the rest
            other_ids = [cid for cid in all_case_ids if cid != target_case_id]
            sampled_others = random.sample(
                other_ids, min(sample_size - 1, len(other_ids))
            )
            eval_case_ids = [target_case_id, *sampled_others]
            sampled = True
        else:
            eval_case_ids = all_case_ids
            sampled = False

        report = ImpactReport(
            target_case_id=target_case_id,
            target_matched=False,
            total_cases=len(all_contexts),
            sampled=sampled,
            sample_size=len(eval_case_ids),
        )

        for case_id in eval_case_ids:
            context = all_contexts.get(case_id, {})
            if not context:
                continue
            all_passed, details = ConditionEvaluator.evaluate_all(context, conditions)

            decision, rejection = self._get_case_summary(context)

            match = CaseMatch(
                case_id=case_id,
                matched=all_passed,
                condition_details=details,
                decision=decision,
                rejection_reason=rejection,
            )

            if case_id == target_case_id:
                report.target_matched = all_passed
            elif all_passed:
                report.collateral_matches.append(match)
            else:
                report.safe_cases.append(case_id)

        # Build summary text
        report.summary = self._build_summary(report)
        return report

    def _build_summary(self, report: ImpactReport) -> str:
        """Build human-readable impact summary."""
        lines = []
        lines.append("=== Impact Assessment ===")
        if report.sampled:
            lines.append(
                f"Sampled {report.sample_size} of {report.total_cases} cases "
                f"(random selection; target case always included)."
            )
        else:
            lines.append(f"Scanning {report.total_cases} cases...")
        lines.append("")

        # Target case
        status = (
            "MATCH (target)"
            if report.target_matched
            else "NO MATCH (WARNING - target case does not match!)"
        )
        lines.append(f"  Case {report.target_case_id}: {status}")

        # Collateral matches
        if report.collateral_matches:
            lines.append("")
            lines.append(f"  Collateral matches ({len(report.collateral_matches)}):")
            for cm in report.collateral_matches:
                lines.append(f"    Case {cm.case_id}: MATCH (unintended)")
                lines.append(f"      Current decision: {cm.decision}")
                if cm.rejection_reason:
                    lines.append(f"      Rejection: '{cm.rejection_reason}'")
                # Show which conditions matched
                for det in cm.condition_details:
                    if det.get("passed"):
                        lines.append(
                            f"      {det['field']} {det['operator']} "
                            f"-> actual: {_truncate(det.get('actual'))}"
                        )
        else:
            lines.append(f"  {len(report.safe_cases)} other cases: NO MATCH (safe)")

        lines.append("")

        if report.target_matched and not report.collateral_matches:
            lines.append("This rule is safe to apply.")
        elif not report.target_matched:
            lines.append(
                "WARNING: The target case does NOT match these conditions. "
                "The conditions need to be revised."
            )
        else:
            lines.append(
                f"WARNING: {len(report.collateral_matches)} other case(s) "
                f"also match. Review needed - should the rule apply to them too?"
            )

        if report.sampled:
            lines.append("")
            lines.append(
                f"NOTE: Only {report.sample_size} of {report.total_cases} cases "
                f"were evaluated. Run with a larger sample_size to increase confidence."
            )

        return "\n".join(lines)


def _truncate(value, max_len: int = 60) -> str:
    """Truncate a value for display."""
    s = str(value)
    if len(s) > max_len:
        return s[:max_len] + "..."
    return s
