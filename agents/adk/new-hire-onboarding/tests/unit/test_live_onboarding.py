import pytest

from app.live_onboarding import (
    CASES,
    SESSION_TO_CASE,
    artifact_response,
    create_live_case,
    mark_document_signed,
    mark_hardware_delivered,
)


class FakeSessionService:
    def __init__(self) -> None:
        self.created_sessions: list[dict] = []

    async def create_session(self, **kwargs) -> None:
        self.created_sessions.append(kwargs)


class FakeResumeHandler:
    def __init__(self) -> None:
        self.signed_calls: list[tuple[str, str]] = []
        self.hardware_calls: list[tuple[str, str, str]] = []

    async def receive_signed_documents_callback(
        self, user_id: str, session_id: str
    ) -> None:
        self.signed_calls.append((user_id, session_id))

    async def receive_hardware_delivery_callback(
        self, user_id: str, session_id: str, tracking_id: str
    ) -> None:
        self.hardware_calls.append((user_id, session_id, tracking_id))


@pytest.fixture(autouse=True)
def clear_live_state() -> None:
    CASES.clear()
    SESSION_TO_CASE.clear()


@pytest.mark.asyncio
async def test_create_live_case_generates_unsigned_packet() -> None:
    session_service = FakeSessionService()

    case = await create_live_case(session_service)

    assert case.status == "waiting_for_employee_signature"
    assert case.current_step == "WELCOME_SENT"
    assert case.pending_signals == ["document_signed"]
    assert [artifact["id"] for artifact in case.artifacts] == ["welcome-packet"]
    assert session_service.created_sessions[0]["session_id"] == case.session_id
    assert (
        "New Hire Onboarding Packet"
        in artifact_response(case.id, "welcome-packet").body.decode()
    )


@pytest.mark.asyncio
async def test_signature_resume_stores_signed_packet_and_waits_for_hardware() -> None:
    case = await create_live_case(FakeSessionService())
    resume_handler = FakeResumeHandler()

    await mark_document_signed(case, resume_handler)

    assert case.document_signed is True
    assert case.status == "waiting_for_hardware_delivery"
    assert case.current_step == "IT_PROVISIONED"
    assert case.pending_signals == ["hardware_delivered"]
    assert resume_handler.signed_calls == [(case.user_id, case.session_id)]
    assert [artifact["id"] for artifact in case.artifacts] == [
        "signed-packet",
        "welcome-packet",
    ]
    assert "Signed locally" in artifact_response(case.id, "signed-packet").body.decode()


@pytest.mark.asyncio
async def test_hardware_resume_creates_receipt_then_day_one_schedule() -> None:
    case = await create_live_case(FakeSessionService())
    resume_handler = FakeResumeHandler()
    await mark_document_signed(case, resume_handler)

    await mark_hardware_delivered(case, resume_handler)

    assert case.hardware_delivered is True
    assert case.status == "completed"
    assert case.current_step == "COMPLETED"
    assert case.pending_signals == []
    assert resume_handler.hardware_calls == [
        (case.user_id, case.session_id, case.employee["tracking_id"])
    ]
    assert [artifact["id"] for artifact in case.artifacts] == [
        "day-one-schedule",
        "hardware-receipt",
        "signed-packet",
        "welcome-packet",
    ]
    assert (
        "Hardware Delivery Receipt"
        in artifact_response(case.id, "hardware-receipt").body.decode()
    )
    assert (
        "Day One Schedule"
        in artifact_response(case.id, "day-one-schedule").body.decode()
    )
