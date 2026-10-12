"""Rule Discoverer Sub-Agent

Uses Gemini Pro to analyze SME feedback against case data and propose
new ALF rules with conservative, narrow conditions.

ADK-transferable: single run() entry point, structured I/O.
"""

import json
import logging
import re
import time
from dataclasses import dataclass, field
from datetime import date

from .case_loader import CaseData
from .config import (
    RULES_BOOK_PATH,
    get_llm_call_delay,
    get_llm_location,
    get_llm_model,
    get_llm_project_id,
)
from .prompts import (
    RULE_DISCOVERY_SYSTEM_PROMPT,
    RULE_DISCOVERY_TASK_TEMPLATE,
    RULE_REVISION_TASK_TEMPLATE,
    extract_relevant_rules_book_sections,
)
from .rule_writer import RuleWriterAgent

logger = logging.getLogger("LearningAgent.RuleDiscoverer")


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class ProposedRule:
    """Structured output from RuleDiscovererAgent."""

    rule_dict: dict = field(default_factory=dict)
    raw_llm_response: str = ""
    llm_model: str = ""
    llm_latency_ms: float = 0.0
    parse_errors: list[str] = field(default_factory=list)
    success: bool = False


# ---------------------------------------------------------------------------
# LLM Client
# ---------------------------------------------------------------------------


class _LLMClient:
    """Lazy-initialized Agent Platform (Vertex AI) Gemini Pro client."""

    _model = None

    @classmethod
    def get_model(cls):
        if cls._model is None:
            from google.cloud import aiplatform
            from vertexai.generative_models import (
                GenerativeModel,
            )

            project_id = get_llm_project_id()
            if not project_id:
                raise ValueError("PROJECT_ID not set. Export it or add to .env file.")
            aiplatform.init(project=project_id, location=get_llm_location())
            cls._model = GenerativeModel(get_llm_model())
            logger.info(f"Initialized {get_llm_model()} (project={project_id})")
        return cls._model

    @classmethod
    def generate(cls, prompt: str) -> tuple[str, float]:
        """Call Gemini Pro and return (response_text, latency_ms)."""
        model = cls.get_model()
        start = time.time()
        response = model.generate_content(prompt)
        latency_ms = (time.time() - start) * 1000
        call_delay = get_llm_call_delay()
        if call_delay > 0:
            time.sleep(call_delay)
        return response.text.strip(), latency_ms


# ---------------------------------------------------------------------------
# JSON parser (replicates ALF engine's _parse_response)
# ---------------------------------------------------------------------------


def _strip_markdown_fences(text: str) -> str:
    """Remove markdown code fences from text, returning the inner content."""
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


def _extract_json_object(text: str) -> str:
    """Extract the outermost JSON object from text by matching braces."""
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


def _parse_json_response(text: str) -> dict:
    """Parse JSON from LLM response, handling markdown blocks and trailing text."""
    clean = _strip_markdown_fences(text.strip())
    json_str = _extract_json_object(clean)
    # Fix trailing commas
    json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)
    return json.loads(json_str)


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class RuleDiscovererAgent:
    """Sub-agent: Proposes new ALF rules via Gemini Pro.

    Takes case data + SME feedback -> returns a complete rule dict
    with narrow, conservative conditions.
    """

    def __init__(self):
        self._writer = RuleWriterAgent()
        self._rules_book_cache: str | None = None

    def _load_rules_book(self) -> str:
        """Load the reconstructed rules book (cached)."""
        if self._rules_book_cache is None:
            if RULES_BOOK_PATH.exists():
                with open(RULES_BOOK_PATH, encoding="utf-8") as f:
                    self._rules_book_cache = f.read()
            else:
                self._rules_book_cache = "(Rules book not found)"
        return self._rules_book_cache

    def _get_failing_info(self, case_data: CaseData) -> tuple[str, str, str]:
        """Extract failing phase, step, and rejection reason from case data."""
        for phase_key in ["phase1", "phase2", "phase3", "phase4"]:
            phase = case_data.artifacts.get(phase_key, {})
            decision = phase.get("decision", "")
            if decision in ("REJECT", "SET_ASIDE", "EMAIL_APPROVER"):
                rejection = phase.get("rejection_template", "")
                failing_step = ""
                for v in phase.get("validations", []):
                    if isinstance(v, dict) and not v.get("passed", True):
                        failing_step = f"Step {v.get('step', '?')}"
                        if not rejection:
                            rejection = v.get("rejection_template", "")
                        break
                return phase_key, failing_step, rejection

        return "unknown", "", ""

    def _build_validation_details(self, case_data: CaseData) -> str:
        """Build detailed validation step results for the LLM prompt."""
        lines = []
        for phase_key in ["phase1", "phase2", "phase3", "phase4"]:
            phase = case_data.artifacts.get(phase_key, {})
            if not phase:
                continue
            lines.append(
                f"--- {phase_key} (decision: {phase.get('decision', '?')}) ---"
            )
            for v in phase.get("validations", []):
                if isinstance(v, dict):
                    status = "PASS" if v.get("passed") else "FAIL"
                    step = v.get("step", "?")
                    rule = v.get("rule", "")
                    tmpl = v.get("rejection_template", "")
                    evidence = v.get("evidence", "")
                    lines.append(f"  Step {step} [{status}]: {rule}")
                    if evidence:
                        lines.append(f"    Evidence: {evidence[:200]}")
                    if tmpl:
                        lines.append(f"    Template: {tmpl}")
        return "\n".join(lines) if lines else "(no validation details available)"

    def run(
        self,
        case_data: CaseData,
        sme_feedback: str,
    ) -> ProposedRule:
        """Propose a new ALF rule based on case data and SME feedback.

        Args:
            case_data: Loaded case data from CaseLoaderAgent.
            sme_feedback: SME's natural language description of desired change.

        Returns:
            ProposedRule with the proposed rule dict.
        """
        result = ProposedRule(llm_model=get_llm_model())

        # Gather context
        failing_phase, failing_step, rejection_reason = self._get_failing_info(
            case_data
        )
        agent_decision = case_data.postprocessing.get("Invoice Processing", {}).get(
            "Invoice Status", "Unknown"
        )

        # Get existing rules and scopes
        existing_rules = self._writer.get_existing_rules()
        existing_scopes = self._writer.get_existing_scopes()
        next_id = self._writer.next_rule_id()

        # Get relevant rules book sections
        rules_book = self._load_rules_book()
        rules_book_context = extract_relevant_rules_book_sections(
            rules_book, failing_phase, failing_step
        )

        # Build invoice and extraction JSON (truncated for prompt)
        invoice = case_data.context.get("invoice", {})
        extraction = case_data.artifacts.get("extraction", {})

        # Build the task prompt
        task_prompt = RULE_DISCOVERY_TASK_TEMPLATE.format(
            sme_feedback=sme_feedback,
            case_id=case_data.case_id,
            agent_decision=agent_decision,
            rejection_reason=rejection_reason or "(none)",
            failing_phase=f"{failing_phase}, {failing_step}"
            if failing_step
            else failing_phase,
            case_summary=case_data.summary,
            validation_details=self._build_validation_details(case_data),
            invoice_json=json.dumps(invoice, indent=2, default=str)[:3000],
            extraction_json=json.dumps(extraction, indent=2, default=str)[:3000],
            existing_rules_json=json.dumps(
                [
                    {
                        "id": r["id"],
                        "name": r["name"],
                        "scope": r["scope"],
                        "conditions": r["conditions"],
                    }
                    for r in existing_rules
                ],
                indent=2,
            )[:4000],
            existing_scopes=json.dumps(existing_scopes, indent=2),
            rules_book_context=rules_book_context,
            next_rule_id=next_id,
        )

        full_prompt = RULE_DISCOVERY_SYSTEM_PROMPT + "\n\n===TASK===\n" + task_prompt

        # Call LLM
        try:
            response_text, latency_ms = _LLMClient.generate(full_prompt)
            result.raw_llm_response = response_text
            result.llm_latency_ms = latency_ms

            # Parse JSON
            rule_dict = _parse_json_response(response_text)

            # Ensure ID matches
            rule_dict["id"] = next_id

            # Ensure metadata has standard fields
            meta = rule_dict.setdefault("metadata", {})
            meta.setdefault("added_by", "Learning Agent (SME-guided)")
            meta.setdefault("added_date", date.today().isoformat())
            meta.setdefault("cases_affected", [case_data.case_id])
            meta.setdefault("issue_reference", "Learning Agent - SME guided")

            # Ensure enabled
            rule_dict.setdefault("enabled", True)

            # Validate
            errors = self._writer.validate_rule(rule_dict)
            if errors:
                result.parse_errors = errors
                result.rule_dict = rule_dict
                result.success = False
            else:
                result.rule_dict = rule_dict
                result.success = True

        except Exception as e:
            result.parse_errors = [str(e)]
            result.success = False
            logger.error(f"Rule discovery failed: {e}")

        return result

    def revise(
        self,
        case_data: CaseData,
        current_rule: dict,
        revision_feedback: str,
        impact_summary: str = "",
    ) -> ProposedRule:
        """Revise an existing proposed rule based on SME feedback.

        Args:
            case_data: The target case data.
            current_rule: The current proposed rule dict.
            revision_feedback: SME's revision request.
            impact_summary: Impact assessment summary to inform revision.

        Returns:
            ProposedRule with revised rule dict.
        """
        result = ProposedRule(llm_model=get_llm_model())

        invoice = case_data.context.get("invoice", {})
        extraction = case_data.artifacts.get("extraction", {})

        task_prompt = RULE_REVISION_TASK_TEMPLATE.format(
            revision_feedback=revision_feedback,
            current_rule_json=json.dumps(current_rule, indent=2),
            impact_summary=impact_summary,
            case_id=case_data.case_id,
            case_summary=case_data.summary,
            invoice_json=json.dumps(invoice, indent=2, default=str)[:3000],
            extraction_json=json.dumps(extraction, indent=2, default=str)[:3000],
            rule_id=current_rule.get("id", "?"),
        )

        full_prompt = (
            RULE_DISCOVERY_SYSTEM_PROMPT + "\n\n===REVISION TASK===\n" + task_prompt
        )

        try:
            response_text, latency_ms = _LLMClient.generate(full_prompt)
            result.raw_llm_response = response_text
            result.llm_latency_ms = latency_ms

            rule_dict = _parse_json_response(response_text)

            # Preserve original ID
            rule_dict["id"] = current_rule["id"]

            # Update metadata
            meta = rule_dict.setdefault("metadata", {})
            meta["added_by"] = "Learning Agent (SME-guided)"
            meta["added_date"] = date.today().isoformat()
            meta.setdefault("cases_affected", [case_data.case_id])

            rule_dict.setdefault("enabled", True)

            errors = self._writer.validate_rule(rule_dict)
            if errors:
                result.parse_errors = errors
                result.rule_dict = rule_dict
                result.success = False
            else:
                result.rule_dict = rule_dict
                result.success = True

        except Exception as e:
            result.parse_errors = [str(e)]
            result.success = False
            logger.error(f"Rule revision failed: {e}")

        return result
