#!/usr/bin/env python3
"""Agent Processing Investigation Script (Reconstructed Rules Book)

Version: 2.1.0
Last Updated: 2026-02-16

This script validates agent behavior against reconstructed_rules_book.md (v1.1.1)
which contains the validation rules including:
- Phase 1: Initial Intake (extraction, customer, tax compliance, WAF, single invoice)
- Phase 2: Content Validation (line items, PO)
- Phase 3: External Validation (tax ID checksum, future date)
- Phase 4: Calculation Validation (totals, line sums, WAF hours)

Core Philosophy:
- Independent agent validation - No comparison to human annotations
- Reconstructed rules as ground truth - Validate against reconstructed_rules_book.md
- Evidence-based analysis - Uses extraction data + agent intermediate outputs only
- LLM-based validation - Dynamic rule interpretation from rules book

Usage:
    # Investigate all cases
    python investigate_agent_reconst.py

    # Investigate rejected cases only
    python investigate_agent_reconst.py --status-filter REJECTED

    # Investigate single case
    python investigate_agent_reconst.py --case 1322369453811212272

    # Focus on specific phase
    python investigate_agent_reconst.py --phase-filter "Phase 2"
"""

import argparse
import hashlib
import json
import os
import re
import sys
import time
import traceback
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, ClassVar

# Third-party imports
try:
    from dotenv import load_dotenv
    from google.cloud import aiplatform
    from pydantic import BaseModel, Field
    from vertexai.preview.generative_models import (
        GenerationConfig,
        GenerativeModel,
    )
except ImportError:
    print("Error: Missing required package. Install with:")
    print("pip install google-cloud-aiplatform pydantic python-dotenv")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).parent  # shared_libraries/investigation/ folder
# Resolve paths: investigation/ -> shared_libraries/ -> invoice_processing/ (package root with data/ inside)
AGENT_PKG_DIR = Path(__file__).resolve().parent.parent.parent

# Project root for .env resolution
PROJECT_ROOT = AGENT_PKG_DIR.parent.parent.parent

# Master data loader — provides domain-agnostic configuration
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))  # shared_libraries/
try:
    from master_data_loader import MasterData, load_master_data

    _MASTER_DATA_AVAILABLE = True
except ImportError:
    _MASTER_DATA_AVAILABLE = False
    MasterData = None  # type hint fallback

# Module-level master data container (set in main() via dict to avoid `global`)
_master_data_container: dict[str, Any] = {"instance": None}


def _get_master_data() -> "MasterData | None":
    """Return the module-level master data instance (may be None)."""
    return _master_data_container["instance"]


_env_file = PROJECT_ROOT / ".env"
if _env_file.exists():
    load_dotenv(_env_file)
else:
    load_dotenv()

# ============================================================================
# CONFIGURATION
# ============================================================================
INPUT_BASE_DIR = AGENT_PKG_DIR / "exemplary_data"  # Ground truth / input cases
AGENT_OUTPUT_DIR = AGENT_PKG_DIR / "data" / "agent_output"  # Agent output directory

# Use reconstructed_rules_book.md from shared data directory
RULES_BOOK_PATH = AGENT_PKG_DIR / "data" / "reconstructed_rules_book.md"

# ============================================================================
# NAMED CONSTANTS (extracted from magic values for PLR2004)
# ============================================================================
_MIN_SECTION_LINES = 5
_HIGH_CONFIDENCE_THRESHOLD = 0.95
_OVERLAP_THRESHOLD = 0.75
_WAF_HOURS_STEP = 33
_BALANCE_TOLERANCE = 0.02
_FULL_COMPLIANCE_SCORE = 100
_PARTIAL_COMPLIANCE_THRESHOLD = 60
_MAX_PARTIAL_VIOLATIONS = 2
_COMPLETE_EXTRACTION_THRESHOLD = 90
_PARTIAL_EXTRACTION_THRESHOLD = 70
_MAX_LINE_WIDTH = 75

# Output directory for investigation results (used by batch runner only)
INVESTIGATION_OUTPUT_DIR = AGENT_PKG_DIR / "data" / "investigation_output"

# Google Cloud Configuration (lazy -- resolved at call time for deployment compatibility)
# Stored in a mutable dict so helpers can update without `global` statements.
_gcp_config: dict[str, Any] = {
    "PROJECT_ID": None,
    "LOCATION": os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    "GEMINI_PRO_MODEL": os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-pro"),
    "initialized": False,
}

# Module-level aliases kept for backward compatibility (read-only convenience).
PROJECT_ID = _gcp_config["PROJECT_ID"]
LOCATION = _gcp_config["LOCATION"]
GEMINI_PRO_MODEL = _gcp_config["GEMINI_PRO_MODEL"]


def _ensure_gcp_initialized():
    """Lazy-initialize GCP/Vertex AI on first use (not at import time).

    Agent Engine sets env vars after module import, so we must defer.
    """
    if _gcp_config["initialized"]:
        return
    _gcp_config["PROJECT_ID"] = os.getenv("GOOGLE_CLOUD_PROJECT")
    _gcp_config["LOCATION"] = os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")
    _gcp_config["GEMINI_PRO_MODEL"] = os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-pro")
    if not _gcp_config["PROJECT_ID"]:
        raise RuntimeError(
            "PROJECT_ID not found in environment. "
            "Set it in .env file or export PROJECT_ID=your-gcp-project-id"
        )
    aiplatform.init(project=_gcp_config["PROJECT_ID"], location=_gcp_config["LOCATION"])
    _gcp_config["initialized"] = True


# ============================================================================
# INVESTIGATION CONFIGURATION (v1.4.0)
# ============================================================================


@dataclass
class InvestigationConfig:
    """Configuration for investigation agent behavior.

    v1.5.0: Updated thresholds to be MORE CONSERVATIVE (reduce false positives).

    Philosophy: The investigation agent should be VERY CAUTIOUS about flagging
    violations. It's MUCH better to miss a real violation than to create a false
    positive that wastes human review time and undermines trust in the critic.
    """

    # Confidence thresholds - v1.5.0: INCREASED for more conservative behavior
    min_violation_confidence: float = (
        0.90  # Only flag violations with ≥90% confidence (was 80%)
    )
    min_ambiguous_confidence: float = (
        0.70  # Below this, mark as INSUFFICIENT_DATA (was 50%)
    )

    # Retry configuration for LLM calls
    llm_max_retries: int = 3
    llm_retry_base_delay: float = 1.0  # Seconds, doubles each retry (1s, 2s, 4s)

    # Tolerance configuration - v1.5.0: INCREASED margin for borderline cases
    investigator_margin: float = 0.25  # 25% extra margin for borderline cases (was 15%)

    # Cautious mode flags - v1.5.0: More conservative defaults
    require_multiple_evidence: bool = (
        True  # Require 2+ evidence points for violation (was False)
    )
    exclude_infrastructure_failures: bool = True  # Don't count 503s as violations
    treat_ambiguous_as_compliant: bool = (
        True  # Benefit of the doubt for ambiguous cases
    )

    # Status handling
    infrastructure_error_patterns: tuple = field(
        default_factory=lambda: (
            "503",
            "UNAVAILABLE",
            "timeout",
            "connection",
            "failed to connect",
            "DeadlineExceeded",
            "ServiceUnavailable",
            "DEADLINE_EXCEEDED",
        )
    )

    def is_infrastructure_error(self, error_message: str) -> bool:
        """Check if an error message indicates an infrastructure failure."""
        if not error_message:
            return False
        error_lower = error_message.lower()
        return any(
            pattern.lower() in error_lower
            for pattern in self.infrastructure_error_patterns
        )

    @classmethod
    def from_discovered_rules(
        cls, rule_discovery: "RuleDiscoveryEngine"
    ) -> "InvestigationConfig":
        """Create config from discovered rules (v2.0.0).

        Loads confidence thresholds and investigator margin from the
        tolerance_thresholds rule group if available.
        """
        config = cls()
        if not rule_discovery:
            return config

        group = rule_discovery.get_rule_group("tolerance_thresholds")
        if not group:
            return config

        rules_data = group.get("rules", [])
        if isinstance(rules_data, list):
            config._apply_thresholds_from_list(rules_data)
        elif isinstance(rules_data, dict):
            config._apply_thresholds_from_dict(rules_data)

        return config

    def _apply_thresholds_from_list(self, rules_data: list) -> None:
        """Apply confidence thresholds from a list of rule dicts."""
        for rule in rules_data:
            if not isinstance(rule, dict):
                continue
            if (
                rule.get("rule_id") == "investigator_confidence_thresholds"
                or "confidence" in str(rule.get("description", "")).lower()
            ):
                self._apply_thresholds_from_dict(rule)
                break

    def _apply_thresholds_from_dict(self, data: dict) -> None:
        """Apply confidence thresholds from a single dict."""
        if "min_violation_confidence" in data:
            self.min_violation_confidence = float(data["min_violation_confidence"])
        if "min_ambiguous_confidence" in data:
            self.min_ambiguous_confidence = float(data["min_ambiguous_confidence"])
        if "investigator_margin" in data:
            self.investigator_margin = float(data["investigator_margin"])


# Global config instance (can be overridden)
INVESTIGATION_CONFIG = InvestigationConfig()


# Load reconstructed rules book
RULES_BOOK_CONTENT = ""
if RULES_BOOK_PATH.exists():
    RULES_BOOK_CONTENT = RULES_BOOK_PATH.read_text(encoding="utf-8")
    print(f"Loaded rules book: {RULES_BOOK_PATH.name}")
else:
    print(f"Warning: reconstructed_rules_book.md not found at {RULES_BOOK_PATH}")

# ============================================================================
# PYDANTIC MODELS
# ============================================================================


class CaseProcessingSummary(BaseModel):
    """Summary of agent processing for a single case"""

    case_id: str

    # Final outcome
    final_status: str = Field(description="ACCEPTED, REJECTED, SET_ASIDE")
    final_decision_class: str = Field(description="ACCEPT, REJECT, UNCERTAIN")

    # Processing trace
    invoice_type: str = Field(description="From classification step")
    vendor_name: str | None = None
    invoice_total: float | None = None
    invoice_date: str | None = None

    # Phase results
    phase1_result: str = Field(description="Continue, Reject, Set Aside")
    phase1_reason: str | None = None

    phase2_result: str
    phase2_reason: str | None = None

    phase2_5_result: str = Field(
        default="Continue", description="External validation result"
    )
    phase2_5_reason: str | None = None

    phase3_result: str
    phase3_reason: str | None = None

    phase4_result: str
    phase4_reason: str | None = None

    # Exception handling
    exceptions_applied: list[str] = Field(default_factory=list)

    # First rejection point (if any)
    first_rejection_phase: str | None = None
    first_rejection_reason: str | None = None

    # Preprocessing data quality
    preprocessing_issues: list[str] = Field(
        default_factory=list,
        description="Missing or problematic preprocessing fields",
    )


class DataSourceValidation(BaseModel):
    """Validation of data source usage per Section 0"""

    field_name: str
    expected_source: str = Field(description="extraction or preprocessing")
    actual_source: str | None = None
    is_forbidden_field: bool = False
    is_valid: bool = True
    severity: str | None = None
    issue: str | None = None


class PhaseValidation(BaseModel):
    """Rule compliance validation for a single phase"""

    phase_name: str = Field(description="Phase 1, Phase 2, Phase 3, Phase 4")
    case_id: str

    # Agent's action
    agent_action: str = Field(description="Continue, Reject, Set Aside")
    agent_reason: str = Field(default="Not provided")

    # Rule-based validation
    expected_action_per_rules: str = Field(
        description="What reconstructed_rules_book.md says should happen"
    )

    rule_compliance: str = Field(
        description="COMPLIANT, VIOLATION, AMBIGUOUS, INSUFFICIENT_DATA, INCONCLUSIVE"
    )
    # v1.4.0: Added INCONCLUSIVE for infrastructure failures (503, timeouts)
    # INCONCLUSIVE cases are excluded from compliance score calculations

    # Evidence
    preprocessing_evidence: dict[str, Any] = Field(
        default_factory=dict,
        description="Relevant fields from preprocessing data",
    )

    agent_intermediate_output: dict[str, Any] = Field(
        default_factory=dict, description="What agent extracted/calculated"
    )

    # Compliance details
    applicable_rules: list[str] = Field(
        default_factory=list,
        description="e.g., ['Section 0.2', 'Step 15', 'Rule 33.1']",
    )

    compliance_explanation: str = Field(
        description="Why agent is compliant/violated rules"
    )

    violated_rules: list[str] = Field(default_factory=list)
    followed_rules: list[str] = Field(default_factory=list)

    # Data source validation (new for reconstructed rules)
    data_source_validations: list[DataSourceValidation] = Field(
        default_factory=list, description="Section 0 data source compliance"
    )

    # Correction needed (if violation)
    correction_needed: str | None = Field(default=None)
    correction_priority: str | None = Field(default="MEDIUM")


class RejectionPattern(BaseModel):
    """Analysis of a specific rejection pattern"""

    rejection_reason: str = Field(
        description="e.g., 'PO number mismatch', 'Missing vendor WAF'"
    )

    affected_phase: str = Field(description="Which phase triggers this rejection")

    case_count: int = Field(description="Number of cases with this rejection")

    percentage: float = Field(description="% of total rejections")

    example_case_ids: list[str] = Field(description="Sample cases showing this pattern")

    rule_reference: list[str] = Field(description="Rules that govern this rejection")

    # Rule compliance
    legitimate_rejections: int = Field(
        description="Cases where rejection was correct per rules"
    )

    incorrect_rejections: int = Field(
        description="Cases where agent should NOT have rejected per rules"
    )

    # Root cause
    root_cause_category: str = Field(
        description="DATA_QUALITY, RULE_VIOLATION, CORRECT_REJECTION, RULE_AMBIGUITY, DATA_SOURCE_ERROR"
    )

    recommendation: str


class AgentCaseInvestigation(BaseModel):
    """Complete investigation of agent processing for one case"""

    case_id: str

    # Processing summary
    processing_summary: CaseProcessingSummary

    # Phase-by-phase validation
    phase_validations: list[PhaseValidation]

    # Overall assessment
    overall_rule_compliance: str = Field(
        description="FULLY_COMPLIANT, PARTIAL_VIOLATION, MAJOR_VIOLATION, INCONCLUSIVE"
    )
    # v1.4.0: Added INCONCLUSIVE for cases where infrastructure failures prevented validation

    compliance_score: float = Field(
        ge=0.0, le=100.0, description="% of phases where agent followed rules"
    )

    # Rejection analysis (if rejected)
    is_rejected: bool
    rejection_justified: bool | None = Field(
        default=None,
        description="Was rejection correct per reconstructed_rules_book.md?",
    )
    rejection_justification: str | None = None

    # Data quality
    preprocessing_data_quality: str = Field(description="COMPLETE, PARTIAL, POOR")
    preprocessing_completeness: float = Field(ge=0.0, le=100.0)

    # Data source compliance (new for reconstructed rules)
    data_source_compliance: str = Field(
        default="NOT_CHECKED", description="COMPLIANT, VIOLATION, PARTIAL"
    )
    data_source_violations: list[str] = Field(default_factory=list)

    # Recommendations
    agent_improvements: list[str] = Field(default_factory=list)
    rule_clarifications_needed: list[str] = Field(default_factory=list)
    data_quality_improvements: list[str] = Field(default_factory=list)

    # Layer 3: Per-group validation results (v2.0.0)
    group_validation_results: dict[str, Any] | None = Field(
        default=None, description="Per-group validation results from Layer 3"
    )
    layer3_violations: int = Field(
        default=0,
        description="Number of violations found by Layer 3 per-group validation",
    )

    # Executive summary
    summary: str


class AgentInvestigationSummary(BaseModel):
    """Aggregate analysis across all cases"""

    timestamp: str
    rules_book_version: str = Field(default="reconstructed_rules_book.md v1.1.1")
    total_cases_investigated: int

    # Outcome breakdown
    accepted_cases: int
    rejected_cases: int
    set_aside_cases: int

    acceptance_rate: float
    rejection_rate: float

    # Rejection analysis
    rejection_patterns: list[RejectionPattern] = Field(
        description="Sorted by frequency"
    )

    most_common_rejection_phase: str
    most_common_rejection_reason: str

    # Rule compliance
    fully_compliant_cases: int
    partial_violation_cases: int
    major_violation_cases: int

    overall_compliance_rate: float = Field(
        description="% of cases where agent followed all rules correctly"
    )

    # Phase-specific metrics
    phase1_rejection_rate: float
    phase2_rejection_rate: float
    phase3_rejection_rate: float
    phase4_rejection_rate: float

    # Justified vs unjustified rejections
    justified_rejections: int = Field(description="Agent correctly rejected per rules")
    unjustified_rejections: int = Field(
        description="Agent rejected but should have accepted per rules"
    )

    # Top violations
    top_rule_violations: list[str] = Field(description="Most frequently violated rules")

    # Data source compliance (new for reconstructed rules)
    data_source_compliant_cases: int = Field(default=0)
    data_source_violation_cases: int = Field(default=0)

    # Data quality impact
    cases_with_preprocessing_issues: int
    data_quality_impact_on_rejections: float = Field(
        description="% of rejections caused by preprocessing issues"
    )

    # Recommendations
    top_agent_fixes: list[str]
    top_rule_clarifications: list[str]
    top_data_quality_fixes: list[str]

    # Executive summary
    executive_summary: str


# ============================================================================
# SECTION EXTRACTION FOR RECONSTRUCTED RULES BOOK
# ============================================================================


class ReconstructedRulesExtractor:
    """Extracts sections from reconstructed_rules_book.md format.

    The reconstructed rules book uses format like:
    - ## 0. Data Source Priorities
    - ## 4. Phase 1 Validation Rules
    - ### 4.2 Work Type Classification
    - #### Step 15: Duplicate Invoice Detection
    """

    def __init__(self, rules_content: str):
        self.rules_content = rules_content
        self.lines = rules_content.split("\n")

    def extract_section(self, section_id: str) -> str:
        """Extract a numbered section (e.g., "0", "4.2", "3.8").

        Handles formats:
        - ## 0. Data Source Priorities
        - ### 4.2 Work Type Classification
        - #### 3.8 ABN Validation
        """
        section_lines = []
        capturing = False
        section_level = 0

        # Patterns to match section headers
        patterns = [
            rf"^##\s*{re.escape(section_id)}[\.\s]",  # ## 0. or ## 4.
            rf"^###\s*{re.escape(section_id)}[\.\s]",  # ### 4.2 or ### 3.8
            rf"^####\s*{re.escape(section_id)}[\.\s]",  # #### subsection
            rf"Section\s*{re.escape(section_id)}[\s:]",  # Section 0:
        ]

        for line in self.lines:
            # Check if this line starts the target section
            if not capturing:
                for pattern in patterns:
                    if re.match(pattern, line, re.IGNORECASE):
                        capturing = True
                        section_level = line.count("#")
                        section_lines.append(line)
                        break
            else:
                # Check if we've hit the next section at same or higher level
                if line.startswith("#"):
                    current_level = len(re.match(r"^#+", line).group())
                    if current_level <= section_level:
                        break
                section_lines.append(line)

        return "\n".join(section_lines) if section_lines else ""

    def extract_step(self, step_number: str) -> str:
        """Extract a specific step (e.g., "15", "22", "33").

        Handles formats:
        - ### Step 15: Duplicate Invoice Detection
        - #### Step 22: ABN Matching
        - | **15** | Status Check |
        """
        section_lines = []
        capturing = False

        patterns = [
            rf"^###\s*Step\s*{step_number}[\s:]",
            rf"^####\s*Step\s*{step_number}[\s:]",
            rf"Step\s*{step_number}[\s:]",
            rf"\|\s*\*\*{step_number}\*\*\s*\|",
        ]

        for _i, line in enumerate(self.lines):
            if not capturing:
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        capturing = True
                        # Capture from here
                        section_lines.append(line)
                        break
            else:
                # Stop at next step or major section
                if re.match(r"^#{2,4}\s*(Step\s*\d+|Phase|\d+\.)", line, re.IGNORECASE):
                    break
                if (
                    re.match(r"^\|\s*\*\*\d+\*\*\s*\|", line)
                    and len(section_lines) > _MIN_SECTION_LINES
                ):
                    break
                section_lines.append(line)

        return "\n".join(section_lines) if section_lines else ""

    def extract_rule(self, rule_id: str) -> str:
        """Extract a specific rule (e.g., "4.1", "33.1", "12.1").

        Handles formats:
        - #### [Rule 4.1: WAF Exceptions]
        - ### [Rule 33.1: Manual WAF Verification]
        """
        section_lines = []
        capturing = False

        patterns = [
            rf"\[Rule\s*{re.escape(rule_id)}[\s:\]]",
            rf"Rule\s*{re.escape(rule_id)}[\s:]",
        ]

        for line in self.lines:
            if not capturing:
                for pattern in patterns:
                    if re.search(pattern, line, re.IGNORECASE):
                        capturing = True
                        section_lines.append(line)
                        break
            else:
                # Stop at next rule or major section
                if re.match(r"^\[Rule\s*\d+", line) or re.match(
                    r"^#{2,4}\s*\[Rule", line
                ):
                    break
                if re.match(r"^#{2,3}\s*(?:Phase|Section|\d+\.)", line):
                    break
                section_lines.append(line)

        return "\n".join(section_lines) if section_lines else ""

    def get_data_source_rules(self) -> str:
        """Extract Section 0: Data Source Priorities"""
        return self.extract_section("0")

    def get_work_type_rules(self) -> str:
        """Extract Section 4.2: Work Type Classification"""
        return self.extract_section("4.2")

    def get_abn_validation_rules(self) -> str:
        """Extract Section 3.8 and Step 22"""
        section_3_8 = self.extract_section("3.8")
        step_22 = self.extract_step("22")
        return f"{section_3_8}\n\n{step_22}"

    def get_vendor_name_rules(self) -> str:
        """Extract Step 22.1: Vendor Name Verification"""
        return self.extract_step("22.1")

    def get_duplicate_detection_rules(self) -> str:
        """Extract Step 15: Duplicate Invoice Detection (Phase 2.5)"""
        return self.extract_step("15")

    def get_invoice_type_rules(self) -> str:
        """Extract Section 9.3: Invoice Type Determination"""
        return self.extract_section("9.3")

    def get_waf_hours_rules(self) -> str:
        """Extract Step 33 and Rule 33.1 (WAF hours validation)"""
        step_33 = self.extract_step("33")
        rule_33_1 = self.extract_rule("33.1")
        return f"{step_33}\n\n{rule_33_1}"

    def get_waf_rules(self) -> str:
        """Extract Step 4 and Rule 4.1"""
        step_4 = self.extract_step("4")
        rule_4_1 = self.extract_rule("4.1")
        return f"{step_4}\n\n{rule_4_1}"

    def get_phase_rules(self, phase_name: str) -> str:
        """Extract all rules for a specific phase"""
        phase_map = {
            "Phase 1": "4",
            "Phase 2": "5",
            # Phase 2.5 not used in general agent
            "Phase 3": "6",
            "Phase 4": "7",
        }
        section_id = phase_map.get(phase_name, "")
        if section_id:
            return self.extract_section(section_id)
        return ""


# Initialize the rules extractor
RULES_EXTRACTOR = ReconstructedRulesExtractor(RULES_BOOK_CONTENT)


# ============================================================================
# RULE DISCOVERY ENGINE (v2.0.0 - Layer 2)
# ============================================================================


class RuleDiscoveryEngine:
    """Discovers validation rules from reconstructed_rules_book.md using LLM at startup.

    Layer 2 of the 3-layer validation architecture:
    - Reads the entire rules book
    - Calls LLM to discover and group all validation rules
    - Caches results to JSON file with rules book SHA-256 hash
    - Provides lookup methods for discovered rules

    Cache invalidation: If rules book content changes (different hash), re-discovers.

    v2.0.0: New class replacing hardcoded constants in DataSourceValidator,
    BypassDetector, ToleranceExtractor, and LLM prompt strings.
    """

    def __init__(
        self,
        rules_content: str,
        model_name: str | None = None,
        cache_path: Path | None = None,
    ):
        self.rules_content = rules_content
        self.model_name = model_name or _gcp_config["GEMINI_PRO_MODEL"]
        self.cache_path = cache_path or (
            AGENT_PKG_DIR / "data" / "rule_discovery_cache.json"
        )
        self.discovered_rules = {}
        self.model = GenerativeModel(
            self.model_name,
            generation_config=GenerationConfig(
                temperature=0, response_mime_type="application/json"
            ),
        )

    def discover_rules(self, force_refresh: bool = False) -> dict:
        """Discover rules from rules book. Uses cache if available and valid.

        Args:
            force_refresh: If True, bypass cache and re-discover.

        Returns:
            Dictionary with discovered rule groups.
        """
        rules_hash = self._compute_rules_hash()

        # Try cache
        if not force_refresh and self.cache_path.exists():
            cached = self._load_cache()
            if cached and cached.get("rules_book_hash") == rules_hash:
                print(f"  Loaded rules from cache (hash: {rules_hash[:12]}...)")
                self.discovered_rules = cached
                return cached

        # Cache miss — discover via LLM
        print("  Discovering rules from rules book (this may take 10-20 seconds)...")
        discovered = self._call_llm_for_discovery()

        discovered["rules_book_hash"] = rules_hash
        discovered["discovery_timestamp"] = datetime.now().isoformat()
        discovered["version"] = "2.0.0"

        self._save_cache(discovered)
        print(
            f"  Rules discovered and cached ({len(discovered.get('rule_groups', []))} groups)"
        )
        self.discovered_rules = discovered
        return discovered

    def get_rule_group(self, group_id: str) -> dict | None:
        """Get a specific rule group by ID."""
        for group in self.discovered_rules.get("rule_groups", []):
            if group.get("group_id") == group_id:
                return group
        return None

    def get_rule(self, group_id: str, rule_id: str) -> dict | None:
        """Get a specific rule from a group."""
        group = self.get_rule_group(group_id)
        if not group:
            return None
        for rule in group.get("rules", []):
            if rule.get("rule_id") == rule_id:
                return rule
        return None

    def _compute_rules_hash(self) -> str:
        """Compute SHA-256 hash of rules book content."""
        return hashlib.sha256(self.rules_content.encode("utf-8")).hexdigest()

    def _load_cache(self) -> dict | None:
        """Load cached rules from JSON file."""
        try:
            with open(self.cache_path, encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"  Warning: Failed to load rule cache: {e}")
            return None

    def _save_cache(self, rules: dict):
        """Save discovered rules to JSON cache file."""
        try:
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8") as f:
                json.dump(rules, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"  Warning: Failed to save rule cache: {e}")

    def _call_llm_for_discovery(self) -> dict:
        """Call LLM to discover and group rules from rules book."""
        _domain = (
            _get_master_data().display_name
            if _get_master_data()
            else "invoice processing"
        )
        prompt = f"""You are analyzing a {_domain} rules book to discover ALL validation rules.
Your task is to extract every hardcodeable validation parameter — field lists, keywords,
thresholds, entity names, exemption lists — and group them logically.

RULES BOOK CONTENT:
```
{self.rules_content}
```

Extract and return a JSON object with "rule_groups" array containing these 7 groups:

1. **data_source_rules** (from Section 0):
   - "invoice_content_fields": array of {{"field": "...", "source": "extraction", "description": "..."}}
   - "po_wo_metadata_fields": array of {{"field": "...", "source": "configuration", "description": "..."}}
   - "forbidden_fields": array of {{"field": "...", "reason": "..."}}

2. **bypass_exemption_rules** (from Section 4.2, Rule 33.1, WAF exemptions):
   - "waf_exempt_work_types": array of strings (work types exempt from WAF hours check)
   - "waf_exempt_vendors_category_a": array of strings (parts/freight vendors)
   - "waf_exempt_keywords_category_b": array of strings (service keywords)
   - "bypass_indicators": array of strings (general bypass patterns like "exempt", "skip", etc.)

3. **tolerance_thresholds** (from Steps 32, 33, 35, 36):
   - Array of {{"step": int, "tolerance_value": float, "unit": "hours"|"currency"|"percent", "description": "..."}}
   - Include: WAF hours tolerance, balance tolerance, line sum tolerance, parts PO tolerance
   - Also include investigator confidence thresholds: min_violation_confidence, min_ambiguous_confidence, investigator_margin

4. **entity_whitelists** (from configuration):
   - "organization_entities": array of strings (all valid customer entity names, case-insensitive)

5. **work_type_classification** (from Section 4.2):
   - Array of {{"work_type": "...", "keywords": [...], "is_default": bool}}
   - Include confidence_threshold for LLM classification

6. **labour_keywords** (from Step 33):
   - Array of strings identifying labour/service line items for hours calculation

7. **root_cause_categories** (from investigation framework):
   - Array of {{"category": "...", "description": "...", "severity": "CRITICAL"|"HIGH"|"MEDIUM"|null, "affected_rules": [...]}}

Return JSON:
{{
  "rule_groups": [
    {{
      "group_id": "data_source_rules",
      "name": "Data Source Priority Rules",
      "description": "Section 0 - which data source to use for each field",
      "applicable_phases": ["Phase 2", "Phase 4"],
      "source_section": "Section 0",
      "rules": [ ... extracted rules ... ]
    }},
    ... 6 more groups ...
  ]
}}

CRITICAL: Extract EXACT field names, keywords, and values from the rules book.
Do NOT invent values. Preserve exact spelling and capitalization from the document.
"""

        try:
            response = self.model.generate_content(prompt)
            json_str = clean_json_response(response.text)
            result = json.loads(json_str)
            if "rule_groups" not in result:
                result = {"rule_groups": []}
            return result
        except Exception as e:
            print(f"  ERROR: Rule discovery failed: {str(e)[:200]}")
            return {"rule_groups": []}


# ============================================================================
# PER-GROUP VALIDATOR (v2.0.0 - Layer 3)
# ============================================================================


class PerGroupValidator:
    """Validates a case against discovered rule groups using LLM with ultra-conservative checks.

    Layer 3 of the 3-layer validation architecture:
    - v2.0.2: ALL rule groups validated by LLM — fully dynamic, no hardcoded logic.
      Deterministic groups (data_source_rules, tolerance_thresholds, entity_whitelists,
      labour_keywords, root_cause_categories) are BATCHED into a single LLM call.
      Subjective groups (work_type_classification, bypass_exemption_rules) get
      individual LLM calls.
    - Triple-check mechanism: all 3 runs must agree to confirm a violation.
    - 95% confidence threshold + 75% overlap required.

    Philosophy: Layer 3 violations are INFORMATIONAL — they enrich the audit trail
    but do NOT override Layer 1 compliance scores. Only flag violations when the
    LLM is ABSOLUTELY CERTAIN based on the discovered rules.
    """

    # Groups that are batched into a single LLM call (deterministic rules)
    BATCH_GROUPS: ClassVar[set[str]] = {
        "data_source_rules",
        "tolerance_thresholds",
        "entity_whitelists",
        "labour_keywords",
        "root_cause_categories",
    }

    # Groups that get individual LLM calls (subjective judgment)
    INDIVIDUAL_GROUPS: ClassVar[set[str]] = {
        "work_type_classification",
        "bypass_exemption_rules",
    }

    def __init__(
        self,
        model_name: str | None = None,
        config: "InvestigationConfig | None" = None,
    ):
        self.model_name = model_name or _gcp_config["GEMINI_PRO_MODEL"]
        self.config = config or INVESTIGATION_CONFIG
        self.model = GenerativeModel(
            self.model_name,
            generation_config=GenerationConfig(
                temperature=0, response_mime_type="application/json"
            ),
        )

    def validate_all_groups(
        self,
        case_id: str,
        rule_groups: list,
        case_data: dict[str, Any],
        enable_double_check: bool = True,
    ) -> dict:
        """Validate case against all rule groups.

        v2.0.2: Batches deterministic groups into ONE LLM call, then runs
        individual calls for subjective groups.
        """
        all_violations = []
        group_results = []
        double_check_stats = {"total": 0, "confirmed": 0, "discarded": 0}

        # Separate groups into batch and individual
        batch_groups = [
            g for g in rule_groups if g.get("group_id") in self.BATCH_GROUPS
        ]
        individual_groups = [
            g for g in rule_groups if g.get("group_id") in self.INDIVIDUAL_GROUPS
        ]
        unknown_groups = [
            g
            for g in rule_groups
            if g.get("group_id") not in self.BATCH_GROUPS
            and g.get("group_id") not in self.INDIVIDUAL_GROUPS
        ]

        # 1) Batch call for deterministic groups (single LLM call)
        if batch_groups:
            batch_result = self._validate_batch(
                case_id,
                batch_groups,
                case_data,
                enable_double_check=enable_double_check,
            )
            group_results.append(batch_result)
            all_violations.extend(batch_result.get("violations", []))

            if batch_result.get("double_check_performed"):
                double_check_stats["total"] += 1
                if batch_result.get("double_check_result") == "confirmed":
                    double_check_stats["confirmed"] += 1
                elif batch_result.get("double_check_result") == "discarded":
                    double_check_stats["discarded"] += 1

        # 2) Individual calls for subjective groups
        for rule_group in individual_groups:
            result = self._validate_individual(
                case_id,
                rule_group,
                case_data,
                enable_double_check=enable_double_check,
            )
            group_results.append(result)
            all_violations.extend(result.get("violations", []))

            if result.get("double_check_performed"):
                double_check_stats["total"] += 1
                if result.get("double_check_result") == "confirmed":
                    double_check_stats["confirmed"] += 1
                elif result.get("double_check_result") == "discarded":
                    double_check_stats["discarded"] += 1

        # 3) Skip unknown groups
        for rule_group in unknown_groups:
            group_id = rule_group.get("group_id", "unknown")
            group_results.append(
                {
                    "group_id": group_id,
                    "violations": [],
                    "compliant_rules": [],
                    "reasoning": f"Unknown group '{group_id}', skipped.",
                    "double_check_performed": False,
                }
            )

        return {
            "case_id": case_id,
            "total_violations": len(all_violations),
            "all_violations": all_violations,
            "group_results": group_results,
            "double_check_stats": double_check_stats,
        }

    # Keep validate_group for backward compatibility (called if someone uses it directly)
    def validate_group(
        self,
        case_id: str,
        rule_group: dict,
        case_data: dict[str, Any],
        enable_double_check: bool = True,
    ) -> dict:
        """Validate a single group — delegates to batch or individual."""
        group_id = rule_group.get("group_id", "unknown")
        if group_id in self.BATCH_GROUPS:
            return self._validate_batch(
                case_id, [rule_group], case_data, enable_double_check
            )
        if group_id in self.INDIVIDUAL_GROUPS:
            return self._validate_individual(
                case_id, rule_group, case_data, enable_double_check
            )
        return {
            "group_id": group_id,
            "violations": [],
            "compliant_rules": [],
            "reasoning": f"Unknown group '{group_id}', skipped.",
            "double_check_performed": False,
        }

    # ==================================================================
    # BATCH VALIDATION — single LLM call for all deterministic groups
    # ==================================================================

    def _validate_batch(
        self,
        case_id: str,
        rule_groups: list,
        case_data: dict[str, Any],
        enable_double_check: bool = True,
    ) -> dict:
        """Validate multiple deterministic rule groups in a single LLM call.

        v2.0.2: Sends ALL deterministic rules in one prompt. Ultra-conservative.
        """
        group_names = [g.get("name", g.get("group_id", "?")) for g in rule_groups]
        print(f"      [Batch: {', '.join(group_names)}]...", end=" ")

        prompt = self._build_batch_prompt(case_id, rule_groups, case_data)
        return self._run_with_triple_check(
            prompt, "batch_deterministic", enable_double_check
        )

    # ==================================================================
    # INDIVIDUAL VALIDATION — separate LLM call per subjective group
    # ==================================================================

    def _validate_individual(
        self,
        case_id: str,
        rule_group: dict,
        case_data: dict[str, Any],
        enable_double_check: bool = True,
    ) -> dict:
        """Validate a single subjective rule group with its own LLM call.

        v2.0.2: Ultra-conservative prompt with triple-check.
        """
        group_id = rule_group.get("group_id", "unknown")
        group_name = rule_group.get("name", group_id)
        print(f"      [{group_name}]...", end=" ")

        prompt = self._build_individual_prompt(case_id, rule_group, case_data)
        return self._run_with_triple_check(prompt, group_id, enable_double_check)

    # ==================================================================
    # TRIPLE-CHECK MECHANISM (shared by batch and individual)
    # ==================================================================

    def _run_with_triple_check(
        self, prompt: str, group_id: str, enable_double_check: bool = True
    ) -> dict:
        """Run LLM validation with triple-check mechanism.

        1. First call
        2. If violations found + double-check enabled → second call
        3. If first two agree → third call
        4. All three must agree to confirm violations
        """
        # First call
        first_result = self._call_group_llm(prompt, group_id)
        first_result["violations"] = [
            v
            for v in first_result.get("violations", [])
            if v.get("confidence", 0) >= _HIGH_CONFIDENCE_THRESHOLD
        ]

        if not first_result.get("violations"):
            print("OK")
            first_result["double_check_performed"] = False
            return first_result

        if not enable_double_check:
            print("VIOLATION")
            first_result["double_check_performed"] = False
            return first_result

        # Second call (double-check)
        print("ISSUE found, double-checking...", end=" ")
        second_result = self._call_group_llm(prompt, group_id)
        second_result["violations"] = [
            v
            for v in second_result.get("violations", [])
            if v.get("confidence", 0) >= _HIGH_CONFIDENCE_THRESHOLD
        ]

        if not self._compare_results(first_result, second_result):
            print("DISCARDED (2nd run disagrees)")
            return {
                "group_id": group_id,
                "violations": [],
                "compliant_rules": first_result.get("compliant_rules", []),
                "reasoning": "Double-check discarded: second run did not confirm violations.",
                "double_check_performed": True,
                "double_check_result": "discarded",
                "first_run_violations": first_result.get("violations", []),
                "second_run_violations": second_result.get("violations", []),
            }

        # Third call (triple-check)
        third_result = self._call_group_llm(prompt, group_id)
        third_result["violations"] = [
            v
            for v in third_result.get("violations", [])
            if v.get("confidence", 0) >= _HIGH_CONFIDENCE_THRESHOLD
        ]

        if not self._compare_results(first_result, third_result):
            print("DISCARDED (3rd run disagrees)")
            return {
                "group_id": group_id,
                "violations": [],
                "compliant_rules": first_result.get("compliant_rules", []),
                "reasoning": "Triple-check discarded: third run did not confirm violations.",
                "double_check_performed": True,
                "double_check_result": "discarded",
            }

        # All three agree — confirmed
        print("CONFIRMED (3/3 agree)")
        first_result["double_check_performed"] = True
        first_result["double_check_result"] = "confirmed"
        return first_result

    # ==================================================================
    # PROMPT BUILDERS
    # ==================================================================

    def _build_batch_prompt(
        self, case_id: str, rule_groups: list, case_data: dict[str, Any]
    ) -> str:
        """Build a single LLM prompt containing ALL deterministic rule groups.

        v2.0.2: One prompt, one call — fully dynamic, no hardcoded logic.
        """
        extraction_data = case_data.get("agent_outputs", {}).get("extraction", {})
        agent_outputs = case_data.get("agent_outputs", {})

        # Collect ALL phase outputs (batch covers multiple phases)
        phase_map = {
            "Phase 1": "phase1",
            "Phase 2": "phase2",
            "Phase 3": "phase3",
            "Phase 4": "phase4",
        }
        phase_outputs = {}
        for phase_name, key in phase_map.items():
            data = agent_outputs.get(key, {})
            if data:
                phase_outputs[phase_name] = data

        def truncate_json(obj, max_chars=3000):
            s = json.dumps(obj, indent=2, default=str)
            return s[:max_chars] + "\n... (truncated)" if len(s) > max_chars else s

        # Build combined rules section
        rules_sections = []
        for group in rule_groups:
            gid = group.get("group_id", "unknown")
            gname = group.get("name", gid)
            gdesc = group.get("description", "")
            grules = group.get("rules", {})
            rules_sections.append(
                f"### {gname} (group_id: {gid})\n"
                f"Description: {gdesc}\n"
                f"Rules:\n```json\n{truncate_json(grules, 2000)}\n```"
            )
        combined_rules = "\n\n".join(rules_sections)

        _domain = (
            _get_master_data().display_name
            if _get_master_data()
            else "invoice processing"
        )
        prompt = f"""You are validating an agent's {_domain} against multiple rule groups.

**CRITICAL PHILOSOPHY — YOU MUST FOLLOW THIS:**

You are a SECONDARY validator. The primary validation (Layer 1) has ALREADY thoroughly
validated this case phase by phase. Your job is ONLY to catch EGREGIOUS, OBVIOUS errors
that the primary validation missed. You are NOT expected to find issues — most cases
should be FULLY COMPLIANT.

The cost of FALSE POSITIVES is EXTREMELY HIGH — each false positive wastes human review
time and undermines trust in the investigation system. The cost of missing a minor
violation is LOW.

**WHEN TO FLAG A VIOLATION — ALL of these conditions MUST be met:**
1. The violation is SUBSTANTIAL and UNAMBIGUOUS — not borderline, not subjective
2. You are ABSOLUTELY CERTAIN (≥95% confidence) the agent made an error
3. There is NO reasonable alternative explanation for the agent's action
4. The evidence is CONCRETE and VERIFIABLE — you can point to specific values
5. You would stake your professional reputation on this finding
6. The issue would cause SIGNIFICANT business impact if left uncorrected

**WHEN TO MARK AS COMPLIANT — ANY of these is sufficient:**
- The agent's decision is within generous practical tolerance (use 25% margin)
- The case is borderline in ANY way
- There's a reasonable business explanation you might not know about
- Numerical values are close but not exact (rounding, formatting differences)
- The agent may have access to context you cannot see in the data
- Entity names vary due to trading names, abbreviations, or subsidiaries
- Work type classification is defensible even if you'd classify differently
- The field name appears in output but may be for logging/reporting, not as a data source

**SPECIFIC RULES FOR DETERMINISTIC CHECKS:**
- Data sources: The general agent uses ONLY extraction data from PDFs (no preprocessing)
  AS ITS DATA SOURCE (not just referenced it in logs). The field must appear as the
  SOURCE of a calculation, not just mentioned.
- Tolerances: Only flag if the numerical difference is CLEARLY beyond tolerance
  WITH a 25% investigator margin applied. If the agent rejected the case (caught
  the issue), that is COMPLIANT, not a violation.
- Entity whitelists: The organization may have multiple valid entity names
  (trading names, abbreviations, subsidiaries). If the name is PLAUSIBLY a valid
  customer entity, it is valid. Only flag if the entity is COMPLETELY unrelated.
- Labour keywords: The agent may identify labour using methods beyond exact keyword
  matching. Only flag if labour was COMPLETELY missed AND it caused a wrong decision.

CASE ID: {case_id}

RULE GROUPS TO CHECK:
{combined_rules}

CASE DATA — EXTRACTION (from PDF):
```json
{truncate_json(extraction_data)}
```

AGENT OUTPUTS (all phases):
```json
{truncate_json(phase_outputs, 5000)}
```

TASK: Check if the agent EGREGIOUSLY violated ANY rules across these groups.

RETURN JSON:
{{
  "group_id": "batch_deterministic",
  "violations": [
    {{
      "rule_id": "group_id.specific_rule",
      "rule_description": "what the rule requires",
      "violation_description": "what the agent did wrong",
      "evidence": "specific CONCRETE evidence with exact values",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "confidence": 0.0-1.0
    }}
  ],
  "compliant_rules": ["rule_id1", "rule_id2"],
  "reasoning": "overall assessment"
}}

ONLY include violations with confidence >= 0.95. When in ANY doubt, mark as compliant.
An empty violations list is the EXPECTED and PREFERRED outcome for most cases.
"""
        return prompt

    def _build_individual_prompt(
        self, case_id: str, rule_group: dict, case_data: dict[str, Any]
    ) -> str:
        """Build LLM prompt for a single subjective rule group.

        v2.0.2: Ultra-conservative prompt for subjective groups.
        """
        extraction_data = case_data.get("agent_outputs", {}).get("extraction", {})
        agent_outputs = case_data.get("agent_outputs", {})

        phase_map = {
            "Phase 1": "phase1",
            "Phase 2": "phase2",
            "Phase 3": "phase3",
            "Phase 4": "phase4",
        }
        phase_outputs = {}
        for phase_name in rule_group.get("applicable_phases", []):
            key = phase_map.get(phase_name)
            if key:
                phase_outputs[phase_name] = agent_outputs.get(key, {})

        def truncate_json(obj, max_chars=3000):
            s = json.dumps(obj, indent=2, default=str)
            return s[:max_chars] + "\n... (truncated)" if len(s) > max_chars else s

        _domain = (
            _get_master_data().display_name
            if _get_master_data()
            else "invoice processing"
        )
        prompt = f"""You are validating an agent's {_domain} against a specific rule group.

**CRITICAL PHILOSOPHY — YOU MUST FOLLOW THIS:**

You are a SECONDARY validator. The primary validation (Layer 1) has ALREADY thoroughly
validated this case. Your job is ONLY to catch EGREGIOUS, OBVIOUS errors.

The cost of FALSE POSITIVES is EXTREMELY HIGH. The cost of missing a minor violation is LOW.

**WHEN TO FLAG A VIOLATION — ALL of these conditions MUST be met:**
1. The violation is SUBSTANTIAL and UNAMBIGUOUS — not borderline, not subjective
2. You are ABSOLUTELY CERTAIN (≥95% confidence) the agent made an error
3. There is NO reasonable alternative explanation for the agent's action
4. The evidence is CONCRETE and VERIFIABLE from the data provided
5. You would stake your professional reputation on this finding
6. The issue would cause SIGNIFICANT business impact if left uncorrected

**WHEN TO MARK AS COMPLIANT — ANY of these is sufficient:**
- The agent's decision is within generous practical tolerance
- The case is borderline in ANY way
- There's a reasonable business explanation you might not know about
- Work type classification is subjective and the agent's choice is defensible
- Trading names, entity variations, or business relationships could explain differences
- The agent may have access to context you cannot see

**SPECIFIC GUIDANCE:**
- Work type classification is INHERENTLY SUBJECTIVE. "PM" vs "Repairs" is often ambiguous.
  Only flag if the classification is OBVIOUSLY and EGREGIOUSLY wrong with no defensible
  interpretation.
- Bypass/exemption detection: the agent may have valid reasons not visible in the data.
  Only flag if the bypass is CLEARLY invalid per the explicit rules.
- In the Australian business environment, trading names, subsidiaries, and brand names
  frequently differ from legal entity names. ASSUME same entity unless ZERO explanation exists.

CASE ID: {case_id}

RULE GROUP: {rule_group.get("name", "Unknown")}
DESCRIPTION: {rule_group.get("description", "")}
SOURCE SECTION: {rule_group.get("source_section", "N/A")}

RULES TO CHECK:
```json
{truncate_json(rule_group.get("rules", []), 4000)}
```

CASE DATA — EXTRACTION (from PDF):
```json
{truncate_json(extraction_data)}
```

AGENT OUTPUTS (relevant phases):
```json
{truncate_json(phase_outputs)}
```

TASK: Check if the agent EGREGIOUSLY violated ANY rules in this group.

RETURN JSON:
{{
  "group_id": "{rule_group.get("group_id", "unknown")}",
  "violations": [
    {{
      "rule_id": "string",
      "rule_description": "what the rule requires",
      "violation_description": "what the agent did wrong",
      "evidence": "specific CONCRETE evidence from case data",
      "severity": "CRITICAL|HIGH|MEDIUM|LOW",
      "confidence": 0.0-1.0
    }}
  ],
  "compliant_rules": ["rule_id1", "rule_id2"],
  "reasoning": "overall assessment"
}}

ONLY include violations with confidence >= 0.95. When in ANY doubt, mark as compliant.
An empty violations list is the EXPECTED and PREFERRED outcome.
"""
        return prompt

    # ==================================================================
    # LLM CALL AND COMPARISON
    # ==================================================================

    def _call_group_llm(self, prompt: str, group_id: str) -> dict:
        """Call LLM for group validation."""
        try:
            response = self.model.generate_content(prompt)
            json_str = clean_json_response(response.text)
            result = json.loads(json_str)
            result["group_id"] = group_id
            return result
        except Exception as e:
            return {
                "group_id": group_id,
                "violations": [],
                "compliant_rules": [],
                "reasoning": f"LLM call failed: {str(e)[:150]}",
                "error": str(e),
            }

    def _compare_results(self, first: dict, second: dict) -> bool:
        """Compare two validation results to determine if violations are consistent.

        v2.0.2: Requires 75% overlap for confirmation.
        Returns True if violations are confirmed (both runs found overlapping issues).
        Returns False if inconsistent (discard violations).
        """
        first_violations = {
            v.get("rule_id") for v in first.get("violations", []) if v.get("rule_id")
        }
        second_violations = {
            v.get("rule_id") for v in second.get("violations", []) if v.get("rule_id")
        }

        if not first_violations:
            return False

        if not second_violations:
            return False

        overlap = first_violations & second_violations
        overlap_ratio = len(overlap) / len(first_violations)
        return overlap_ratio >= _OVERLAP_THRESHOLD


# ============================================================================
# DATA SOURCE VALIDATION (Section 0)
# ============================================================================


class DataSourceValidator:
    """Validates agent used correct data sources per Section 0 of reconstructed_rules_book.md.

    Critical Rule: Use EXTRACTION for invoice content, PREPROCESSING only for PO/WO metadata.

    v2.0.0: Field lists are now loaded from RuleDiscoveryEngine (Layer 2) instead of
    being hardcoded. Falls back to hardcoded defaults if discovery is unavailable.
    """

    # Hardcoded defaults (used as fallback if rule discovery is unavailable)
    _DEFAULT_INVOICE_CONTENT_FIELDS: ClassVar[dict[str, str]] = {
        "invoice_total_inc_gst": "Invoice total including GST",
        "invoice_total_ex_gst": "Invoice total excluding GST",
        "gst_amount": "GST/tax amount",
        "invoice_number": "Invoice number from PDF",
        "invoice_date": "Invoice date from PDF",
        "vendor_name": "Vendor name from PDF",
        "line_items": "Invoice line items",
        "balance": "Calculated balance (Inc GST - Ex GST - GST)",
    }

    _DEFAULT_PO_WO_METADATA_FIELDS: ClassVar[dict[str, str]] = {
        "po_number": "Purchase Order number",
        "wo_status": "Work Order status",
        "po_status": "Purchase Order status",
        "po_approval_date": "PO approval date",
        "location": "Site/location code",
        "site_description": "Site description",
        "total_cost": "PO total value",
        "reference_tax_id": "Reference tax ID / ABN",
        "vendor_number": "Vendor number",
        "work_after_hours_allowed": "Work after hours flag",
    }

    _DEFAULT_FORBIDDEN_PREPROCESSING_FIELDS: ClassVar[dict[str, str]] = {
        "pretax_total": "Contains PO subtotal, not invoice subtotal",
        "gst_total": "Contains PO GST, not invoice GST",
        "invoice_total": "Contains PO total, not invoice total",
        "balance": "Calculated from unreliable PO totals",
        "line_items_json": "Contains PO line items, not invoice line items",
    }

    def __init__(self, rule_discovery: "RuleDiscoveryEngine | None" = None):
        """Initialize with discovered rules or fall back to defaults.

        Args:
            rule_discovery: RuleDiscoveryEngine instance with discovered rules.
                           If None, uses hardcoded defaults.
        """
        self.INVOICE_CONTENT_FIELDS = dict(self._DEFAULT_INVOICE_CONTENT_FIELDS)
        self.PO_WO_METADATA_FIELDS = dict(self._DEFAULT_PO_WO_METADATA_FIELDS)
        self.FORBIDDEN_PREPROCESSING_FIELDS = dict(
            self._DEFAULT_FORBIDDEN_PREPROCESSING_FIELDS
        )

        if rule_discovery:
            self._load_from_discovery(rule_discovery)

    def _load_from_discovery(self, rule_discovery: "RuleDiscoveryEngine") -> None:
        """Load field lists from discovered rules, overriding defaults."""
        group = rule_discovery.get_rule_group("data_source_rules")
        if not group:
            return

        fields = self._normalize_rules_data(group.get("rules", {}))
        self._load_field_list(
            fields, "invoice_content_fields", "INVOICE_CONTENT_FIELDS"
        )
        self._load_field_list(fields, "po_wo_metadata_fields", "PO_WO_METADATA_FIELDS")
        self._load_field_list(
            fields,
            "forbidden_preprocessing_fields",
            "FORBIDDEN_PREPROCESSING_FIELDS",
            value_key="reason",
        )

    @staticmethod
    def _normalize_rules_data(rules_data: Any) -> dict:
        """Normalize LLM rules response (dict or list) into a flat dict."""
        if isinstance(rules_data, dict):
            return rules_data
        if isinstance(rules_data, list):
            merged: dict[str, Any] = {}
            for rule in rules_data:
                if isinstance(rule, dict):
                    for k, v in rule.items():
                        if k not in ("rule_id", "description"):
                            merged[k] = v
            return merged
        return {}

    def _load_field_list(
        self,
        fields: dict,
        key: str,
        attr: str,
        value_key: str = "description",
    ) -> None:
        """Load a list of field dicts into the given instance attribute."""
        raw = fields.get(key, [])
        if raw and isinstance(raw, list):
            setattr(
                self,
                attr,
                {
                    f["field"]: f.get(value_key, f.get("description", ""))
                    for f in raw
                    if isinstance(f, dict) and "field" in f
                },
            )

    def validate_data_source_usage(
        self,
        extraction_data: dict,
        preprocessing_data: dict,
        agent_phase_output: dict,
    ) -> list[DataSourceValidation]:
        """Check if agent used correct data sources for all fields.

        Returns list of DataSourceValidation objects.
        """
        validations = []

        # Check if agent used forbidden preprocessing fields
        for (
            field_name,
            description,
        ) in self.FORBIDDEN_PREPROCESSING_FIELDS.items():
            # Look for evidence agent used this field
            if self._field_referenced_in_output(
                field_name, agent_phase_output, "preprocessing"
            ):
                validations.append(
                    DataSourceValidation(
                        field_name=field_name,
                        expected_source="extraction",
                        actual_source="preprocessing",
                        is_forbidden_field=True,
                        is_valid=False,
                        severity="CRITICAL",
                        issue=f"Agent used FORBIDDEN preprocessing field '{field_name}' - {description}",
                    )
                )

        # Check invoice content fields
        for invoice_field, _description in self.INVOICE_CONTENT_FIELDS.items():
            if self._field_referenced_in_output(
                invoice_field, agent_phase_output, "preprocessing"
            ):
                validations.append(
                    DataSourceValidation(
                        field_name=invoice_field,
                        expected_source="extraction",
                        actual_source="preprocessing",
                        is_forbidden_field=False,
                        is_valid=False,
                        severity="HIGH",
                        issue=f"Agent used preprocessing for '{invoice_field}' but should use extraction",
                    )
                )
            elif self._field_referenced_in_output(
                invoice_field, agent_phase_output, "extraction"
            ):
                validations.append(
                    DataSourceValidation(
                        field_name=invoice_field,
                        expected_source="extraction",
                        actual_source="extraction",
                        is_valid=True,
                    )
                )

        return validations

    def _field_referenced_in_output(
        self, field_name: str, output: dict, source_type: str
    ) -> bool:
        """Check if a field was referenced from a specific source in agent output."""
        output_str = json.dumps(output).lower()

        # Look for patterns like "preprocessing.field_name" or "extraction.field_name"
        pattern = f"{source_type}.{field_name}".lower()
        if pattern in output_str:
            return True

        # Look for field name with source context
        if field_name.lower() in output_str:
            # Check nearby context for source
            idx = output_str.find(field_name.lower())
            context = output_str[max(0, idx - 50) : idx + 50]
            if source_type.lower() in context:
                return True

        return False

    def validate_balance_calculation(
        self,
        extraction_data: dict,
        preprocessing_data: dict,
        agent_calculated_balance: float | None,
    ) -> DataSourceValidation:
        """Validate balance was calculated from extraction data, not preprocessing.

        Correct formula: balance = invoice_total_inc_gst - (invoice_total_ex_gst + gst_amount)
        All values must come from extraction.
        """
        invoice = extraction_data.get("invoice", {})

        ext_inc = invoice.get("invoice_total_inc_gst", 0) or 0
        ext_ex = invoice.get("invoice_total_ex_gst", 0) or 0
        ext_gst = invoice.get("gst_amount", 0) or 0

        correct_balance = ext_inc - (ext_ex + ext_gst)

        # Validate agent balance matches extraction calculation
        if agent_calculated_balance is not None:
            matches_extraction = (
                abs(agent_calculated_balance - correct_balance) < _BALANCE_TOLERANCE
            )

            if not matches_extraction:
                return DataSourceValidation(
                    field_name="balance",
                    expected_source="calculated_from_extraction",
                    actual_source="unknown",
                    is_forbidden_field=False,
                    is_valid=False,
                    severity="HIGH",
                    issue=f"Agent balance ({agent_calculated_balance}) does not match extraction calculation ({correct_balance:.2f})",
                )

        return DataSourceValidation(
            field_name="balance",
            expected_source="calculated_from_extraction",
            actual_source="extraction",
            is_valid=True,
        )


# ============================================================================
# AGENT OUTPUT EXTRACTOR (v1.3.0)
# ============================================================================


class AgentOutputExtractor:
    """Extracts actual computed values from agent's intermediate outputs.

    Philosophy: Validate what the agent DID, not what it SHOULD HAVE computed.
    This reduces false positives from extraction failures, data differences, etc.

    v1.3.0: New class to improve investigation accuracy.
    """

    def __init__(self, agent_outputs: dict[str, Any]):
        """Args:
        agent_outputs: Dictionary containing all agent phase outputs
                      (phase1, phase2, phase3, phase4, etc.)
        """
        self.outputs = agent_outputs

    def get_validation_step(self, phase: str, step: int) -> dict[str, Any] | None:
        """Get a specific validation step from a phase's output.

        Args:
            phase: Phase key (e.g., "phase1", "phase4")
            step: Step number (e.g., 33 for WAF hours)

        Returns:
            Validation step dict with keys: step, rule, passed, evidence, details
            Returns None if step not found
        """
        phase_output = self.outputs.get(phase, {})
        validations = phase_output.get("validations", [])

        for v in validations:
            if v.get("step") == step:
                return v
        return None

    def get_agent_computed_value(
        self, phase: str, step: int, detail_key: str, fallback: Any = None
    ) -> Any:
        """Get a specific computed value from agent's validation details.

        Args:
            phase: Phase key
            step: Step number
            detail_key: Key within the "details" dict
            fallback: Value to return if not found

        Returns:
            The computed value or fallback
        """
        validation = self.get_validation_step(phase, step)
        if validation is None:
            return fallback

        details = validation.get("details", {})
        return details.get(detail_key, fallback)

    def get_agent_decision(self, phase: str) -> str:
        """Get the agent's decision for a phase."""
        phase_output = self.outputs.get(phase, {})
        return phase_output.get("decision", "Unknown")

    def get_agent_reason(self, phase: str) -> str | None:
        """Get the agent's rejection reason for a phase."""
        phase_output = self.outputs.get(phase, {})
        return phase_output.get("rejection_reason")

    def step_was_executed(self, phase: str, step: int) -> bool:
        """Check if a specific step was executed by the agent."""
        return self.get_validation_step(phase, step) is not None

    def step_passed(self, phase: str, step: int) -> bool | None:
        """Check if a specific step passed. Returns None if step not found."""
        validation = self.get_validation_step(phase, step)
        if validation is None:
            return None
        return validation.get("passed", None)

    def get_step_evidence(self, phase: str, step: int) -> str:
        """Get the evidence string from a validation step."""
        validation = self.get_validation_step(phase, step)
        if validation is None:
            return ""
        return validation.get("evidence", "")

    def get_all_phase_validations(self, phase: str) -> list[dict[str, Any]]:
        """Get all validation steps for a phase."""
        phase_output = self.outputs.get(phase, {})
        return phase_output.get("validations", [])


# ============================================================================
# BYPASS DETECTOR (v1.3.0)
# ============================================================================


class BypassDetector:
    """Detects when agent intentionally bypassed a validation step.

    v2.0.0: Bypass indicators are now loaded from RuleDiscoveryEngine (Layer 2)
    instead of being hardcoded. Falls back to hardcoded defaults if discovery
    is unavailable.

    v1.3.0: New class to reduce false positives from valid exemptions.
    """

    # Default bypass patterns (used as fallback)
    _DEFAULT_BYPASS_INDICATORS: ClassVar[list[str]] = [
        "exempt",
        "skip",
        "not applicable",
        "not required",
        "bypassed",
        "excluded",
        "no data available",
        "data not found",
        "not checked",
        "outside scope",
        "no waf",
        "no waf",
    ]

    def __init__(
        self,
        rules_extractor: "ReconstructedRulesExtractor",
        rule_discovery: "RuleDiscoveryEngine" = None,
    ):
        """Args:
        rules_extractor: For dynamically extracting exemption rules.
        rule_discovery: RuleDiscoveryEngine instance. If provided, loads bypass
                       indicators from discovered rules.
        """
        self.rules_extractor = rules_extractor
        self._exemption_cache = {}

        # v2.0.0: Load bypass indicators from discovered rules
        self.BYPASS_INDICATORS = list(self._DEFAULT_BYPASS_INDICATORS)
        if rule_discovery:
            group = rule_discovery.get_rule_group("bypass_exemption_rules")
            if group:
                rules_data = group.get("rules", {})
                # Handle rules as dict or list
                if isinstance(rules_data, dict):
                    indicators = rules_data.get(
                        "bypass_indicators", rules_data.get("patterns", [])
                    )
                    if indicators and isinstance(indicators, list):
                        self.BYPASS_INDICATORS = indicators
                elif isinstance(rules_data, list):
                    for rule in rules_data:
                        if isinstance(rule, dict):
                            indicators = rule.get(
                                "bypass_indicators", rule.get("patterns", [])
                            )
                            if indicators and isinstance(indicators, list):
                                self.BYPASS_INDICATORS = indicators
                                break

    def detect_bypass(
        self, phase: str, step: int, agent_evidence: str
    ) -> dict[str, Any]:
        """Detect if agent bypassed a step and why.

        Args:
            phase: Phase name (e.g., "Phase 4")
            step: Step number
            agent_evidence: The evidence string from agent's validation

        Returns:
            Dict with:
                - bypassed: bool
                - bypass_type: str (exempt_work_type, exempt_vendor, no_data, etc.)
                - bypass_reason: str
                - is_valid_bypass: bool (per rules book)
        """
        evidence_lower = agent_evidence.lower()

        # Check for bypass indicators
        for indicator in self.BYPASS_INDICATORS:
            if indicator in evidence_lower:
                bypass_type = self._classify_bypass_type(evidence_lower, step)
                return {
                    "bypassed": True,
                    "bypass_type": bypass_type,
                    "bypass_reason": agent_evidence,
                    "is_valid_bypass": self._is_valid_bypass(phase, step, bypass_type),
                }

        return {
            "bypassed": False,
            "bypass_type": None,
            "bypass_reason": None,
            "is_valid_bypass": None,
        }

    def _classify_bypass_type(self, evidence_lower: str, step: int) -> str:
        """Classify the type of bypass from evidence."""
        if "work type" in evidence_lower and "exempt" in evidence_lower:
            return "exempt_work_type"
        if (
            "vendor" in evidence_lower and "exempt" in evidence_lower
        ) or "pest control" in evidence_lower:
            return "exempt_vendor"
        if (
            "no data" in evidence_lower
            or "not found" in evidence_lower
            or "no waf" in evidence_lower
        ):
            return "no_data"
        if "skip" in evidence_lower:
            return "explicit_skip"
        return "unknown"

    def _is_valid_bypass(self, phase: str, step: int, bypass_type: str) -> bool:
        """Check if bypass is valid per rules book.
        Uses cached exemption rules extracted from rules book.
        """
        cache_key = f"{phase}_{step}"

        if cache_key not in self._exemption_cache:
            # Extract exemption rules for this step
            self._exemption_cache[cache_key] = self._extract_exemptions(phase, step)

        exemptions = self._exemption_cache[cache_key]

        # Check if bypass type matches any valid exemption
        if bypass_type == "exempt_work_type":
            return "work_type" in exemptions.get("exemption_categories", [])
        if bypass_type == "exempt_vendor":
            return "vendor" in exemptions.get("exemption_categories", [])
        if bypass_type == "no_data":
            return exemptions.get("allows_no_data_bypass", False)

        return False

    def _extract_exemptions(self, phase: str, step: int) -> dict[str, Any]:
        """Extract exemption rules for a step from rules book."""
        step_rules = self.rules_extractor.extract_step(str(step))

        exemptions = {
            "exemption_categories": [],
            "allows_no_data_bypass": False,
            "raw_rules": step_rules[:500],
        }

        step_lower = step_rules.lower()

        # Detect exemption categories from rules text
        if "exempt work type" in step_lower or (
            "work type" in step_lower and "skip" in step_lower
        ):
            exemptions["exemption_categories"].append("work_type")
        if "exempt" in step_lower and (
            "pm" in step_lower or "cleaning" in step_lower or "trolley" in step_lower
        ):
            exemptions["exemption_categories"].append("work_type")
        if "exempt vendor" in step_lower or (
            "vendor" in step_lower and "skip" in step_lower
        ):
            exemptions["exemption_categories"].append("vendor")
        if "pest control" in step_lower:
            exemptions["exemption_categories"].append("vendor")
        if (
            "no data" in step_lower
            or "not available" in step_lower
            or "0" in step_lower
        ):
            exemptions["allows_no_data_bypass"] = True

        return exemptions

    def get_valid_exemptions_for_step(self, phase: str, step: int) -> list[str]:
        """Get list of valid exemption types for a step."""
        cache_key = f"{phase}_{step}"
        if cache_key not in self._exemption_cache:
            self._exemption_cache[cache_key] = self._extract_exemptions(phase, step)
        return self._exemption_cache[cache_key].get("exemption_categories", [])


# ============================================================================
# TOLERANCE EXTRACTOR (v1.3.0)
# ============================================================================


class ToleranceExtractor:
    """Extracts tolerance values from rules book dynamically.

    Supports extracting:
    - Numerical tolerances (e.g., "0.5 hours", "3%", "$1.00")
    - Percentage tolerances
    - Boundary conditions

    v2.0.0: Tolerance values are now pre-loaded from RuleDiscoveryEngine (Layer 2)
    for steps covered by discovery. Falls back to regex parsing for other steps.

    v1.3.0: New class for adaptive tolerance handling.
    """

    def __init__(
        self,
        rules_extractor: "ReconstructedRulesExtractor",
        rule_discovery: "RuleDiscoveryEngine" = None,
    ):
        self.rules_extractor = rules_extractor
        self._tolerance_cache = {}

        # v2.0.0: Pre-load tolerance values from discovered rules
        if rule_discovery:
            group = rule_discovery.get_rule_group("tolerance_thresholds")
            if group:
                rules_data = group.get("rules", [])
                if isinstance(rules_data, list):
                    for rule in rules_data:
                        if not isinstance(rule, dict):
                            continue
                        step = rule.get("step")
                        if step is None:
                            continue
                        # Step can be int or string like "4.2"; only cache integer steps
                        try:
                            step_int = int(step)
                        except (ValueError, TypeError):
                            continue
                        self._tolerance_cache[step_int] = {
                            "value": rule.get(
                                "tolerance_value", rule.get("base_tolerance")
                            ),
                            "unit": rule.get("unit", "hours"),
                            "boundary_type": "inclusive",
                            "investigator_margin": rule.get(
                                "investigator_margin", 0.15
                            ),
                            "raw_rules": rule.get("description", ""),
                            "source": "discovery",
                        }

    def get_tolerance_for_step(self, step: int) -> dict[str, Any]:
        """Get tolerance configuration for a specific step.

        Returns:
            Dict with:
                - value: The tolerance value
                - unit: hours, percent, currency
                - boundary_type: inclusive, exclusive
                - investigator_margin: Additional margin for borderline cases
        """
        if step in self._tolerance_cache:
            return self._tolerance_cache[step]

        step_rules = self.rules_extractor.extract_step(str(step))
        tolerance_info = self._parse_tolerance_from_rules(step_rules, step)

        self._tolerance_cache[step] = tolerance_info
        return tolerance_info

    def _parse_tolerance_from_rules(self, rules_text: str, step: int) -> dict[str, Any]:
        """Parse tolerance values from rules text."""
        result = {
            "value": None,
            "unit": None,
            "boundary_type": "inclusive",
            "investigator_margin": 0.15,  # 15% additional margin for investigator
            "raw_rules": rules_text[:200],
        }

        rules_lower = rules_text.lower()

        # Pattern: "X hours" or "X hour" - specifically look for tolerance patterns
        hours_patterns = [
            r"tolerance[:\s=]+(\d+\.?\d*)\s*hours?",
            r"(\d+\.?\d*)\s*hours?\s*tolerance",
            r"\+\s*(\d+\.?\d*)\s*hours?",
            r"(\d+\.?\d*)\s*hours?\s*\(.*tolerance",
        ]
        for pattern in hours_patterns:
            match = re.search(pattern, rules_lower)
            if match:
                result["value"] = float(match.group(1))
                result["unit"] = "hours"
                break

        # If no specific tolerance pattern found, look for general hours mention
        if result["value"] is None:
            general_match = re.search(r"(\d+\.?\d*)\s*hours?", rules_lower)
            if general_match and "tolerance" in rules_lower:
                result["value"] = float(general_match.group(1))
                result["unit"] = "hours"

        # Pattern: "X%" or "X percent"
        percent_match = re.search(r"(\d+\.?\d*)\s*(%|percent)", rules_lower)
        if percent_match and result["value"] is None:
            result["value"] = float(percent_match.group(1))
            result["unit"] = "percent"

        # Pattern: "$X" or "X dollars"
        currency_match = re.search(r"\$(\d+\.?\d*)", rules_lower)
        if currency_match and result["value"] is None:
            result["value"] = float(currency_match.group(1))
            result["unit"] = "currency"

        # Determine boundary type
        if "<=" in rules_text or "≤" in rules_text:
            result["boundary_type"] = "inclusive"
        elif "<" in rules_text:
            result["boundary_type"] = "exclusive"

        # Default tolerance for Step 33 (WAF hours) if not found
        if step == _WAF_HOURS_STEP and result["value"] is None:
            result["value"] = 0.5
            result["unit"] = "hours"

        return result

    def apply_investigator_margin(
        self, tolerance: dict[str, Any], base_value: float | None = None
    ) -> float:
        """Apply additional investigator margin to tolerance.

        The investigator should be MORE lenient than the agent to avoid
        false positives on borderline cases.
        """
        margin = tolerance.get("investigator_margin", 0.15)
        tol_value = tolerance.get("value", 0)

        if tol_value is None:
            return base_value if base_value else 0

        # Add margin on top of tolerance
        return tol_value * (1 + margin)

    def is_within_tolerance(
        self,
        actual: float,
        expected: float,
        step: int,
        apply_investigator_margin: bool = True,
    ) -> dict[str, Any]:
        """Check if actual value is within tolerance of expected.

        Args:
            actual: The actual value
            expected: The expected value
            step: Step number to get tolerance from
            apply_investigator_margin: Whether to apply additional margin

        Returns:
            Dict with within_tolerance, difference, tolerance_used, etc.
        """
        tolerance_config = self.get_tolerance_for_step(step)

        tol_value = tolerance_config.get("value", 0) or 0
        unit = tolerance_config.get("unit", "")

        if apply_investigator_margin:
            tol_value = self.apply_investigator_margin(tolerance_config, tol_value)

        # Calculate difference based on unit
        if unit == "percent":
            # Percentage tolerance
            difference = abs(actual - expected)
            threshold = expected * (tol_value / 100) if expected != 0 else tol_value
            within_tolerance = difference <= threshold
        else:
            # Absolute tolerance
            difference = abs(actual - expected)
            within_tolerance = difference <= tol_value

        return {
            "within_tolerance": within_tolerance,
            "difference": difference,
            "tolerance_value": tol_value,
            "tolerance_unit": unit,
            "investigator_margin_applied": apply_investigator_margin,
            "boundary_type": tolerance_config.get("boundary_type", "inclusive"),
        }


# ============================================================================
# LLM VALIDATION WITH RECONSTRUCTED RULES
# ============================================================================


class LLMRulesValidatorReconstructed:
    """LLM-based rule validation using reconstructed_rules_book.md.

    Key differences from original:
    - Uses detailed sections from reconstructed rules
    - Validates data source usage (Section 0)
    - Validates LLM confidence thresholds (Section 4.2)
    - Validates ABN checksum and re-extraction (Section 3.8)
    - Validates vendor name semantic similarity (Step 22.1)
    - Validates duplicate detection (Step 15)
    """

    # General investigator guidelines prepended to all validation prompts
    INVESTIGATOR_GUIDELINES = """
================================================================================
INVESTIGATOR CONFIDENCE GUIDELINES (APPLY TO ALL VALIDATIONS)
================================================================================

You are an INVESTIGATOR reviewing the main agent's processing decisions. Your role
is to identify GENUINE, SIGNIFICANT rule violations - NOT to nitpick marginal cases
or flag issues that don't have meaningful business impact.

**CRITICAL PHILOSOPHY: BE CONSERVATIVE**

The cost of FALSE POSITIVES (incorrectly flagging a compliant action as violation)
is HIGHER than the cost of FALSE NEGATIVES (missing a minor violation). Therefore:
- When in doubt, mark as COMPLIANT (valid=true)
- Only flag CLEAR, UNAMBIGUOUS violations
- Give the agent maximum benefit of the doubt

**CORE PRINCIPLES:**

1. **VERY HIGH CONFIDENCE REQUIRED:** Only flag a violation when you are EXTREMELY
   CONFIDENT (>90%) that the main agent genuinely violated the rules in a MEANINGFUL way.
   If confidence is 80-90%, mark as COMPLIANT with a note. If <80%, always COMPLIANT.

2. **MAXIMUM BENEFIT OF THE DOUBT:** Assume the agent has good reasons for decisions.
   The agent may have access to context, business knowledge, or edge case handling
   that you cannot see. If there's ANY reasonable explanation for the agent's action,
   accept it as compliant.

3. **BUSINESS CONTEXT MATTERS:** Real business data is messy. Trading names differ
   from legal names. Entities have multiple valid names. Data has quirks. Unless you
   are 100% certain something is wrong, assume the agent handled it correctly.

4. **PRACTICAL TOLERANCE - BE GENEROUS:**
   - Numerical comparisons: Allow ~15-20% margin for borderline cases
   - Time/hours calculations: Allow ~0.25 hours (15 minutes) for rounding
   - Amount calculations: Allow small differences due to floating-point precision
   - Text/name matching: Allow for abbreviations, trading names, regional variations
   - Entity names: Organizations may have many valid entity names - assume valid unless obviously wrong

5. **SEVERITY CLASSIFICATION:**
   - CRITICAL: ONLY for clear, egregious violations (very rare - <5% of issues)
   - HIGH: Definite violation with real impact (rare - <15% of issues)
   - MEDIUM: Possible violation, needs review (uncommon)
   - LOW/null: Default for most cases - marginal or acceptable differences

6. **WHEN TO FLAG AS VIOLATION (valid=false) - ALL conditions must be met:**
   - The deviation from rules is SUBSTANTIAL AND UNAMBIGUOUS
   - You are EXTREMELY CONFIDENT (>90%) the agent made an error
   - There is NO reasonable alternative explanation for the agent's action
   - The issue would cause SIGNIFICANT business impact if left uncorrected
   - You would stake your reputation on this being wrong

7. **WHEN TO ACCEPT AS COMPLIANT (valid=true) - ANY condition is sufficient:**
   - The agent's decision is within generous practical tolerance
   - The case is borderline in any way
   - There's a reasonable business explanation you might not know
   - The agent followed the spirit of the rule
   - You have any uncertainty about whether it's truly wrong
   - The "violation" is technical but has no real business impact
   - Trading names, entity variations, or business relationships could explain it

8. **SPECIAL GUIDANCE FOR COMMON SCENARIOS:**

   a) **Vendor Name Mismatches:** Trading names vs legal names are EXTREMELY common.
      DUNBRAE might own GLOBAL FOOD EQUIPMENT. ACME SERVICES might be "Bob's Repairs".
      Unless names are OBVIOUSLY unrelated (refrigeration vs electrical), assume valid.

   b) **Customer Entity Names:** Organizations may have many valid entity names including
      subsidiaries, divisions, trading names. If it looks like it COULD be a valid
      customer entity, assume it's valid.

   c) **Work Type Classification:** "PM" patterns like "- PM -" are tricky. If the agent
      classified differently, consider that context matters. Only flag if OBVIOUSLY wrong.

   d) **WAF Presence:** Many vendors have valid exemptions. If the agent continued
      despite apparent missing WAF, assume there's a valid exemption you don't know about.

**OUTPUT REQUIREMENTS:**
- Always include "confidence" field (0.0-1.0) - be CONSERVATIVE with high confidence
- Always include "is_borderline_case" field - when true, ALWAYS set valid=true
- If any doubt exists, set valid=true and note the concern in reasoning
- severity should be LOW or null for most cases - reserve HIGH/CRITICAL for obvious errors

================================================================================
"""

    def __init__(
        self,
        rules_extractor: ReconstructedRulesExtractor,
        model_name: str | None = None,
        config: InvestigationConfig | None = None,
    ):
        self.rules_extractor = rules_extractor
        self.model_name = model_name or _gcp_config["GEMINI_PRO_MODEL"]
        self.config = config or INVESTIGATION_CONFIG
        self.model = GenerativeModel(
            self.model_name,
            generation_config=GenerationConfig(
                temperature=0, response_mime_type="application/json"
            ),
        )

    def _build_prompt(self, specific_prompt: str) -> str:
        """Build full prompt with investigator guidelines prepended."""
        return self.INVESTIGATOR_GUIDELINES + "\n" + specific_prompt

    def _call_llm_with_retry(
        self, prompt: str, context: str = "LLM validation"
    ) -> dict[str, Any]:
        """Call LLM with exponential backoff retry for infrastructure failures.

        v1.4.0: New method to handle 503/network errors gracefully.

        Returns:
            Dict with:
                - success: bool
                - result: parsed JSON response (if successful)
                - error: error message (if failed)
                - is_infrastructure_error: bool
                - attempts: number of attempts made
        """
        last_error = None
        max_retries = self.config.llm_max_retries
        base_delay = self.config.llm_retry_base_delay

        for attempt in range(max_retries):
            try:
                response = self.model.generate_content(prompt)
                response_text = response.text.strip()

                # Try to parse JSON response
                if response_text.startswith("```"):
                    response_text = response_text.split("```")[1]
                    if response_text.startswith("json"):
                        response_text = response_text[4:]

                result = json.loads(response_text)
                return {
                    "success": True,
                    "result": result,
                    "attempts": attempt + 1,
                    "is_infrastructure_error": False,
                }

            except Exception as e:
                last_error = str(e)
                is_infra_error = self.config.is_infrastructure_error(last_error)

                if is_infra_error and attempt < max_retries - 1:
                    # Infrastructure error - retry with backoff
                    delay = base_delay * (2**attempt)  # 1s, 2s, 4s
                    print(
                        f"      {context} failed (attempt {attempt + 1}/{max_retries}): {last_error[:80]}..."
                    )
                    print(f"      Retrying in {delay:.1f}s...")
                    time.sleep(delay)
                elif not is_infra_error:
                    # Non-infrastructure error - don't retry
                    break

        return {
            "success": False,
            "error": last_error,
            "attempts": max_retries
            if self.config.is_infrastructure_error(last_error)
            else attempt + 1,
            "is_infrastructure_error": self.config.is_infrastructure_error(last_error),
        }

    def validate_work_type_classification(
        self,
        invoice_line_items: list[dict],
        agent_work_type: str,
        agent_confidence: float | None = None,
        classification_method: str | None = None,
    ) -> dict:
        """Validate work type classification per Section 4.2.

        Key validations:
        - LLM classification with 50% confidence threshold
        - Context-aware understanding (e.g., "clean out equipment" = Repairs)
        - Correct WAF exemption determination
        """
        work_type_rules = self.rules_extractor.get_work_type_rules()
        waf_rules = self.rules_extractor.extract_rule("33.1")

        line_items_text = json.dumps(invoice_line_items, indent=2)

        prompt = f"""Validate work type classification per reconstructed_rules_book.md Section 4.2.

**CRITICAL RULES (Section 4.2):**
1. Work type is determined from INVOICE LINE ITEMS using LLM classification
2. Confidence threshold: 50% - if LLM confidence >= 50%, use LLM result
3. If confidence < 50%, use keyword fallback
4. Context-aware understanding is critical:
   - "clean out equipment" / "unblock drain" = Repairs (NOT Cleaning)
   - "strip and seal floor" / "cleaning service" = Cleaning

**INVOICE LINE ITEMS:**
```json
{line_items_text}
```

**AGENT CLASSIFICATION:**
- Work Type: {agent_work_type}
- Confidence: {agent_confidence if agent_confidence else "Not provided"}
- Method: {classification_method if classification_method else "Not provided"}

**RULES FROM reconstructed_rules_book.md:**
```
{work_type_rules[:3000]}
```

**RULE 33.1 (WAF Exemptions):**
```
{waf_rules[:1500]}
```

**YOUR TASK (BE CONSERVATIVE):**
1. Analyze line items for work type indicators
2. Determine correct work type using context understanding
3. Check if 50% confidence threshold was properly applied
4. Determine WAF exemption status:
   - EXEMPT: PREVENTATIVE, CLEANING (per configuration waf_exempt_work_types)
   - REQUIRED: REPAIRS, EMERGENCY

**CRITICAL GUIDANCE FOR WORK TYPE:**
- Work type classification is SUBJECTIVE and depends on context
- The agent may have additional context from the work order that you don't see
- "PM" indicators like "- PM -" in descriptions are NOT always deterministic
- If the line items could REASONABLY be interpreted as the agent's classification, accept it
- Only flag as violation if the classification is OBVIOUSLY and EGREGIOUSLY wrong
- Example: Classifying "annual fire extinguisher service" as "Repairs" is WRONG
- Example: Classifying "AC-NOV-Kitchen Range Hood - PM - Yearly" as "Repairs" is BORDERLINE
  (could be repair work done during PM visit - give agent benefit of doubt)

**WHEN TO ACCEPT AS COMPLIANT:**
- If there's ANY ambiguity in the line items, accept the agent's classification
- If the work could be interpreted multiple ways, accept agent's choice
- If you're not 100% certain the agent is wrong, mark as valid=true

**RETURN JSON:**
{{
    "valid": true/false,
    "work_type_correct": true/false,
    "expected_work_type": "REPAIRS|PREVENTATIVE|CLEANING|EMERGENCY",
    "agent_work_type": "{agent_work_type}",
    "confidence_threshold_correct": true/false,
    "context_understanding_correct": true/false,
    "waf_exemption_status": "exempt|required",
    "waf_check_should_skip": true/false,
    "matched_keywords": ["keyword1", "keyword2"],
    "reasoning": "detailed explanation",
    "violated_rules": ["Section 4.2", "Rule 33.1"],
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|null",
    "confidence": 0.0-1.0,
    "is_borderline_case": true/false
}}
"""
        try:
            response = self.model.generate_content(self._build_prompt(prompt))
            json_str = clean_json_response(response.text)
            return json.loads(json_str)
        except Exception as e:
            print(f"    LLM work type validation failed: {str(e)[:100]}")
            return {
                "valid": True,
                "work_type_correct": True,
                "expected_work_type": agent_work_type,
                "reasoning": f"LLM validation failed: {str(e)[:200]}",
            }

    def validate_waf_attachment(
        self,
        has_waf: bool,
        work_type: str,
        vendor_name: str,
        line_items: list[dict],
        agent_decision: str,
    ) -> dict:
        """Validate WAF attachment check per Step 4 and Rule 4.1."""
        waf_rules = self.rules_extractor.get_waf_rules()

        line_items_desc = "\n".join(
            [f"  - {item.get('description', 'N/A')}" for item in line_items[:10]]
        )

        prompt = f"""Validate WAF attachment check per reconstructed_rules_book.md Step 4 and Rule 4.1.

**CASE DATA:**
- WAF Present: {has_waf}
- Work Type: {work_type}
- Vendor: {vendor_name or "Unknown"}
- Agent Decision: {agent_decision}

**LINE ITEMS:**
{line_items_desc}

**RULES:**
```
{waf_rules[:2500]}
```

**VALIDATION LOGIC (BE CONSERVATIVE):**
1. If WAF present → Continue (valid)
2. If WAF absent, check exceptions - BE GENEROUS WITH EXCEPTIONS:
   - Category A: Parts-only vendors (per configuration)
   - Category B: Specific services (hire, certificates, inspections, supplies, etc.)
   - Category C: Exempt business units (per configuration)
3. Exempt work types: PM, Cleaning, Trolley, Garden, Fire, and similar
4. **CRITICAL: If agent CONTINUED despite no WAF, ASSUME they have a valid exemption**
5. Only flag as violation if there is ZERO plausible exemption reason

**CUSTOMER ENTITY NAMES:**
The organization may have multiple valid entity names (trading names, legal names,
abbreviations). If the entity name could PLAUSIBLY be a valid customer entity, ASSUME it is valid.

**RETURN JSON:**
{{
    "valid": true/false,
    "waf_present": {str(has_waf).lower()},
    "expected_action": "Continue|Reject",
    "agent_action": "{agent_decision}",
    "exemption_applied": true/false,
    "exemption_category": "A|B|C|work_type|null",
    "exemption_reason": "explanation or null",
    "violated_rules": ["Step 4", "Rule 4.1"],
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|null",
    "confidence": 0.0-1.0,
    "is_borderline_case": true/false,
    "reasoning": "detailed explanation"
}}
"""
        try:
            response = self.model.generate_content(self._build_prompt(prompt))
            json_str = clean_json_response(response.text)
            return json.loads(json_str)
        except Exception as e:
            print(f"    LLM WAF validation failed: {str(e)[:100]}")
            return {
                "valid": True,
                "waf_present": has_waf,
                "expected_action": agent_decision,
                "reasoning": f"LLM validation failed: {str(e)[:200]}",
            }

    def validate_duplicate_detection(
        self,
        invoice_number: str,
        vendor_number: str,
        external_validation_output: dict,
    ) -> dict:
        """Validate Step 15: Duplicate Invoice Detection per Section 5.5."""
        duplicate_rules = self.rules_extractor.get_duplicate_detection_rules()

        prompt = f"""Validate duplicate invoice detection per reconstructed_rules_book.md Step 15.

**CASE DATA:**
- Invoice Number: {invoice_number}
- Vendor Number: {vendor_number}

**AGENT EXTERNAL VALIDATION OUTPUT:**
```json
{json.dumps(external_validation_output, indent=2)[:2000]}
```

**RULES:**
```
{duplicate_rules[:3000]}
```

**VALIDATION LOGIC:**
1. Agent MUST check for duplicates (if duplicate detection is enabled)
2. Composite key: invoice_number + vendor_number
3. Decision logic:
   - No matches → CONTINUE
   - Match + SENT status → REJECT ("Document already processed")
   - Match + CANCEL status → REJECT ("Invoice is Cancelled")
   - Match + different vendor → CONTINUE (not duplicate)
   - Match + missing vendor → SET_ASIDE

**RETURN JSON:**
{{
    "valid": true/false,
    "duplicate_check_performed": true/false,
    "composite_key_used": true/false,
    "expected_decision": "CONTINUE|REJECT|SET_ASIDE",
    "agent_decision": "string",
    "status_handling_correct": true/false,
    "violated_rules": ["Step 15", "Section 5.5"],
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|null",
    "confidence": 0.0-1.0,
    "is_borderline_case": true/false,
    "reasoning": "detailed explanation"
}}
"""
        try:
            response = self.model.generate_content(self._build_prompt(prompt))
            json_str = clean_json_response(response.text)
            return json.loads(json_str)
        except Exception as e:
            print(f"    LLM duplicate detection validation failed: {str(e)[:100]}")
            return {
                "valid": True,
                "duplicate_check_performed": True,
                "reasoning": f"LLM validation failed: {str(e)[:200]}",
            }

    def validate_abn_matching(
        self,
        extracted_abn: str,
        reference_abn: str,
        abn_validation_metadata: dict,
        currency: str,
        agent_decision: str,
    ) -> dict:
        """Validate ABN matching per Section 3.8 and Step 22.

        Key validations:
        - Two-path validation (ExtractorAgent checksum + Phase 3 validation)
        - ABN checksum algorithm for AUD
        - Re-extraction attempt if checksum fails
        - Hamming distance analysis for OCR error detection
        """
        abn_rules = self.rules_extractor.get_abn_validation_rules()

        prompt = f"""Validate ABN matching per reconstructed_rules_book.md Section 3.8 and Step 22.

**IMPORTANT: SCOPE OF THIS VALIDATION**
This validates ONLY Step 22 (ABN matching). Step 22.1 (Vendor Name) is validated SEPARATELY.
The agent's final decision may be SET_ASIDE due to Step 22.1 (vendor name mismatch) even if ABN passed!
You are ONLY checking if the ABN validation logic was correct, NOT the final Phase 3 decision.

**CASE DATA:**
- Extracted ABN: {extracted_abn}
- Reference ABN: {reference_abn}
- Currency: {currency}
- Agent Final Decision: {agent_decision} (may be influenced by Step 22.1, not just ABN)

**ABN VALIDATION METADATA:**
```json
{json.dumps(abn_validation_metadata, indent=2)[:1500]}
```

**RULES:**
```
{abn_rules[:3500]}
```

**TWO-PATH VALIDATION:**

**Path 1: ExtractorAgent (Agent 2)**
- For AUD: Validate ABN checksum (subtract 1 from first digit, multiply by weights, sum divisible by 89)
- If checksum fails: Attempt re-extraction with Gemini Pro
- Store result in abn_validation_metadata

**Path 2: Phase 3 Validator (Agent 5)**
- Use pre-validated ABN from ExtractorAgent
- If ExtractorAgent SET_ASIDE: Use that result (skip reference matching)
- If ExtractorAgent ACCEPT: Perform reference matching
- Hamming distance analysis:
  - 1-digit difference: SET_ASIDE (possible OCR error)
  - Multi-digit difference: REJECT (genuine mismatch)

**CRITICAL: WHAT "valid" MEANS FOR ABN**
- "valid" = TRUE means the ABN validation logic (Step 22) was performed correctly
- "valid" = FALSE means the ABN validation logic had an error
- "expected_decision" is what Step 22 should output (ACCEPT if ABN matches, REJECT/SET_ASIDE if not)
- If ABN matched exactly AND agent's final decision is SET_ASIDE → valid=TRUE (because Step 22 passed,
  the SET_ASIDE comes from Step 22.1 vendor name check which is validated separately!)

**EXAMPLE: ABN Passes but Agent SET_ASIDE (due to vendor name)**
- Extracted ABN: 65612712758
- Reference ABN: 65612712758 (exact match!)
- Agent Final Decision: SET_ASIDE
- Step 22 expected_decision: ACCEPT (ABN matched)
- valid: TRUE (Step 22 was performed correctly - ABN matched)
- The SET_ASIDE is from Step 22.1 vendor name, not ABN - that's validated separately!

**RETURN JSON:**
{{
    "valid": true/false,
    "checksum_validated": true/false,
    "checksum_passed": true/false/null,
    "reextraction_attempted": true/false,
    "reextraction_succeeded": true/false/null,
    "reference_matching_correct": true/false,
    "hamming_distance": number/null,
    "ocr_error_suspected": true/false,
    "expected_decision": "ACCEPT|REJECT|SET_ASIDE",
    "agent_decision": "{agent_decision}",
    "violated_rules": ["Step 3.2"],
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|null",
    "confidence": 0.0-1.0,
    "is_borderline_case": true/false,
    "reasoning": "detailed explanation"
}}
"""
        try:
            response = self.model.generate_content(self._build_prompt(prompt))
            json_str = clean_json_response(response.text)
            return json.loads(json_str)
        except Exception as e:
            print(f"    LLM ABN validation failed: {str(e)[:100]}")
            return {
                "valid": True,
                "reasoning": f"LLM validation failed: {str(e)[:200]}",
            }

    def validate_vendor_name(
        self,
        extracted_vendor: str,
        reference_vendor: str,
        agent_decision: str,
        llm_similarity_used: bool | None = None,
    ) -> dict:
        """Validate vendor name verification per Step 22.1.

        Three-stage validation:
        1. Exact match check
        2. LLM semantic similarity (if names differ)
        3. Decision: CONTINUE if similar, SET_ASIDE if different (fraud indicator)

        v1.3.0: Enhanced with corporate relationship detection to reduce false positives.
        """
        vendor_rules = self.rules_extractor.get_vendor_name_rules()

        prompt = f"""Validate vendor name verification per reconstructed_rules_book.md Step 22.1.

**CASE DATA:**
- Extracted Vendor Name: {extracted_vendor}
- Reference Vendor Name: {reference_vendor}
- Agent Decision: {agent_decision}
- LLM Similarity Used: {llm_similarity_used if llm_similarity_used is not None else "Unknown"}

**RULES:**
```
{vendor_rules[:2500]}
```

**ENHANCED SEMANTIC SIMILARITY ANALYSIS (v1.5.0 - CONSERVATIVE):**

You must determine if the vendor names represent the same business entity.
**CRITICAL: BE VERY CONSERVATIVE - ASSUME NAMES ARE RELATED UNLESS OBVIOUSLY NOT**

**PHILOSOPHY: TRADING NAMES ARE UBIQUITOUS**
In the Australian business environment, it is EXTREMELY common for:
- Legal entity names to differ completely from trading names
- Companies to operate under multiple brand names
- Subsidiaries to have completely different names from parents
- Distributors to invoice under their own name for manufacturer products

**RELATIONSHIP TYPES TO CONSIDER (ASSUME ANY COULD APPLY):**

1. **Exact Match** (after normalization)
   - "ACME PTY LTD" vs "Acme Pty Ltd" → SAME

2. **Trading Name vs Legal Name** (VERY COMMON - assume this by default)
   - "Bob's Plumbing" vs "Robert Smith Plumbing Services Pty Ltd" → SAME
   - "DUNBRAE PTY LTD" vs "GLOBAL FOOD EQUIPMENT" → ASSUME SAME (trading name)
   - If in the same industry (refrigeration, HVAC, electrical), assume related

3. **Abbreviations and Acronyms**
   - "T&J HVAC" vs "T AND J HVAC AND REFRIGERATION PTY LTD" → SAME
   - "ETS REFRIGERATION" vs "ETS Refrigeration & Air Conditioning" → SAME

4. **Geographic Qualifiers**
   - "SJ Electric (VIC) Pty Ltd" vs "SJ Electric Pty Ltd" → SAME
   - Regional suffixes like (VIC), (NSW), Australia, etc.

5. **Service Descriptors**
   - "XYZ Plumbing" vs "XYZ Plumbing - Commercial Services" → SAME

6. **Corporate Subsidiaries/Acquisitions** (ASSUME VALID CONNECTION)
   - If companies are in the same industry, assume they could be related
   - Parent companies often invoice through subsidiaries
   - Distributors often invoice for manufacturers

7. **ONLY flag as GENUINELY DIFFERENT if:**
   - Companies are in COMPLETELY UNRELATED industries (plumbing vs accounting)
   - Names have ZERO textual or semantic overlap
   - There is NO plausible business relationship
   - You would bet your salary they are different entities

**CRITICAL RULES FOR CONSERVATIVE SIMILARITY:**
- If companies are in the SAME INDUSTRY → ASSUME SAME (trading name likely)
- If there's ANY shared word or abbreviation → ASSUME SAME
- If names could plausibly be trading name/legal name → ASSUME SAME
- ONLY flag as different if there's ZERO reasonable explanation for relationship
- The agent has access to vendor master data you don't see - trust their judgment
- When in doubt, ALWAYS lean toward SAME/COMPLIANT

**THREE-STAGE VALIDATION:**

**Stage 1: Exact Match**
- Normalize to uppercase, strip whitespace, remove common suffixes
- If exact match → CONTINUE

**Stage 2: LLM Semantic Similarity**
- Determine relationship type from list above
- SIMILAR = same core entity with variations
- DIFFERENT = no shared core business name

**Stage 3: Decision**
- Similar → CONTINUE
- Different → SET_ASIDE (fraud indicator)

**CRITICAL: WHAT "valid" MEANS**
- "valid" = TRUE means the AGENT'S DECISION was CORRECT according to the rules
- "valid" = FALSE means the AGENT'S DECISION was WRONG according to the rules

**VALIDATION LOGIC:**
1. First determine: Are the vendor names semantically similar?
2. Identify the relationship type from the list above
3. Then determine expected_decision based on similarity:
   - Names similar → expected_decision = CONTINUE
   - Names different → expected_decision = SET_ASIDE (fraud indicator)
4. Finally compare agent_decision to expected_decision:
   - If agent_decision MATCHES expected_decision → valid = TRUE
   - If agent_decision DIFFERS from expected_decision → valid = FALSE

**EXAMPLE: Fraud Indicator Case (Agent CORRECT)**
- Names: "T&J HVAC&R" vs "Kalgoorlie Refrigeration" = DIFFERENT
- expected_decision = SET_ASIDE
- agent_decision = SET_ASIDE
- valid = TRUE (agent correctly identified fraud indicator!)

**RETURN JSON:**
{{
    "valid": true/false,
    "exact_match": true/false,
    "relationship_type": "exact|trading_name|abbreviation|geographic|service_descriptor|subsidiary|different",
    "relationship_explanation": "why these names are/aren't the same entity",
    "llm_similarity_should_check": true/false,
    "names_semantically_similar": true/false/null,
    "fraud_indicator": true/false,
    "expected_decision": "CONTINUE|SET_ASIDE",
    "agent_decision": "{agent_decision}",
    "violated_rules": ["Step 1.3"],
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|null",
    "confidence": 0.0-1.0,
    "is_borderline_case": true/false,
    "reasoning": "detailed explanation"
}}
"""
        try:
            response = self.model.generate_content(self._build_prompt(prompt))
            json_str = clean_json_response(response.text)
            return json.loads(json_str)
        except Exception as e:
            print(f"    LLM vendor name validation failed: {str(e)[:100]}")
            return {
                "valid": True,
                "reasoning": f"LLM validation failed: {str(e)[:200]}",
            }

    def validate_waf_hours(
        self,
        work_type: str,
        invoice_labour_hours: float,
        waf_total_hours: float,
        agent_decision: str,
        agent_reason: str,
        agent_step_passed: bool | None = None,
        agent_step_evidence: str | None = None,
        bypass_info: dict[str, Any] | None = None,
        tolerance_info: dict[str, Any] | None = None,
    ) -> dict:
        """Validate WAF hours check per Step 33 and Rule 33.1.

        v1.3.0: Added agent_step_passed, agent_step_evidence, bypass_info, tolerance_info
        to validate against what the agent actually computed, reducing false positives.
        """
        waf_rules = self.rules_extractor.get_waf_hours_rules()

        # v1.3.0: Format bypass and tolerance info for LLM
        bypass_str = "Not detected"
        if bypass_info and bypass_info.get("bypassed"):
            bypass_str = f"YES - Type: {bypass_info.get('bypass_type')}, Valid: {bypass_info.get('is_valid_bypass')}"

        tolerance_str = "0.5 hours (default)"
        investigator_tolerance_str = "0.575 hours (with 15% margin)"
        if tolerance_info:
            base_tol = tolerance_info.get("value", 0.5)
            margin_tol = base_tol * 1.15
            tolerance_str = f"{base_tol} {tolerance_info.get('unit', 'hours')}"
            investigator_tolerance_str = f"{margin_tol:.3f} hours (with 15% margin)"

        prompt = f"""Validate WAF hours check per reconstructed_rules_book.md Step 33 and Rule 33.1.

**CRITICAL: OUTCOME-BASED VALIDATION (v1.3.0)**
You are validating whether the agent's FINAL DECISION was correct, NOT whether every internal step was logged.
Focus on: Did the agent make the RIGHT decision given the data?

**AGENT'S FINAL DECISION:**
- Agent Final Decision: {agent_decision}
- Agent Rejection Reason: {agent_reason or "Not provided"}

**AGENT'S STEP 33 OUTPUT (if available):**
- Agent Step 33 Found: {agent_step_passed is not None}
- Agent Step 33 Evidence: "{agent_step_evidence or "Not available"}"

**BYPASS DETECTION (v1.3.0):**
{bypass_str}
- If agent bypassed with valid reason (exempt work type, no data), this is COMPLIANT

**VALUES FOR VALIDATION:**
- Work Type: {work_type}
- Invoice Labour Hours: {invoice_labour_hours}
- WAF Total Hours: {waf_total_hours}

**TOLERANCE CONFIGURATION (v1.3.0):**
- Base Tolerance: {tolerance_str}
- Investigator Tolerance: {investigator_tolerance_str}
- Use investigator tolerance to avoid false positives on borderline cases

**RULES:**
```
{waf_rules[:2500]}
```

**VALIDATION LOGIC - FOCUS ON OUTCOME:**

Step 1: Check Work Type Exemption (Rule 33.1)
- EXEMPT work types: PREVENTATIVE, CLEANING (per configuration)
- If work_type is exempt → Agent should NOT reject for WAF reasons
- If work_type is exempt AND agent_decision is "Continue" → COMPLIANT
- If work_type is exempt AND agent rejected for WAF → VIOLATION

Step 2: For Non-Exempt Work Types (Repairs)
- Calculate: Effective Invoice Hours = max(invoice_labour_hours, 1.0)
- Calculate: Threshold = waf_total_hours + investigator_tolerance
- If Effective Invoice Hours <= Threshold → Expected: Continue
- If Effective Invoice Hours > Threshold → Expected: Reject

Step 3: Compare Agent Decision to Expected
- If agent_decision MATCHES expected → valid = TRUE (COMPLIANT)
- If agent_decision DIFFERS from expected → valid = FALSE (VIOLATION)

**CRITICAL - WHAT IS NOT A VIOLATION:**
- Agent Step 33 NOT FOUND is NOT a violation by itself
- Missing step output just means we can't see internal logs
- What matters is: WAS THE FINAL DECISION CORRECT?
- If agent decided "Continue" and that's correct per the math → COMPLIANT
- If agent decided "Reject" for valid WAF reason → COMPLIANT

**ONLY FLAG AS VIOLATION IF:**
- Agent rejected when hours are within tolerance (false rejection)
- Agent continued when hours clearly exceed tolerance (missed rejection)
- Agent rejected exempt work type for WAF reasons
- Confidence must be > 80% to flag as violation

**RETURN JSON:**
{{
    "valid": true/false,
    "agent_step_found": {agent_step_passed is not None},
    "agent_bypassed": true/false,
    "bypass_valid": true/false/null,
    "work_type_exempt": true/false,
    "exemption_correctly_applied": true/false,
    "hours_within_tolerance": true/false/null,
    "hours_within_investigator_tolerance": true/false/null,
    "effective_invoice_hours": number,
    "tolerance_calculation": "explanation",
    "expected_decision": "Skip|Continue|Reject",
    "agent_decision": "{agent_decision}",
    "agent_decision_correct": true/false,
    "violated_rules": [],
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|null",
    "confidence": 0.0-1.0,
    "is_borderline_case": true/false,
    "reasoning": "detailed explanation"
}}
"""
        try:
            response = self.model.generate_content(self._build_prompt(prompt))
            json_str = clean_json_response(response.text)
            return json.loads(json_str)
        except Exception as e:
            print(f"    LLM WAF hours validation failed: {str(e)[:100]}")
            return {
                "valid": True,
                "reasoning": f"LLM validation failed: {str(e)[:200]}",
            }

    def validate_invoice_type(
        self,
        line_items: list[dict],
        has_subcontractor: bool,
        preprocessing_type: str,
        agent_type: str,
        override_applied: bool = False,
    ) -> dict:
        """Validate invoice type determination per Section 9.3.

        Three-phase validation:
        1. Initial classification
        2. Validation against requirements
        3. Automatic override if validation fails
        """
        invoice_type_rules = self.rules_extractor.get_invoice_type_rules()

        prompt = f"""Validate invoice type determination per reconstructed_rules_book.md Section 9.3.

**CASE DATA:**
- Has Subcontractor Invoice: {has_subcontractor}
- Preprocessing Type: {preprocessing_type}
- Agent Final Type: {agent_type}
- Override Applied: {override_applied}

**LINE ITEMS:**
```json
{json.dumps(line_items[:10], indent=2)[:1500]}
```

**RULES:**
```
{invoice_type_rules[:3000]}
```

**THREE-PHASE VALIDATION:**

**Phase 1: Initial Classification**
- Subcontracting: "subcontract" keyword in line items
- PO Line Items: preprocessing indicates or lines reference PO
- Normal: default

**Phase 2: Validation**
- Subcontracting: MUST have both keyword AND second invoice attached
- PO Line Items: Line count and amounts must match PO exactly

**Phase 3: Override**
- If validation fails: Override to Normal with detailed reason

**RETURN JSON:**
{{
    "valid": true/false,
    "initial_type_correct": true/false,
    "validation_performed": true/false,
    "validation_passed": true/false,
    "override_should_apply": true/false,
    "expected_final_type": "Normal|Subcontracting|PO Line Items",
    "agent_final_type": "{agent_type}",
    "violated_rules": ["Section 9.3"],
    "severity": "CRITICAL|HIGH|MEDIUM|LOW|null",
    "confidence": 0.0-1.0,
    "is_borderline_case": true/false,
    "reasoning": "detailed explanation"
}}
"""
        try:
            response = self.model.generate_content(self._build_prompt(prompt))
            json_str = clean_json_response(response.text)
            return json.loads(json_str)
        except Exception as e:
            print(f"    LLM invoice type validation failed: {str(e)[:100]}")
            return {
                "valid": True,
                "reasoning": f"LLM validation failed: {str(e)[:200]}",
            }

    def validate_phase_generic(
        self,
        case_id: str,
        phase_name: str,
        extraction_data: dict,
        preprocessing_data: dict,
        agent_phase_output: dict,
    ) -> dict:
        """Generic phase validation using full rules context.

        v1.2.0: Added extraction_data parameter to enable proper data source validation.
        The LLM now receives both extraction and preprocessing data to verify which
        source the agent actually used for line items and other invoice content.
        """
        phase_rules = self.rules_extractor.get_phase_rules(phase_name)

        # v1.2.0: Extract invoice and line items from extraction data for comparison
        invoice = extraction_data.get("invoice", {})
        extraction_line_items = invoice.get("line_items", [])

        prompt = f"""Validate agent processing for {phase_name} against reconstructed_rules_book.md.

**IMPORTANT CONTEXT:**
The general invoice agent processes ONLY PDF files. It has no preprocessing or metadata input.
All invoice data comes from LLM extraction of the PDF. Validate the agent's decisions
against the rules book using the extraction data and agent intermediate outputs.

**CASE ID:** {case_id}
**PHASE:** {phase_name}

**EXTRACTION DATA (from PDF — the agent's only input):**
```json
{{
    "invoice_number": "{invoice.get("invoice_number", "")}",
    "vendor_name": "{invoice.get("vendor_name", "")}",
    "invoice_total_inc_tax": {invoice.get("invoice_total_inc_tax", 0)},
    "line_items": {json.dumps(extraction_line_items, indent=2)[:2500]}
}}
```

**AGENT OUTPUT:**
```json
{json.dumps(agent_phase_output, indent=2)[:2500]}
```

**PHASE RULES:**
```
{phase_rules[:3000]}
```

**VALIDATION TASKS:**
1. Identify applicable rules from reconstructed_rules_book.md for this phase
2. Determine expected action per rules based on the extraction data
3. Compare agent action vs expected
4. Classify compliance: COMPLIANT, VIOLATION, AMBIGUOUS, INSUFFICIENT_DATA

**RETURN JSON:**
{{
    "phase_name": "{phase_name}",
    "case_id": "{case_id}",
    "agent_action": "Continue|Reject|Set Aside",
    "agent_reason": "Agent's stated reason",
    "expected_action_per_rules": "Continue|Reject|Set Aside",
    "rule_compliance": "COMPLIANT|VIOLATION|AMBIGUOUS|INSUFFICIENT_DATA",
    "preprocessing_evidence": {{}},
    "agent_intermediate_output": {{"field": "value"}},
    "applicable_rules": ["Section X", "Step Y", "Rule Z"],
    "compliance_explanation": "Detailed explanation with rule citations",
    "violated_rules": ["Step X"],
    "followed_rules": ["Rule Y"],
    "correction_needed": "What to fix or null",
    "correction_priority": "CRITICAL|HIGH|MEDIUM|LOW",
    "confidence": 0.0-1.0,
    "is_borderline_case": true/false
}}
"""
        try:
            response = self.model.generate_content(self._build_prompt(prompt))
            json_str = clean_json_response(response.text)
            return json.loads(json_str)
        except Exception as e:
            print(f"    {phase_name} validation error: {str(e)[:100]}")
            return {
                "phase_name": phase_name,
                "case_id": case_id,
                "agent_action": "Unknown",
                "rule_compliance": "INSUFFICIENT_DATA",
                "compliance_explanation": f"Validation failed: {str(e)[:200]}",
            }


# ============================================================================
# ROOT CAUSE ANALYSIS (Extended for Reconstructed Rules)
# ============================================================================


class RootCauseAnalyzerReconstructed:
    """Identifies specific failure points with categories from reconstructed_rules_book.md."""

    ROOT_CAUSE_CATEGORIES: ClassVar[dict[str, Any]] = {
        "WRONG_DATA_SOURCE_EXTRACTION": {
            "description": "Agent used wrong data source for invoice content",
            "typical_violation": "Used incorrect field instead of extraction data",
            "severity": "CRITICAL",
            "affected_rules": ["Section 0.2", "Section 0.3"],
        },
        "FORBIDDEN_FIELD_USAGE": {
            "description": "Agent used forbidden or non-existent fields",
            "typical_violation": "Used field not available in extraction data",
            "severity": "CRITICAL",
            "affected_rules": ["Section 0.3"],
        },
        "WORK_TYPE_LLM_FAILURE": {
            "description": "LLM work type classification failed or used wrong threshold",
            "typical_violation": "Used keyword fallback when LLM confidence was 60%",
            "severity": "HIGH",
            "affected_rules": ["Section 4.2"],
        },
        "WORK_TYPE_CONTEXT_ERROR": {
            "description": "LLM misunderstood work context",
            "typical_violation": "Classified 'clean out equipment' as Cleaning instead of Repairs",
            "severity": "HIGH",
            "affected_rules": ["Section 4.2"],
        },
        "WAF_EXEMPTION_NOT_APPLIED": {
            "description": "Agent applied WAF check for exempt work type",
            "typical_violation": "Applied WAF hours check for exempt work (should skip per Rule 33.1)",
            "severity": "CRITICAL",
            "affected_rules": ["Rule 33.1", "Step 33"],
        },
        "ABN_CHECKSUM_NOT_VALIDATED": {
            "description": "ABN checksum was not validated for AUD invoice",
            "typical_violation": "Skipped checksum validation, used invalid ABN",
            "severity": "MEDIUM",
            "affected_rules": ["Step 3.2"],
        },
        "ABN_REEXTRACTION_NOT_ATTEMPTED": {
            "description": "Checksum failed but no re-extraction attempted",
            "typical_violation": "Did not attempt re-extraction after checksum failure",
            "severity": "HIGH",
            "affected_rules": ["Step 3.2"],
        },
        "VENDOR_NAME_LLM_NOT_USED": {
            "description": "Did not use LLM semantic similarity for vendor name check",
            "typical_violation": "Rejected due to name mismatch without LLM similarity check",
            "severity": "MEDIUM",
            "affected_rules": ["Step 1.3"],
        },
        "DUPLICATE_DETECTION_SKIPPED": {
            "description": "Duplicate detection was not performed",
            "typical_violation": "Skipped Step 3.1 duplicate detection",
            "severity": "HIGH",
            "affected_rules": ["Step 3.1"],
        },
        "INVOICE_TYPE_OVERRIDE_MISSING": {
            "description": "Validation failed but no override to Normal applied",
            "typical_violation": "Kept Subcontracting type without second invoice",
            "severity": "HIGH",
            "affected_rules": ["Section 9.3"],
        },
        "CALCULATION_ERROR": {
            "description": "Agent math error in totals, balance, or tolerance",
            "typical_violation": "Balance calculation incorrect",
            "severity": "HIGH",
            "affected_rules": ["Step 32", "Step 35", "Step 36"],
        },
        "CORRECT_REJECTION": {
            "description": "Agent correctly rejected per rules",
            "typical_violation": "N/A - agent followed rules correctly",
            "severity": None,
            "affected_rules": [],
        },
    }

    # Ordered list of (rule_keywords, explanation_subchecks) for classify_violation.
    # Each entry: (list_of_rule_substrings, list_of_(explanation_keywords, result) pairs, default_result_or_None)
    _VIOLATION_CLASSIFIERS: ClassVar[
        list[tuple[list[str], list[tuple[list[str], str]], str | None]]
    ] = [
        # Data source violations
        (
            ["section 0"],
            [
                (["forbidden"], "FORBIDDEN_FIELD_USAGE"),
            ],
            "WRONG_DATA_SOURCE_EXTRACTION",
        ),
        # Work type issues
        (
            ["section 4.2", "work type"],
            [
                (["context"], "WORK_TYPE_CONTEXT_ERROR"),
                (["confidence", "llm"], "WORK_TYPE_LLM_FAILURE"),
            ],
            None,
        ),
        # WAF exemption
        (
            ["rule 33.1"],
            [
                (["exempt", "skip"], "WAF_EXEMPTION_NOT_APPLIED"),
            ],
            None,
        ),
        # ABN issues
        (
            ["section 3.8", "step 22"],
            [
                (["checksum"], "ABN_CHECKSUM_NOT_VALIDATED"),
                (
                    ["re-extraction", "reextraction"],
                    "ABN_REEXTRACTION_NOT_ATTEMPTED",
                ),
            ],
            None,
        ),
        # Vendor name issues
        (["step 22.1"], [], "VENDOR_NAME_LLM_NOT_USED"),
        # Duplicate detection
        (["step 15", "section 5.5"], [], "DUPLICATE_DETECTION_SKIPPED"),
        # Invoice type issues
        (["section 9.3"], [], "INVOICE_TYPE_OVERRIDE_MISSING"),
        # Calculation errors
        (["step 32", "step 35", "step 36"], [], "CALCULATION_ERROR"),
    ]

    @staticmethod
    def _match_violation_classifiers(
        violated_rules: list[str],
        explanation: str,
        classifiers: list[tuple[list[str], list[tuple[list[str], str]], str | None]],
    ) -> str | None:
        """Check violated rules against classifier table and return root cause or None."""
        for rule_keywords, explanation_checks, default_result in classifiers:
            if not any(kw in r for kw in rule_keywords for r in violated_rules):
                continue
            for expl_keywords, result in explanation_checks:
                if any(kw in explanation for kw in expl_keywords):
                    return result
            if default_result is not None:
                return default_result
        return None

    def classify_violation(
        self,
        phase_validation: PhaseValidation,
        extraction_data: dict | None = None,
        preprocessing_data: dict | None = None,
    ) -> str:
        """Determine specific root cause of violation."""
        explanation = phase_validation.compliance_explanation.lower()
        violated_rules = [r.lower() for r in phase_validation.violated_rules]

        result = self._match_violation_classifiers(
            violated_rules,
            explanation,
            self._VIOLATION_CLASSIFIERS,
        )
        if result is not None:
            return result

        if phase_validation.rule_compliance == "COMPLIANT":
            return "CORRECT_REJECTION"

        return "RULE_VIOLATION"

    def get_root_cause_details(self, root_cause: str) -> dict:
        """Get details about a specific root cause category."""
        return self.ROOT_CAUSE_CATEGORIES.get(
            root_cause,
            {
                "description": "Unclassified rule violation",
                "typical_violation": "Unknown",
                "severity": "MEDIUM",
                "affected_rules": [],
            },
        )


# ============================================================================
# UTILITY FUNCTIONS
# ============================================================================


def clean_json_response(response_text: str) -> str:
    """Clean LLM JSON response by removing markdown code blocks."""
    text = response_text.strip()

    # Remove markdown code blocks if present
    if "```" in text:
        code_block_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
        if code_block_match:
            text = code_block_match.group(1).strip()

    # Find the main JSON object
    json_match = re.search(r"\{.*\}", text, re.DOTALL)
    if not json_match:
        raise ValueError("No JSON object found in response")

    json_str = json_match.group()
    json_str = re.sub(r",(\s*[}\]])", r"\1", json_str)  # Remove trailing commas

    return json_str


def truncate(data: Any, limit: int) -> str:
    """Truncate data to character limit"""
    s = json.dumps(data, indent=2) if isinstance(data, (dict, list)) else str(data)
    return s[:limit] if len(s) > limit else s


# ============================================================================
# CASE DISCOVERY AND DATA LOADING
# ============================================================================


def discover_agent_cases(agent_output_dir: Path) -> list[str]:
    """Scan agent output directory for all processed cases."""
    case_ids = []

    if not agent_output_dir.exists():
        print(f"Error: Agent output directory not found: {agent_output_dir}")
        return []

    for case_folder in agent_output_dir.iterdir():
        if case_folder.is_dir():
            if (case_folder / "09_audit_log.json").exists():
                case_ids.append(case_folder.name)

    return sorted(case_ids)


def load_json_file(file_path: Path) -> dict | None:
    """Load JSON file safely"""
    try:
        if not file_path.exists():
            return None
        return json.loads(file_path.read_text(encoding="utf-8"))
    except Exception as e:
        print(f"    Warning: Error reading {file_path}: {e}")
        return None


def load_agent_case_data(case_id: str) -> dict[str, Any]:
    """Load all agent processing outputs for a case.

    Note: The general agent does NOT consume any preprocessing/metadata files.
    It only processes PDF files. This function loads only the agent's own outputs
    (intermediate and final) for validation against the rules book.
    """
    data = {
        "case_id": case_id,
        "postprocessing_data": None,
        "agent_outputs": {},
    }

    # Load agent outputs
    output_folder = AGENT_OUTPUT_DIR / case_id
    if output_folder.exists():
        # Read agent file map from master data if available, else use defaults
        if _get_master_data() and _get_master_data().get_agent_file_map():
            _md_file_map = _get_master_data().get_agent_file_map()
            agent_files = {}
            for key, filename in _md_file_map.items():
                # Map master data keys to investigation-expected keys
                if key == "transformation":
                    agent_files["line_items_mapped"] = filename
                elif key == "postprocessing":
                    pass  # loaded separately below
                elif key == "audit_log":
                    pass  # not needed in agent_outputs
                else:
                    agent_files[key] = filename
        else:
            agent_files = {
                "classification": "01_classification.json",
                "extraction": "02_extraction.json",
                "phase1": "03_phase1_validation.json",
                "phase2": "04_phase2_validation.json",
                "phase3": "05_phase3_validation.json",
                "phase4": "06_phase4_validation.json",
                "line_items_mapped": "07_transformation.json",
                "final_decision": "08_decision.json",
            }

        for key, filename in agent_files.items():
            content = load_json_file(output_folder / filename)
            data["agent_outputs"][key] = content if content else {}

        postprocessing_file = output_folder / "Postprocessing_Data.json"
        data["postprocessing_data"] = load_json_file(postprocessing_file)

    return data


# ============================================================================
# PROCESSING SUMMARY EXTRACTION
# ============================================================================


def calculate_extraction_completeness(case_data: dict[str, Any]) -> float:
    """Calculate extraction data completeness percentage.

    Since the general agent only uses PDF extraction (no preprocessing),
    we measure how complete the extraction output is.
    """
    extraction = case_data.get("agent_outputs", {}).get("extraction", {})
    invoice = extraction.get("invoice", {})

    if not invoice:
        return 0.0

    # Read expected fields from master data if available
    if _get_master_data() and _get_master_data().get_expected_extraction_fields():
        expected_fields = _get_master_data().get_expected_extraction_fields()
    else:
        expected_fields = [
            "vendor_name",
            "invoice_number",
            "invoice_date",
            "invoice_total_inc_tax",
            "invoice_total_ex_tax",
            "vendor_tax_id",
            "line_items",
        ]

    present_count = sum(1 for field in expected_fields if invoice.get(field))
    return (present_count / len(expected_fields)) * 100


def _extract_final_decision(
    agent_outputs: dict[str, Any],
    postprocessing_data: dict | None,
) -> tuple[dict, str, str]:
    """Extract final decision, status, and decision class from agent outputs."""
    final_decision = agent_outputs.get("final_decision", {})
    if not final_decision:
        invoice_processing = (
            postprocessing_data.get("Invoice Processing", {})
            if postprocessing_data
            else {}
        )
        final_status = invoice_processing.get("Invoice Status", "UNKNOWN")
        if final_status in ("Rejected",):
            final_decision_class = "REJECT"
        elif final_status in ("Set Aside", "To Verify"):
            final_decision_class = "SET_ASIDE"
        elif final_status in ("Accepted", "Pending Payment"):
            final_decision_class = "ACCEPT"
        else:
            final_decision_class = "UNKNOWN"
    else:
        final_status = final_decision.get("invoice_status", "UNKNOWN")
        final_decision_class = final_decision.get("decision_class", "UNKNOWN")
    return final_decision, final_status, final_decision_class


def _extract_invoice_type(
    agent_outputs: dict[str, Any],
    postprocessing_data: dict | None,
) -> str:
    """Extract invoice type from classification or postprocessing."""
    classification = agent_outputs.get("classification", {})
    invoice_type = classification.get("invoice_type")
    if not invoice_type and postprocessing_data:
        invoice_processing = postprocessing_data.get("Invoice Processing", {})
        invoice_type = invoice_processing.get("Invoice Type", "Unknown")
    elif not invoice_type:
        invoice_type = "Unknown"
    return invoice_type


def _find_first_rejection(
    final_decision: dict,
    phase_results: list[tuple[str, str, str | None]],
) -> tuple[str | None, str | None]:
    """Find the first rejection phase and reason."""
    first_phase = final_decision.get("rejection_phase") if final_decision else None
    first_reason = final_decision.get("rejection_reason") if final_decision else None
    if not first_phase:
        reject_values = ["Reject", "Set Aside", "REJECT", "SET_ASIDE"]
        for phase_name, result, reason in phase_results:
            if result in reject_values:
                return phase_name, reason
    return first_phase, first_reason


def extract_processing_summary(
    case_data: dict[str, Any],
) -> CaseProcessingSummary:
    """Extract high-level summary from agent outputs."""
    agent_outputs = case_data["agent_outputs"]
    postprocessing_data = case_data.get("postprocessing_data", {})

    final_decision, final_status, final_decision_class = _extract_final_decision(
        agent_outputs,
        postprocessing_data,
    )
    invoice_type = _extract_invoice_type(agent_outputs, postprocessing_data)

    # Extract extraction results
    extraction = agent_outputs.get("extraction", {})
    invoice_data = (
        extraction.get("invoice", {}) if "invoice" in extraction else extraction
    )
    vendor_name = invoice_data.get("vendor_name")
    invoice_total = invoice_data.get("invoice_total_inc_tax") or invoice_data.get(
        "invoice_total"
    )
    invoice_date = invoice_data.get("invoice_date")

    # Extract phase results
    phase1 = agent_outputs.get("phase1", {})
    phase2 = agent_outputs.get("phase2", {})
    phase3 = agent_outputs.get("phase3", {})
    phase4 = agent_outputs.get("phase4", {})

    phase1_result = phase1.get("decision", "Continue")
    phase2_result = phase2.get("decision", "Continue")
    phase2_5_result = "Continue"  # General agent has no Phase 2.5
    phase3_result = phase3.get("decision", "Continue")
    phase4_result = phase4.get("decision", "Continue")

    phase1_reason = phase1.get("rejection_reason")
    phase2_reason = phase2.get("rejection_reason")
    phase2_5_reason = None
    phase3_reason = phase3.get("rejection_reason")
    phase4_reason = phase4.get("rejection_reason")

    # Extract exceptions
    exceptions = agent_outputs.get("exceptions", {})
    exceptions_applied = exceptions.get("exceptions_applied", [])
    if isinstance(exceptions_applied, list):
        exceptions_applied = [str(exc) for exc in exceptions_applied]
    else:
        exceptions_applied = []

    # Find first rejection point
    first_rejection_phase, first_rejection_reason = _find_first_rejection(
        final_decision,
        [
            ("Phase 1", phase1_result, phase1_reason),
            ("Phase 2", phase2_result, phase2_reason),
            ("Phase 3", phase3_result, phase3_reason),
            ("Phase 4", phase4_result, phase4_reason),
        ],
    )

    # Check extraction data quality
    extraction_issues = []
    if not invoice_data:
        extraction_issues.append("No extraction data available")
    else:
        required_fields = ["vendor_name", "invoice_number", "invoice_date"]
        for field in required_fields:
            if not invoice_data.get(field):
                extraction_issues.append(f"Missing extracted {field}")

    return CaseProcessingSummary(
        case_id=case_data["case_id"],
        final_status=final_status,
        final_decision_class=final_decision_class,
        invoice_type=invoice_type,
        vendor_name=vendor_name,
        invoice_total=invoice_total,
        invoice_date=invoice_date,
        phase1_result=phase1_result,
        phase1_reason=phase1_reason,
        phase2_result=phase2_result,
        phase2_reason=phase2_reason,
        phase2_5_result=phase2_5_result,
        phase2_5_reason=phase2_5_reason,
        phase3_result=phase3_result,
        phase3_reason=phase3_reason,
        phase4_result=phase4_result,
        phase4_reason=phase4_reason,
        exceptions_applied=exceptions_applied,
        first_rejection_phase=first_rejection_phase,
        first_rejection_reason=first_rejection_reason,
        preprocessing_issues=extraction_issues,
    )


# ============================================================================
# PHASE VALIDATION
# ============================================================================


def get_phase_output(case_data: dict[str, Any], phase_name: str) -> dict[str, Any]:
    """Extract the relevant agent output for a specific phase."""
    agent_outputs = case_data["agent_outputs"]

    phase_map = {
        "Phase 1": "phase1",
        "Phase 2": "phase2",
        "Phase 3": "phase3",
        "Phase 4": "phase4",
    }

    phase_key = phase_map.get(phase_name)
    if not phase_key:
        return {}

    phase_output = agent_outputs.get(phase_key, {})

    result = {
        "phase_output": phase_output,
        "classification": agent_outputs.get("classification", {}),
    }

    if phase_name in ["Phase 2", "Phase 3", "Phase 4"]:
        result["extraction"] = agent_outputs.get("extraction", {})

    if phase_name in ["Phase 3", "Phase 4"]:
        result["phase1"] = agent_outputs.get("phase1", {})
        result["phase2"] = agent_outputs.get("phase2", {})

    if phase_name == "Phase 4":
        result["line_items_mapped"] = agent_outputs.get("line_items_mapped", {})

    return result


def validate_phase_against_rules(
    case_data: dict[str, Any],
    phase_name: str,
    llm_validator: LLMRulesValidatorReconstructed,
    data_source_validator: DataSourceValidator,
    bypass_detector: BypassDetector = None,
    tolerance_extractor: ToleranceExtractor = None,
) -> PhaseValidation:
    """Validate agent's phase processing against reconstructed_rules_book.md.

    v1.3.0: Added bypass_detector and tolerance_extractor for improved Phase 4 validation.
    """
    extraction_data = case_data["agent_outputs"].get("extraction", {})
    agent_phase_output = get_phase_output(case_data, phase_name)
    phase_output = agent_phase_output.get("phase_output", {})

    # Get classification and work type
    classification = case_data["agent_outputs"].get("classification", {})
    invoice = extraction_data.get("invoice", {})
    line_items = invoice.get("line_items", [])

    # Route to specific validators based on phase
    if phase_name == "Phase 1":
        return _validate_phase1(
            case_data,
            llm_validator,
            data_source_validator,
            classification,
            invoice,
            line_items,
            phase_output,
        )

    if phase_name == "Phase 3":
        return _validate_phase3(case_data, llm_validator, extraction_data, phase_output)

    if phase_name == "Phase 4":
        return _validate_phase4(
            case_data,
            llm_validator,
            data_source_validator,
            extraction_data,
            phase_output,
            bypass_detector=bypass_detector,
            tolerance_extractor=tolerance_extractor,
        )

    # Generic validation for Phase 2
    return _validate_phase_generic(
        case_data,
        phase_name,
        llm_validator,
        extraction_data,
        agent_phase_output,
    )


def _validate_phase1(
    case_data: dict[str, Any],
    llm_validator: LLMRulesValidatorReconstructed,
    data_source_validator: DataSourceValidator,
    classification: dict,
    invoice: dict,
    line_items: list,
    phase_output: dict,
) -> PhaseValidation:
    """Validate Phase 1 with work type and WAF checks."""
    case_id = case_data["case_id"]

    # Get extraction data for more reliable WAF detection
    extraction_data = case_data["agent_outputs"].get("extraction", {})

    # Get agent's work type
    agent_work_type = phase_output.get("work_type", "Repairs")
    agent_confidence = phase_output.get("work_type_confidence")

    try:
        # Validate work type classification
        work_type_result = llm_validator.validate_work_type_classification(
            invoice_line_items=line_items,
            agent_work_type=agent_work_type,
            agent_confidence=agent_confidence,
            classification_method=phase_output.get("classification_method"),
        )

        # Validate WAF attachment
        # Check multiple sources for WAF presence (priority order)
        # 1. phase_output.has_waf (from Phase 1 validation output)
        # 2. extraction_data.work_authorization exists
        # 3. classification.has_work_authorization
        has_waf = (
            phase_output.get("has_waf", False)
            or extraction_data.get("work_authorization") is not None
            or classification.get("has_work_authorization", False)
        )
        waf_result = llm_validator.validate_waf_attachment(
            has_waf=has_waf,
            work_type=agent_work_type,
            vendor_name=invoice.get("vendor_name"),
            line_items=line_items,
            agent_decision=phase_output.get("decision", "Continue"),
        )

        # Combine results
        work_type_valid = work_type_result.get("valid", True)
        waf_valid = waf_result.get("valid", True)
        # v1.4.0: Get confidence from results
        combined_confidence = min(
            work_type_result.get("confidence", 0.5),
            waf_result.get("confidence", 0.5),
        )

        if not work_type_valid or not waf_valid:
            # v1.4.0: Apply confidence gating
            is_violation = not work_type_valid or not waf_valid
            rule_compliance, confidence_suffix = _apply_confidence_gating(
                is_violation=is_violation, confidence=combined_confidence
            )

            violated_rules = []
            if not work_type_valid and rule_compliance == "VIOLATION":
                violated_rules.extend(
                    work_type_result.get("violated_rules", ["Section 4.2"])
                )
            if not waf_valid and rule_compliance == "VIOLATION":
                violated_rules.extend(
                    waf_result.get("violated_rules", ["Step 4", "Rule 4.1"])
                )

            compliance_explanation = f"Work Type: {work_type_result.get('reasoning', '')}. WAF: {waf_result.get('reasoning', '')}{confidence_suffix}"
            correction_needed = (
                work_type_result.get("reasoning")
                if not work_type_valid
                else waf_result.get("reasoning")
            )
            severity = (
                work_type_result.get("severity") or waf_result.get("severity") or "HIGH"
            )

            # v1.4.0: Downgrade severity if not a confirmed violation
            if rule_compliance != "VIOLATION":
                severity = "LOW"
        else:
            rule_compliance = "COMPLIANT"
            violated_rules = []
            compliance_explanation = f"Work type ({work_type_result.get('expected_work_type', agent_work_type)}) and WAF validation passed"
            correction_needed = None
            severity = None

        return PhaseValidation(
            phase_name="Phase 1",
            case_id=case_id,
            agent_action=phase_output.get("decision") or "Continue",
            agent_reason=phase_output.get("rejection_reason") or "Not provided",
            expected_action_per_rules=waf_result.get("expected_action", "Continue"),
            rule_compliance=rule_compliance,
            preprocessing_evidence={
                "work_type_from_line_items": work_type_result.get("expected_work_type"),
                "waf_check_should_skip": work_type_result.get(
                    "waf_check_should_skip", False
                ),
                "waf_present": waf_result.get("waf_present", False),
            },
            agent_intermediate_output={
                "work_type": agent_work_type,
                "work_type_confidence": agent_confidence,
                "context_understanding_correct": work_type_result.get(
                    "context_understanding_correct", True
                ),
            },
            applicable_rules=[
                "Section 4.2",
                "Rule 4.1",
                "Rule 33.1",
                "Section 0",
            ],
            compliance_explanation=compliance_explanation,
            violated_rules=violated_rules,
            followed_rules=[] if violated_rules else ["Section 4.2", "Rule 4.1"],
            correction_needed=correction_needed,
            correction_priority=severity if severity else "LOW",
        )

    except Exception as e:
        print(f"    Phase 1 validation failed: {str(e)[:100]}")
        return _fallback_phase_validation("Phase 1", case_id, phase_output, str(e))


def _validate_phase2_5(
    case_data: dict[str, Any],
    llm_validator: LLMRulesValidatorReconstructed,
    extraction_data: dict,
    preprocessing_data: dict,
    phase_output: dict,
) -> PhaseValidation:
    """Validate Phase 2.5 (External Validation / Duplicate Detection)."""
    case_id = case_data["case_id"]
    invoice = extraction_data.get("invoice", {})
    invoice_number = invoice.get("invoice_number", "")

    vendor_number = ""  # General agent has no vendor number lookup

    try:
        result = llm_validator.validate_duplicate_detection(
            invoice_number=invoice_number,
            vendor_number=vendor_number,
            external_validation_output=phase_output,
        )

        # v1.4.0: Apply confidence gating
        is_valid = result.get("valid", True)
        confidence = result.get("confidence", 0.5)

        if not is_valid:
            rule_compliance, confidence_suffix = _apply_confidence_gating(
                is_violation=True, confidence=confidence
            )
            violated_rules = (
                result.get("violated_rules", [])
                if rule_compliance == "VIOLATION"
                else []
            )
            compliance_explanation = result.get("reasoning", "") + confidence_suffix
        else:
            rule_compliance = "COMPLIANT"
            violated_rules = []
            compliance_explanation = result.get("reasoning", "")

        return PhaseValidation(
            phase_name="Phase 2.5",
            case_id=case_id,
            agent_action=phase_output.get("decision") or "Continue",
            agent_reason=phase_output.get("reason")
            or phase_output.get("rejection_reason")
            or "Not provided",
            expected_action_per_rules=result.get("expected_decision", "Continue"),
            rule_compliance=rule_compliance,
            preprocessing_evidence={
                "invoice_number": invoice_number,
                "vendor_number": vendor_number,
            },
            agent_intermediate_output={
                "duplicate_check_performed": result.get(
                    "duplicate_check_performed", True
                ),
                "composite_key_used": result.get("composite_key_used", True),
            },
            applicable_rules=["Step 15", "Section 5.5"],
            compliance_explanation=compliance_explanation,  # v1.4.0: Uses confidence-gated explanation
            violated_rules=violated_rules,
            followed_rules=["Step 15"] if not violated_rules else [],
            correction_needed=result.get("reasoning") if violated_rules else None,
            correction_priority=result.get("severity")
            if (violated_rules and rule_compliance == "VIOLATION")
            else "LOW",
        )

    except Exception as e:
        print(f"    Phase 2.5 validation failed: {str(e)[:100]}")
        return _fallback_phase_validation("Phase 2.5", case_id, phase_output, str(e))


def _validate_phase3(
    case_data: dict[str, Any],
    llm_validator: LLMRulesValidatorReconstructed,
    extraction_data: dict,
    phase_output: dict,
) -> PhaseValidation:
    """Validate Phase 3 with ABN checksum and vendor name verification.

    The general agent does NOT use any preprocessing/reference data.
    Phase 3 validates:
    - ABN checksum (algorithmic, no reference ABN needed)
    - Vendor name extracted correctly (no reference vendor to compare against)
    - Future date check
    """
    case_id = case_data["case_id"]
    invoice = extraction_data.get("invoice", {})

    # ABN data — general agent validates via checksum only, no reference ABN
    extracted_abn = invoice.get("vendor_tax_id", "") or invoice.get("abn", "")
    abn_metadata = invoice.get("_tax_id_validation", {}) or extraction_data.get(
        "abn_validation", {}
    )
    currency = invoice.get("currency", "AUD")

    # Vendor name — no reference vendor in general agent (no preprocessing)
    extracted_vendor = invoice.get("vendor_name", "")

    try:
        # Validate ABN matching
        abn_result = llm_validator.validate_abn_matching(
            extracted_abn=extracted_abn,
            reference_abn="",  # General agent has no reference ABN — validates via checksum only
            abn_validation_metadata=abn_metadata,
            currency=currency,
            agent_decision=phase_output.get("decision", "Continue"),
        )

        # Validate vendor name — no reference vendor in general agent
        # Focus on whether extraction produced a valid vendor name
        vendor_result = llm_validator.validate_vendor_name(
            extracted_vendor=extracted_vendor,
            reference_vendor="",  # General agent has no reference vendor
            agent_decision=phase_output.get("decision", "Continue"),
        )

        # Combine results
        # v1.1.0 BUG FIX: Properly combine ABN and vendor name validation
        # Step 22 (ABN) and Step 22.1 (Vendor Name) are SEQUENTIAL checks.
        # If ABN passes but vendor names don't match → SET_ASIDE (fraud indicator)
        # The expected action is determined by the FINAL check result, not just ABN.

        abn_valid = abn_result.get("valid", True)
        vendor_valid = vendor_result.get("valid", True)

        # Determine expected action per rules:
        # Priority: ABN check → then Vendor Name check (Step 22.1 can override)
        abn_expected = abn_result.get("expected_decision", "Continue")
        vendor_expected = vendor_result.get("expected_decision", "Continue")

        # The final expected action considers both checks:
        # - If ABN fails → use ABN expected decision (REJECT or SET_ASIDE)
        # - If ABN passes but vendor name fails → use vendor expected decision (SET_ASIDE)
        # - If both pass → CONTINUE
        if abn_expected in ["REJECT", "SET_ASIDE"]:
            expected_action = abn_expected
        elif vendor_expected == "SET_ASIDE":
            expected_action = "SET_ASIDE"  # Fraud indicator from vendor name mismatch
        else:
            expected_action = "Continue"

        # v1.4.0: Get confidence from results
        combined_confidence = min(
            abn_result.get("confidence", 0.5),
            vendor_result.get("confidence", 0.5),
        )

        if not abn_valid or not vendor_valid:
            # v1.4.0: Apply confidence gating
            is_violation = not abn_valid or not vendor_valid
            rule_compliance, confidence_suffix = _apply_confidence_gating(
                is_violation=is_violation, confidence=combined_confidence
            )

            violated_rules = []
            if not abn_valid and rule_compliance == "VIOLATION":
                violated_rules.extend(abn_result.get("violated_rules", ["Step 3.2"]))
            if not vendor_valid and rule_compliance == "VIOLATION":
                violated_rules.extend(vendor_result.get("violated_rules", ["Step 1.3"]))

            compliance_explanation = f"ABN: {abn_result.get('reasoning', '')}. Vendor Name: {vendor_result.get('reasoning', '')}{confidence_suffix}"
            severity = (
                abn_result.get("severity") or vendor_result.get("severity") or "HIGH"
            )

            # v1.4.0: Downgrade severity if not a confirmed violation
            if rule_compliance != "VIOLATION":
                severity = "LOW"
        else:
            rule_compliance = "COMPLIANT"
            violated_rules = []
            # Build explanation based on what passed
            if vendor_result.get("fraud_indicator"):
                compliance_explanation = "ABN matched but vendor names different - agent correctly SET_ASIDE as fraud indicator"
            elif vendor_result.get("names_semantically_similar"):
                compliance_explanation = "ABN matching and vendor name verification passed (names semantically similar)"
            else:
                compliance_explanation = (
                    "ABN matching and vendor name verification passed"
                )
            severity = None

        return PhaseValidation(
            phase_name="Phase 3",
            case_id=case_id,
            agent_action=phase_output.get("decision") or "Continue",
            agent_reason=phase_output.get("rejection_reason") or "Not provided",
            expected_action_per_rules=expected_action,
            rule_compliance=rule_compliance,
            preprocessing_evidence={
                "extracted_abn": extracted_abn,
                "extracted_vendor": extracted_vendor,
                "currency": currency,
                "checksum_valid": abn_metadata.get("valid") if abn_metadata else None,
                "vendor_name_present": bool(extracted_vendor),
            },
            agent_intermediate_output={
                "extracted_abn": extracted_abn,
                "extracted_vendor": extracted_vendor,
                "checksum_validated": abn_result.get("checksum_validated", False),
                "reextraction_attempted": abn_result.get(
                    "reextraction_attempted", False
                ),
                "fraud_indicator_detected": vendor_result.get("fraud_indicator", False),
            },
            applicable_rules=["Step 3.2", "Step 3.3", "Step 1.3"],
            compliance_explanation=compliance_explanation,
            violated_rules=violated_rules,
            followed_rules=["Step 3.2", "Step 3.3", "Step 1.3"]
            if not violated_rules
            else [],
            correction_needed=compliance_explanation if violated_rules else None,
            correction_priority=severity if severity else "LOW",
        )

    except Exception as e:
        print(f"    Phase 3 validation failed: {str(e)[:100]}")
        return _fallback_phase_validation("Phase 3", case_id, phase_output, str(e))


def _gather_phase4_inputs(
    case_data: dict[str, Any],
    extraction_data: dict,
    bypass_detector: BypassDetector | None,
    tolerance_extractor: ToleranceExtractor | None,
) -> dict[str, Any]:
    """Gather all inputs needed for Phase 4 validation."""
    invoice = extraction_data.get("invoice", {})
    line_items = invoice.get("line_items", [])
    agent_extractor = AgentOutputExtractor(case_data["agent_outputs"])

    phase1_output = case_data["agent_outputs"].get("phase1", {})
    work_type = phase1_output.get("work_type", "Repairs")

    labour_keywords = ["labour", "labor", "technician", "hours"]
    invoice_labour_hours = sum(
        float(item.get("quantity", 0) or 0)
        for item in line_items
        if any(kw in item.get("description", "").lower() for kw in labour_keywords)
    )

    waf_total_hours = 0
    waf = extraction_data.get("work_authorization")
    if waf:
        waf_total_hours = waf.get("authorized_hours", 0) or 0

    agent_step33 = agent_extractor.get_validation_step("phase4", 33)
    agent_step_passed = None
    agent_step_evidence = ""
    if agent_step33:
        agent_step_passed = agent_step33.get("passed")
        agent_step_evidence = agent_step33.get("evidence", "")

    bypass_info = None
    if bypass_detector and agent_step_evidence:
        bypass_info = bypass_detector.detect_bypass("Phase 4", 33, agent_step_evidence)

    tolerance_info = None
    if tolerance_extractor:
        tolerance_info = tolerance_extractor.get_tolerance_for_step(33)

    return {
        "work_type": work_type,
        "invoice_labour_hours": invoice_labour_hours,
        "waf_total_hours": waf_total_hours,
        "agent_step33": agent_step33,
        "agent_step_passed": agent_step_passed,
        "agent_step_evidence": agent_step_evidence,
        "bypass_info": bypass_info,
        "tolerance_info": tolerance_info,
    }


def _build_phase4_compliance(
    waf_result: dict,
    ds_violations: list,
) -> tuple[str, list[str], str, str | None]:
    """Determine compliance status for Phase 4 from WAF and data-source results.

    Returns (rule_compliance, violated_rules, compliance_explanation, severity).
    """
    has_ds_violations = len(ds_violations) > 0
    waf_valid = waf_result.get("valid", True)

    if waf_valid and not has_ds_violations:
        exempt_label = (
            "skipped (exempt)" if waf_result.get("work_type_exempt") else "passed"
        )
        return "COMPLIANT", [], f"WAF check {exempt_label}", None

    waf_confidence = waf_result.get("confidence", 0.5)
    rule_compliance, confidence_suffix = _apply_confidence_gating(
        is_violation=True,
        confidence=waf_confidence,
    )

    violated_rules: list[str] = []
    if not waf_valid and rule_compliance == "VIOLATION":
        violated_rules.extend(
            waf_result.get("violated_rules", ["Step 33", "Rule 33.1"])
        )
    if has_ds_violations and rule_compliance == "VIOLATION":
        violated_rules.extend(["Section 0"])

    explanation_parts: list[str] = []
    if not waf_valid:
        explanation_parts.append(f"WAF: {waf_result.get('reasoning', '')}")
    if has_ds_violations:
        ds_issues = [v.issue for v in ds_violations if v.issue]
        explanation_parts.append(f"Data Sources: {'; '.join(ds_issues)}")

    compliance_explanation = " | ".join(explanation_parts) + confidence_suffix
    severity = waf_result.get("severity") or "HIGH" if has_ds_violations else None
    if rule_compliance != "VIOLATION":
        severity = "LOW"

    return rule_compliance, violated_rules, compliance_explanation, severity


def _validate_phase4(
    case_data: dict[str, Any],
    llm_validator: LLMRulesValidatorReconstructed,
    data_source_validator: DataSourceValidator,
    extraction_data: dict,
    phase_output: dict,
    bypass_detector: BypassDetector = None,
    tolerance_extractor: ToleranceExtractor = None,
) -> PhaseValidation:
    """Validate Phase 4 with WAF hours and data source compliance.

    v1.3.0: Added bypass_detector and tolerance_extractor for improved accuracy.
    Uses AgentOutputExtractor to validate against agent's actual computed values.
    """
    case_id = case_data["case_id"]
    inputs = _gather_phase4_inputs(
        case_data,
        extraction_data,
        bypass_detector,
        tolerance_extractor,
    )

    try:
        waf_result = llm_validator.validate_waf_hours(
            work_type=inputs["work_type"],
            invoice_labour_hours=inputs["invoice_labour_hours"],
            waf_total_hours=inputs["waf_total_hours"],
            agent_decision=phase_output.get("decision", "Continue"),
            agent_reason=phase_output.get("rejection_reason"),
            agent_step_passed=inputs["agent_step_passed"],
            agent_step_evidence=inputs["agent_step_evidence"],
            bypass_info=inputs["bypass_info"],
            tolerance_info=inputs["tolerance_info"],
        )

        data_source_validations = data_source_validator.validate_data_source_usage(
            extraction_data=extraction_data,
            preprocessing_data={},
            agent_phase_output=phase_output,
        )
        ds_violations = [v for v in data_source_validations if not v.is_valid]

        rule_compliance, violated_rules, compliance_explanation, severity = (
            _build_phase4_compliance(waf_result, ds_violations)
        )

        bypass_info = inputs["bypass_info"]
        return PhaseValidation(
            phase_name="Phase 4",
            case_id=case_id,
            agent_action=phase_output.get("decision") or "Continue",
            agent_reason=phase_output.get("rejection_reason") or "Not provided",
            expected_action_per_rules=waf_result.get("expected_decision", "Continue"),
            rule_compliance=rule_compliance,
            preprocessing_evidence={
                "work_type": inputs["work_type"],
                "invoice_labour_hours": inputs["invoice_labour_hours"],
                "waf_total_hours": inputs["waf_total_hours"],
                "work_type_exempt": waf_result.get("work_type_exempt", False),
                "agent_step_found": inputs["agent_step33"] is not None,
                "agent_bypassed": bypass_info.get("bypassed", False)
                if bypass_info
                else False,
                "bypass_valid": bypass_info.get("is_valid_bypass")
                if bypass_info
                else None,
                "hours_within_tolerance": waf_result.get("hours_within_tolerance"),
                "hours_within_investigator_tolerance": waf_result.get(
                    "hours_within_investigator_tolerance"
                ),
            },
            agent_intermediate_output={
                "exemption_correctly_applied": waf_result.get(
                    "exemption_correctly_applied", True
                ),
                "hours_within_tolerance": waf_result.get("hours_within_tolerance"),
                "agent_step_evidence": inputs["agent_step_evidence"][:200]
                if inputs["agent_step_evidence"]
                else None,
                "agent_step_passed": inputs["agent_step_passed"],
            },
            applicable_rules=["Step 33", "Rule 33.1", "Section 0"],
            compliance_explanation=compliance_explanation,
            violated_rules=violated_rules,
            followed_rules=["Step 33", "Rule 33.1", "Section 0"]
            if not violated_rules
            else [],
            data_source_validations=data_source_validations,
            correction_needed=compliance_explanation if violated_rules else None,
            correction_priority=severity if severity else "LOW",
        )

    except Exception as e:
        print(f"    Phase 4 validation failed: {str(e)[:100]}")
        return _fallback_phase_validation("Phase 4", case_id, phase_output, str(e))


def _validate_phase_generic(
    case_data: dict[str, Any],
    phase_name: str,
    llm_validator: LLMRulesValidatorReconstructed,
    extraction_data: dict,
    agent_phase_output: dict,
) -> PhaseValidation:
    """Generic phase validation using LLM.

    Validates agent's phase output against rules book using extraction data
    and agent intermediate outputs only (no preprocessing data).
    """
    case_id = case_data["case_id"]

    try:
        result = llm_validator.validate_phase_generic(
            case_id=case_id,
            phase_name=phase_name,
            extraction_data=extraction_data,
            preprocessing_data={},  # General agent has no preprocessing
            agent_phase_output=agent_phase_output,
        )

        # Convert dict to PhaseValidation
        return PhaseValidation(
            phase_name=result.get("phase_name") or phase_name,
            case_id=case_id,
            agent_action=result.get("agent_action") or "Unknown",
            agent_reason=result.get("agent_reason") or "Not provided",
            expected_action_per_rules=result.get(
                "expected_action_per_rules", "Unknown"
            ),
            rule_compliance=result.get("rule_compliance", "INSUFFICIENT_DATA"),
            preprocessing_evidence=result.get("preprocessing_evidence", {}),
            agent_intermediate_output=result.get("agent_intermediate_output", {}),
            applicable_rules=result.get("applicable_rules", []),
            compliance_explanation=result.get("compliance_explanation", ""),
            violated_rules=result.get("violated_rules", []),
            followed_rules=result.get("followed_rules", []),
            correction_needed=result.get("correction_needed"),
            correction_priority=result.get("correction_priority", "MEDIUM"),
        )

    except Exception as e:
        print(f"    {phase_name} validation error: {str(e)[:100]}")
        phase_output = agent_phase_output.get("phase_output", {})
        return _fallback_phase_validation(phase_name, case_id, phase_output, str(e))


def _fallback_phase_validation(
    phase_name: str,
    case_id: str,
    phase_output: dict,
    error_message: str,
    config: InvestigationConfig = None,
) -> PhaseValidation:
    """Create fallback PhaseValidation when validation fails.

    v1.4.0: Now distinguishes between infrastructure errors (INCONCLUSIVE)
    and other errors (INSUFFICIENT_DATA). Infrastructure errors are not
    counted against compliance scores.
    """
    config = config or INVESTIGATION_CONFIG
    agent_action = (
        phase_output.get("decision")
        or phase_output.get("validation_result")
        or "Unknown"
    )
    agent_reason = (
        phase_output.get("rejection_reason") or phase_output.get("reason") or "Unknown"
    )

    # v1.4.0: Detect infrastructure errors and mark as INCONCLUSIVE
    is_infra_error = config.is_infrastructure_error(error_message)

    if is_infra_error:
        rule_compliance = "INCONCLUSIVE"
        compliance_explanation = (
            f"Infrastructure failure (will retry on next run): {error_message[:150]}"
        )
        correction_priority = "LOW"  # Not an agent issue
    else:
        rule_compliance = "INSUFFICIENT_DATA"
        compliance_explanation = f"Validation failed: {error_message[:200]}"
        correction_priority = "MEDIUM"

    return PhaseValidation(
        phase_name=phase_name,
        case_id=case_id,
        agent_action=agent_action,
        agent_reason=agent_reason,
        expected_action_per_rules="Unknown (validation failed)",
        rule_compliance=rule_compliance,
        preprocessing_evidence={"is_infrastructure_error": is_infra_error},
        agent_intermediate_output={},
        applicable_rules=[],
        compliance_explanation=compliance_explanation,
        violated_rules=[],
        followed_rules=[],
        correction_needed=None,
        correction_priority=correction_priority,
    )


def _apply_confidence_gating(
    is_violation: bool,
    confidence: float,
    violation_compliance: str = "VIOLATION",
    compliant_compliance: str = "COMPLIANT",
    config: InvestigationConfig = None,
) -> tuple[str, str]:
    """Apply confidence-based gating to violation determination.

    v1.4.0: New function to minimize false positives by requiring high
    confidence before flagging violations.

    Args:
        is_violation: Whether the validation detected a violation
        confidence: Confidence level from LLM (0.0-1.0)
        violation_compliance: Status to return if violation is confirmed
        compliant_compliance: Status to return if compliant
        config: Investigation configuration

    Returns:
        Tuple of (rule_compliance, explanation_suffix)
    """
    config = config or INVESTIGATION_CONFIG

    if not is_violation:
        return compliant_compliance, ""

    # v1.4.0: Apply confidence thresholds
    if confidence >= config.min_violation_confidence:
        # High confidence - flag as violation
        return violation_compliance, f" [confidence: {confidence:.0%}]"
    if confidence >= config.min_ambiguous_confidence:
        # Medium confidence - mark as ambiguous (benefit of doubt)
        return (
            "AMBIGUOUS",
            f" [confidence: {confidence:.0%} < {config.min_violation_confidence:.0%} threshold - giving benefit of doubt]",
        )
    # Low confidence - insufficient data
    return (
        "INSUFFICIENT_DATA",
        f" [confidence: {confidence:.0%} too low to determine]",
    )


# ============================================================================
# CASE INVESTIGATION ORCHESTRATION
# ============================================================================


def _create_skipped_phase_validation(
    phase_name: str,
    case_id: str,
    first_rejection_phase: str | None,
) -> PhaseValidation:
    """Create a SKIPPED PhaseValidation for phases not executed due to early rejection."""
    return PhaseValidation(
        phase_name=phase_name,
        case_id=case_id,
        agent_action="Not Executed",
        agent_reason=f"Skipped due to rejection in {first_rejection_phase}",
        expected_action_per_rules="Not Executed",
        rule_compliance="SKIPPED",
        preprocessing_evidence={"skipped_reason": "early_rejection"},
        agent_intermediate_output={},
        applicable_rules=[],
        compliance_explanation=f"Phase not executed due to earlier rejection in {first_rejection_phase}",
        violated_rules=[],
        followed_rules=[],
        data_source_validations=[],
        correction_needed=None,
        correction_priority="LOW",
    )


def _run_phase_validations(
    case_id: str,
    case_data: dict[str, Any],
    phases_executed: dict[str, bool],
    first_rejection_phase: str | None,
    llm_validator: LLMRulesValidatorReconstructed,
    data_source_validator: DataSourceValidator,
    bypass_detector: BypassDetector | None,
    tolerance_extractor: ToleranceExtractor | None,
) -> tuple[list[PhaseValidation], str | None]:
    """Validate each phase, skipping those after an early rejection."""
    phase_validations: list[PhaseValidation] = []
    early_rejection_occurred = False

    for phase_name in ["Phase 1", "Phase 2", "Phase 3", "Phase 4"]:
        if early_rejection_occurred and not phases_executed.get(phase_name, False):
            print(f"    Validating {phase_name}...", end=" ")
            print("- SKIPPED (early rejection)")
            phase_validations.append(
                _create_skipped_phase_validation(
                    phase_name, case_id, first_rejection_phase
                )
            )
            continue

        print(f"    Validating {phase_name}...", end=" ")
        phase_validation = validate_phase_against_rules(
            case_data=case_data,
            phase_name=phase_name,
            llm_validator=llm_validator,
            data_source_validator=data_source_validator,
            bypass_detector=bypass_detector,
            tolerance_extractor=tolerance_extractor,
        )
        phase_validations.append(phase_validation)

        if phase_validation.agent_action in ["Reject", "REJECT"]:
            early_rejection_occurred = True
            if not first_rejection_phase:
                first_rejection_phase = phase_name

        compliance_symbol = {
            "COMPLIANT": "OK",
            "VIOLATION": "X",
            "AMBIGUOUS": "?",
            "INSUFFICIENT_DATA": "!",
            "INCONCLUSIVE": "~",
            "SKIPPED": "-",
        }.get(phase_validation.rule_compliance, ".")
        print(f"{compliance_symbol} {phase_validation.rule_compliance}")

    return phase_validations, first_rejection_phase


def _compute_compliance(
    phase_validations: list[PhaseValidation],
) -> tuple[float, str]:
    """Compute compliance score and overall compliance label."""
    excluded_statuses = {"SKIPPED", "INCONCLUSIVE", "INSUFFICIENT_DATA"}
    executed = [
        pv for pv in phase_validations if pv.rule_compliance not in excluded_statuses
    ]
    config = INVESTIGATION_CONFIG
    compliant_count = sum(
        1
        for pv in executed
        if pv.rule_compliance == "COMPLIANT"
        or (config.treat_ambiguous_as_compliant and pv.rule_compliance == "AMBIGUOUS")
    )
    inconclusive_count = sum(
        1 for pv in phase_validations if pv.rule_compliance == "INCONCLUSIVE"
    )
    if inconclusive_count == len(phase_validations):
        print("  WARNING: All phases inconclusive due to infrastructure failures")
        return 0.0, "INCONCLUSIVE"
    if len(executed) > 0:
        score = (compliant_count / len(executed)) * 100
        if score == _FULL_COMPLIANCE_SCORE:
            return score, "FULLY_COMPLIANT"
        if score >= _PARTIAL_COMPLIANCE_THRESHOLD:
            return score, "PARTIAL_VIOLATION"
        return score, "MAJOR_VIOLATION"
    return 100.0, "FULLY_COMPLIANT"


def _assess_rejection(
    processing_summary: CaseProcessingSummary,
    phase_validations: list[PhaseValidation],
) -> tuple[bool, bool | None, str | None]:
    """Assess whether a rejection was justified."""
    is_rejected = processing_summary.final_status == "Rejected"
    justified = None
    justification = None
    if is_rejected and processing_summary.first_rejection_phase:
        pv = next(
            (
                p
                for p in phase_validations
                if p.phase_name == processing_summary.first_rejection_phase
            ),
            None,
        )
        if pv:
            justified = pv.rule_compliance == "COMPLIANT"
            justification = pv.compliance_explanation
    return is_rejected, justified, justification


def _collect_data_source_violations(
    phase_validations: list[PhaseValidation],
) -> tuple[str, list[str]]:
    """Collect data source violations and determine compliance label."""
    violations: list[str] = []
    for pv in phase_validations:
        for dsv in pv.data_source_validations:
            if not dsv.is_valid:
                violations.append(dsv.issue or f"{dsv.field_name}: wrong source")
    if not violations:
        return "COMPLIANT", violations
    if len(violations) <= _MAX_PARTIAL_VIOLATIONS:
        return "PARTIAL", violations
    return "VIOLATION", violations


def _assess_extraction_quality(case_data: dict[str, Any]) -> tuple[str, float]:
    """Assess extraction data quality."""
    completeness = calculate_extraction_completeness(case_data)
    if completeness >= _COMPLETE_EXTRACTION_THRESHOLD:
        return "COMPLETE", completeness
    if completeness >= _PARTIAL_EXTRACTION_THRESHOLD:
        return "PARTIAL", completeness
    return "POOR", completeness


def _collect_recommendations(
    phase_validations: list[PhaseValidation],
) -> tuple[list[str], list[str], list[str]]:
    """Collect agent improvements, rule clarifications, and data quality fixes."""
    improvements: list[str] = []
    clarifications: list[str] = []
    quality_fixes: list[str] = []
    for pv in phase_validations:
        if pv.rule_compliance == "VIOLATION" and pv.correction_needed:
            improvements.append(pv.correction_needed)
        elif pv.rule_compliance == "AMBIGUOUS":
            clarifications.extend(pv.applicable_rules)
        elif pv.rule_compliance == "INSUFFICIENT_DATA":
            quality_fixes.append(f"{pv.phase_name}: {pv.compliance_explanation}")
    return improvements, clarifications, quality_fixes


def _run_layer3_validation(
    case_id: str,
    case_data: dict[str, Any],
    per_group_validator: PerGroupValidator | None,
    discovered_rules: dict | None,
    enable_double_check: bool,
) -> tuple[dict | None, int]:
    """Run Layer 3 per-group validation if enabled."""
    if not per_group_validator or not discovered_rules:
        return None, 0
    rule_groups = discovered_rules.get("rule_groups", [])
    if not rule_groups:
        return None, 0

    print(f"  Layer 3: Per-group validation ({len(rule_groups)} groups)...")
    results = per_group_validator.validate_all_groups(
        case_id=case_id,
        rule_groups=rule_groups,
        case_data=case_data,
        enable_double_check=enable_double_check,
    )
    violations = results.get("total_violations", 0)
    dc_stats = results.get("double_check_stats", {})
    if violations > 0:
        print(f"    Layer 3 result: {violations} violation(s) found")
    else:
        print("    Layer 3 result: All rule groups compliant")
    if dc_stats.get("discarded", 0) > 0:
        print(
            f"    Double-check: {dc_stats['discarded']} violation(s) discarded as inconsistent"
        )
    return results, violations


def investigate_agent_case(
    case_id: str,
    case_data: dict[str, Any],
    llm_validator: LLMRulesValidatorReconstructed,
    data_source_validator: DataSourceValidator,
    bypass_detector: BypassDetector = None,
    tolerance_extractor: ToleranceExtractor = None,
    per_group_validator: PerGroupValidator = None,
    discovered_rules: dict | None = None,
    enable_double_check: bool = True,
) -> AgentCaseInvestigation:
    """Complete investigation of agent processing for one case.

    v2.0.0: Added per_group_validator and discovered_rules for Layer 3 validation.
    v1.3.0: Added bypass_detector and tolerance_extractor for reduced false positives.
    v1.3.1: Skip validation for phases that weren't executed (early rejection).
    """
    _ensure_gcp_initialized()
    print(f"  Investigating case {case_id}...")

    processing_summary = extract_processing_summary(case_data)

    # Determine which phases were actually executed
    phase_key_map = {
        "Phase 1": "phase1",
        "Phase 2": "phase2",
        "Phase 3": "phase3",
        "Phase 4": "phase4",
    }
    agent_outputs = case_data.get("agent_outputs", {})
    phases_executed = {
        pn: bool(
            agent_outputs.get(k, {}).get("decision")
            or agent_outputs.get(k, {}).get("validations")
        )
        for pn, k in phase_key_map.items()
    }
    first_rejection_phase = (
        processing_summary.first_rejection_phase if processing_summary else None
    )

    # Phase validations
    phase_validations, first_rejection_phase = _run_phase_validations(
        case_id,
        case_data,
        phases_executed,
        first_rejection_phase,
        llm_validator,
        data_source_validator,
        bypass_detector,
        tolerance_extractor,
    )

    # Compliance
    compliance_score, overall_compliance = _compute_compliance(phase_validations)

    # Rejection assessment
    is_rejected, rejection_justified, rejection_justification = _assess_rejection(
        processing_summary,
        phase_validations,
    )

    # Data source compliance
    data_source_compliance, data_source_violations = _collect_data_source_violations(
        phase_validations,
    )

    # Extraction quality
    extraction_quality, extraction_completeness = _assess_extraction_quality(case_data)

    # Recommendations
    agent_improvements, rule_clarifications, data_quality_improvements = (
        _collect_recommendations(phase_validations)
    )

    # Summary
    summary_parts = [
        f"Case {case_id}",
        overall_compliance,
        f"compliance score {compliance_score:.1f}%",
    ]
    if is_rejected:
        justified_str = "justified" if rejection_justified else "UNJUSTIFIED"
        summary_parts.append(f"rejected ({justified_str})")
    if data_source_compliance != "COMPLIANT":
        summary_parts.append(f"data source issues: {len(data_source_violations)}")

    # Layer 3
    group_validation_results, layer3_violations = _run_layer3_validation(
        case_id,
        case_data,
        per_group_validator,
        discovered_rules,
        enable_double_check,
    )
    if layer3_violations > 0:
        summary_parts.append(f"layer3 violations: {layer3_violations}")

    summary = ", ".join(summary_parts)

    return AgentCaseInvestigation(
        case_id=case_id,
        processing_summary=processing_summary,
        phase_validations=phase_validations,
        overall_rule_compliance=overall_compliance,
        compliance_score=compliance_score,
        is_rejected=is_rejected,
        rejection_justified=rejection_justified,
        rejection_justification=rejection_justification,
        preprocessing_data_quality=extraction_quality,
        preprocessing_completeness=extraction_completeness,
        data_source_compliance=data_source_compliance,
        data_source_violations=data_source_violations,
        agent_improvements=agent_improvements,
        rule_clarifications_needed=rule_clarifications,
        data_quality_improvements=data_quality_improvements,
        group_validation_results=group_validation_results,
        layer3_violations=layer3_violations,
        summary=summary,
    )


# ============================================================================
# REJECTION PATTERN ANALYSIS
# ============================================================================


def _classify_rejection_root_cause(details: dict) -> tuple[str, str]:
    """Return (root_cause, recommendation) for a rejection pattern's detail bucket."""
    if details["incorrect"] > details["legitimate"]:
        return (
            "RULE_VIOLATION",
            f"Fix agent logic - {details['incorrect']} unjustified rejections",
        )
    if details["legitimate"] > 0:
        return (
            "CORRECT_REJECTION",
            f"Rejections appear justified per rules ({details['legitimate']} cases)",
        )
    return ("DATA_QUALITY", "Review extraction data quality for these cases")


def analyze_rejection_patterns(
    case_investigations: list[AgentCaseInvestigation],
) -> list[RejectionPattern]:
    """Identify and analyze common rejection patterns across cases."""
    rejection_reasons: list[str] = []
    rejection_details: dict[str, dict] = defaultdict(
        lambda: {
            "phase": None,
            "case_ids": [],
            "legitimate": 0,
            "incorrect": 0,
            "rules": set(),
        }
    )

    for inv in case_investigations:
        if not inv.is_rejected:
            continue

        rejection_phase = inv.processing_summary.first_rejection_phase
        rejection_reason = (
            inv.processing_summary.first_rejection_reason or "Unknown rejection reason"
        )
        rejection_reasons.append(rejection_reason)

        details = rejection_details[rejection_reason]
        details["phase"] = rejection_phase
        details["case_ids"].append(inv.case_id)

        if inv.rejection_justified:
            details["legitimate"] += 1
        elif inv.rejection_justified is False:
            details["incorrect"] += 1

        for phase_val in inv.phase_validations:
            if phase_val.phase_name == rejection_phase:
                details["rules"].update(phase_val.applicable_rules)

    reason_counts = Counter(rejection_reasons)
    total_rejections = len(rejection_reasons) if rejection_reasons else 1

    patterns = []
    for reason, count in reason_counts.most_common():
        details = rejection_details[reason]
        root_cause, recommendation = _classify_rejection_root_cause(details)
        patterns.append(
            RejectionPattern(
                rejection_reason=reason,
                affected_phase=details["phase"] or "Unknown",
                case_count=count,
                percentage=(count / total_rejections) * 100,
                example_case_ids=details["case_ids"][:5],
                rule_reference=sorted(details["rules"])[:10],
                legitimate_rejections=details["legitimate"],
                incorrect_rejections=details["incorrect"],
                root_cause_category=root_cause,
                recommendation=recommendation,
            )
        )

    return patterns


# ============================================================================
# AGGREGATE ANALYSIS
# ============================================================================


def _aggregate_layer3_stats(
    investigations: list[AgentCaseInvestigation],
) -> dict[str, Any]:
    """Compute Layer 3 aggregate statistics."""
    layer3_cases = sum(1 for inv in investigations if inv.group_validation_results)
    layer3_total = sum(inv.layer3_violations for inv in investigations)
    layer3_avg = round(layer3_total / layer3_cases, 2) if layer3_cases > 0 else 0

    total_dc = 0
    discarded = 0
    for inv in investigations:
        if inv.group_validation_results:
            dc = inv.group_validation_results.get("double_check_stats", {})
            total_dc += dc.get("total", 0)
            discarded += dc.get("discarded", 0)

    dc_rate = round((discarded / total_dc * 100) if total_dc > 0 else 0, 2)
    return {
        "layer3_cases_validated": layer3_cases,
        "layer3_total_violations": layer3_total,
        "layer3_avg_violations_per_case": layer3_avg,
        "double_check_count": total_dc,
        "double_check_discarded": discarded,
        "double_check_discard_rate": dc_rate,
    }


def _aggregate_top_recommendations(
    investigations: list[AgentCaseInvestigation],
) -> tuple[list[str], list[str], list[str]]:
    """Aggregate top fixes, clarifications, and quality fixes."""
    fixes: list[str] = []
    clarifications: list[str] = []
    quality: list[str] = []
    for inv in investigations:
        fixes.extend(inv.agent_improvements)
        clarifications.extend(inv.rule_clarifications_needed)
        quality.extend(inv.data_quality_improvements)
    return (
        [f for f, _ in Counter(fixes).most_common(10)],
        [c for c, _ in Counter(clarifications).most_common(10)],
        [q for q, _ in Counter(quality).most_common(10)],
    )


def aggregate_agent_investigations(
    investigations: list[AgentCaseInvestigation],
) -> dict[str, Any]:
    """Aggregate analysis across all investigated cases."""
    total_cases = len(investigations)
    if total_cases == 0:
        return {}

    # Outcome breakdown
    accepted_cases = sum(1 for inv in investigations if not inv.is_rejected)
    rejected_cases = sum(1 for inv in investigations if inv.is_rejected)
    set_aside_cases = sum(
        1
        for inv in investigations
        if inv.processing_summary.final_status == "Set Aside"
    )
    acceptance_rate = (accepted_cases / total_cases) * 100
    rejection_rate = (rejected_cases / total_cases) * 100

    # Rule compliance breakdown
    fully_compliant = sum(
        1 for inv in investigations if inv.overall_rule_compliance == "FULLY_COMPLIANT"
    )
    partial_violation = sum(
        1
        for inv in investigations
        if inv.overall_rule_compliance == "PARTIAL_VIOLATION"
    )
    major_violation = sum(
        1 for inv in investigations if inv.overall_rule_compliance == "MAJOR_VIOLATION"
    )
    inconclusive = sum(
        1 for inv in investigations if inv.overall_rule_compliance == "INCONCLUSIVE"
    )
    conclusive_cases = total_cases - inconclusive
    overall_compliance_rate = (
        (fully_compliant / conclusive_cases * 100) if conclusive_cases > 0 else 0.0
    )

    # Data source compliance
    data_source_compliant = sum(
        1 for inv in investigations if inv.data_source_compliance == "COMPLIANT"
    )
    data_source_violation = sum(
        1 for inv in investigations if inv.data_source_compliance != "COMPLIANT"
    )

    # Rejections
    justified_rejections = sum(
        1
        for inv in investigations
        if inv.is_rejected and inv.rejection_justified is True
    )
    unjustified_rejections = sum(
        1
        for inv in investigations
        if inv.is_rejected and inv.rejection_justified is False
    )

    # Phase-specific rejection rates
    phase_rejections = defaultdict(int)
    for inv in investigations:
        if inv.processing_summary.first_rejection_phase:
            phase_rejections[inv.processing_summary.first_rejection_phase] += 1

    phase1_rejection_rate = (phase_rejections.get("Phase 1", 0) / total_cases) * 100
    phase2_rejection_rate = (phase_rejections.get("Phase 2", 0) / total_cases) * 100
    phase3_rejection_rate = (phase_rejections.get("Phase 3", 0) / total_cases) * 100
    phase4_rejection_rate = (phase_rejections.get("Phase 4", 0) / total_cases) * 100

    rejection_patterns = analyze_rejection_patterns(investigations)
    most_common_rejection_phase = (
        max(phase_rejections.items(), key=lambda x: x[1])[0]
        if phase_rejections
        else "None"
    )
    most_common_rejection_reason = (
        rejection_patterns[0].rejection_reason if rejection_patterns else "None"
    )

    # Top rule violations
    all_violated_rules: list[str] = []
    for inv in investigations:
        for pv in inv.phase_validations:
            all_violated_rules.extend(pv.violated_rules)
    top_rule_violations = [
        f"{rule} - {count} cases"
        for rule, count in Counter(all_violated_rules).most_common(10)
    ]

    # Data quality impact
    cases_with_preprocessing_issues = sum(
        1
        for inv in investigations
        if inv.preprocessing_data_quality in ["PARTIAL", "POOR"]
    )
    data_quality_rejections = sum(
        1
        for inv in investigations
        if inv.is_rejected and inv.preprocessing_data_quality in ["PARTIAL", "POOR"]
    )
    data_quality_impact = (
        (data_quality_rejections / rejected_cases * 100) if rejected_cases > 0 else 0.0
    )

    top_agent_fixes, top_rule_clarifications, top_data_quality_fixes = (
        _aggregate_top_recommendations(investigations)
    )

    # Executive summary
    exec_parts = [
        f"Investigated {total_cases} cases using reconstructed_rules_book.md v1.1.1",
        f"{rejection_rate:.1f}% rejection rate",
    ]
    if unjustified_rejections > 0:
        unjust_pct = (
            (unjustified_rejections / rejected_cases * 100) if rejected_cases > 0 else 0
        )
        exec_parts.append(f"{unjust_pct:.1f}% unjustified rejections")
    exec_parts.append(f"{most_common_rejection_phase} has highest rejection rate")
    exec_parts.append(f"Overall agent compliance: {overall_compliance_rate:.1f}%")
    if data_source_violation > 0:
        exec_parts.append(f"Data source violations: {data_source_violation} cases")

    layer3 = _aggregate_layer3_stats(investigations)
    if layer3["layer3_total_violations"] > 0:
        exec_parts.append(
            f"Layer 3 found {layer3['layer3_total_violations']} additional violation(s)"
        )
    if layer3["double_check_discarded"] > 0:
        exec_parts.append(
            f"Double-check discarded {layer3['double_check_discarded']} false positive(s)"
        )

    executive_summary = ". ".join(exec_parts) + "."

    return {
        "rules_book_version": "reconstructed_rules_book.md v1.1.1",
        "total_cases_investigated": total_cases,
        "accepted_cases": accepted_cases,
        "rejected_cases": rejected_cases,
        "set_aside_cases": set_aside_cases,
        "acceptance_rate": round(acceptance_rate, 2),
        "rejection_rate": round(rejection_rate, 2),
        "rejection_patterns": [p.model_dump() for p in rejection_patterns],
        "most_common_rejection_phase": most_common_rejection_phase,
        "most_common_rejection_reason": most_common_rejection_reason,
        "fully_compliant_cases": fully_compliant,
        "partial_violation_cases": partial_violation,
        "major_violation_cases": major_violation,
        "inconclusive_cases": inconclusive,  # v1.4.0: Infrastructure failures
        "overall_compliance_rate": round(overall_compliance_rate, 2),
        "phase1_rejection_rate": round(phase1_rejection_rate, 2),
        "phase2_rejection_rate": round(phase2_rejection_rate, 2),
        # Phase 2.5 not used in general agent
        "phase3_rejection_rate": round(phase3_rejection_rate, 2),
        "phase4_rejection_rate": round(phase4_rejection_rate, 2),
        "justified_rejections": justified_rejections,
        "unjustified_rejections": unjustified_rejections,
        "top_rule_violations": top_rule_violations,
        "data_source_compliant_cases": data_source_compliant,
        "data_source_violation_cases": data_source_violation,
        "cases_with_preprocessing_issues": cases_with_preprocessing_issues,
        "data_quality_impact_on_rejections": round(data_quality_impact, 2),
        "top_agent_fixes": top_agent_fixes,
        "top_rule_clarifications": top_rule_clarifications,
        "top_data_quality_fixes": top_data_quality_fixes,
        "executive_summary": executive_summary,
        # v2.0.0: Layer 3 statistics
        **layer3,
    }


# ============================================================================
# REPORTING
# ============================================================================


def _print_word_wrapped(text: str, indent: str = "    ") -> None:
    """Print text with word wrapping at _MAX_LINE_WIDTH."""
    words = text.split()
    line = indent
    for word in words:
        if len(line) + len(word) + 1 > _MAX_LINE_WIDTH:
            print(line)
            line = indent + word
        else:
            line += " " + word if line != indent else word
    if line.strip():
        print(line)


def _print_violation_detail(pv: PhaseValidation) -> None:
    """Print detailed violation info for a single phase."""
    rules_str = ", ".join(pv.violated_rules) if pv.violated_rules else "Unknown"
    print(f"\n  [{pv.phase_name}] {rules_str}")
    print(f"  {'-' * 68}")
    print(f"  Agent Did:     {pv.agent_action}")
    if pv.agent_reason and pv.agent_reason != "Not provided":
        print(f'                 Reason: "{pv.agent_reason}"')
    print(f"  Should Have:   {pv.expected_action_per_rules}")

    print("\n  Issue:")
    _print_word_wrapped(pv.compliance_explanation)

    if pv.correction_needed:
        print(f"\n  Fix Required ({pv.correction_priority}):")
        _print_word_wrapped(pv.correction_needed)

    if pv.preprocessing_evidence:
        relevant = {k: v for k, v in pv.preprocessing_evidence.items() if v is not None}
        if relevant:
            print("\n  Evidence:")
            for key, value in list(relevant.items())[:5]:
                print(f"    - {key}: {value}")


def _print_layer3_violations(investigation: AgentCaseInvestigation) -> None:
    """Print Layer 3 per-group violations section."""
    if (
        not investigation.group_validation_results
        or investigation.layer3_violations == 0
    ):
        return
    print(f"\n  {'=' * 70}")
    print("  LAYER 3 VIOLATIONS (Per-Group Validation):")
    print(f"  {'=' * 70}")

    for violation in investigation.group_validation_results.get("all_violations", []):
        group_id = violation.get("group_id", violation.get("rule_id", "unknown"))
        rule_id = violation.get("rule_id", "unknown")
        desc = violation.get("violation_description", "")
        evidence = violation.get("evidence", "")
        confidence = violation.get("confidence", 0)
        severity = violation.get("severity", "MEDIUM")

        print(f"\n  [{group_id}] Rule: {rule_id} (severity: {severity})")
        print(f"  {'-' * 68}")
        print(f"  Violation: {desc[:200]}")
        if evidence:
            print(f"  Evidence: {evidence[:200]}")
        print(f"  Confidence: {confidence:.0%}")

    # Show double-check discards
    dc_stats = investigation.group_validation_results.get("double_check_stats", {})
    if dc_stats.get("discarded", 0) > 0:
        print(
            f"\n  DOUBLE-CHECK: {dc_stats['discarded']} violation(s) discarded as inconsistent (false positive reduction)"
        )


def print_case_investigation_report(investigation: AgentCaseInvestigation):
    """Print clear, actionable report for a single case investigation."""
    violations = [
        pv
        for pv in investigation.phase_validations
        if pv.rule_compliance == "VIOLATION"
    ]
    compliant = [
        pv
        for pv in investigation.phase_validations
        if pv.rule_compliance == "COMPLIANT"
    ]
    skipped = [
        pv for pv in investigation.phase_validations if pv.rule_compliance == "SKIPPED"
    ]
    executed_phases = len(investigation.phase_validations) - len(skipped)

    _print_report_header(investigation, violations, skipped, executed_phases)
    _print_phase_results_table(investigation)

    if investigation.data_source_violations:
        print("\n  DATA SOURCE VIOLATIONS (Section 0):")
        for ds_issue in investigation.data_source_violations[:3]:
            print(f"    - {ds_issue}")

    if violations:
        print(f"\n  {'=' * 70}")
        print("  VIOLATIONS DETAIL (Agent behavior NOT compliant with rules book):")
        print(f"  {'=' * 70}")
        for pv in violations:
            _print_violation_detail(pv)

    _print_layer3_violations(investigation)

    if (
        len(violations) == 0
        and investigation.layer3_violations == 0
        and len(compliant) == executed_phases
    ):
        print(
            "\n  All phases passed - agent behavior complies with reconstructed_rules_book.md"
        )


def _print_report_header(
    investigation: AgentCaseInvestigation,
    violations: list,
    skipped: list,
    executed_phases: int,
) -> None:
    """Print result header and final status."""
    if len(violations) == 0:
        result_icon = "OK"
        result_text = "COMPLIANT"
        if len(skipped) > 0:
            result_text += f" ({len(skipped)} phases skipped)"
    else:
        result_icon = "X"
        result_text = (
            f"VIOLATION ({len(violations)} of {executed_phases} executed phases failed)"
        )

    print(
        f"\n  RESULT: {result_icon} {result_text} | Compliance Score: {investigation.compliance_score:.1f}%"
    )

    status_info = f"Final Status: {investigation.processing_summary.final_status}"
    if investigation.is_rejected:
        justified = "Justified" if investigation.rejection_justified else "UNJUSTIFIED"
        status_info += f" ({justified})"
    print(f"  {status_info}")


def _print_phase_results_table(investigation: AgentCaseInvestigation) -> None:
    """Print the phase results table in two columns."""
    print("\n  PHASE RESULTS:")
    phase_results = []
    for pv in investigation.phase_validations:
        icon = {
            "COMPLIANT": "OK",
            "VIOLATION": "X ",
            "INSUFFICIENT_DATA": "? ",
        }.get(
            pv.rule_compliance,
            "- ",
        )
        phase_results.append(f"{pv.phase_name}: {icon} {pv.rule_compliance}")
    for i in range(0, len(phase_results), 2):
        left = phase_results[i] if i < len(phase_results) else ""
        right = phase_results[i + 1] if i + 1 < len(phase_results) else ""
        print(f"    {left:<35} {right}")


def _print_aggregate_rejection_analysis(aggregate: dict[str, Any]) -> None:
    """Print rejection analysis section of aggregate report."""
    if aggregate["rejected_cases"] == 0:
        return
    print("\nREJECTION ANALYSIS:")
    print(f"  Total rejections: {aggregate['rejected_cases']}")
    print(
        f"  Justified rejections: {aggregate['justified_rejections']} (correct per rules)"
    )
    print(
        f"  Unjustified rejections: {aggregate['unjustified_rejections']} (agent errors!)"
    )
    if aggregate["unjustified_rejections"] > 0:
        unjust_pct = (
            aggregate["unjustified_rejections"] / aggregate["rejected_cases"]
        ) * 100
        print(f"    -> {unjust_pct:.1f}% of rejections are agent errors")


def _print_aggregate_layer3(aggregate: dict[str, Any]) -> None:
    """Print Layer 3 and double-check sections of aggregate report."""
    if aggregate.get("layer3_cases_validated", 0) == 0:
        return
    print("\nLAYER 3 VALIDATION (Per-Group):")
    print(f"  Cases validated: {aggregate['layer3_cases_validated']}")
    print(f"  Total violations found: {aggregate['layer3_total_violations']}")
    print(
        f"  Average violations per case: {aggregate['layer3_avg_violations_per_case']}"
    )
    if aggregate.get("double_check_count", 0) > 0:
        print("\nDOUBLE-CHECK MECHANISM:")
        print(f"  Total double-checks performed: {aggregate['double_check_count']}")
        print(
            f"  Violations discarded (inconsistent): {aggregate['double_check_discarded']}"
        )
        print(f"  Discard rate: {aggregate['double_check_discard_rate']:.1f}%")


def print_aggregate_report(aggregate: dict[str, Any]):
    """Print formatted aggregate analysis report."""
    print(f"\n{'=' * 80}")
    print("AGGREGATE ANALYSIS (Reconstructed Rules Book)")
    print("=" * 80)

    print(f"\nRules Book: {aggregate.get('rules_book_version', 'Unknown')}")
    print(f"Total cases investigated: {aggregate['total_cases_investigated']}")

    print("\nOUTCOME BREAKDOWN:")
    print(
        f"  Accepted: {aggregate['accepted_cases']} ({aggregate['acceptance_rate']:.1f}%)"
    )
    print(
        f"  Rejected: {aggregate['rejected_cases']} ({aggregate['rejection_rate']:.1f}%)"
    )
    print(f"  Set Aside: {aggregate['set_aside_cases']}")

    print("\nRULE COMPLIANCE:")
    print(
        f"  Fully compliant: {aggregate['fully_compliant_cases']} cases ({aggregate['overall_compliance_rate']:.1f}%)"
    )
    print(f"  Partial violations: {aggregate['partial_violation_cases']} cases")
    print(f"  Major violations: {aggregate['major_violation_cases']} cases")
    inconclusive = aggregate.get("inconclusive_cases", 0)
    if inconclusive > 0:
        print(f"  Inconclusive (infra failures): {inconclusive} cases")
        print("    -> These cases need re-investigation when infrastructure is stable")

    print("\nDATA SOURCE COMPLIANCE (Section 0):")
    print(f"  Compliant: {aggregate.get('data_source_compliant_cases', 0)} cases")
    print(f"  Violations: {aggregate.get('data_source_violation_cases', 0)} cases")

    _print_aggregate_rejection_analysis(aggregate)

    print("\nTOP REJECTION PATTERNS:")
    for i, pattern in enumerate(aggregate["rejection_patterns"][:5], 1):
        print(
            f'  {i}. "{pattern["rejection_reason"]}" - {pattern["case_count"]} cases ({pattern["percentage"]:.1f}%)'
        )
        print(f"     Phase: {pattern['affected_phase']}")
        print(
            f"     Legitimate: {pattern['legitimate_rejections']}, Incorrect: {pattern['incorrect_rejections']}"
        )
        print(f"     Root Cause: {pattern['root_cause_category']}")

    print("\nPHASE-SPECIFIC REJECTION RATES:")
    print(f"  Phase 1: {aggregate['phase1_rejection_rate']:.1f}%")
    print(f"  Phase 2: {aggregate['phase2_rejection_rate']:.1f}%")
    print(f"  Phase 3: {aggregate['phase3_rejection_rate']:.1f}%")
    print(f"  Phase 4: {aggregate['phase4_rejection_rate']:.1f}%")
    print(f"  -> Highest: {aggregate['most_common_rejection_phase']}")

    if aggregate["top_rule_violations"]:
        print("\nTOP RULE VIOLATIONS:")
        for i, violation in enumerate(aggregate["top_rule_violations"][:5], 1):
            print(f"  {i}. {violation}")

    if aggregate.get("cases_with_preprocessing_issues", 0) > 0:
        print("\nDATA QUALITY IMPACT:")
        print(
            f"  Cases with extraction quality issues: {aggregate['cases_with_preprocessing_issues']}"
        )
        print(
            f"  Quality-related rejections: {aggregate.get('data_quality_impact_on_rejections', 0):.1f}% of total rejections"
        )

    if aggregate["top_agent_fixes"]:
        print("\nTOP AGENT FIXES NEEDED:")
        for i, fix in enumerate(aggregate["top_agent_fixes"][:5], 1):
            print(f"  {i}. {fix[:100]}...")

    if aggregate["top_rule_clarifications"]:
        print("\nTOP RULE CLARIFICATIONS NEEDED:")
        for i, clar in enumerate(aggregate["top_rule_clarifications"][:5], 1):
            print(f"  {i}. {clar}")

    _print_aggregate_layer3(aggregate)


# ============================================================================
# MAIN FUNCTION
# ============================================================================


def _build_arg_parser() -> argparse.ArgumentParser:
    """Build the CLI argument parser."""
    parser = argparse.ArgumentParser(
        description="Agent Investigation using reconstructed_rules_book.md (v2.1.0 - Domain-Independent)"
    )
    parser.add_argument("--case", "-c", type=str, help="Single case ID to investigate")
    parser.add_argument(
        "--num-cases", "-n", type=int, default=0, help="Limit cases (0=all)"
    )
    parser.add_argument(
        "--status-filter",
        "-s",
        choices=["ACCEPTED", "REJECTED", "SET_ASIDE", "ALL"],
        default="ALL",
        help="Filter by final status",
    )
    parser.add_argument(
        "--phase-filter",
        "-p",
        choices=["Phase 1", "Phase 2", "Phase 3", "Phase 4"],
        help="Focus on specific phase",
    )
    parser.add_argument(
        "--show-compliant",
        action="store_true",
        help="Include compliant cases in output",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    parser.add_argument(
        "--disable-layer3",
        action="store_true",
        help="Disable Layer 3 per-group validation",
    )
    parser.add_argument(
        "--disable-double-check",
        action="store_true",
        help="Disable double-check mechanism",
    )
    parser.add_argument(
        "--force-rule-discovery",
        action="store_true",
        help="Force re-discovery of rules",
    )
    parser.add_argument(
        "--show-rule-groups",
        action="store_true",
        help="Show discovered rule groups and exit",
    )
    parser.add_argument(
        "--master-data",
        "-m",
        type=str,
        default=None,
        help="Path to master_data config file",
    )
    return parser


def _filter_cases(case_ids: list[str], args: argparse.Namespace) -> list[str] | None:
    """Filter and select cases to investigate based on CLI args.

    Returns None if a requested single case was not found.
    """
    if args.case:
        if args.case in case_ids:
            return [args.case]
        print(f"\nError: Case {args.case} not found")
        return None

    if args.status_filter != "ALL":
        _status_map = {
            "ACCEPTED": lambda s: s != "Rejected",
            "REJECTED": lambda s: s == "Rejected",
            "SET_ASIDE": lambda s: s == "Set Aside",
        }
        predicate = _status_map.get(args.status_filter, lambda _s: True)
        print(f"  Filtering by status: {args.status_filter}...")
        filtered = []
        for cid in case_ids:
            summary = extract_processing_summary(load_agent_case_data(cid))
            if predicate(summary.final_status):
                filtered.append(cid)
        cases = filtered
    else:
        cases = case_ids

    if args.num_cases > 0:
        cases = cases[: args.num_cases]
    return cases


def _run_case_investigations(
    cases: list[str],
    args: argparse.Namespace,
    llm_validator: LLMRulesValidatorReconstructed,
    data_source_validator: DataSourceValidator,
    bypass_detector: BypassDetector,
    tolerance_extractor: ToleranceExtractor,
    per_group_validator: PerGroupValidator | None,
    discovered_rules: dict | None,
) -> list[AgentCaseInvestigation]:
    """Run investigations on all selected cases."""
    investigations: list[AgentCaseInvestigation] = []
    total = len(cases)
    for idx, case_id in enumerate(cases, start=1):
        print(f"\n{'=' * 80}")
        print(f"[{idx}/{total}] Case: {case_id}")
        print(f"{'=' * 80}")
        case_data = load_agent_case_data(case_id)
        try:
            investigation = investigate_agent_case(
                case_id=case_id,
                case_data=case_data,
                llm_validator=llm_validator,
                data_source_validator=data_source_validator,
                bypass_detector=bypass_detector,
                tolerance_extractor=tolerance_extractor,
                per_group_validator=per_group_validator,
                discovered_rules=discovered_rules,
                enable_double_check=not args.disable_double_check,
            )
            investigations.append(investigation)
            print_case_investigation_report(investigation)
            print("\n  OK Investigation completed")
        except Exception as e:
            print(f"  X Investigation failed: {str(e)[:200]}")
            if args.verbose:
                traceback.print_exc()
    return investigations


def _save_results(
    investigations: list[AgentCaseInvestigation],
    aggregate: dict[str, Any],
) -> None:
    """Save investigation results and aggregate summary to disk."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_dir = INVESTIGATION_OUTPUT_DIR / f"agent_investigation_reconst_{timestamp}"
    output_dir.mkdir(parents=True, exist_ok=True)

    case_dir = output_dir / "case_investigations"
    case_dir.mkdir(exist_ok=True)
    for investigation in investigations:
        case_file = case_dir / f"{investigation.case_id}.json"
        with open(case_file, "w", encoding="utf-8") as f:
            json.dump(investigation.model_dump(), f, indent=2, ensure_ascii=False)

    summary_file = output_dir / "aggregate_summary.json"
    summary_model = AgentInvestigationSummary(
        timestamp=datetime.now().isoformat(),
        rules_book_version=aggregate.get(
            "rules_book_version", "reconstructed_rules_book.md v1.1.1"
        ),
        total_cases_investigated=aggregate["total_cases_investigated"],
        accepted_cases=aggregate["accepted_cases"],
        rejected_cases=aggregate["rejected_cases"],
        set_aside_cases=aggregate["set_aside_cases"],
        acceptance_rate=aggregate["acceptance_rate"],
        rejection_rate=aggregate["rejection_rate"],
        rejection_patterns=[
            RejectionPattern(**p) for p in aggregate["rejection_patterns"]
        ],
        most_common_rejection_phase=aggregate["most_common_rejection_phase"],
        most_common_rejection_reason=aggregate["most_common_rejection_reason"],
        fully_compliant_cases=aggregate["fully_compliant_cases"],
        partial_violation_cases=aggregate["partial_violation_cases"],
        major_violation_cases=aggregate["major_violation_cases"],
        overall_compliance_rate=aggregate["overall_compliance_rate"],
        phase1_rejection_rate=aggregate["phase1_rejection_rate"],
        phase2_rejection_rate=aggregate["phase2_rejection_rate"],
        phase3_rejection_rate=aggregate["phase3_rejection_rate"],
        phase4_rejection_rate=aggregate["phase4_rejection_rate"],
        justified_rejections=aggregate["justified_rejections"],
        unjustified_rejections=aggregate["unjustified_rejections"],
        top_rule_violations=aggregate["top_rule_violations"],
        data_source_compliant_cases=aggregate.get("data_source_compliant_cases", 0),
        data_source_violation_cases=aggregate.get("data_source_violation_cases", 0),
        cases_with_preprocessing_issues=aggregate["cases_with_preprocessing_issues"],
        data_quality_impact_on_rejections=aggregate[
            "data_quality_impact_on_rejections"
        ],
        top_agent_fixes=aggregate["top_agent_fixes"],
        top_rule_clarifications=aggregate["top_rule_clarifications"],
        top_data_quality_fixes=aggregate["top_data_quality_fixes"],
        executive_summary=aggregate["executive_summary"],
    )
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_model.model_dump(), f, indent=2, ensure_ascii=False)

    print(f"\n{'=' * 80}")
    print(f"Results saved to: {output_dir}")
    print(f"  Summary: {summary_file}")
    print(f"  Cases: {case_dir}/")
    print("=" * 80)


def _load_and_print_config(args) -> str:
    """Load master data, print configuration header, and return domain name."""
    if _MASTER_DATA_AVAILABLE:
        try:
            _master_data_container["instance"] = load_master_data(args.master_data)
        except FileNotFoundError:
            print("  Note: No master data file found. Using hardcoded defaults.")
        except Exception as e:
            print(
                f"  Note: Failed to load master data ({e}). Using hardcoded defaults."
            )

    _md = _get_master_data()
    domain_name = _md.display_name if _md else "Invoice Processing"
    print("=" * 80)
    print(f"AGENT PROCESSING INVESTIGATION ({domain_name})")
    print("=" * 80)
    print("\nVersion: 2.1.0 (Domain-Independent)")
    print("\nConfiguration:")
    print(f"  Domain: {domain_name}")
    if _md and _md.source_path:
        print(f"  Master data: {_md.source_path}")
    print(f"  Project: {_gcp_config['PROJECT_ID']}")
    print(f"  Model: {_gcp_config['GEMINI_PRO_MODEL']}")
    print(f"  Rules: {RULES_BOOK_PATH}")
    print(f"  Layer 3: {'DISABLED' if args.disable_layer3 else 'ENABLED'}")
    print(f"  Double-check: {'DISABLED' if args.disable_double_check else 'ENABLED'}")
    return domain_name


def _init_validators(args, rule_discovery):
    """Initialize all validators and return them as a tuple.

    Returns (llm_validator, data_source_validator, bypass_detector,
             tolerance_extractor, per_group_validator, discovered_rules).
    """
    llm_validator = LLMRulesValidatorReconstructed(
        RULES_EXTRACTOR, _gcp_config["GEMINI_PRO_MODEL"]
    )
    data_source_validator = DataSourceValidator(rule_discovery=rule_discovery)
    bypass_detector = BypassDetector(RULES_EXTRACTOR, rule_discovery=rule_discovery)
    tolerance_extractor = ToleranceExtractor(
        RULES_EXTRACTOR, rule_discovery=rule_discovery
    )
    per_group_validator = None
    discovered = rule_discovery.discover_rules(force_refresh=False)
    if not args.disable_layer3:
        per_group_validator = PerGroupValidator(
            _gcp_config["GEMINI_PRO_MODEL"], INVESTIGATION_CONFIG
        )
    else:
        discovered = None
    return (
        llm_validator,
        data_source_validator,
        bypass_detector,
        tolerance_extractor,
        per_group_validator,
        discovered,
    )


def main():
    """Main entry point."""
    args = _build_arg_parser().parse_args()
    _load_and_print_config(args)

    # Layer 2: Rule Discovery
    print(f"\n{'=' * 80}")
    print("LAYER 2: Rule Discovery")
    print("=" * 80)
    rule_discovery = RuleDiscoveryEngine(
        RULES_BOOK_CONTENT, _gcp_config["GEMINI_PRO_MODEL"]
    )
    discovered_rules = rule_discovery.discover_rules(
        force_refresh=args.force_rule_discovery
    )
    rule_groups = discovered_rules.get("rule_groups", [])
    print(f"  Discovered {len(rule_groups)} rule groups:")
    for group in rule_groups:
        print(
            f"    - {group.get('name', group.get('group_id', '?'))}: {len(group.get('rules', []))} rule(s)"
        )

    if args.show_rule_groups:
        _print_rule_groups_detail(rule_groups)
        return

    # Initialize validators
    (
        llm_validator,
        data_source_validator,
        bypass_detector,
        tolerance_extractor,
        per_group_validator,
        discovered_rules,
    ) = _init_validators(args, rule_discovery)

    # Discover and filter cases
    print("\nDiscovering cases in agent output directory...")
    case_ids = discover_agent_cases(AGENT_OUTPUT_DIR)
    print(f"Found {len(case_ids)} processed cases")
    if not case_ids:
        print("\nNo cases found. Exiting.")
        return

    cases = _filter_cases(case_ids, args)
    if cases is None:
        return
    print(f"\nInvestigating {len(cases)} cases...")

    # Run investigations
    investigations = _run_case_investigations(
        cases,
        args,
        llm_validator,
        data_source_validator,
        bypass_detector,
        tolerance_extractor,
        per_group_validator,
        discovered_rules,
    )
    if not investigations:
        print("\n\nNo successful investigations.")
        return

    # Aggregate and report
    print(f"\n{'=' * 80}")
    aggregate = aggregate_agent_investigations(investigations)
    print_aggregate_report(aggregate)
    _save_results(investigations, aggregate)


def _print_rule_groups_detail(rule_groups: list) -> None:
    """Print detailed discovered rule groups and exit."""
    print(f"\n{'=' * 80}")
    print(f"DISCOVERED RULE GROUPS ({len(rule_groups)} total)")
    print("=" * 80)
    for group in rule_groups:
        print(f"\nGroup: {group.get('name', '?')}")
        print(f"  ID: {group.get('group_id', '?')}")
        print(f"  Description: {group.get('description', '')}")
        print(f"  Phases: {', '.join(group.get('applicable_phases', []))}")
        print(f"  Source: {group.get('source_section', 'N/A')}")
        print(f"  Rules ({len(group.get('rules', []))}):")
        for rule in group.get("rules", []):
            print(
                f"    - {rule.get('rule_id', '?')}: {str(rule.get('description', ''))[:80]}"
            )


if __name__ == "__main__":
    main()
