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

import json
import logging

from google.adk.runners import Runner
from google.genai import types

from app.state_schema import OnboardingStep

logger = logging.getLogger(__name__)


class OnboardingResumeHandler:
    def __init__(self, runner: Runner):
        """Initializes the resume handler with the active ADK Runner."""
        self.runner = runner

    def _log_structured(self, severity: str, message: str, **kwargs) -> None:
        """Helper to output formatted JSON logs that Cloud Logging can parse natively."""
        payload = {"severity": severity, "message": message, **kwargs}
        logger.info(json.dumps(payload))

    async def receive_signed_documents_callback(
        self, user_id: str, session_id: str
    ) -> None:
        """Simulates an external webhook notifying that the employee signed onboarding documents.

        Hydrates the existing session, transitions the checkpoint to DOCUMENTS_SIGNED, and resumes.
        """
        self._log_structured(
            severity="INFO",
            message=f"Received document signature notification for session {session_id}",
            event="webhook_received",
            webhook_type="document_signed",
            session_id=session_id,
            user_id=user_id,
        )

        try:
            self._log_structured(
                severity="INFO",
                message=f"State machine transitioned to {OnboardingStep.DOCUMENTS_SIGNED}",
                event="state_transition",
                session_id=session_id,
                user_id=user_id,
                new_step=OnboardingStep.DOCUMENTS_SIGNED,
            )

            # Trigger runner wake-up and run execution ambiently
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text="Resume onboarding: Contract has been signed."
                        )
                    ],
                ),
                state_delta={
                    "current_step": OnboardingStep.DOCUMENTS_SIGNED,
                    "pending_signals": [],
                },
            ):
                self._log_structured(
                    severity="INFO",
                    message=f"Wake-up execution event: {event}",
                    event="runner_event",
                    session_id=session_id,
                    user_id=user_id,
                )

            self._log_structured(
                severity="INFO",
                message="Ambient document signature execution turn completed successfully",
                event="runner_turn_success",
                session_id=session_id,
                user_id=user_id,
            )
        except Exception as e:
            self._log_structured(
                severity="ERROR",
                message=f"Ambient document signature execution turn failed: {e!s}",
                event="runner_turn_failure",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
            )
            raise

    async def receive_hardware_delivery_callback(
        self, user_id: str, session_id: str, tracking_id: str
    ) -> None:
        """Simulates a carrier callback confirming laptop package delivery at the employee's house.

        Hydrates the session, transitions the checkpoint to HARDWARE_DELIVERED, and resumes.
        """
        self._log_structured(
            severity="INFO",
            message=f"Received hardware package delivery webhook for tracking ID {tracking_id}",
            event="webhook_received",
            webhook_type="hardware_delivered",
            session_id=session_id,
            user_id=user_id,
            tracking_id=tracking_id,
        )

        try:
            self._log_structured(
                severity="INFO",
                message=f"State machine transitioned to {OnboardingStep.HARDWARE_DELIVERED}",
                event="state_transition",
                session_id=session_id,
                user_id=user_id,
                new_step=OnboardingStep.HARDWARE_DELIVERED,
            )

            # Trigger runner wake-up and run execution ambiently
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=types.Content(
                    role="user",
                    parts=[
                        types.Part.from_text(
                            text=f"Resume onboarding: Hardware delivered with tracking ID {tracking_id}."
                        )
                    ],
                ),
                state_delta={
                    "current_step": OnboardingStep.HARDWARE_DELIVERED,
                    "pending_signals": [],
                },
            ):
                self._log_structured(
                    severity="INFO",
                    message=f"Wake-up execution event: {event}",
                    event="runner_event",
                    session_id=session_id,
                    user_id=user_id,
                )

            self._log_structured(
                severity="INFO",
                message="Ambient hardware delivery execution turn completed successfully",
                event="runner_turn_success",
                session_id=session_id,
                user_id=user_id,
            )
        except Exception as e:
            self._log_structured(
                severity="ERROR",
                message=f"Ambient hardware delivery execution turn failed: {e!s}",
                event="runner_turn_failure",
                session_id=session_id,
                user_id=user_id,
                error=str(e),
            )
            raise
