"""Configuration for the Invoice Processing learning core.

All paths resolved relative to this file's location.
LLM config loaded from shared .env file.
"""

import os
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Directory layout
# ---------------------------------------------------------------------------

CORE_DIR = Path(__file__).parent  # invoice_processing/core/
AGENT_PKG_DIR = CORE_DIR.parent  # invoice_processing/ (package root)

# Data lives inside the agent package (self-contained)
DATA_DIR = AGENT_PKG_DIR / "data"
AGENTIC_FLOW_OUT = DATA_DIR / "agent_output"
ALF_OUT_DIR = DATA_DIR / "alf_output"
RULE_BASE_PATH = DATA_DIR / "rule_base.json"
RULES_BOOK_PATH = DATA_DIR / "reconstructed_rules_book.md"
SESSIONS_DIR = DATA_DIR / "learning_sessions"

# Project root for .env resolution (contrib/python/invoice-processing/)
PROJECT_ROOT = AGENT_PKG_DIR.parent

# Legacy aliases (for backward compatibility within modules)
LEARNING_AGENT_DIR = AGENT_PKG_DIR

# ---------------------------------------------------------------------------
# Ensure shared_libraries is importable
# ---------------------------------------------------------------------------

_shared_libs_str = str(AGENT_PKG_DIR / "shared_libraries")
if _shared_libs_str not in sys.path:
    sys.path.insert(0, _shared_libs_str)

# ---------------------------------------------------------------------------
# .env loading
# ---------------------------------------------------------------------------

ENV_PATH = PROJECT_ROOT / ".env"
try:
    from dotenv import load_dotenv

    load_dotenv(ENV_PATH)
except ImportError:
    pass  # dotenv not installed; assume env vars are set externally

# ---------------------------------------------------------------------------
# LLM configuration (mirrors acting_agent / alf_engine.py)
# ---------------------------------------------------------------------------


def get_llm_project_id():
    """Return the Google Cloud project (deferred for Agent Engine compatibility).

    Reads GOOGLE_CLOUD_PROJECT, falling back to google.auth.default()
    for Agent Engine containers.
    """
    project = os.getenv("GOOGLE_CLOUD_PROJECT")
    if not project:
        try:
            import google.auth

            _, project = google.auth.default()
        except Exception:
            pass
    return project


def get_llm_location():
    """Return LOCATION from env (deferred for Agent Engine compatibility)."""
    return os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1")


def get_llm_model():
    """Return GEMINI_PRO_MODEL from env (deferred for Agent Engine compatibility)."""
    return os.getenv("GEMINI_PRO_MODEL", "gemini-3.5-pro")


def get_llm_call_delay():
    """Return API_CALL_DELAY_SECONDS from env (deferred for Agent Engine compatibility)."""
    return float(os.getenv("API_CALL_DELAY_SECONDS", "1.0"))


# ---------------------------------------------------------------------------
# Master data loader (optional — provides domain-agnostic configuration)
# ---------------------------------------------------------------------------

try:
    from ..shared_libraries.master_data_loader import load_master_data

    _master = load_master_data()
    _MASTER_DATA = _master
except Exception:
    _MASTER_DATA = None

# ---------------------------------------------------------------------------
# Artifact file mapping (agent output folder -> context key)
# Reads from master data if available, else uses hardcoded defaults.
# ---------------------------------------------------------------------------

if _MASTER_DATA and _MASTER_DATA.get_agent_file_map():
    _md_map = _MASTER_DATA.get_agent_file_map()
    ARTIFACT_MAP = {}
    for key, filename in _md_map.items():
        # Normalize master data keys to match what case_loader expects
        if key == "final_decision":
            ARTIFACT_MAP["decision"] = filename
        elif key == "transformation":
            ARTIFACT_MAP["transformer"] = filename
        else:
            ARTIFACT_MAP[key] = filename
else:
    ARTIFACT_MAP = {
        "classification": "01_classification.json",
        "extraction": "02_extraction.json",
        "phase1": "03_phase1_validation.json",
        "phase2": "04_phase2_validation.json",
        "phase3": "05_phase3_validation.json",
        "phase4": "06_phase4_validation.json",
        "transformer": "07_transformation.json",
        "decision": "08_decision.json",
        "audit_log": "09_audit_log.json",
        "postprocessing": "Postprocessing_Data.json",
    }

# ---------------------------------------------------------------------------
# Terminal formatting helpers
# ---------------------------------------------------------------------------


class Color:
    """ANSI color codes for terminal output."""

    BOLD = "\033[1m"
    DIM = "\033[2m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    RED = "\033[91m"
    CYAN = "\033[96m"
    MAGENTA = "\033[95m"
    BLUE = "\033[94m"
    RESET = "\033[0m"
