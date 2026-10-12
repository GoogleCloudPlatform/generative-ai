"""Rule Writer Sub-Agent

Reads, validates, and writes rules to rule_base.json.
Handles backup, ID assignment, schema validation, and conflict detection.

ADK-transferable: single run() entry point, structured I/O.
"""

import json
import shutil
from dataclasses import dataclass
from datetime import datetime

from ..shared_libraries.alf_engine import (
    SUPPORTED_ACTION_TYPES,
    SUPPORTED_CONDITION_OPERATORS,
)
from .config import RULE_BASE_PATH

# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class WriteResult:
    """Structured output from RuleWriterAgent."""

    success: bool
    rule_id: str
    mode: str  # "add" or "update"
    backup_path: str = ""
    total_rules: int = 0
    message: str = ""


# ---------------------------------------------------------------------------
# Agent
# ---------------------------------------------------------------------------


class RuleWriterAgent:
    """Sub-agent: Manages rule_base.json read/write operations."""

    def load_rule_base(self) -> dict:
        """Load and return the current rule_base.json."""
        if not RULE_BASE_PATH.exists():
            raise FileNotFoundError(f"Rule base not found: {RULE_BASE_PATH}")
        with open(RULE_BASE_PATH, encoding="utf-8") as f:
            return json.load(f)

    def get_existing_rules(self) -> list[dict]:
        """Return list of rule dicts from rule_base.json."""
        rb = self.load_rule_base()
        return rb.get("rules", [])

    def get_existing_scopes(self) -> dict[str, list[str]]:
        """Return mapping of scope -> [rule_id, ...]."""
        scopes = {}
        for rule in self.get_existing_rules():
            scope = rule.get("scope", "global")
            scopes.setdefault(scope, []).append(rule.get("id", "?"))
        return scopes

    def next_rule_id(self) -> str:
        """Generate the next ALF-NNN rule ID."""
        rules = self.get_existing_rules()
        max_num = 0
        for r in rules:
            rid = r.get("id", "")
            if rid.startswith("ALF-"):
                try:
                    num = int(rid.split("-")[1])
                    max_num = max(max_num, num)
                except (IndexError, ValueError):
                    pass
        return f"ALF-{max_num + 1:03d}"

    def validate_rule(self, rule_dict: dict) -> list[str]:
        """Validate a rule dict against the schema.

        Returns list of error messages (empty if valid).
        """
        errors = []

        # Required fields
        for field in ["id", "name", "conditions", "actions"]:
            if field not in rule_dict:
                errors.append(f"Missing required field: '{field}'")

        # Validate conditions
        for i, cond in enumerate(rule_dict.get("conditions", [])):
            if "field" not in cond:
                errors.append(f"Condition {i}: missing 'field'")
            if "operator" not in cond:
                errors.append(f"Condition {i}: missing 'operator'")
            elif cond["operator"] not in SUPPORTED_CONDITION_OPERATORS:
                errors.append(
                    f"Condition {i}: unsupported operator '{cond['operator']}'. "
                    f"Supported: {sorted(SUPPORTED_CONDITION_OPERATORS)}"
                )

        # Validate actions
        for i, act in enumerate(rule_dict.get("actions", [])):
            if "type" not in act:
                errors.append(f"Action {i}: missing 'type'")
            elif act["type"] not in SUPPORTED_ACTION_TYPES:
                errors.append(
                    f"Action {i}: unsupported type '{act['type']}'. "
                    f"Supported: {sorted(SUPPORTED_ACTION_TYPES)}"
                )

        return errors

    def check_conflicts(self, rule_dict: dict) -> list[str]:
        """Check if proposed rule conflicts with existing rules.

        Returns list of warning messages.
        """
        warnings = []
        existing = self.get_existing_rules()
        new_id = rule_dict.get("id")
        new_scope = rule_dict.get("scope", "global")
        new_priority = rule_dict.get("priority", 100)

        for r in existing:
            # Duplicate ID
            if r.get("id") == new_id:
                warnings.append(f"Rule ID '{new_id}' already exists")

            # Same scope + same priority
            if r.get("scope") == new_scope and r.get("priority") == new_priority:
                warnings.append(
                    f"Priority collision with {r['id']} in scope '{new_scope}' "
                    f"at priority {new_priority}"
                )

        # Show existing rules in same scope
        scope_rules = [r["id"] for r in existing if r.get("scope") == new_scope]
        if scope_rules:
            warnings.append(
                f"Scope '{new_scope}' already has rules: {scope_rules}. "
                f"Only ONE rule per scope can fire (mutual exclusion)."
            )

        return warnings

    def run(
        self,
        rule_dict: dict,
        mode: str = "add",
    ) -> WriteResult:
        """Write a rule to rule_base.json.

        Args:
            rule_dict: Complete rule dict matching ALF schema.
            mode: "add" (new rule) or "update" (replace existing by ID).

        Returns:
            WriteResult with success status and details.
        """
        # Validate
        errors = self.validate_rule(rule_dict)
        if errors:
            return WriteResult(
                success=False,
                rule_id=rule_dict.get("id", "?"),
                mode=mode,
                message="Validation errors:\n" + "\n".join(f"  - {e}" for e in errors),
            )

        # Load current rule base
        rb = self.load_rule_base()

        # Backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = RULE_BASE_PATH.with_suffix(f".json.bak.{timestamp}")
        shutil.copy2(RULE_BASE_PATH, backup_path)

        rule_id = rule_dict["id"]

        if mode == "add":
            # Check for duplicate ID
            existing_ids = {r["id"] for r in rb.get("rules", [])}
            if rule_id in existing_ids:
                return WriteResult(
                    success=False,
                    rule_id=rule_id,
                    mode=mode,
                    backup_path=str(backup_path),
                    message=f"Rule ID '{rule_id}' already exists. Use mode='update'.",
                )
            rb["rules"].append(rule_dict)

        elif mode == "update":
            # Replace existing rule by ID
            found = False
            for i, r in enumerate(rb["rules"]):
                if r["id"] == rule_id:
                    rb["rules"][i] = rule_dict
                    found = True
                    break
            if not found:
                return WriteResult(
                    success=False,
                    rule_id=rule_id,
                    mode=mode,
                    backup_path=str(backup_path),
                    message=f"Rule ID '{rule_id}' not found for update.",
                )

        # Update metadata
        rb.setdefault("metadata", {})
        rb["metadata"]["total_rules"] = len(rb["rules"])
        rb["metadata"]["last_modified"] = datetime.now().isoformat()
        rb["metadata"]["last_modified_by"] = "Learning Agent (SME-guided)"

        # Write
        with open(RULE_BASE_PATH, "w", encoding="utf-8") as f:
            json.dump(rb, f, indent=2, ensure_ascii=False)

        return WriteResult(
            success=True,
            rule_id=rule_id,
            mode=mode,
            backup_path=str(backup_path),
            total_rules=len(rb["rules"]),
            message=f"Rule {rule_id} {'added' if mode == 'add' else 'updated'} successfully. "
            f"Total rules: {len(rb['rules'])}. "
            f"Backup: {backup_path.name}",
        )

    def delete_rule(self, rule_id: str) -> WriteResult:
        """Delete a rule from rule_base.json by ID.

        Args:
            rule_id: The ALF rule ID to delete (e.g., "ALF-001").

        Returns:
            WriteResult with success status and details.
        """
        rb = self.load_rule_base()

        # Backup
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = RULE_BASE_PATH.with_suffix(f".json.bak.{timestamp}")
        shutil.copy2(RULE_BASE_PATH, backup_path)

        # Find and remove
        original_count = len(rb.get("rules", []))
        rb["rules"] = [r for r in rb.get("rules", []) if r.get("id") != rule_id]

        if len(rb["rules"]) == original_count:
            return WriteResult(
                success=False,
                rule_id=rule_id,
                mode="delete",
                backup_path=str(backup_path),
                message=f"Rule ID '{rule_id}' not found.",
            )

        # Update metadata
        rb.setdefault("metadata", {})
        rb["metadata"]["total_rules"] = len(rb["rules"])
        rb["metadata"]["last_modified"] = datetime.now().isoformat()
        rb["metadata"]["last_modified_by"] = "Learning Agent (SME-guided)"

        with open(RULE_BASE_PATH, "w", encoding="utf-8") as f:
            json.dump(rb, f, indent=2, ensure_ascii=False)

        return WriteResult(
            success=True,
            rule_id=rule_id,
            mode="delete",
            backup_path=str(backup_path),
            total_rules=len(rb["rules"]),
            message=f"Rule {rule_id} deleted successfully. "
            f"Total rules: {len(rb['rules'])}. "
            f"Backup: {backup_path.name}",
        )

    def _format_conditions(self, rule_dict: dict, lines: list) -> None:
        """Append formatted conditions to display lines."""
        lines.append("Conditions:")
        for i, c in enumerate(rule_dict.get("conditions", []), 1):
            desc = c.get("description", "")
            val_display = c.get("value", "")
            if isinstance(val_display, list):
                val_display = json.dumps(val_display)
            elif val_display is None:
                val_display = "(null)"
            lines.append(
                f"  {i}. {c.get('field', '?')} {c.get('operator', '?')} {val_display}"
            )
            if desc:
                lines.append(f"     ({desc})")

    def _format_actions(self, rule_dict: dict, lines: list) -> None:
        """Append formatted actions to display lines."""
        lines.append("Actions:")
        for i, a in enumerate(rule_dict.get("actions", []), 1):
            action_type = a.get("type", "?")
            if action_type == "llm_continue_processing":
                lines.append(f"  {i}. {action_type} from {a.get('resume_from', '?')}")
                ctx = a.get("correction_context", "")
                if ctx:
                    # Show first 200 chars
                    lines.append(f"     Context: {ctx[:200]}...")
            elif action_type == "llm_patch_fields":
                fields = a.get("target_fields", [])
                lines.append(f"  {i}. {action_type}: {', '.join(fields)}")
            else:
                lines.append(f"  {i}. {action_type}")

    def _format_metadata(self, rule_dict: dict, lines: list) -> None:
        """Append formatted metadata to display lines if present."""
        meta = rule_dict.get("metadata", {})
        if meta:
            lines.append("")
            lines.append("Metadata:")
            if meta.get("severity"):
                lines.append(f"  Severity: {meta['severity']}")
            if meta.get("root_cause"):
                lines.append(f"  Root cause: {meta['root_cause']}")
            if meta.get("rules_book_section"):
                lines.append(f"  Rules book: {meta['rules_book_section']}")

    def format_rule_display(self, rule_dict: dict) -> str:
        """Format a rule dict for terminal display."""
        lines = []
        lines.append(f"=== Proposed Rule: {rule_dict.get('id', '?')} ===")
        lines.append(f"Name: {rule_dict.get('name', '?')}")
        lines.append(f"Description: {rule_dict.get('description', '?')}")
        lines.append(f"Scope: {rule_dict.get('scope', '?')}")
        lines.append(f"Priority: {rule_dict.get('priority', '?')}")
        lines.append("")

        self._format_conditions(rule_dict, lines)
        lines.append("")
        self._format_actions(rule_dict, lines)
        self._format_metadata(rule_dict, lines)

        return "\n".join(lines)
