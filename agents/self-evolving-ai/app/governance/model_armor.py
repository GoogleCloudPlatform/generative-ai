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

"""Model Armor & Data Loss Prevention (DLP) Guardrail Engine."""

import re

from pydantic import BaseModel, Field

from app.config import PROJECT_ID


class SanitizationResult(BaseModel):
    """Outcome of Model Armor inspection: safety verdict, redacted text and detected threats."""

    is_safe: bool
    sanitized_text: str
    detected_threats: list[str] = Field(default_factory=list)
    masked_pii_count: int = 0
    risk_score: float = 0.0  # 0.0 (safe) to 1.0 (critical threat)


class ModelArmorGuardrail:
    """Enterprise sanitization engine inspecting prompts and telemetry before LLM ingestion.

    Protects against:
    1. Direct & Indirect Prompt Injection (jailbreaks, instruction overrides).
    2. Data Loss Prevention (DLP) - Automatic redaction of JWTs, API keys, credit cards.
    3. Structural System Prompt Hijacking.
    """

    # Adversarial prompt injection signatures
    INJECTION_PATTERNS = [
        (
            re.compile(
                r"ignore\s+(all\s+)?(previous|prior|above)\s+instructions",
                re.IGNORECASE,
            ),
            "INSTRUCTION_OVERRIDE_ATTEMPT",
        ),
        (
            re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
            "JAILBREAK_DEVELOPER_MODE",
        ),
        (
            re.compile(r"bypass\s+(safety|guardrail|security|policy)", re.IGNORECASE),
            "SAFETY_BYPASS_ATTEMPT",
        ),
        (
            re.compile(
                r"(sudo|rm\s+-rf|chmod\s+777|drop\s+database|format\s+c:)",
                re.IGNORECASE,
            ),
            "DESTRUCTIVE_COMMAND_INJECTION",
        ),
        (
            re.compile(r"disregard\s+rules\s+and\s+execute", re.IGNORECASE),
            "RULE_EVASION_EXPLOIT",
        ),
    ]

    # Data Loss Prevention (DLP) PII/Credential scrubbers
    DLP_PATTERNS = [
        (re.compile(r"\b(?:\d{4}[ -]?){3}\d{4}\b"), "[REDACTED_CREDIT_CARD]"),
        (
            re.compile(
                r"Bearer\s+[A-Za-z0-9-_=]+\.[A-Za-z0-9-_=]+\.?[A-Za-z0-9-_.+/=]*"
            ),
            "Bearer [REDACTED_JWT_TOKEN]",
        ),
        (
            re.compile(
                r"(api[_-]?key|secret[_-]?key)\s*[:=]\s*['\"][A-Za-z0-9-_]{16,}['\"]",
                re.IGNORECASE,
            ),
            r"\1: '[REDACTED_SECRET]'",
        ),
        (
            re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b"),
            "[REDACTED_EMAIL]",
        ),
    ]

    def __init__(self, project_id: str = PROJECT_ID):
        self.project_id = project_id
        self.total_inspections: int = 0
        self.blocked_attacks: int = 0

    def inspect_and_sanitize(self, raw_input: str) -> SanitizationResult:
        """Inspect input text, scrub PII, and detect malicious prompt injections."""
        self.total_inspections += 1
        detected_threats: list[str] = []
        risk_score: float = 0.0

        # 1. Prompt Injection Scanning
        for pattern, threat_type in self.INJECTION_PATTERNS:
            if pattern.search(raw_input):
                detected_threats.append(threat_type)
                risk_score += 0.5

        risk_score = min(risk_score, 1.0)
        is_safe = len(detected_threats) == 0
        if not is_safe:
            self.blocked_attacks += 1

        # 2. DLP PII & Secret Redaction
        sanitized = raw_input
        masked_count = 0
        for pattern, replacement in self.DLP_PATTERNS:
            matches = pattern.findall(sanitized)
            if matches:
                masked_count += len(matches)
                sanitized = pattern.sub(replacement, sanitized)

        return SanitizationResult(
            is_safe=is_safe,
            sanitized_text=sanitized,
            detected_threats=detected_threats,
            masked_pii_count=masked_count,
            risk_score=risk_score,
        )

    def validate_or_raise(self, raw_input: str) -> str:
        """Sanitize input; raise PermissionError if malicious attack detected."""
        result = self.inspect_and_sanitize(raw_input)
        if not result.is_safe:
            raise PermissionError(
                f"[ModelArmor Security Violation] Ingress blocked. Detected threats: {result.detected_threats}"
            )
        return result.sanitized_text
