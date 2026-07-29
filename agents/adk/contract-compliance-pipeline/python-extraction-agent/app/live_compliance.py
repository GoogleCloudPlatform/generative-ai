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

import html
import os
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from fastapi import HTTPException
from fastapi.responses import HTMLResponse
from app.state_schema import ComplianceStep

# Directories for artifact storage (relative to project root)
SANDBOX_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
ARTIFACTS_ROOT = os.path.join(SANDBOX_ROOT, "local_artifacts")


def _secure_artifact_dir(case_id: str) -> Path:
    """Resolves target case directories securely and verifies bounds limit (Rule 8)."""
    safe_case_id = os.path.basename(case_id)
    target_dir = os.path.join(ARTIFACTS_ROOT, "compliance", safe_case_id)
    
    # Fully resolve absolute path boundaries
    absolute_root = os.path.abspath(ARTIFACTS_ROOT) + os.path.sep
    absolute_target = os.path.abspath(target_dir)
    
    if not absolute_target.startswith(absolute_root):
        raise PermissionError("Access Denied: Path traversal detected on artifact write.")
        
    path_obj = Path(absolute_target)
    path_obj.mkdir(parents=True, exist_ok=True)
    return path_obj


@dataclass
class LiveComplianceCase:
    id: str
    session_id: str
    user_id: str
    filename: str
    current_step: str = ComplianceStep.INGESTED
    pending_signals: list[str] = field(default_factory=list)
    status: str = "started"
    adk_status: str = "session_created"
    risk_tier: str = "MEDIUM"
    passed: bool = False
    handoff: dict[str, Any] = field(default_factory=dict)
    events: list[dict[str, str]] = field(default_factory=list)
    artifacts: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


CASES: dict[str, LiveComplianceCase] = {}
SESSION_TO_CASE: dict[str, str] = {}
LATEST_CASE_ID: str | None = None


def get_case(case_id: str) -> LiveComplianceCase:
    case = CASES.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Compliance case not found")
    return case


def _event(case: LiveComplianceCase, kind: str, title: str, detail: str) -> None:
    case.events.insert(0, {
        "kind": kind,
        "title": title,
        "detail": detail,
        "time": time.strftime("%H:%M:%S"),
    })
    case.updated_at = time.time()


def _artifact(case: LiveComplianceCase, artifact_id: str, title: str, filename: str) -> None:
    href = f"/api/compliance/cases/{case.id}/artifacts/{artifact_id}"
    existing = next((item for item in case.artifacts if item["id"] == artifact_id), None)
    payload = {
        "id": artifact_id,
        "title": title,
        "filename": filename,
        "href": href,
        "created_at": time.strftime("%H:%M:%S"),
    }
    if existing:
        existing.update(payload)
    else:
        case.artifacts.insert(0, payload)


# --- HTML VISUAL REPORTS RENDERERS ---

def _extracted_fields_html(case: LiveComplianceCase, details: dict, risk: dict) -> str:
    factors_li = "".join([f"<li>{html.escape(f)}</li>" for f in risk.get("risk_factors", [])])
    if not factors_li:
        factors_li = "<li>No significant legal risk factors identified.</li>"
        
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Extraction Summary - Case {html.escape(case.id)}</title>
    <style>
      :root {{
        --bg: #121212;
        --card: #181818;
        --card-soft: #1f1f1f;
        --ink: #ffffff;
        --muted: #b3b3b3;
        --quiet: #7c7c7c;
        --line: #4d4d4d;
        --accent: #1ed760;
        --accent-hover: #1db954;
        --error: #f3727f;
        --amber: #ffa42b;
        --shadow-heavy: rgba(0, 0, 0, 0.5) 0px 8px 24px;
        --shadow-card: rgba(0, 0, 0, 0.3) 0px 8px 8px;
        --shadow-inset: rgb(18, 18, 18) 0px 1px 0px, rgb(124, 124, 124) 0px 0px 0px 1px inset;
        --font-title: SpotifyMixUITitle, CircularSp-Arab, CircularSp-Hebr, CircularSp-Cyrl, CircularSp-Grek, CircularSp-Deva, "Helvetica Neue", Helvetica, Arial, "Hiragino Sans", "Hiragino Kaku Gothic ProN", Meiryo, "MS Gothic", sans-serif;
        --font-ui: SpotifyMixUI, CircularSp-Arab, CircularSp-Hebr, CircularSp-Cyrl, CircularSp-Grek, CircularSp-Deva, "Helvetica Neue", Helvetica, Arial, "Hiragino Sans", "Hiragino Kaku Gothic ProN", Meiryo, "MS Gothic", sans-serif;
      }}
      body {{
        margin: 0;
        padding: clamp(14px, 4vw, 34px);
        color: var(--ink);
        font-family: var(--font-ui);
        background: var(--bg);
      }}
      main {{
        max-width: 800px;
        margin: 0 auto;
        padding: clamp(20px, 4vw, 30px);
        border: 0;
        border-radius: 8px;
        background: var(--card);
        box-shadow: var(--shadow-heavy);
      }}
      header {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: flex-start;
        gap: 20px;
        border-bottom: 1px solid var(--line);
        padding-bottom: 18px;
        margin-bottom: 24px;
      }}
      h1 {{
        margin: 0;
        font-family: var(--font-title);
        font-size: 24px;
        font-weight: 700;
        line-height: 1.18;
      }}
      h2 {{
        margin: 24px 0 10px;
        font-size: 14px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        color: var(--ink);
      }}
      p, li {{
        font-size: 14px;
        line-height: 1.5;
        color: var(--muted);
      }}
      ul {{
        padding-left: 20px;
        margin: 0;
      }}
      .meta {{
        color: var(--quiet);
        font-family: monospace;
        font-size: 11px;
        text-align: right;
      }}
      .grid {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 12px;
        margin: 18px 0;
      }}
      .item {{
        border: 0;
        padding: 12px;
        background: var(--card-soft);
        border-radius: 8px;
        box-shadow: var(--shadow-inset);
      }}
      .item span {{
        display: block;
        color: var(--quiet);
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        margin-bottom: 4px;
      }}
      .item strong {{
        display: block;
        font-size: 16px;
      }}
      .badge {{
        display: inline-block;
        padding: 4px 8px;
        border-radius: 99px;
        font-size: 10.5px;
        font-weight: 600;
        text-transform: uppercase;
        border: 1px solid currentColor;
      }}
      .badge.high {{ background: transparent; color: var(--error); }}
      .badge.medium {{ background: transparent; color: var(--amber); }}
      .badge.low {{ background: transparent; color: var(--accent); }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <h1>Legal Ingestion Parameter Sheet</h1>
          <p>Extracted variables from raw document text by Extractor Specialist subagent.</p>
        </div>
        <div class="meta">
          Case: {html.escape(case.id[:8])}<br />
          Ingested: {html.escape(case.filename)}
        </div>
      </header>
      
      <h2>Core Parameters</h2>
      <section class="grid">
        <div class="item"><span>Contractor / Vendor</span><strong>{html.escape(details.get("contractor_name", "N/A"))}</strong></div>
        <div class="item"><span>Client Entity</span><strong>{html.escape(details.get("client_name", "N/A"))}</strong></div>
        <div class="item"><span>Total Contract Value</span><strong>${details.get("contract_value", 0.0):,.2f}</strong></div>
        <div class="item"><span>Contract Duration</span><strong>{details.get("term_length_years", 1)} year(s) ({html.escape(details.get("start_date", ""))} to {html.escape(details.get("end_date", ""))})</strong></div>
        <div class="item"><span>Liability Capping Limits</span><strong>{html.escape(details.get("liability_limit", "N/A"))}</strong></div>
        <div class="item"><span>Commercial Insurance Coverage</span><strong>${details.get("insurance_coverage", 0.0):,.2f}</strong></div>
        <div class="item"><span>Auto-Renewal Trigger</span><strong>{ "Yes (Auto-renewal enabled)" if details.get("auto_renewal") else "No (Term terminates cleanly)" }</strong></div>
        <div class="item"><span>Exit Notices Safety</span><strong>{ "Termination Safety Clause exists" if details.get("has_termination_clause") else "None (Missing standard exit notices!)" }</strong></div>
      </section>
      
      <h2>Specialist Risk Diagnostics</h2>
      <div class="item" style="margin-bottom: 12px;">
        <span style="margin-bottom: 6px;">Evaluated Risk Level Bounds</span>
        <span class="badge {risk.get('risk_tier', 'MEDIUM').lower()}">{html.escape(risk.get("risk_tier", "MEDIUM"))} Legal Risk</span>
      </div>
      <h2>Key Risk Indicators (KRIs)</h2>
      <ul>
        {factors_li}
      </ul>
    </main>
  </body>
</html>"""


def _compliance_cert_html(case: LiveComplianceCase, details: dict, verdict: dict) -> str:
    passed = verdict.get("passed", False)
    status_class = "approved" if passed else "flagged"
    violations = [str(v) for v in verdict.get("violations", [])]
    violation_count = len(violations)
    if "SYSTEM TIMEOUT" in "".join(violations):
        status_class = "manual"
        
    verdict_text = "PASSED COMPLIANCE" if passed else "FLAGGED FOR REVIEW"
    if status_class == "manual":
        verdict_text = "ROUTED FOR MANUAL REVIEW"

    verdict_caption = (
        "Zero policy threshold exceptions identified."
        if passed
        else f"{violation_count} policy exception{'s' if violation_count != 1 else ''} require legal review."
    )
    if status_class == "manual":
        verdict_caption = "Fail-close routing activated because the remote compliance service was unavailable."

    violations_li = "".join(
        [
            (
                "<li>"
                f"<span>Exception {idx}</span>"
                f"<strong>{html.escape(v)}</strong>"
                "</li>"
            )
            for idx, v in enumerate(violations, 1)
        ]
    )
    if passed:
        violations_li = "<li><span>Clear</span><strong>Zero policy threshold exceptions identified.</strong></li>"
    elif not violations_li:
        violations_li = "<li><span>Review</span><strong>Go returned a review verdict without enumerated policy exceptions.</strong></li>"
        
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Compliance Certificate - {html.escape(details.get("contractor_name", "Vendor"))}</title>
    <style>
      :root {{
        --bg: #121212;
        --card: #181818;
        --card-soft: #1f1f1f;
        --ink: #ffffff;
        --muted: #b3b3b3;
        --quiet: #7c7c7c;
        --line: #4d4d4d;
        --success: #1ed760;
        --success-ink: #121212;
        --error: #f3727f;
        --amber: #ffa42b;
        --shadow-heavy: rgba(0, 0, 0, 0.5) 0px 8px 24px;
        --shadow-card: rgba(0, 0, 0, 0.3) 0px 8px 8px;
        --font-title: SpotifyMixUITitle, CircularSp-Arab, CircularSp-Hebr, CircularSp-Cyrl, CircularSp-Grek, CircularSp-Deva, "Helvetica Neue", Helvetica, Arial, "Hiragino Sans", "Hiragino Kaku Gothic ProN", Meiryo, "MS Gothic", sans-serif;
        --font-ui: SpotifyMixUI, CircularSp-Arab, CircularSp-Hebr, CircularSp-Cyrl, CircularSp-Grek, CircularSp-Deva, "Helvetica Neue", Helvetica, Arial, "Hiragino Sans", "Hiragino Kaku Gothic ProN", Meiryo, "MS Gothic", sans-serif;
      }}
      body {{
        margin: 0;
        padding: clamp(14px, 4vw, 34px);
        color: var(--ink);
        font-family: var(--font-ui);
        background: var(--bg);
      }}
      main {{
        max-width: 760px;
        margin: 0 auto;
        padding: clamp(24px, 5vw, 36px);
        border: 0;
        border-radius: 8px;
        background: var(--card);
        position: relative;
        box-shadow: var(--shadow-heavy);
      }}
      h1 {{
        margin: 0 0 6px;
        font-family: var(--font-title);
        font-size: 24px;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        line-height: 1.15;
      }}
      h2 {{
        margin: 24px 0 10px;
        font-size: 14px;
        text-transform: uppercase;
        letter-spacing: 1.4px;
        color: var(--quiet);
        border-bottom: 1px solid var(--line);
        padding-bottom: 6px;
      }}
      p, li {{
        font-size: 14px;
        line-height: 1.5;
        color: var(--muted);
      }}
      .badge-strip {{
        border: 1px solid var(--line);
        padding: 18px;
        border-radius: 8px;
        margin: 20px 0;
        text-align: center;
        background: var(--card-soft);
        box-shadow: var(--shadow-card);
      }}
      .badge-strip.approved {{
        border-color: var(--success);
        color: var(--success);
      }}
      .badge-strip.flagged {{
        border-color: var(--error);
        color: var(--error);
      }}
      .badge-strip.manual {{
        border-color: var(--amber);
        color: var(--amber);
      }}
      .badge-strip strong {{
        display: block;
        font-size: 26px;
        font-weight: 700;
        letter-spacing: 1.2px;
        margin-bottom: 4px;
      }}
      .badge-strip span {{
        display: block;
        font-size: 11px;
        text-transform: uppercase;
        letter-spacing: 0.8px;
      }}
      .exception-count {{
        display: inline-flex;
        align-items: center;
        justify-content: center;
        min-width: 34px;
        height: 28px;
        margin-right: 8px;
        border-radius: 999px;
        background: var(--card-soft);
        color: var(--error);
        font-weight: 700;
      }}
      ul {{
        padding-left: 20px;
        margin: 0;
      }}
      .exception-list {{
        display: flex;
        flex-direction: column;
        gap: 10px;
        padding: 0;
        list-style: none;
      }}
      .exception-list li {{
        border: 1px solid var(--line);
        border-left: 4px solid { "var(--success)" if passed else ("var(--amber)" if status_class == "manual" else "var(--error)") };
        border-radius: 8px;
        background: var(--card-soft);
        padding: 12px 14px;
      }}
      .exception-list span {{
        display: block;
        margin-bottom: 4px;
        color: var(--quiet);
        font-size: 10px;
        font-weight: 700;
        letter-spacing: 0.8px;
        text-transform: uppercase;
      }}
      .exception-list strong {{
        color: var(--ink);
        font-size: 14px;
        line-height: 1.45;
      }}
      .cert-meta {{
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        margin-top: 28px;
        padding-top: 18px;
        border-top: 1px solid var(--line);
        font-size: 11px;
        color: var(--quiet);
      }}
      .stamp {{
        border: 2px dashed var(--line);
        padding: 10px;
        text-align: center;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: bold;
        text-transform: uppercase;
        color: var(--line);
      }}
      .stamp.approved-stamp {{
        border-color: var(--success);
        color: var(--success);
      }}
      .stamp.rejected-stamp {{
        border-color: var(--error);
        color: var(--error);
      }}
      .stamp.review-stamp {{
        border-color: var(--amber);
        color: var(--amber);
      }}
    </style>
  </head>
  <body>
    <main>
      <div style="text-align: center; margin-bottom: 12px;">
        <h1 style="color: var(--quiet); font-size: 12px; margin-bottom: 4px; font-family: var(--font-ui); font-weight: 700;">Contract Compliance Engine</h1>
        <h1>A2A Audit Certificate</h1>
      </div>
      
      <div class="badge-strip {status_class}">
        <strong>{verdict_text}</strong>
        <span>{html.escape(verdict_caption)}</span>
      </div>
      
      <h2>Validation Diagnostics Summary</h2>
      <p>
        Contract compliance validation conducted by <strong>go-compliance-agent</strong> micro-service on a dedicated Go validation container running policy rules validation.
      </p>
      
      <h2><span class="exception-count">{violation_count}</span>Policy Threshold Exception Log</h2>
      <ul class="exception-list">
        {violations_li}
      </ul>
      
      <div class="cert-meta">
        <div>
          <strong>Case transaction ID:</strong> {html.escape(case.id)}<br />
          <strong>A2A target container:</strong> go-compliance-agent:8888<br />
          <strong>Audit Timestamp:</strong> {html.escape(verdict.get("verdict_timestamp", ""))}
        </div>
        <div style="justify-self: end; width: 180px;">
          {f"<div class='stamp approved-stamp'>Approved Safe</div>" if passed else (f"<div class='stamp review-stamp'>Manual Review</div>" if status_class == "manual" else "<div class='stamp rejected-stamp'>Review Required</div>")}
        </div>
      </div>
    </main>
  </body>
</html>"""


# --- CORE CASE OPERATIONS ---

async def create_compliance_case(filename: str, db_session_service) -> LiveComplianceCase:
    """Scaffolds the active case data structure and registers persistent SQLite sessions."""
    global LATEST_CASE_ID
    
    case_id = str(uuid.uuid4())
    case = LiveComplianceCase(
        id=case_id,
        session_id=case_id,
        user_id="ops_center",
        filename=filename
    )
    
    # Register the session in the sqlite persistence engine (enables resume matching)
    await db_session_service.create_session(
        app_name="app",
        user_id=case.user_id,
        session_id=case.session_id,
        state={
            "case_id": case.id,
            "current_step": ComplianceStep.INGESTED,
            "contract_filename": filename,
            "contract_details": {},
            "risk_assessment": {},
            "compliance_verdict": {},
            "pending_signals": []
        }
    )
    
    _event(case, "system", "Pipeline Initialized", f"Compliance audit started for contract '{filename}'.")
    _event(case, "agent", "Coordinator hydrated", "Contract extraction and Go compliance handoff ready.")
    
    CASES[case.id] = case
    SESSION_TO_CASE[case.session_id] = case.id
    LATEST_CASE_ID = case.id
    return case


def save_artifact_file(case: LiveComplianceCase, artifact_id: str, title: str, filename: str, content: str) -> None:
    """Saves generated visual HTML reports securely to sandboxed storage."""
    # Strip dangerous parameters to prevent directory traversals (Rule 8)
    safe_filename = os.path.basename(filename)
    
    # Enforces boundary and writes
    case_dir = _secure_artifact_dir(case.id)
    target_path = case_dir / safe_filename
    
    target_path.write_text(content, encoding="utf-8")
    _artifact(case, artifact_id, title, safe_filename)


def sync_case_with_session_state(case: LiveComplianceCase, state: dict) -> None:
    """Synchronizes in-memory dashboard cases with ADK database state parameters."""
    if not state:
        return
        
    case.current_step = state.get("current_step", case.current_step)
    case.pending_signals = state.get("pending_signals", case.pending_signals)
    
    details = state.get("contract_details", {})
    risk = state.get("risk_assessment", {})
    verdict = state.get("compliance_verdict", {})
    handoff = state.get("handoff", {})
    if handoff:
        case.handoff = handoff
    
    # Risk parameters mapping
    if risk:
        case.risk_tier = risk.get("risk_tier", case.risk_tier)
        
    # Verdict metrics mapping
    if verdict:
        case.passed = verdict.get("passed", False)
        
    # Synchronize tracking logs
    if "trace_logs" in state:
        # Avoid duplicate rendering in Cockpit dashboard
        case.events = [e for e in case.events if e["kind"] != "trace"]
        for log in state["trace_logs"]:
            _event(case, "trace", f"Span completed: {log['span']}", f"Service: {log['service']} | Duration: {log['duration_ms']}ms | Status: {log['status']}")
            
    # Check transitions to write artifacts dynamically
    if details and "parameters-sheet" not in [a["id"] for a in case.artifacts]:
        # extraction artifact generated
        html_param = _extracted_fields_html(case, details, risk)
        save_artifact_file(case, "parameters-sheet", "Legal parameters sheet", "parameters_sheet.html", html_param)
        _event(case, "agent", "Legal sheet generated", "A clean visual parameters sheet was compiled and attached to artifacts.")
        
    if verdict and "compliance-cert" not in [a["id"] for a in case.artifacts]:
        # compliance verification card compiled
        html_cert = _compliance_cert_html(case, details, verdict)
        save_artifact_file(case, "compliance-cert", "Compliance A2A Certificate", "compliance_certificate.html", html_cert)
        
        passed_lbl = "APPROVED" if case.passed else "REJECTED (EXCEPTIONS)"
        if "SYSTEM TIMEOUT" in "".join(verdict.get("violations", [])):
            passed_lbl = "PENDING MANUAL REVIEW (TIMEOUT)"
            
        _event(case, "agent", "A2A certificate generated", f"Auditing verdict verified: {passed_lbl}.")
        
    # Sync visual status flags
    if case.current_step == ComplianceStep.INGESTED:
        case.status = "processing_extraction"
    elif case.current_step == ComplianceStep.EXTRACTED:
        case.status = "processing_risk"
    elif case.current_step == ComplianceStep.COMPLIANCE_PENDING:
        case.status = "waiting_a2a_task"
        _event(case, "network", "A2A task pending", "Connection reports latency. State checkpoints saved for later completion.")
    elif case.current_step == ComplianceStep.COMPLIANCE_COMPLETE:
        case.status = "compiling_final_report"
    elif case.current_step == ComplianceStep.MANUAL_REVIEW:
        case.status = "manual_review_needed"
    elif case.current_step == ComplianceStep.REVIEW_READY:
        case.status = "review_completed_with_violations"
    elif case.current_step == ComplianceStep.APPROVED:
        case.status = "approved"
        
    case.updated_at = time.time()


def artifact_response(case_id: str, artifact_id: str) -> HTMLResponse:
    """Serves case artifact documents dynamically, verifying bounds (Rule 8 & 120)."""
    case = get_case(case_id)
    artifact = next((item for item in case.artifacts if item["id"] == artifact_id), None)
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact reference not found")
        
    # Enforces boundary limits
    safe_filename = os.path.basename(artifact["filename"])
    case_dir = _secure_artifact_dir(case.id)
    target_path = case_dir / safe_filename
    
    if not target_path.exists():
        raise HTTPException(status_code=404, detail="Artifact physical report file missing")
        
    return HTMLResponse(target_path.read_text(encoding="utf-8"))


def case_payload(case: LiveComplianceCase) -> dict[str, Any]:
    """Serializes the complete visual case payload for visual Cockpit frontend."""
    return {
        "id": case.id,
        "session_id": case.session_id,
        "user_id": case.user_id,
        "filename": case.filename,
        "current_step": case.current_step,
        "pending_signals": case.pending_signals,
        "status": case.status,
        "adk_status": case.adk_status,
        "risk_tier": case.risk_tier,
        "passed": case.passed,
        "handoff": case.handoff,
        "events": case.events,
        "artifacts": case.artifacts,
        "updated_at": case.updated_at,
    }


def latest_case_payload() -> dict[str, Any]:
    """Returns visual data on the latest audit case."""
    if not LATEST_CASE_ID or LATEST_CASE_ID not in CASES:
        return {"active": False, "message": "No compliance cases processed yet."}
    return {"active": True, "case": case_payload(CASES[LATEST_CASE_ID])}
