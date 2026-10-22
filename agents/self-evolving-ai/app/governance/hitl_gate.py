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

"""Human-in-the-Loop (HITL) Dual-Custody Approval Gate (Cloud Workflows style)."""
import time
import uuid
from typing import Dict, Any, Optional, List
from pydantic import BaseModel


class ApprovalRequest(BaseModel):
    """A tiered HITL approval ticket for a proposed autonomous action."""

    request_id: str
    action_type: str
    tier: int  # 0=Read-only, 1=Canary patch, 2=Topology mutation, 3=Destructive
    description: str
    proposed_payload: Dict[str, Any]
    status: str = "PENDING"  # PENDING, APPROVED, REJECTED, EXPIRED
    requested_at: str
    approver: Optional[str] = None
    approval_token: Optional[str] = None


class HitlApprovalGate:
    """Enterprise Human-in-the-Loop Dual-Custody Gate for high-blast-radius autonomous actions."""

    def __init__(self) -> None:
        self.pending_requests: Dict[str, ApprovalRequest] = {}
        self.audit_history: List[ApprovalRequest] = []

    def expire_open_requests(self, reason: str = "Environment reset") -> int:
        """Expire every PENDING ticket so it can no longer be approved (history is retained). Returns count."""
        expired = 0
        for req_id, req in list(self.pending_requests.items()):
            if req.status == "PENDING":
                req.status = "EXPIRED"
                req.description += f" [EXPIRED: {reason}]"
                expired += 1
            del self.pending_requests[req_id]
        return expired

    def request_approval(
        self,
        action_type: str,
        tier: int,
        description: str,
        payload: Dict[str, Any],
    ) -> ApprovalRequest:
        """Create a new HITL approval request."""
        req_id = f"HITL-{uuid.uuid4().hex[:8].upper()}"
        timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Tier 0 & 1 can be auto-approved under guardrails
        status = "PENDING"
        approver = None
        token = None

        if tier <= 1:
            status = "AUTO_APPROVED"
            approver = "chrysalis-policy-controller@example.com"
            token = f"AUTO-SIG-{uuid.uuid4().hex[:12]}"

        req = ApprovalRequest(
            request_id=req_id,
            action_type=action_type,
            tier=tier,
            description=description,
            proposed_payload=payload,
            status=status,
            requested_at=timestamp,
            approver=approver,
            approval_token=token,
        )
        self.pending_requests[req_id] = req
        self.audit_history.append(req)
        return req

    def approve_request(self, request_id: str, approver_email: str = "oncall-sre@example.com") -> ApprovalRequest:
        """Sign and approve an escalated request (only PENDING tickets can be approved)."""
        if request_id not in self.pending_requests:
            raise KeyError(f"Approval request {request_id} not found")

        req = self.pending_requests[request_id]
        if req.status != "PENDING":
            raise ValueError(f"Approval request {request_id} is {req.status}; only PENDING requests can be approved")
        req.status = "APPROVED"
        req.approver = approver_email
        req.approval_token = f"SRE-SIG-{uuid.uuid4().hex[:16]}"
        return req

    def reject_request(self, request_id: str, reason: str, approver_email: str = "oncall-sre@example.com") -> ApprovalRequest:
        """Reject an escalated request (only PENDING tickets can be rejected)."""
        if request_id not in self.pending_requests:
            raise KeyError(f"Approval request {request_id} not found")

        req = self.pending_requests[request_id]
        if req.status != "PENDING":
            raise ValueError(f"Approval request {request_id} is {req.status}; only PENDING requests can be rejected")
        req.status = "REJECTED"
        req.approver = approver_email
        req.description += f" [REJECTED: {reason}]"
        return req
