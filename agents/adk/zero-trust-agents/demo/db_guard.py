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
Database Security Guard: Cryptographic Verification & Audit Trail
-----------------------------------------------------------------
This script intercepts incoming agent billing requests, validates their signatures,
and commits them to a local ledger. It also contains an auditing engine that
scans the database to detect manual record tampering.
"""

import sys
import json
import hmac
import hashlib
from pathlib import Path

# Paths to files
PIPELINE_FILE = Path(__file__).parent / "transaction_pipeline.json"
LEDGER_FILE = Path(__file__).parent / "ledger.json"

# Database IAM Key Registry (Matching public key directory)
AGENT_KEYS = {
    "support-refund-agent-04": b"KMS_SECRET_KEY_FOR_REFUND_AGENT_04_X98712",
    "support-auditor-12": b"KMS_SECRET_KEY_FOR_AUDITOR_12_F9E2D1"
}

def verify_signature(payload, signature):
    """
    Verifies that the payload was signed by the registered agent.
    """
    agent_id = payload.get("agent_id")
    secret = AGENT_KEYS.get(agent_id)
    
    if not secret:
        return False
        
    serialized_payload = json.dumps(payload, sort_keys=True)
    expected_sig = hmac.new(secret, serialized_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # Secure constant-time comparison to prevent timing attacks
    return hmac.compare_digest(expected_sig, signature)

def process_ingress():
    """
    Reads the shared transaction pipeline, verifies the signature, and appends to ledger.
    """
    if not PIPELINE_FILE.exists():
        print("\033[93mNo transaction found in pipeline. Please run the agent first.\033[0m")
        return

    with open(PIPELINE_FILE, "r") as f:
        transaction = json.load(f)

    payload = transaction.get("payload")
    signature = transaction.get("signature")
    agent_id = payload.get("agent_id")

    print(f"\033[95m[DB Guard]\033[0m Intercepted transaction from '{agent_id}'")
    print(f"\033[95m[DB Guard]\033[0m Validating signature...")

    if verify_signature(payload, signature):
        print(f"\033[92m[DB Guard] SUCCESS: Cryptographic signature verified! Row committed to ledger.\033[0m")
        
        # Read existing ledger
        ledger = []
        if LEDGER_FILE.exists():
            with open(LEDGER_FILE, "r") as lf:
                try:
                    ledger = json.load(lf)
                except json.JSONDecodeError:
                    ledger = []

        # Append new transaction record
        ledger.append({
            "agent_id": agent_id,
            "payload": payload,
            "signature": signature
        })

        with open(LEDGER_FILE, "w") as lf:
            json.dump(ledger, lf, indent=2)

        # Clear pipeline file
        PIPELINE_FILE.unlink()
    else:
        print(f"\033[91m[DB Guard] ⚠️ CRITICAL ALARM: Cryptographic signature verification FAILED!\033[0m")
        print(f"\033[91m[DB Guard] Rejecting write request from agent '{agent_id}'. Non-repudiation failure.\033[0m")
        sys.exit(1)

def audit_ledger():
    """
    Scans the ledger file and re-verifies every transaction to detect manual DB tampering.
    """
    if not LEDGER_FILE.exists() or LEDGER_FILE.stat().st_size == 0:
        print("\033[93mThe database ledger is empty. Nothing to audit.\033[0m")
        return

    with open(LEDGER_FILE, "r") as f:
        ledger = json.load(f)

    print("\033[94m[DB Auditor] Starting database ledger integrity scan...\033[0m")
    print("-" * 80)
    
    breach_detected = False
    
    for idx, record in enumerate(ledger):
        agent_id = record.get("agent_id")
        payload = record.get("payload")
        signature = record.get("signature")

        # Verify record
        is_valid = verify_signature(payload, signature)
        
        status_text = "\033[92m[VERIFIED]\033[0m" if is_valid else "\033[91m[TAMPERED / BREACH]\033[0m"
        print(f"Row {idx+1:02d} | Agent: {agent_id:<25} | Status: {status_text}")
        print(f"       | Payload: {json.dumps(payload)}")
        print(f"       | Signature: {signature[:16]}...{signature[-8:]}")
        
        if not is_valid:
            breach_detected = True
            
    print("-" * 80)
    if breach_detected:
        print("\033[91m⚠️  AUDIT ALARM: DATABASE INTEGRITY VIOLATION DETECTED!\033[0m")
        print("\033[91mOne or more rows were modified directly, bypassing the cryptographic agent signature pipeline!\033[0m")
        sys.exit(1)
    else:
        print("\033[92m✓ AUDIT SUCCESS: All database records verified. Ledger integrity intact.\033[0m")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python3 db_guard.py [process | audit]")
        sys.exit(1)

    command = sys.argv[1]
    if command == "process":
        process_ingress()
    elif command == "audit":
        audit_ledger()
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)
