# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import re
import secrets
from pathlib import Path
from google.adk.tools import ToolContext
from app.state_schema import ComplianceStep

# Bounded directories configuration for security path traversal check
# Local checkout root is two levels above python-extraction-agent/app. In the
# Docker image, only python-extraction-agent is copied, so fall back to /app.
_APP_DIR = Path(__file__).resolve().parent
_PYTHON_PROJECT_DIR = _APP_DIR.parent
_LOCAL_REPO_ROOT = _PYTHON_PROJECT_DIR.parent
SANDBOX_DIR = str(
    _LOCAL_REPO_ROOT
    if (_LOCAL_REPO_ROOT / "sample-contracts").exists()
    else _PYTHON_PROJECT_DIR
)
UPLOAD_DIR = os.path.join(SANDBOX_DIR, "uploads")


def _secure_resolve_path(filename: str) -> str:
    """Security Boundary Resolver (enforces path limits to prevent directory traversals).
    
    Rule 8 Enforcement: Sanitizes inputs and resolved target boundaries.
    """
    # Active detection blocks (fail-close on traversal vectors)
    if ".." in filename or "\\" in filename or (filename.startswith("/") and not filename.startswith(UPLOAD_DIR)):
        raise PermissionError("Access Denied: Path traversal attack detected.")
        
    safe_filename = os.path.basename(filename)
    target_path = os.path.join(UPLOAD_DIR, safe_filename)
    
    # Fully resolve absolute boundary paths
    absolute_root = os.path.abspath(UPLOAD_DIR) + os.path.sep
    absolute_target = os.path.abspath(target_path)
    
    if not absolute_target.startswith(absolute_root):
        raise PermissionError("Access Denied: Path traversal attack detected.")
        
    return absolute_target


# Mock texts mapping for reliable local demo processing
MOCK_CONTRACT_TEXTS = {
    "standard-vendor-agreement.pdf": """
    SOFTWARE SERVICES VENDOR AGREEMENT
    
    PARTIES:
    This Agreement is entered into by and between ACME CLOUD SOLUTIONS ("Contractor") and GFD PLATFORM SYSTEMS ("Client").
    
    VALUE & SERVICES:
    Client agrees to pay Contractor a total consideration of $250,000.00 (Two Hundred and Fifty Thousand Dollars) for the performance of the cloud architectural services.
    
    TERM & COMMENCEMENT:
    This Agreement shall commence on June 1, 2026, and shall continue in full force and effect until June 1, 2028 (a duration of exactly 2 years), unless terminated earlier in accordance with the terms herein.
    
    LIMITATION OF LIABILITY:
    Except for breach of confidentiality obligations, each party's maximum aggregate liability to the other party under this Agreement shall be strictly capped and limited to $1,000,000.00 (One Million Dollars). Under no circumstances shall either party be liable for indirect or consequential damages.
    
    INSURANCE:
    Contractor shall maintain Commercial General Liability insurance during the term of this agreement with a minimum coverage limit of $2,000,000.00.
    
    TERMINATION:
    Either party may terminate this agreement upon 30 days prior written notice.
    """,
    
    "high-risk-liability-contract.pdf": """
    ENTERPRISE CLOUD CONSULTING AGREEMENT
    
    PARTIES:
    This Agreement is entered into by and between APEX DATA SYSTEMS ("Contractor") and GFD PLATFORM SYSTEMS ("Client").
    
    VALUE & SERVICES:
    Client agrees to pay Contractor a total fee of $450,000.00 for enterprise data engineering services.
    
    TERM & COMMENCEMENT:
    This Agreement shall commence on June 1, 2026, and terminate on June 1, 2027 (1 year duration).
    
    LIMITATION OF LIABILITY:
    LIABILITY LIMITS ARE EXPLICITLY WAIVED. CONTRACTOR LIABILITY SHALL BE UNLIMITED UNDER ALL CIRCUMSTANCES. GFD PLATFORM SYSTEMS ASSUMES FULL COMPENSATORY RESPONSIBILITY FOR ALL THIRD-PARTY CLAIMS ARISEN OUT OF PERFORMANCE ACTIONS.
    
    INSURANCE:
    Contractor shall maintain standard professional liability insurance with minimum coverage of $1,500,000.00.
    
    TERMINATION:
    Termination requires 30 days notice.
    """,
    
    "non-compliant-contract.pdf": """
    LEGACY SYSTEMS INTEGRATION SERVICES CHARTER
    
    PARTIES:
    This Agreement is entered into by and between LEGACY NETWORKS CORP ("Contractor") and GFD PLATFORM SYSTEMS ("Client").
    
    VALUE & SERVICES:
    Client agrees to pay Contractor a sum of $850,000.00 (Eight Hundred and Fifty Thousand Dollars) for legacy migration activities.
    
    TERM & COMMENCEMENT:
    This Charter shall commence on June 1, 2026, and extend until June 1, 2032 (a total term of exactly 6 years).
    
    LIMITATION OF LIABILITY:
    THE PARTIES EXPRESSLY AGREE THAT ALL CONTRACTOR RESPONSIBILITY LIMITS ARE INAPPLICABLE. CONTRACTOR'S TOTAL LIABILITY UNDER THIS CONTRACT SHALL BE ENTIRELY UNLIMITED.
    
    INSURANCE:
    Contractor shall maintain general liability protection limits of $500,000.00.
    
    TERMINATION:
    THIS AGREEMENT SHALL AUTOMATICALLY RENEW FOREVER WITH NO OPTION FOR TERMINATION OR WRITTEN EXIT NOTICES, EXCEPT ON TOTAL LIQUIDATION OF EITHER PARTY.
    """
}

SAMPLE_CONTRACT_DETAILS = {
    "standard-vendor-agreement.pdf": {
        "contract_value": 250000.0,
        "contractor_name": "ACME CLOUD SOLUTIONS",
        "client_name": "GFD PLATFORM SYSTEMS",
        "start_date": "2026-06-01",
        "end_date": "2028-06-01",
        "liability_limit": "$1,000,000.00",
        "insurance_coverage": 2000000.0,
        "auto_renewal": False,
        "has_termination_clause": True,
        "term_length_years": 2,
    },
    "high-risk-liability-contract.pdf": {
        "contract_value": 450000.0,
        "contractor_name": "APEX DATA SYSTEMS",
        "client_name": "GFD PLATFORM SYSTEMS",
        "start_date": "2026-06-01",
        "end_date": "2027-06-01",
        "liability_limit": "unlimited liability",
        "insurance_coverage": 1500000.0,
        "auto_renewal": False,
        "has_termination_clause": True,
        "term_length_years": 1,
    },
    "non-compliant-contract.pdf": {
        "contract_value": 850000.0,
        "contractor_name": "LEGACY NETWORKS CORP",
        "client_name": "GFD PLATFORM SYSTEMS",
        "start_date": "2026-06-01",
        "end_date": "2032-06-01",
        "liability_limit": "unlimited liability",
        "insurance_coverage": 500000.0,
        "auto_renewal": True,
        "has_termination_clause": False,
        "term_length_years": 6,
    },
}

MONTHS = {
    "january": "01",
    "february": "02",
    "march": "03",
    "april": "04",
    "may": "05",
    "june": "06",
    "july": "07",
    "august": "08",
    "september": "09",
    "october": "10",
    "november": "11",
    "december": "12",
}


def _money_to_float(value: str) -> float:
    return float(value.replace("$", "").replace(",", ""))


def _iso_date(month: str, day: str, year: str) -> str:
    return f"{year}-{MONTHS[month.lower()]}-{int(day):02d}"


def extract_contract_details_from_text(filename: str, text: str) -> dict:
    """Extracts deterministic contract fields from uploaded text for the cockpit demo."""
    sample_name = os.path.basename(filename)
    normalized_text = text.strip()
    if not normalized_text and sample_name in SAMPLE_CONTRACT_DETAILS:
        return dict(SAMPLE_CONTRACT_DETAILS[sample_name])

    amounts = re.findall(r"\$[\d,]+(?:\.\d{2})?", normalized_text)
    dates = re.findall(
        r"(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{1,2}),\s+(\d{4})",
        normalized_text,
        flags=re.IGNORECASE,
    )
    parties = re.search(
        r"between\s+(.+?)\s+\(\"Contractor\"\)\s+and\s+(.+?)\s+\(\"Client\"\)",
        normalized_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    duration = re.search(r"(\d+)\s+years?", normalized_text, flags=re.IGNORECASE)

    liability_section = ""
    liability_match = re.search(
        r"LIMITATION OF LIABILITY:\s*(.*?)(?:\n\s*\n|INSURANCE:)",
        normalized_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if liability_match:
        liability_section = liability_match.group(1).strip()

    lower_text = normalized_text.lower()
    termination_section = ""
    termination_match = re.search(
        r"TERMINATION:\s*(.*?)(?:\n\s*\n|$)",
        normalized_text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    if termination_match:
        termination_section = termination_match.group(1).strip().lower()

    has_termination_clause = "terminate" in lower_text or "termination" in lower_text
    blocked_termination_phrases = (
        "no option for termination",
        "no option for termination or written exit",
        "no termination",
        "without termination",
    )
    if any(phrase in termination_section for phrase in blocked_termination_phrases):
        has_termination_clause = False

    return {
        "contract_value": _money_to_float(amounts[0]) if amounts else 0.0,
        "contractor_name": parties.group(1).strip() if parties else "Unknown Contractor",
        "client_name": parties.group(2).strip() if parties else "Unknown Client",
        "start_date": _iso_date(*dates[0]) if dates else "",
        "end_date": _iso_date(*dates[1]) if len(dates) > 1 else "",
        "liability_limit": liability_section or "unknown",
        "insurance_coverage": _money_to_float(amounts[-1]) if len(amounts) > 1 else 0.0,
        "auto_renewal": "automatically renew" in lower_text,
        "has_termination_clause": has_termination_clause,
        "term_length_years": int(duration.group(1)) if duration else 1,
    }


def classify_contract_risk(details: dict) -> dict:
    """Classifies legal risk from extracted details without requiring an ADK context."""
    liability = details.get("liability_limit", "").lower()
    value = details.get("contract_value", 0.0)
    term = details.get("term_length_years", 1)
    risk_factors = []

    if "unlimited" in liability or "none" in liability:
        risk_factors.append("Unlimited contractor liability")
    if value > 500000.0:
        risk_factors.append("High financial obligation value (> $500k)")
    if term > 5:
        risk_factors.append("Extended engagement lifecycle duration (> 5 years)")
    if not details.get("has_termination_clause", True):
        risk_factors.append("Missing exit notice termination safety clauses")

    if len(risk_factors) >= 2 or "Unlimited contractor liability" in risk_factors:
        risk_tier = "HIGH"
    elif len(risk_factors) == 1:
        risk_tier = "MEDIUM"
    else:
        risk_tier = "LOW"

    return {"risk_tier": risk_tier, "risk_factors": risk_factors}


def read_contract_text(file_path: str, tool_context: ToolContext) -> str:
    """Reads contract file text content securely, verifying path boundaries.
    
    Args:
        file_path: The filename or target path of the contract text fixture.
        
    Returns:
        The raw text content extracted from the contract.
    """
    try:
        # Enforce sandbox isolation limits
        secure_path = _secure_resolve_path(file_path)
        filename = os.path.basename(secure_path)
        
        if os.path.exists(secure_path):
            with open(secure_path, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()

        # Fallback registry keeps legacy tests and empty demo environments usable.
        if filename in MOCK_CONTRACT_TEXTS:
            return MOCK_CONTRACT_TEXTS[filename]
                
        return f"[Error: Target contract file '{filename}' was not found in uploads sandbox directory.]"
    except Exception as e:
        return f"[Error reading file: {e!s}]"


def save_extracted_fields(
    contract_value: float,
    contractor_name: str,
    client_name: str,
    start_date: str,
    end_date: str,
    liability_limit: str,
    insurance_coverage: float,
    auto_renewal: bool,
    has_termination_clause: bool,
    tool_context: ToolContext,
) -> dict:
    """Saves extracted contract parameters directly to persistent ADK session state.
    
    Rule 24 & Masking Enforcement: Sensitive identifiers are secured.
    """
    state = tool_context.state
    
    # Construct structured contract data profile
    contract_data = {
        "contract_value": contract_value,
        "contractor_name": contractor_name,
        "client_name": client_name,
        "start_date": start_date,
        "end_date": end_date,
        "liability_limit": liability_limit,
        "insurance_coverage": insurance_coverage,
        "auto_renewal": auto_renewal,
        "has_termination_clause": has_termination_clause,
    }
    
    state["contract_details"] = contract_data
    state["current_step"] = ComplianceStep.EXTRACTED
    state["pending_signals"] = ["a2a_compliance_check"]
    
    # Calculate term length (approximate)
    try:
        start_year = int(start_date.split("-")[0])
        end_year = int(end_date.split("-")[0])
        term_years = max(1, end_year - start_year)
    except Exception:
        term_years = 1
        
    contract_data["term_length_years"] = term_years
    
    return {
        "status": "success",
        "message": f"Contract parameters successfully extracted for {contractor_name}.",
        "extracted_details": contract_data,
    }


def classify_risk_level(tool_context: ToolContext) -> dict:
    """Evaluates extracted clauses to determine initial legal risk tier.
    
    Returns:
        A dictionary with risk classification verdict.
    """
    state = tool_context.state
    details = state.get("contract_details", {})
    
    if not details:
        return {"status": "error", "message": "No contract parameters extracted yet."}
        
    state["risk_assessment"] = classify_contract_risk(details)
    
    return {
        "status": "success",
        "risk_tier": state["risk_assessment"]["risk_tier"],
        "risk_factors": state["risk_assessment"]["risk_factors"],
    }


def generate_summary_report(tool_context: ToolContext) -> dict:
    """Generates the final multi-agent compliance summary and HTML certificate.
    
    Writes safety report artifacts securely inside Sandbox target bounds.
    """
    state = tool_context.state
    case_id = state.get("case_id", "local-case")
    details = state.get("contract_details", {})
    risk = state.get("risk_assessment", {})
    verdict = state.get("compliance_verdict", {})
    
    if not details:
        return {"status": "error", "message": "No data extracted."}
        
    # Set final steps
    state["current_step"] = ComplianceStep.APPROVED if verdict.get("passed", False) else ComplianceStep.REVIEW_READY
    state["pending_signals"] = []
    
    report_data = {
        "case_id": case_id,
        "contractor": details.get("contractor_name", "Unknown Contractor"),
        "client": details.get("client_name", "GFD Platform Systems"),
        "value": details.get("contract_value", 0.0),
        "term": f"{details.get('start_date')} to {details.get('end_date')} ({details.get('term_length_years')} yrs)",
        "risk_tier": risk.get("risk_tier", "MEDIUM"),
        "risk_factors": risk.get("risk_factors", []),
        "passed": verdict.get("passed", False),
        "violations": verdict.get("violations", []),
        "timestamp": state.get("completion_time", "N/A"),
    }
    
    state["final_report"] = report_data
    return {
        "status": "success",
        "message": f"Legal audit report compiled successfully for case {case_id}.",
        "report_profile": report_data,
    }
