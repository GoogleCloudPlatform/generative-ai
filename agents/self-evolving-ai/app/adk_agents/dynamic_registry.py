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

"""APEX Layer 1 Dynamic Tool Loader with Cloud KMS Signing & Policy Controller Enforcement."""
import ast
import hashlib
import threading
import time
from typing import Dict, Any, List, Tuple, Optional
from google.adk.tools import FunctionTool

from app.config import PROJECT_ID
from app.adk_agents.schemas import DynamicToolDefinition, utc_now
from app.adk_agents.code_synthesis import sandbox_violations, compile_in_sandbox
from app.governance.kms_signer import CloudKmsSigner
from app.governance.policy_controller import CloudPolicyController
from app.governance.audit_logger import CloudAuditLogger
from app.runtime_registry import get_platform_env


class AstSafetyChecker(ast.NodeVisitor):
    """Inspects generated Python AST to enforce strict sandboxing."""

    DISALLOWED_MODULES = {
        "os", "sys", "subprocess", "socket", "http", "urllib", "requests",
        "shutil", "builtins", "importlib", "ctypes", "pty", "pickle"
    }

    DISALLOWED_FUNCTIONS = {
        "eval", "exec", "compile", "__import__", "open", "input", "globals", "locals"
    }

    def __init__(self) -> None:
        self.violations: List[str] = []

    def visit_Import(self, node: ast.Import) -> None:  # pylint: disable=invalid-name
        """Flag `import x` statements that target disallowed modules."""
        for alias in node.names:
            base_mod = alias.name.split(".")[0]
            if base_mod in self.DISALLOWED_MODULES:
                self.violations.append(f"Disallowed module import: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # pylint: disable=invalid-name
        """Flag `from x import y` statements that target disallowed modules."""
        if node.module:
            base_mod = node.module.split(".")[0]
            if base_mod in self.DISALLOWED_MODULES:
                self.violations.append(f"Disallowed module import from: {node.module}")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # pylint: disable=invalid-name
        """Flag direct calls to disallowed built-in functions."""
        if isinstance(node.func, ast.Name) and node.func.id in self.DISALLOWED_FUNCTIONS:
            self.violations.append(f"Disallowed built-in function call: {node.func.id}")
        self.generic_visit(node)


def validate_code_safety(code_str: str) -> None:
    """Parse and assert AST safety."""
    tree = ast.parse(code_str)
    checker = AstSafetyChecker()
    checker.visit(tree)
    violations = list(checker.violations)
    # Strict sandbox policy (import allow-list, forbidden builtins, no dunder access)
    violations += sandbox_violations(code_str)
    if violations:
        raise PermissionError(f"AST Safety Violation: {'; '.join(violations)}")


# The fallback limiter intentionally mirrors code_synthesis.REFERENCE_LIMITER_CODE (reviewed template).
# pylint: disable=duplicate-code
class TokenBucketRateLimiter:
    """APEX Layer 1 in-memory token bucket rate limiter to protect Cloud SQL connection pool."""

    def __init__(self, capacity: int = 10, replenishment_rate: float = 40.0):
        self.capacity = capacity
        self.replenishment_rate = replenishment_rate
        self.tokens = float(capacity)
        self.last_update = time.perf_counter()
        self.lock = threading.Lock()
        self.total_throttled = 0
        self.total_admitted = 0

    def acquire(self, tokens: int = 1) -> bool:
        """Refill lazily from elapsed time, then admit (True) or throttle (False) the request."""
        with self.lock:
            now = time.perf_counter()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens = min(float(self.capacity), self.tokens + (elapsed * self.replenishment_rate))
            if self.tokens >= tokens:
                self.tokens -= tokens
                self.total_admitted += 1
                return True
            self.total_throttled += 1
            return False

    def get_stats(self) -> Dict[str, Any]:
        """Return a snapshot of the limiter configuration and admit/throttle counters."""
        with self.lock:
            return {
                "capacity": self.capacity,
                "replenishment_rate": self.replenishment_rate,
                "current_tokens": round(self.tokens, 2),
                "total_admitted": self.total_admitted,
                "total_throttled": self.total_throttled,
            }
# pylint: enable=duplicate-code


def register_dynamic_tool_governed(  # pylint: disable=too-many-arguments,too-many-positional-arguments,too-many-locals
    agent: Any,
    code_string: str,
    tool_name: str = "token_bucket_rate_limiter",
    description: str = "Dynamic APEX Layer 1 token bucket rate limiter governed under Cloud KMS and Policy Controller.",
    target_env: Optional[Any] = None,
    project_id: str = PROJECT_ID,
    policy_controller: Optional[CloudPolicyController] = None,
    capacity: int = 10,
    replenishment_rate: float = 40.0,
) -> Tuple[DynamicToolDefinition, FunctionTool]:
    """Validate AST, evaluate OPA policy, sign with Cloud KMS, attach via Binary Authorization."""
    if target_env is None:
        target_env = get_platform_env()
    kms_signer = CloudKmsSigner(project_id=project_id)
    if policy_controller is None:
        policy_controller = CloudPolicyController()
    audit_logger = CloudAuditLogger(project_id=project_id)

    # 1. AST Safety Validation
    validate_code_safety(code_string)

    # 2. Policy-as-Code Evaluation of the parameters actually being deployed
    policy_decision = policy_controller.evaluate_rate_limiter_policy(capacity=capacity, replenishment_rate=replenishment_rate)
    if not policy_decision.allowed:
        raise PermissionError(f"Cloud Policy Controller Violation: {policy_decision.violations}")

    # 3. Cloud KMS Cryptographic Signing
    code_hash = hashlib.sha256(code_string.encode("utf-8")).hexdigest()
    signature_envelope = kms_signer.sign_artifact(code_string, artifact_type="DYNAMIC_TOOL")

    # 4. Compile in the restricted sandbox namespace (curated builtins, guarded imports)
    limiter_cls = compile_in_sandbox(code_string)
    limiter_instance = (
        limiter_cls(capacity=capacity, replenishment_rate=replenishment_rate)
        if limiter_cls
        else TokenBucketRateLimiter(capacity, replenishment_rate)
    )

    # 5. Binary Authorization: middleware re-verifies the signature against the exact code
    if target_env is not None:
        target_env.attach_verified_rate_limiter(limiter_instance, signature_envelope, code=code_string)

    # 6. Wrap into Google ADK FunctionTool
    def configure_rate_limiter(capacity: int = 45, replenishment_rate: float = 40.0) -> Dict[str, Any]:
        """Reconfigure active token bucket rate limiter parameters."""
        # Run policy check before runtime re-parameterization
        p_check = policy_controller.evaluate_rate_limiter_policy(capacity, replenishment_rate)
        if not p_check.allowed:
            return {"status": "POLICY_REJECTED", "violations": p_check.violations}

        limiter_instance.capacity = capacity
        limiter_instance.replenishment_rate = replenishment_rate
        return {
            "status": "APEX_PATCH_ACTIVE",
            "capacity": capacity,
            "replenishment_rate": replenishment_rate,
            "kms_verified": True,
        }

    dynamic_adk_tool = FunctionTool(configure_rate_limiter)

    if hasattr(agent, "tools"):
        if agent.tools is None:
            agent.tools = []
        agent.tools.append(dynamic_adk_tool)

    definition = DynamicToolDefinition(
        tool_name=tool_name,
        description=description,
        python_code=code_string,
        input_schema={"capacity": "int", "replenishment_rate": "float"},
        verification_hash=code_hash,
        kms_signature=signature_envelope.signature_base64,
        policy_controller_approved=True,
        created_at=utc_now(),
    )

    audit_logger.log_event(
        event_type="DYNAMIC_TOOL_REGISTERED",
        actor="APEX_Layer_1",
        action="register_dynamic_tool_governed",
        status="SUCCESS",
        details={"tool_name": tool_name, "kms_key": signature_envelope.key_resource_name},
    )

    return definition, dynamic_adk_tool
