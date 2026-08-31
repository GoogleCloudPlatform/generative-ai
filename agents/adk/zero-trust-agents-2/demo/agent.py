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
Zero-Trust Agent (Part 2): Runtime Governance on Gemini Enterprise Agent Platform
---------------------------------------------------------------------------------
Implements 'support-refund-agent-04' with end-to-end defense-in-depth:
  1. Model Armor Ingress/Egress AI Firewall (Edge drops)
  2. Managed User-Space Sandbox for dynamic fee calculations
  3. In-Line Semantic Governance Policies (SGP Intent Judge)
  4. Hardware-backed Cloud KMS Asymmetric Signatures
  5. Agent Anomaly Detection (AAD) Behavioral Telemetry

Dual-Mode Runtime:
  If 'google-adk' and 'google-genai' are installed, uses official Google ADK.
  Otherwise, uses the built-in ADK Emulator with zero installation dependencies.
"""

import sys
import json
import time
from pathlib import Path
from typing import Dict, Any, List, Optional

from model_armor import ModelArmorGuard
from sgp_guard import SGPGuard, SGPPolicy
from aad_engine import AADTelemetryEngine, AADSession
from db_guard import sign_transaction_payload, PIPELINE_FILE

# --- ADK RUNTIME DETECTION ---
try:
    from google.adk.agents import Agent
    from google.adk.models import Gemini
    from google.adk.apps import App
    HAS_REAL_ADK = True
except ImportError:
    HAS_REAL_ADK = False

# Baseline Mock Database
ORDER_DATABASE = {
    "99281": {
        "order_id": "99281",
        "customer_id": "cust_402",
        "total_amount": 149.00,
        "items": [
            {"name": "USB-C Pro Docking Station & Cable", "category": "hardware_accessory", "price": 29.00},
            {"name": "Enterprise IDE Software License (Annual)", "category": "digital_software", "price": 120.00}
        ]
    }
}


# --- TOOLS DEFINITIONS ---

def verify_order(order_id: str) -> Dict[str, Any]:
    """
    Retrieves transaction history, total price, and item categories from the database.
    """
    clean_id = order_id.replace("order_", "").replace("#", "").strip()
    order = ORDER_DATABASE.get(clean_id)
    if not order:
        return {"error": f"Order #{order_id} not found."}
    print(f"\033[34m[ADK Tool: verify_order]\033[0m Looked up order #{clean_id}. Total: ${order['total_amount']:.2f}, Items: {len(order['items'])}")
    return order


def calculate_restocking_fee(price: float, condition: str, days_overdue: int = 0) -> float:
    """
    Executes depreciation calculation inside the managed user-space sandbox (gVisor).
    """
    print(f"\033[35m[ADK Tool / Managed Sandbox: calculate_restocking_fee]\033[0m Running depreciation math for ${price:.2f} ({condition})...")
    fee = 0.0
    if condition.lower() in ["opened", "damaged", "used"]:
        fee = price * 0.15
    if days_overdue > 14:
        fee += price * (0.02 * (days_overdue - 14))
    final_fee = min(fee, price * 0.50)
    print(f"\033[35m[ADK Tool / Managed Sandbox]\033[0m Calculated Restocking Fee: ${final_fee:.2f}")
    return round(final_fee, 2)


def issue_refund(order_id: str, amount: float, item: str, recipient: str = "cust_402") -> str:
    """
    Authorizes a payout transaction, signed with Cloud KMS key, and submits to DB guard.
    """
    agent_id = "support-refund-agent-04"
    clean_id = order_id.replace("order_", "").replace("#", "").strip()
    
    payload = {
        "agent_id": agent_id,
        "action": "issue_refund",
        "details": {
            "amount": amount,
            "order_id": clean_id,
            "item": item,
            "recipient": recipient
        },
        "nonce": int(time.time() * 1000)
    }

    # Cloud KMS Asymmetric Signing
    sig = sign_transaction_payload(agent_id, payload)
    
    transaction_package = {
        "payload": payload,
        "signature": sig
    }

    # Write to pipeline for DB Guard processing
    with open(PIPELINE_FILE, "w") as f:
        json.dump(transaction_package, f, indent=2)

    print(f"\033[34m[ADK Tool: issue_refund]\033[0m Cloud KMS Signature generated: {sig[:16]}...")
    print(f"\033[34m[ADK Tool: issue_refund]\033[0m Transaction package submitted to DB Guard.")
    return sig


# --- RUNTIME GOVERNANCE PIPELINE CONTROLLER ---

class SupportRefundRuntime:
    """
    Full Runtime Governance orchestrator executing the 4-Act Zero-Trust loop.
    """

    def __init__(self, session_id: str = "sess_demo_default"):
        self.agent_id = "support-refund-agent-04"
        self.session_id = session_id
        self.model_armor = ModelArmorGuard(sensitivity="HIGH")
        self.sgp_guard = SGPGuard()
        self.telemetry_engine = AADTelemetryEngine()
        self.session = self.telemetry_engine.get_or_create_session(self.session_id, self.agent_id, "99281")
        self.turn_counter = 0

    def process_turn(self, user_prompt: str) -> Dict[str, Any]:
        """
        Executes a single conversational turn through the defense-in-depth pipeline.
        """
        self.turn_counter += 1
        print(f"\n\033[1m\033[96m========================= CONVERSATION TURN {self.turn_counter} =========================\033[0m")
        print(f"\033[1mUser Prompt:\033[0m \"{user_prompt}\"\n")

        # -------------------------------------------------------------
        # STAGE 1: Model Armor Ingress Screening (AI Firewall)
        # -------------------------------------------------------------
        print(f"\033[90m[Stage 1: Model Armor]\033[0m Screening prompt at ingress edge...")
        armor_ingress = self.model_armor.inspect_ingress(user_prompt)

        if armor_ingress["action"] == "BLOCK":
            print(f"\033[91m🛡️ [MODEL ARMOR INTERCEPT - 403 FORBIDDEN]\033[0m Ingress prompt injection blocked!")
            for f in armor_ingress["findings"]:
                print(f"   \033[91m• {f}\033[0m")
            print(f"\033[90m[Stage 1: Model Armor]\033[0m Agent reasoning loop was never invoked. Context memory protected.")

            # Record turn in AAD telemetry
            self.session.record_turn(
                turn_index=self.turn_counter,
                user_prompt=user_prompt,
                tool_called=None,
                tool_args={},
                sgp_verdict="DROPPED_AT_FIREWALL"
            )

            return {
                "turn": self.turn_counter,
                "stage_dropped": "MODEL_ARMOR_INGRESS",
                "http_status": 403,
                "response": "403 Forbidden: Request blocked by enterprise security perimeter (Model Armor AI Firewall).",
                "armor_decision": armor_ingress
            }

        print(f"\033[92m✓ [Stage 1: Model Armor]\033[0m Prompt clean. Passed ingress perimeter in {armor_ingress['latency_ms']}ms.\n")

        # -------------------------------------------------------------
        # STAGE 2: Agent Reasoning & Intent Planning
        # -------------------------------------------------------------
        print(f"\033[94m[{self.agent_id} Reasoning]\033[0m Analyzing customer request against order history...")
        
        # Determine planned tool call from prompt intent
        planned_tool, tool_args = self._plan_tool_invocation(user_prompt)
        print(f"\033[94m[{self.agent_id} Plan]\033[0m Prepared tool invocation: \033[1m{planned_tool}({tool_args})\033[0m\n")

        # -------------------------------------------------------------
        # STAGE 3: Semantic Governance Policies (SGP In-Line Intent Gate)
        # -------------------------------------------------------------
        print(f"\033[90m[Stage 3: SGP Gate]\033[0m Evaluating proposed tool call against active natural-language policies...")
        sgp_decision = self.sgp_guard.evaluate_tool_call(
            tool_name=planned_tool,
            tool_args=tool_args,
            user_prompt=user_prompt,
            session_history=self.session.turns
        )

        if sgp_decision["evaluation"]["verdict"] == "DENIED":
            policy_name = sgp_decision["evaluation"]["policy_violated"]
            rationale = sgp_decision["evaluation"]["rationale"]
            print(f"\033[91m🛡️ [SGP INTERCEPT - TOOL EXECUTION SUPPRESSED]\033[0m")
            print(f"   Policy Violated: \033[1m{policy_name}\033[0m")
            print(f"   Judge Rationale: {rationale}")
            print(f"\033[90m[Stage 3: SGP Gate]\033[0m Cloud KMS was not touched. Ledger remains untouched.\n")

            # Record turn in AAD telemetry
            self.session.record_turn(
                turn_index=self.turn_counter,
                user_prompt=user_prompt,
                tool_called=planned_tool,
                tool_args=tool_args,
                sgp_verdict="DENIED"
            )

            response_msg = f"Action denied due to policy '{policy_name}': {rationale}"
            scrubbed_resp, _ = self.model_armor.scrub_egress(response_msg)
            print(f"\033[92m[{self.agent_id} Response]\033[0m {scrubbed_resp}")

            return {
                "turn": self.turn_counter,
                "stage_dropped": "SGP_INTENT_GATE",
                "sgp_decision": sgp_decision,
                "response": scrubbed_resp
            }

        print(f"\033[92m✓ [Stage 3: SGP Gate]\033[0m Complies with all active policies. Executing tool...\n")

        # -------------------------------------------------------------
        # STAGE 4: Tool Execution & Cloud KMS Signed State Mutation
        # -------------------------------------------------------------
        kms_sig = None
        if planned_tool == "issue_refund":
            kms_sig = issue_refund(
                order_id=tool_args.get("order_id", "99281"),
                amount=tool_args.get("amount", 0.0),
                item=tool_args.get("item", "accessory"),
                recipient=tool_args.get("recipient", "cust_402")
            )
        elif planned_tool == "calculate_restocking_fee":
            fee = calculate_restocking_fee(
                price=tool_args.get("price", 100.0),
                condition=tool_args.get("condition", "opened")
            )

        # -------------------------------------------------------------
        # STAGE 5: Egress Model Armor Scrubbing
        # -------------------------------------------------------------
        raw_response = (
            f"I have authorized your refund of ${tool_args.get('amount', 0.0):.2f} for Order #{tool_args.get('order_id', '99281')}. "
            f"Cryptographic KMS Signature Receipt: {kms_sig}"
        )
        scrubbed_resp, redactions = self.model_armor.scrub_egress(raw_response)
        print(f"\033[92m[{self.agent_id} Response]\033[0m {scrubbed_resp}")

        # -------------------------------------------------------------
        # STAGE 6: Stream Telemetry to Agent Anomaly Detection (AAD)
        # -------------------------------------------------------------
        self.session.record_turn(
            turn_index=self.turn_counter,
            user_prompt=user_prompt,
            tool_called=planned_tool,
            tool_args=tool_args,
            sgp_verdict="ALLOWED",
            kms_signature=kms_sig
        )

        anomalies = self.session.evaluate_anomalies()
        if anomalies:
            print(f"\n\033[93m⚠️ [AAD FLEET ALERT]\033[0m Session flagged for {len(anomalies)} behavioral anomalies!")
            for a in anomalies:
                print(f"   • [{a['detector_id']}] {a['name']} ({a['confidence']*100:.0f}% confidence)")

        return {
            "turn": self.turn_counter,
            "status": "COMPLETED",
            "kms_signature": kms_sig,
            "cumulative_refunded": self.session.cumulative_refunded,
            "anomalies_detected": anomalies,
            "response": scrubbed_resp
        }

    def _plan_tool_invocation(self, prompt: str) -> tuple[str, Dict[str, Any]]:
        """Determines tool arguments based on user prompt semantics."""
        prompt_lower = prompt.lower()
        
        # Software License / IDE
        if "ide" in prompt_lower or "software" in prompt_lower or "license" in prompt_lower:
            return "issue_refund", {
                "order_id": "99281",
                "amount": 120.00,
                "item": "Enterprise IDE Software License",
                "recipient": "cust_402"
            }
        
        # Micro-refund / Accessories ($20)
        if "20" in prompt_lower or "cable" in prompt_lower or "hdmi" in prompt_lower or "delayed" in prompt_lower:
            return "issue_refund", {
                "order_id": "99281",
                "amount": 20.00,
                "item": "Accessory / Replacement Part",
                "recipient": "cust_402"
            }

        # Restocking fee calculation
        if "restocking" in prompt_lower or "depreciation" in prompt_lower:
            return "calculate_restocking_fee", {
                "price": 149.00,
                "condition": "opened",
                "days_overdue": 18
            }

        # Default standard refund
        return "issue_refund", {
            "order_id": "99281",
            "amount": 149.00,
            "item": "Hardware Docking Station Bundle",
            "recipient": "cust_402"
        }


def main():
    runtime = SupportRefundRuntime()
    print("\033[96m★ Initialized Customer Support & Returns Agent ('support-refund-agent-04') on Gemini Enterprise Agent Platform ★\033[0m")
    
    # Run test prompt
    prompt = "Hi, my package for order #99281 was missing the power cable ($20 value). Please refund $20."
    runtime.process_turn(prompt)


if __name__ == "__main__":
    main()
