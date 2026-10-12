"""Session Logger

Persists the full conversational trace of each learning agent session:
  - SME inputs (case selection, feedback, revisions, approvals)
  - LLM outputs (proposed rules, raw responses, latency)
  - Impact assessments (target match, collateral matches, safe count)
  - Final outcome (rule written, discarded, or session ended)

Each session is saved as a timestamped JSON file under sessions/.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .config import SESSIONS_DIR


@dataclass
class SessionEvent:
    """One event in the session timeline."""

    timestamp: str
    event_type: str  # case_loaded, sme_feedback, rule_proposed, impact_assessed,
    # sme_revision, rule_revised, rule_approved, rule_written,
    # rule_discarded, session_end
    data: dict = field(default_factory=dict)


@dataclass
class Session:
    """Full session record."""

    session_id: str = ""
    started_at: str = ""
    ended_at: str = ""
    case_id: str = ""
    outcome: str = ""  # "rule_written", "discarded", "quit"
    rule_id_written: str = ""
    events: list[SessionEvent] = field(default_factory=list)


class SessionLogger:
    """Accumulates events during a conversation and saves to disk.

    Usage:
        logger = SessionLogger()
        logger.start()
        logger.log_case_loaded(case_id, summary)
        logger.log_sme_feedback(text)
        logger.log_rule_proposed(rule_dict, raw_response, latency)
        logger.log_impact(report_summary, target_matched, collateral_count)
        logger.log_rule_written(rule_id, backup_path)
        logger.save()
    """

    def __init__(self):
        self._session: Session | None = None

    def start(self):
        """Begin a new session."""
        now = datetime.now()
        self._session = Session(
            session_id=now.strftime("%Y%m%d_%H%M%S"),
            started_at=now.isoformat(),
        )

    def _add_event(self, event_type: str, data: dict):
        if self._session is None:
            self.start()
        self._session.events.append(
            SessionEvent(
                timestamp=datetime.now().isoformat(),
                event_type=event_type,
                data=data,
            )
        )

    # ----- Event loggers -----

    def log_case_loaded(self, case_id: str, summary: str):
        if self._session is None:
            self.start()
        self._session.case_id = case_id
        self._add_event(
            "case_loaded",
            {
                "case_id": case_id,
                "summary": summary,
            },
        )

    def log_sme_feedback(self, feedback: str):
        self._add_event("sme_feedback", {"feedback": feedback})

    def log_rule_proposed(
        self,
        rule_dict: dict,
        raw_llm_response: str = "",
        latency_ms: float = 0.0,
        parse_errors: list[str] | None = None,
        success: bool = True,
    ):
        self._add_event(
            "rule_proposed",
            {
                "rule_dict": rule_dict,
                "raw_llm_response": raw_llm_response[:5000],  # cap size
                "latency_ms": round(latency_ms, 1),
                "parse_errors": parse_errors or [],
                "success": success,
            },
        )

    def log_impact_assessed(
        self,
        summary: str,
        target_matched: bool,
        collateral_count: int,
        safe_count: int,
        collateral_case_ids: list[str] | None = None,
    ):
        self._add_event(
            "impact_assessed",
            {
                "summary": summary,
                "target_matched": target_matched,
                "collateral_count": collateral_count,
                "collateral_case_ids": collateral_case_ids or [],
                "safe_count": safe_count,
            },
        )

    def log_sme_revision(self, revision_text: str):
        self._add_event("sme_revision", {"revision_text": revision_text})

    def log_rule_revised(
        self,
        rule_dict: dict,
        raw_llm_response: str = "",
        latency_ms: float = 0.0,
        success: bool = True,
    ):
        self._add_event(
            "rule_revised",
            {
                "rule_dict": rule_dict,
                "raw_llm_response": raw_llm_response[:5000],
                "latency_ms": round(latency_ms, 1),
                "success": success,
            },
        )

    def log_rule_approved(self):
        self._add_event("rule_approved", {})

    def log_rule_written(self, rule_id: str, backup_path: str, total_rules: int):
        if self._session is None:
            self.start()
        self._session.outcome = "rule_written"
        self._session.rule_id_written = rule_id
        self._add_event(
            "rule_written",
            {
                "rule_id": rule_id,
                "backup_path": backup_path,
                "total_rules": total_rules,
            },
        )

    def log_rule_discarded(self):
        self._add_event("rule_discarded", {})

    def log_conflict_warnings(self, warnings: list[str], sme_proceeded: bool):
        self._add_event(
            "conflict_warnings",
            {
                "warnings": warnings,
                "sme_proceeded": sme_proceeded,
            },
        )

    def log_session_end(self, reason: str = "quit"):
        if self._session:
            self._session.outcome = self._session.outcome or reason
            self._session.ended_at = datetime.now().isoformat()
            self._add_event("session_end", {"reason": reason})

    # ----- Persistence -----

    def save(self) -> Path | None:
        """Save the current session to disk.

        Returns the file path, or None if nothing to save.
        """
        if not self._session or not self._session.events:
            return None

        self._session.ended_at = self._session.ended_at or datetime.now().isoformat()

        SESSIONS_DIR.mkdir(parents=True, exist_ok=True)

        case_suffix = f"_{self._session.case_id}" if self._session.case_id else ""
        filename = f"{self._session.session_id}{case_suffix}.json"
        filepath = SESSIONS_DIR / filename

        # Serialize
        session_dict = {
            "session_id": self._session.session_id,
            "started_at": self._session.started_at,
            "ended_at": self._session.ended_at,
            "case_id": self._session.case_id,
            "outcome": self._session.outcome,
            "rule_id_written": self._session.rule_id_written,
            "events": [
                {
                    "timestamp": e.timestamp,
                    "event_type": e.event_type,
                    "data": e.data,
                }
                for e in self._session.events
            ],
        }

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session_dict, f, indent=2, ensure_ascii=False, default=str)

        return filepath

    def reset(self):
        """Reset for a new case within the same session run."""
        # Save current if it has events, then start fresh
        if self._session and self._session.events:
            self.save()
        self.start()
