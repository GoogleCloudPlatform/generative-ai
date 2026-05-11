import html
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import HTTPException
from fastapi.responses import HTMLResponse

from app.state_schema import OnboardingStep


@dataclass
class LiveOnboardingCase:
    id: str
    session_id: str
    user_id: str
    employee: dict[str, str]
    current_step: str = OnboardingStep.WELCOME_SENT
    pending_signals: list[str] = field(default_factory=lambda: ["document_signed"])
    status: str = "waiting_for_employee_signature"
    document_signed: bool = False
    hardware_delivered: bool = False
    adk_status: str = "session_ready"
    events: list[dict[str, str]] = field(default_factory=list)
    artifacts: list[dict[str, str]] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


CASES: dict[str, LiveOnboardingCase] = {}
SESSION_TO_CASE: dict[str, str] = {}
LATEST_CASE_ID: str | None = None


def static_root() -> Path:
    return Path(__file__).parent / "static"


def artifact_root() -> Path:
    path = Path(__file__).resolve().parents[1] / "local_artifacts" / "onboarding"
    path.mkdir(parents=True, exist_ok=True)
    return path


def _employee() -> dict[str, str]:
    return {
        "name": "Olivia Bennett",
        "email": "olivia.bennett@example.com",
        "start_date": "2026-06-01",
        "role": "Product Manager",
        "team": "Platform Systems",
        "manager": "Avery Stone",
        "corporate_email": "olivia.bennett@example.com",
        "tracking_id": "HW-55443",
        "photo_url": "/live-onboarding/olivia-bennett.jpg",
    }


def _case_dir(case_id: str) -> Path:
    path = artifact_root() / case_id
    path.mkdir(parents=True, exist_ok=True)
    return path


def _event(case: LiveOnboardingCase, kind: str, title: str, detail: str) -> None:
    case.events.insert(
        0,
        {
            "kind": kind,
            "title": title,
            "detail": detail,
            "time": time.strftime("%H:%M:%S"),
        },
    )
    case.updated_at = time.time()


def _artifact(
    case: LiveOnboardingCase, artifact_id: str, title: str, kind: str, filename: str
) -> None:
    href = f"/api/live-onboarding/cases/{case.id}/artifacts/{artifact_id}"
    existing = next(
        (item for item in case.artifacts if item["id"] == artifact_id), None
    )
    payload = {
        "id": artifact_id,
        "title": title,
        "kind": kind,
        "filename": filename,
        "href": href,
        "created_at": time.strftime("%H:%M:%S"),
    }
    if existing:
        existing.update(payload)
    else:
        case.artifacts.insert(0, payload)


def _packet_html(case: LiveOnboardingCase, signed: bool = False) -> str:
    employee = case.employee
    signature = (
        html.escape(employee["name"]) if signed else "Pending employee signature"
    )
    signed_at = time.strftime("%Y-%m-%d %H:%M:%S %Z") if signed else ""
    signature_class = "signed" if signed else "pending"
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Onboarding Packet - {html.escape(employee["name"])}</title>
    <style>
      :root {{
        color-scheme: dark;
        --canvas: #12110e;
        --panel: #1f1e19;
        --panel-soft: #181713;
        --ink: #f4f1e8;
        --muted: #c8c2b6;
        --quiet: #989184;
        --line: #343229;
        --line-strong: #514e43;
        --accent: #f54e00;
        --green: #58b991;
      }}
      body {{
        margin: 0;
        padding: clamp(14px, 4vw, 34px);
        color: var(--ink);
        font-family: Inter, system-ui, "Helvetica Neue", Arial, sans-serif;
        background: var(--canvas);
      }}
      main {{
        max-width: 820px;
        margin: 0 auto;
        padding: clamp(18px, 4vw, 30px);
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--panel);
      }}
      header {{
        display: grid;
        grid-template-columns: minmax(0, 1fr) auto;
        align-items: flex-start;
        gap: 20px;
        border-bottom: 1px solid var(--line-strong);
        padding-bottom: 18px;
      }}
      h1 {{
        margin: 0;
        font-size: clamp(22px, 4vw, 28px);
        letter-spacing: 0;
        line-height: 1.18;
      }}
      h2 {{
        margin: 24px 0 8px;
        font-size: 16px;
      }}
      p, li {{
        font-size: 13px;
        line-height: 1.55;
      }}
      p, li, .signature {{
        color: var(--muted);
      }}
      .meta {{
        color: var(--quiet);
        font-family: ui-sans-serif, system-ui, sans-serif;
        font-size: 12px;
        line-height: 1.5;
        text-align: right;
        overflow-wrap: anywhere;
      }}
      .terms {{
        display: grid;
        grid-template-columns: repeat(2, minmax(0, 1fr));
        gap: 10px;
        margin: 18px 0;
      }}
      .term {{
        border: 1px solid var(--line);
        padding: 12px;
        font-family: ui-sans-serif, system-ui, sans-serif;
        background: var(--panel-soft);
      }}
      .term span {{
        display: block;
        color: var(--quiet);
        font-size: 12px;
        font-weight: 700;
        text-transform: uppercase;
      }}
      .term strong {{
        display: block;
        margin-top: 5px;
        font-size: 14px;
        overflow-wrap: anywhere;
      }}
      .signature {{
        margin-top: 24px;
        border: 1px solid var(--line);
        padding: 14px;
        font-family: ui-sans-serif, system-ui, sans-serif;
      }}
      .signature strong {{
        display: block;
        margin-top: 8px;
        color: var(--accent);
        font-size: clamp(20px, 4vw, 24px);
        font-family: "Brush Script MT", "Segoe Script", cursive;
        font-weight: 500;
      }}
      .signature.signed {{
        border-color: rgba(88, 185, 145, 0.45);
        background: #18251d;
      }}
      .stamp {{
        display: inline-block;
        margin-top: 10px;
        color: var(--green);
        font-size: 12px;
        font-weight: 800;
        text-transform: uppercase;
      }}
      @media (max-width: 620px) {{
        header,
        .terms {{
          grid-template-columns: 1fr;
        }}
        .meta {{
          text-align: left;
        }}
        ul {{
          padding-left: 20px;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <header>
        <div>
          <h1>New Hire Onboarding Packet</h1>
          <p>This local packet is generated for the demo workflow. It is not a legal contract or e-signature integration.</p>
        </div>
        <div class="meta">
          Packet ID: {html.escape(case.id)}<br />
          Session ID: {html.escape(case.session_id)}<br />
          Generated locally
        </div>
      </header>

      <section class="terms">
        <div class="term"><span>Employee</span><strong>{html.escape(employee["name"])}</strong></div>
        <div class="term"><span>Email</span><strong>{html.escape(employee["email"])}</strong></div>
        <div class="term"><span>Role</span><strong>{html.escape(employee["role"])}</strong></div>
        <div class="term"><span>Start date</span><strong>{html.escape(employee["start_date"])}</strong></div>
        <div class="term"><span>Team</span><strong>{html.escape(employee["team"])}</strong></div>
        <div class="term"><span>Manager</span><strong>{html.escape(employee["manager"])}</strong></div>
      </section>

      <h2>Welcome</h2>
      <p>
        Welcome to Platform Systems. This packet confirms the onboarding details that the HR
        onboarding coordinator will use to prepare access, equipment, and the Day One schedule.
      </p>

      <h2>Employee acknowledgements</h2>
      <ul>
        <li>I confirm that my onboarding profile is accurate.</li>
        <li>I acknowledge that IT access and hardware delivery depend on completing this packet.</li>
        <li>I understand this demo stores a local signed artifact for inspection by HR.</li>
      </ul>

      <section class="signature {signature_class}">
        Signature
        <strong>{signature}</strong>
        {"<span class='stamp'>Signed locally at " + html.escape(signed_at) + "</span>" if signed else ""}
      </section>
    </main>
  </body>
</html>"""


def _schedule_html(case: LiveOnboardingCase) -> str:
    employee = case.employee
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Day One Schedule</title>
    <style>
      :root {{
        color-scheme: dark;
        --canvas: #12110e;
        --panel: #1f1e19;
        --panel-soft: #181713;
        --ink: #f4f1e8;
        --muted: #c8c2b6;
        --quiet: #989184;
        --line: #343229;
        --accent: #f54e00;
      }}
      body {{
        margin: 0;
        padding: clamp(14px, 4vw, 34px);
        color: var(--ink);
        font-family: Inter, system-ui, "Helvetica Neue", Arial, sans-serif;
        background: var(--canvas);
      }}
      main {{
        max-width: 760px;
        margin: 0 auto;
        padding: clamp(20px, 5vw, 34px);
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--panel);
      }}
      h1 {{
        margin: 0 0 10px;
        font-size: clamp(24px, 5vw, 34px);
        font-weight: 400;
        letter-spacing: -0.68px;
        line-height: 1.2;
      }}
      p {{
        margin: 0 0 28px;
        color: var(--muted);
        line-height: 1.55;
      }}
      ol {{
        display: grid;
        gap: 12px;
        margin: 0;
        padding: 0;
        list-style: none;
      }}
      li {{
        display: grid;
        grid-template-columns: minmax(58px, 72px) minmax(0, 1fr);
        gap: 16px;
        padding: 14px 16px;
        border: 1px solid var(--line);
        border-radius: 8px;
        color: var(--muted);
        background: var(--panel-soft);
      }}
      strong {{
        color: var(--accent);
        font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 13px;
        font-weight: 500;
      }}
      .meta {{
        color: var(--quiet);
        font-size: 13px;
      }}
      @media (max-width: 520px) {{
        li {{
          grid-template-columns: 1fr;
          gap: 6px;
        }}
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>Day One Schedule for {html.escape(employee["name"])}</h1>
      <p>Sent to {html.escape(employee["corporate_email"])} after hardware delivery was confirmed.</p>
      <ol>
        <li><strong>09:00</strong><span>Welcome and IT login setup</span></li>
        <li><strong>10:00</strong><span>Meet {html.escape(employee["manager"])} and the team</span></li>
        <li><strong>11:30</strong><span>Platform Systems overview</span></li>
        <li><strong>14:00</strong><span>Security and device walkthrough</span></li>
      </ol>
    </main>
  </body>
</html>"""


def _hardware_receipt_html(case: LiveOnboardingCase) -> str:
    employee = case.employee
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Hardware Delivery Receipt</title>
    <style>
      :root {{
        color-scheme: dark;
        --canvas: #12110e;
        --panel: #1f1e19;
        --panel-soft: #181713;
        --ink: #f4f1e8;
        --muted: #c8c2b6;
        --quiet: #989184;
        --line: #343229;
        --success: #58b991;
      }}
      body {{
        margin: 0;
        padding: clamp(14px, 4vw, 34px);
        color: var(--ink);
        font-family: Inter, system-ui, "Helvetica Neue", Arial, sans-serif;
        background: var(--canvas);
      }}
      main {{
        max-width: 680px;
        margin: 0 auto;
        padding: clamp(20px, 5vw, 34px);
        border: 1px solid var(--line);
        border-radius: 12px;
        background: var(--panel);
      }}
      h1 {{
        margin: 0 0 12px;
        font-size: clamp(24px, 5vw, 34px);
        font-weight: 400;
        letter-spacing: -0.68px;
        line-height: 1.2;
      }}
      p {{
        margin: 0;
        color: var(--muted);
        line-height: 1.55;
      }}
      .receipt {{
        margin-top: 24px;
        padding: 18px;
        border: 1px solid rgba(88, 185, 145, 0.42);
        border-radius: 8px;
        background: #18251d;
      }}
      .receipt span {{
        display: block;
        margin-bottom: 6px;
        color: var(--quiet);
        font-size: 12px;
        font-weight: 700;
        letter-spacing: 0.88px;
        text-transform: uppercase;
      }}
      strong {{
        color: var(--success);
        font-family: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, monospace;
        font-size: 14px;
        font-weight: 500;
      }}
    </style>
  </head>
  <body>
    <main>
      <h1>Hardware Delivery Receipt</h1>
      <p>Employee-confirmed local receipt generated by the onboarding demo.</p>
      <section class="receipt">
        <span>Confirmed delivery</span>
        <p><strong>{html.escape(employee["tracking_id"])}</strong> delivered to {html.escape(employee["name"])}.</p>
      </section>
    </main>
  </body>
</html>"""


def _write_artifact(case: LiveOnboardingCase, filename: str, body: str) -> None:
    (_case_dir(case.id) / filename).write_text(body, encoding="utf-8")


def case_payload(case: LiveOnboardingCase) -> dict[str, Any]:
    return {
        "id": case.id,
        "session_id": case.session_id,
        "user_id": case.user_id,
        "employee": case.employee,
        "current_step": case.current_step,
        "pending_signals": case.pending_signals,
        "status": case.status,
        "document_signed": case.document_signed,
        "hardware_delivered": case.hardware_delivered,
        "adk_status": case.adk_status,
        "events": case.events,
        "artifacts": case.artifacts,
        "updated_at": case.updated_at,
    }


async def create_live_case(session_service) -> LiveOnboardingCase:
    global LATEST_CASE_ID

    employee = _employee()
    case_id = str(uuid.uuid4())
    case = LiveOnboardingCase(
        id=case_id,
        session_id=case_id,
        user_id="employee",
        employee=employee,
    )
    await session_service.create_session(
        app_name="app",
        user_id=case.user_id,
        session_id=case.session_id,
        state={
            "current_step": OnboardingStep.WELCOME_SENT,
            "new_hire_details": {
                "name": employee["name"],
                "email": employee["email"],
                "start_date": employee["start_date"],
            },
            "pending_signals": ["document_signed"],
        },
    )
    _write_artifact(case, "welcome_packet.html", _packet_html(case))
    _artifact(
        case,
        "welcome-packet",
        "Unsigned onboarding packet",
        "html",
        "welcome_packet.html",
    )
    _event(
        case,
        "agent",
        "Welcome packet generated",
        "A real local HTML onboarding packet was generated and attached to this case.",
    )
    _event(
        case,
        "state",
        "Agent is waiting",
        "ADK session is parked at WELCOME_SENT until the employee signs the packet.",
    )
    CASES[case.id] = case
    SESSION_TO_CASE[case.session_id] = case.id
    LATEST_CASE_ID = case.id
    return case


async def mark_document_signed(case: LiveOnboardingCase, resume_handler) -> None:
    case.document_signed = True
    case.status = "waking_after_signature"
    case.current_step = OnboardingStep.DOCUMENTS_SIGNED
    case.pending_signals = []
    _write_artifact(
        case, "signed_onboarding_packet.html", _packet_html(case, signed=True)
    )
    _artifact(
        case,
        "signed-packet",
        "Signed onboarding packet",
        "html",
        "signed_onboarding_packet.html",
    )
    _event(
        case,
        "employee",
        f"{case.employee['name']} signed the packet",
        "The employee clicked Sign Packet. A signed local artifact was stored.",
    )
    _event(
        case,
        "webhook",
        "document_signed webhook fired",
        "The app called the same ADK resume handler used by /webhooks/document_signed.",
    )
    try:
        await resume_handler.receive_signed_documents_callback(
            user_id=case.user_id, session_id=case.session_id
        )
        case.adk_status = "document_resume_completed"
        case.current_step = OnboardingStep.IT_PROVISIONED
        case.pending_signals = ["hardware_delivered"]
        case.status = "waiting_for_hardware_delivery"
        _event(
            case,
            "agent",
            "ADK resume completed",
            "The document signature wake turn completed. HR can now wait for hardware delivery.",
        )
    except Exception as exc:
        case.adk_status = "document_resume_failed"
        case.status = "document_signed_adk_resume_failed"
        _event(case, "error", "ADK resume failed", str(exc))
    finally:
        case.updated_at = time.time()


async def mark_hardware_delivered(case: LiveOnboardingCase, resume_handler) -> None:
    case.hardware_delivered = True
    case.status = "waking_after_hardware_delivery"
    case.current_step = OnboardingStep.HARDWARE_DELIVERED
    case.pending_signals = []
    _write_artifact(
        case,
        "hardware_delivery_receipt.html",
        _hardware_receipt_html(case),
    )
    _artifact(
        case,
        "hardware-receipt",
        "Hardware delivery receipt",
        "html",
        "hardware_delivery_receipt.html",
    )
    _event(
        case,
        "employee",
        f"{case.employee['name']} confirmed laptop delivery",
        f"Employee confirmed receipt of tracking ID {case.employee['tracking_id']}.",
    )
    _event(
        case,
        "webhook",
        "hardware_delivered webhook fired",
        "The app called the same ADK resume handler used by /webhooks/hardware_delivered.",
    )
    try:
        await resume_handler.receive_hardware_delivery_callback(
            user_id=case.user_id,
            session_id=case.session_id,
            tracking_id=case.employee["tracking_id"],
        )
        case.adk_status = "hardware_resume_completed"
        case.current_step = OnboardingStep.COMPLETED
        case.status = "completed"
        _write_artifact(case, "day_one_schedule.html", _schedule_html(case))
        _artifact(
            case,
            "day-one-schedule",
            "Day One schedule",
            "html",
            "day_one_schedule.html",
        )
        _event(
            case,
            "agent",
            "Onboarding completed",
            "The hardware wake turn completed and a local Day One schedule artifact was stored.",
        )
    except Exception as exc:
        case.adk_status = "hardware_resume_failed"
        case.status = "hardware_delivered_adk_resume_failed"
        _event(case, "error", "ADK resume failed", str(exc))
    finally:
        case.updated_at = time.time()


def case_for_session(session_id: str) -> LiveOnboardingCase | None:
    case_id = SESSION_TO_CASE.get(session_id)
    if not case_id:
        return None
    return CASES.get(case_id)


def get_case(case_id: str) -> LiveOnboardingCase:
    case = CASES.get(case_id)
    if not case:
        raise HTTPException(status_code=404, detail="Onboarding case not found")
    return case


def artifact_response(case_id: str, artifact_id: str) -> HTMLResponse:
    case = get_case(case_id)
    artifact = next(
        (item for item in case.artifacts if item["id"] == artifact_id), None
    )
    if not artifact:
        raise HTTPException(status_code=404, detail="Artifact not found")
    path = _case_dir(case.id) / artifact["filename"]
    if not path.exists():
        raise HTTPException(status_code=404, detail="Artifact file not found")
    return HTMLResponse(path.read_text(encoding="utf-8"))


def empty_case_payload() -> dict[str, Any]:
    return {"active": False, "message": "No live onboarding case has been started."}


def latest_case_payload() -> dict[str, Any]:
    if not LATEST_CASE_ID or LATEST_CASE_ID not in CASES:
        return empty_case_payload()
    return {"active": True, "case": case_payload(CASES[LATEST_CASE_ID])}
