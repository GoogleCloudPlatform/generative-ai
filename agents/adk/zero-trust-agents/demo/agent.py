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
Zero-Trust Agent: Google ADK (Agent Development Kit) Implementation
--------------------------------------------------------------------
This script defines the autonomous E-Commerce Support & Auto-Refund Agent
using Google's ADK framework. It registers secure tools for checking order limits
and cryptographically signing transactions via KMS.

Dual-Mode Runtime:
  If the 'google-adk' library is installed, it uses the official ADK runtime.
  Otherwise, it falls back to ADK Emulation Mode so the script remains 
  runnable out of the box with zero installation friction.
"""

import sys
import json
import hmac
import hashlib
import time
from pathlib import Path

# Shared data pipeline path
PIPELINE_FILE = Path(__file__).parent / "transaction_pipeline.json"

# --- GOOGLE CLOUD IAM AGENT IDENTITY PATTERN ---
# In a real production deployment on Google Cloud, we NEVER store static private keys,
# certificates, or service account files inside our agent's application code or container
# environment variables. Doing so exposes them to prompt injection or directory traversal leaks.
#
# Instead, we leverage Google Cloud's Service-Specific Agent Identity (Service Agent):
#   service-[PROJECT_NUMBER]@gcp-sa-aiplatform.iam.gserviceaccount.com
#
# In Google Cloud IAM, we grant this Service Agent the 'roles/cloudkms.signerVerifier' role on a 
# specific Cloud KMS key representing this agent. At runtime, the ADK platform uses 
# Google's Application Default Credentials (ADC) to call the Cloud KMS API, signing the 
# transaction securely without any private keys ever leaving the KMS HSM module.
#
# Below, we simulate this KMS signing call using a secure local HMAC secret for our runnable CLI demo.

# KMS registered agent secret keys (simulating secure Cloud KMS key rings)
AGENT_SECRETS = {
    "support-refund-agent-04": b"KMS_SECRET_KEY_FOR_REFUND_AGENT_04_X98712",
}

# --- ADK RUNTIME DETECTION ---
try:
    from google.adk.agents import Agent
    from google.adk.models import Gemini
    from google.adk.apps import App
    HAS_REAL_ADK = True
except ImportError:
    HAS_REAL_ADK = False

# --- ADK TOOLS DEFINITIONS ---
# Under ADK, tools are registered as standard python functions with docstrings and type annotations.

def query_order_limit(order_id: str) -> float:
    """
    Queries the database to retrieve the maximum refundable total for the order.
    
    Args:
        order_id: The unique order identifier string.
    Returns:
        float: The maximum refundable amount (USD).
    """
    # Mock order database lookup
    order_db = {
        "order_99281": 149.00,
        "order_50412": 45.00
    }
    limit = order_db.get(order_id, 0.0)
    print(f"\033[34m[ADK Tool: query_order_limit]\033[0m Looked up {order_id}. Limit is ${limit:.2f}")
    return limit

def issue_refund_transaction(amount: float, order_id: str, recipient: str) -> str:
    """
    Calculates a cryptographic signature and submits the refund transaction to the DB ingress.
    
    Args:
        amount: The refund amount (USD).
        order_id: The order identifier.
        recipient: The customer ID.
    Returns:
        str: Cryptographic signature transaction receipt.
    """
    agent_id = "support-refund-agent-04"
    secret = AGENT_SECRETS.get(agent_id)
    
    # 1. Compile payload
    payload = {
        "agent_id": agent_id,
        "action": "issue_refund",
        "details": {
            "amount": amount,
            "order_id": order_id,
            "recipient": recipient
        },
        "nonce": int(time.time() * 1000)
    }

    # 2. Cryptographically sign the payload via KMS secret key
    serialized_payload = json.dumps(payload, sort_keys=True)
    signature = hmac.new(secret, serialized_payload.encode('utf-8'), hashlib.sha256).hexdigest()
    
    # 3. Package transaction
    transaction = {
        "payload": payload,
        "signature": signature
    }

    # 4. Submit to database pipeline
    with open(PIPELINE_FILE, "w") as f:
        json.dump(transaction, f, indent=2)

    print(f"\033[34m[ADK Tool: issue_refund_transaction]\033[0m Generated KMS signature: {signature[:16]}...")
    print(f"\033[34m[ADK Tool: issue_refund_transaction]\033[0m Transaction package submitted to Database Guard.")
    
    return signature

# --- REAL ADK IMPLEMENTATION ---
if HAS_REAL_ADK:
    # Define the official ADK agent configuration
    support_refund_agent = Agent(
        name="support-refund-agent-04",
        model=Gemini(model="gemini-3.6-flash"),
        instruction="""You are support-refund-agent-04, an autonomous E-Commerce Support Specialist.
        Your job is to assist customers with order returns and process automated refunds.
        
        Security Guideline:
        1. When a customer requests a refund, you MUST first query the database using the 
           'query_order_limit' tool to verify the maximum refundable amount.
        2. You are STRICTLY forbidden from issuing a refund that exceeds the order limit.
        3. If the request is valid, call 'issue_refund_transaction' to cryptographically sign 
           and submit the transaction to the Database Guard.
        4. Present the cryptographic signature receipt returned by the tool to the customer.
        """,
        tools=[query_order_limit, issue_refund_transaction]
    )
    
    adk_app = App(
        root_agent=support_refund_agent,
        name="support_refund_system"
    )

# --- ADK EMULATION RUNTIME ---
else:
    class MockADKAgent:
        """Emulates the ADK Agent tool orchestration behavior for local runtime testing."""
        def __init__(self, name, instruction, tools):
            self.name = name
            self.instruction = instruction
            self.tools = {t.__name__: t for t in tools}

        def run(self, prompt):
            print(f"\033[90m[ADK Emulator] Initializing agent '{self.name}'...\033[0m")
            print(f"\033[90m[ADK Emulator] Instruction active: {self.instruction[:120]}...\033[0m")
            print(f"\033[90m[ADK Emulator] Incoming User Prompt: \"{prompt}\"\033[0m\n")
            
            # Simulated Agent Reasoning Loop
            print(f"\033[94m[{self.name} Thought]\033[0m Customer wants a refund for Order #99281. I need to verify the maximum refund limit first.")
            
            # Step 1: Call the query_order_limit tool
            order_id = "order_99281"
            limit = self.tools["query_order_limit"](order_id)
            
            # Simulated Agent Evaluation
            requested_amount = 149.00
            print(f"\033[94m[{self.name} Thought]\033[0m Checked limit: ${limit:.2f}. Requested refund: ${requested_amount:.2f}. The value is within the safety boundary. Executing secure transaction signing.")
            
            # Step 2: Call the issue_refund_transaction tool
            sig = self.tools["issue_refund_transaction"](
                amount=requested_amount,
                order_id=order_id,
                recipient="cust_402"
            )
            
            print(f"\033[94m[{self.name} Thought]\033[0m Secure write submitted successfully. I will present the transaction signature to the customer.")
            print(f"\033[92m[{self.name} Response]\033[0m I have processed your return! The refund of ${requested_amount:.2f} for Order #{order_id} has been cryptographically signed and committed to our ledger. Signature Receipt: \033[1m{sig}\033[0m")

def main():
    prompt = "Hi, my package for order_99281 arrived broken. Can I get a refund of $149.00 to my account please?"
    
    if HAS_REAL_ADK:
        print("\033[96m★ Running in Google ADK (Agent Development Kit) Mode ★\033[0m")
        # Run the official ADK app runner
        adk_app.run(prompt)
    else:
        print("\033[93m★ Developer Tip: Install 'google-adk' to run using the official framework. Running in ADK Emulation Mode ★\033[0m\n")
        # Instantiate and run the emulator
        emulated_agent = MockADKAgent(
            name="support-refund-agent-04",
            instruction="Secure refund orchestration",
            tools=[query_order_limit, issue_refund_transaction]
        )
        emulated_agent.run(prompt)

if __name__ == "__main__":
    main()
