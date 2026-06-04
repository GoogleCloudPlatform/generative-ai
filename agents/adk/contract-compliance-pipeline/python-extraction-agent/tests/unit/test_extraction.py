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

import pytest
from pathlib import Path
from unittest.mock import MagicMock
from google.adk.tools import ToolContext
from app.state_schema import ComplianceStep
from app.tools import (
    _secure_resolve_path,
    classify_contract_risk,
    classify_risk_level,
    extract_contract_details_from_text,
    read_contract_text,
    save_extracted_fields,
)


PROJECT_ROOT = Path(__file__).resolve().parents[3]


@pytest.fixture
def mock_tool_context():
    """Fixture initializing state mapping structures."""
    context = MagicMock(spec=ToolContext)
    context.state = {
        "case_id": "test-case-id",
        "current_step": ComplianceStep.INGESTED,
        "contract_details": {},
        "risk_assessment": {},
        "compliance_verdict": {},
        "pending_signals": [],
        "trace_logs": []
    }
    return context


def test_read_contract_text_mock_loading(mock_tool_context):
    # Acme contract mock loading check
    text = read_contract_text("standard-vendor-agreement.pdf", mock_tool_context)
    assert "ACME CLOUD SOLUTIONS" in text
    assert "GFD PLATFORM SYSTEMS" in text
    assert "$250,000.00" in text


def test_extract_contract_details_from_physical_samples():
    sample_dir = PROJECT_ROOT / "sample-contracts"

    standard_text = (sample_dir / "standard-vendor-agreement.pdf").read_text()
    standard = extract_contract_details_from_text(
        "standard-vendor-agreement.pdf",
        standard_text,
    )
    assert standard["contract_value"] == 250000.0
    assert standard["contractor_name"] == "ACME CLOUD SOLUTIONS"
    assert standard["insurance_coverage"] == 2000000.0
    assert standard["term_length_years"] == 2
    assert standard["has_termination_clause"] is True
    assert classify_contract_risk(standard)["risk_tier"] == "LOW"

    non_compliant_text = (sample_dir / "non-compliant-contract.pdf").read_text()
    non_compliant = extract_contract_details_from_text(
        "non-compliant-contract.pdf",
        non_compliant_text,
    )
    assert non_compliant["contract_value"] == 850000.0
    assert non_compliant["contractor_name"] == "LEGACY NETWORKS CORP"
    assert non_compliant["insurance_coverage"] == 500000.0
    assert non_compliant["auto_renewal"] is True
    assert non_compliant["has_termination_clause"] is False
    assert classify_contract_risk(non_compliant)["risk_tier"] == "HIGH"


def test_read_contract_text_path_traversal_denied(mock_tool_context):
    # Verify core resolver raises correct PermissionError boundary violations (Rule 8)
    with pytest.raises(PermissionError, match="Access Denied: Path traversal attack detected."):
        _secure_resolve_path("../../../etc/passwd")
        
    # Verify client facing tool catches exception and returns safe diagnostic string
    res = read_contract_text("../../../etc/passwd", mock_tool_context)
    assert "[Error reading file: Access Denied: Path traversal attack detected.]" in res


def test_save_extracted_fields_state_mutations(mock_tool_context):
    details = {
        "contract_value": 300000.0,
        "contractor_name": "Test Vendor Corp",
        "client_name": "GFD Platform Systems",
        "start_date": "2026-06-01",
        "end_date": "2029-06-01",
        "liability_limit": "$1,500,000 limits cap",
        "insurance_coverage": 2000000.0,
        "auto_renewal": False,
        "has_termination_clause": True,
    }
    
    res = save_extracted_fields(
        contract_value=details["contract_value"],
        contractor_name=details["contractor_name"],
        client_name=details["client_name"],
        start_date=details["start_date"],
        end_date=details["end_date"],
        liability_limit=details["liability_limit"],
        insurance_coverage=details["insurance_coverage"],
        auto_renewal=details["auto_renewal"],
        has_termination_clause=details["has_termination_clause"],
        tool_context=mock_tool_context
    )
    
    assert res["status"] == "success"
    
    # Assert persistent mutations mapping
    state = mock_tool_context.state
    assert state["current_step"] == ComplianceStep.EXTRACTED
    assert state["contract_details"]["contractor_name"] == "Test Vendor Corp"
    assert state["contract_details"]["term_length_years"] == 3  # (2029 - 2026)


def test_classify_risk_level_tiers(mock_tool_context):
    state = mock_tool_context.state
    
    # 1. Low risk evaluation mapping
    state["contract_details"] = {
        "contract_value": 150000.0,
        "contractor_name": "A",
        "liability_limit": "$1M limited cap",
        "term_length_years": 2,
        "has_termination_clause": True,
    }
    classify_risk_level(mock_tool_context)
    assert state["risk_assessment"]["risk_tier"] == "LOW"
    assert len(state["risk_assessment"]["risk_factors"]) == 0
    
    # 2. High risk evaluation matching unlimited liability
    state["contract_details"] = {
        "contract_value": 250000.0,
        "contractor_name": "B",
        "liability_limit": "Unlimited GFD Liability exposure",
        "term_length_years": 3,
        "has_termination_clause": True,
    }
    classify_risk_level(mock_tool_context)
    assert state["risk_assessment"]["risk_tier"] == "HIGH"
    assert "Unlimited contractor liability" in state["risk_assessment"]["risk_factors"]
