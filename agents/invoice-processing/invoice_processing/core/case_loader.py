"""Case Loader Sub-Agent

Loads acting agent output artifacts for a specific case, builds the
flattened context that matches ALF engine's format, and produces a
human-readable summary for the SME.

ADK-transferable: single run() entry point, structured I/O.
"""

import json
from dataclasses import dataclass, field
from pathlib import Path

from .config import AGENTIC_FLOW_OUT, ALF_OUT_DIR, ARTIFACT_MAP

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class CaseData:
    """Structured output from CaseLoaderAgent."""

    case_id: str
    artifacts: dict = field(default_factory=dict)  # key -> parsed JSON
    context: dict = field(default_factory=dict)  # flattened ALF-style context
    postprocessing: dict = field(default_factory=dict)  # Postprocessing_Data.json
    alf_audit: dict | None = None  # ALF audit log if exists
    alf_postprocessing: dict | None = None  # ALF revised output if exists
    summary: str = ""  # human-readable summary


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class CaseLoaderAgent:
    """Sub-agent: Loads all artifacts for a case and builds context.

    This replicates the context-building logic from
    ALF/alf_engine.py ActingAgentAdapter.build_case_context()
    to guarantee field-path compatibility with ConditionEvaluator.
    """

    def list_cases(self) -> list[str]:
        """Return sorted list of available case IDs."""
        if not AGENTIC_FLOW_OUT.exists():
            return []
        return sorted(
            d.name
            for d in AGENTIC_FLOW_OUT.iterdir()
            if d.is_dir() and not d.name.startswith(".")
        )

    def run(self, case_id: str) -> CaseData:
        """Load case data and build context.

        Args:
            case_id: The case folder name (numeric ID).

        Returns:
            CaseData with all artifacts, flattened context, and summary.

        Raises:
            FileNotFoundError: If case folder does not exist.
        """
        case_dir = AGENTIC_FLOW_OUT / case_id
        if not case_dir.exists():
            raise FileNotFoundError(
                f"Case folder not found: {case_dir}\n"
                f"Available cases: {', '.join(self.list_cases()[:5])}..."
            )

        data = CaseData(case_id=case_id)

        # --- Load all artifacts ---
        for key, filename in ARTIFACT_MAP.items():
            filepath = case_dir / filename
            if filepath.exists():
                try:
                    with open(filepath, encoding="utf-8") as f:
                        data.artifacts[key] = json.load(f)
                except json.JSONDecodeError:
                    data.artifacts[key] = {}

        data.postprocessing = data.artifacts.get("postprocessing", {})

        # --- Build flattened context (matches ALF engine exactly) ---
        data.context = self._build_context(data.artifacts, case_dir)

        # --- Load ALF output if exists ---
        alf_case_dir = ALF_OUT_DIR / case_id
        if alf_case_dir.exists():
            alf_audit_path = alf_case_dir / "alf_audit_log.json"
            alf_pp_path = alf_case_dir / "Postprocessing_Data.json"
            if alf_audit_path.exists():
                with open(alf_audit_path) as f:
                    data.alf_audit = json.load(f)
            if alf_pp_path.exists():
                with open(alf_pp_path) as f:
                    data.alf_postprocessing = json.load(f)

        # --- Build human summary ---
        data.summary = self._build_summary(data)

        return data

    def _flatten_phase_decisions(self, artifacts: dict, context: dict) -> None:
        """Flatten phase decisions and related fields into the context dict."""
        phase1 = artifacts.get("phase1", {})
        if phase1:
            context["decision_phase1"] = phase1.get("decision")
            context["work_type"] = phase1.get("work_type")
            if "has_waf" in phase1:
                context["has_waf"] = phase1["has_waf"]
            if "waf_exempt" in phase1:
                context["waf_exempt"] = phase1["waf_exempt"]
            if "waf_exempt_reason" in phase1:
                context["waf_exempt_reason"] = phase1["waf_exempt_reason"]

        phase2 = artifacts.get("phase2", {})
        if phase2:
            context["decision_phase2"] = phase2.get("decision")

        phase3 = artifacts.get("phase3", {})
        if phase3:
            context["decision_phase3"] = phase3.get("decision")

        phase4 = artifacts.get("phase4", {})
        if phase4:
            context["decision_phase4"] = phase4.get("decision")

        transformer = artifacts.get("transformer", {})
        if transformer:
            context["line_items_mapped"] = transformer.get("line_items_mapped", [])

    def _build_context(self, artifacts: dict, case_dir: Path) -> dict:
        """Build flattened context matching ALF ActingAgentAdapter.build_case_context().

        This is the critical function - field paths must match exactly
        so ConditionEvaluator produces identical results.
        """
        context = {}

        # Copy all raw artifacts into context under their key
        for key, artifact in artifacts.items():
            context[key] = artifact

        # --- Flatten extraction fields to top level ---
        ext = artifacts.get("extraction", {})
        if ext:
            context["invoice"] = ext.get("invoice", {})
            context["work_authorization"] = ext.get("work_authorization", {})
            context["has_waf"] = ext.get("waf_count", 0) > 0
            context["waf_count"] = ext.get("waf_count", 0)

        # --- Flatten phase decisions ---
        self._flatten_phase_decisions(artifacts, context)

        return context

    def _build_summary_decision(self, data: CaseData, lines: list) -> str:
        """Append decision and rejection info to summary lines.

        Returns:
            outcome_msg for later use.
        """
        pp = data.postprocessing
        inv_status = pp.get("Invoice Processing", {}).get("Invoice Status", "Unknown")
        outcome_msg = pp.get("Outcome Message", {}).get("Outcome Message", "")
        lines.append(f"Decision: {inv_status}")

        # Find the failing phase and rejection reason
        rejection_reason = ""
        failing_phase = ""
        failing_step = ""
        for phase_key in ["phase1", "phase2", "phase3", "phase4"]:
            phase = data.artifacts.get(phase_key, {})
            if phase.get("decision") in (
                "REJECT",
                "SET_ASIDE",
                "EMAIL_APPROVER",
            ):
                failing_phase = phase.get("phase_name", phase_key)
                rejection_reason = phase.get("rejection_template", "")
                # Find specific failing step
                for v in phase.get("validations", []):
                    if isinstance(v, dict) and not v.get("passed", True):
                        failing_step = f"Step {v.get('step', '?')}"
                        if not rejection_reason:
                            rejection_reason = v.get("rejection_template", "")
                        break
                break

        if rejection_reason:
            lines.append(f"Rejection reason: '{rejection_reason}'")
        if failing_phase:
            step_info = f", {failing_step}" if failing_step else ""
            lines.append(f"Failed at: {failing_phase}{step_info}")
        if outcome_msg:
            lines.append(f"Outcome: {outcome_msg.strip()}")

        return outcome_msg

    def _build_summary_key_details(self, ctx: dict, lines: list) -> None:
        """Append key invoice details to summary lines."""
        lines.append("Key details:")
        invoice = ctx.get("invoice", {})

        vendor = invoice.get("vendor_name", "?")
        lines.append(f"  Vendor: {vendor}")

        inv_total = invoice.get("invoice_total_inc_tax", "?")
        currency = invoice.get("currency", "")
        lines.append(f"  Invoice Total: ${inv_total} {currency}".rstrip())

        inv_date = invoice.get("invoice_date", "?")
        lines.append(f"  Invoice Date: {inv_date}")

        tax_id = invoice.get("vendor_tax_id", "?")
        lines.append(f"  Tax ID: {tax_id}")

        work_type = ctx.get("work_type")
        if work_type:
            lines.append(f"  Work type: {work_type}")

        has_waf = ctx.get("has_waf", False)
        waf_count = ctx.get("waf_count", 0)
        lines.append(
            f"  Has WAF: {'Yes' if has_waf else 'No'} (waf_count: {waf_count})"
        )

        waf_exempt = ctx.get("waf_exempt", False)
        if waf_exempt:
            reason = ctx.get("waf_exempt_reason", "")
            lines.append(f"  WAF exempt: Yes ({reason})")

        # Line items summary
        line_items = invoice.get("line_items", [])
        if line_items:
            descs = [li.get("description", "?")[:40] for li in line_items[:5]]
            lines.append(f"  Line items: {len(line_items)} ({', '.join(descs)})")

    def _build_summary_validation_phases(self, data: CaseData, lines: list) -> None:
        """Append phase-by-phase validation summary to lines."""
        lines.append("Validation phases:")
        for phase_key, label in [
            ("phase1", "Phase 1 (Intake)"),
            ("phase2", "Phase 2 (PO/Invoice)"),
            ("phase3", "Phase 3 (Status/Date)"),
            ("phase4", "Phase 4 (Totals/EWAF)"),
        ]:
            phase = data.artifacts.get(phase_key, {})
            if not phase:
                lines.append(f"  {label}: not reached")
                continue
            decision = phase.get("decision", "?")
            validations = phase.get("validations", [])
            passed = sum(
                1 for v in validations if isinstance(v, dict) and v.get("passed")
            )
            total = len(validations)
            lines.append(f"  {label}: {decision} ({passed}/{total} steps passed)")
            # Show failing steps
            for v in validations:
                if isinstance(v, dict) and not v.get("passed", True):
                    step = v.get("step", "?")
                    rule = v.get("rule", "")
                    tmpl = v.get("rejection_template", "")
                    lines.append(f"    FAILED Step {step}: {rule}")
                    if tmpl:
                        lines.append(f"      Template: '{tmpl}'")

    def _build_summary_alf_status(self, data: CaseData, lines: list) -> None:
        """Append ALF status section to summary lines."""
        if data.alf_audit:
            fired = data.alf_audit.get("any_rules_fired", False)
            matched = data.alf_audit.get("rules_matched", 0)
            if fired:
                rules_applied = data.alf_audit.get("rules_applied", [])
                rule_ids = [r.get("rule_id", "?") for r in rules_applied]
                lines.append(
                    f"ALF status: {matched} rule(s) fired ({', '.join(rule_ids)})"
                )
                # Show revised status
                if data.alf_postprocessing:
                    alf_status = data.alf_postprocessing.get(
                        "Invoice Processing", {}
                    ).get("Invoice Status", "?")
                    lines.append(f"  ALF revised status: {alf_status}")
            else:
                lines.append("ALF status: No rules fired for this case")
        else:
            lines.append("ALF status: Not evaluated")

    def _build_summary(self, data: CaseData) -> str:
        """Build a human-readable case summary for the SME."""
        ctx = data.context
        lines = []

        # Header
        lines.append(f"=== Case {data.case_id} ===")

        # Decision and rejection info
        self._build_summary_decision(data, lines)
        lines.append("")

        # Key details
        self._build_summary_key_details(ctx, lines)
        lines.append("")

        # Phase-by-phase validation summary
        self._build_summary_validation_phases(data, lines)
        lines.append("")

        # ALF status
        self._build_summary_alf_status(data, lines)

        return "\n".join(lines)
