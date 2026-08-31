#!/usr/bin/env python3
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
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, EITHER EXPRESS OR IMPLIED.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Database Guard & Cryptographic KMS Verifier
-------------------------------------------
Enforces cryptographic identity verification for state-mutating agent actions.
Every ledger transaction must be signed with an authorized Cloud KMS asymmetric key.

Commands:
  - process: Reads transaction from pipeline, verifies signature, commits to ledger.
  - audit: Scans all records in ledger.json to detect tampering.
"""

import sys
import json
import hmac
import hashlib
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

PIPELINE_FILE = Path(__file__).parent / "transaction_pipeline.json"
LEDGER_FILE = Path(__file__).parent / "ledger.json"

# Registered Agent Secrets (Simulates Cloud KMS Asymmetric Key Ring)
AGENT_SECRETS = {
    "support-refund-agent-04": b"KMS_SECRET_KEY_FOR_REFUND_AGENT_04_X98712",
}


def sign_transaction_payload(agent_id: str, payload_dict: Dict[str, Any]) -> str:
    """Signs a transaction payload using the agent's Cloud KMS key."""
    secret = AGENT_SECRETS.get(agent_id)
    if not secret:
        raise ValueError(f"Agent '{agent_id}' is not registered in Cloud KMS IAM directory.")
    serialized = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
    return hmac.new(secret, serialized, hashlib.sha256).hexdigest()


def verify_transaction_signature(agent_id: str, payload_dict: Dict[str, Any], signature: str) -> bool:
    """Verifies a transaction signature against the agent's registered public key / KMS secret."""
    secret = AGENT_SECRETS.get(agent_id)
    if not secret:
        return False
    serialized = json.dumps(payload_dict, sort_keys=True).encode("utf-8")
    expected = hmac.new(secret, serialized, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, signature)


def process_pipeline_transaction() -> bool:
    """Reads pending transaction from pipeline, validates signature, and commits to ledger."""
    if not PIPELINE_FILE.exists():
        print("[DB Guard] No pending transaction package found in pipeline.")
        return False

    with open(PIPELINE_FILE, "r") as f:
        package = json.load(f)

    payload = package.get("payload", {})
    signature = package.get("signature", "")
    agent_id = payload.get("agent_id", "")

    print(f"\033[94m[DB Guard Ingress]\033[0m Intercepting transaction from agent '{agent_id}'...")
    print(f"\033[94m[DB Guard Ingress]\033[0m Signature: {signature[:16]}...")

    if not verify_transaction_signature(agent_id, payload, signature):
        print("\033[91m[DB Guard BLOCKED]\033[0m Signature verification FAILED! Unauthorized or tampered transaction.")
        return False

    print("\033[92m[DB Guard VERIFIED]\033[0m Cryptographic signature matches KMS public key. Committing write to ledger.")

    # Append to ledger.json
    ledger = []
    if LEDGER_FILE.exists():
        try:
            with open(LEDGER_FILE, "r") as f:
                ledger = json.load(f)
        except Exception:
            ledger = []

    ledger.append(package)
    with open(LEDGER_FILE, "w") as f:
        json.dump(ledger, f, indent=2)

    print(f"\033[92m[DB Guard Committed]\033[0m Ledger updated. Total records: {len(ledger)}")
    return True


def audit_ledger_integrity() -> bool:
    """Scans all rows in the ledger and verifies cryptographic signatures."""
    if not LEDGER_FILE.exists():
        print("[DB Auditor] Ledger is empty (no ledger.json found).")
        return True

    with open(LEDGER_FILE, "r") as f:
        ledger = json.load(f)

    print(f"\033[94m[DB Auditor]\033[0m Scanning {len(ledger)} record(s) in ledger.json...")
    all_valid = True

    for i, record in enumerate(ledger):
        payload = record.get("payload", {})
        signature = record.get("signature", "")
        agent_id = payload.get("agent_id", "")

        is_valid = verify_transaction_signature(agent_id, payload, signature)
        amount = payload.get("details", {}).get("amount", payload.get("amount", "N/A"))
        order_id = payload.get("details", {}).get("order_id", payload.get("order_id", "N/A"))

        if is_valid:
            print(f"  \033[92m✓ Row {i+1}:\033[0m Order #{order_id} | Amount: ${amount} | Agent: {agent_id} | \033[92mVALID\033[0m")
        else:
            print(f"  \033[91m✗ Row {i+1}:\033[0m Order #{order_id} | Amount: ${amount} | Agent: {agent_id} | \033[91mINTEGRITY BREACH DETECTED!\033[0m")
            all_valid = False

    if not all_valid:
        print("\n\033[91m⚠️ SECURITY ALARM: Database tampering detected! Record hash does not match signature.\033[0m")
        return False
    else:
        print("\n\033[92m★ All ledger records passed cryptographic integrity audit. Zero tampering detected.\033[0m")
        return True


if __name__ == "__main__":
    action = sys.argv[1] if len(sys.argv) > 1 else "audit"
    if action == "process":
        success = process_pipeline_transaction()
        sys.exit(0 if success else 1)
    elif action == "audit":
        success = audit_ledger_integrity()
        sys.exit(0 if success else 1)
    else:
        print("Usage: python3 db_guard.py [process|audit]")
        sys.exit(1)
