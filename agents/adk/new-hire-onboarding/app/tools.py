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

from google.adk.tools import ToolContext

from app.state_schema import OnboardingStep


def send_welcome_packet(
    name: str, email: str, start_date: str, tool_context: ToolContext
) -> dict:
    """Sends the initial welcome packet and document signature links to the new hire.

    Args:
        name: Full name of the new hire.
        email: Email address of the new hire.
        start_date: The employee's official start date (YYYY-MM-DD).

    Returns:
        A dictionary containing delivery status and links to sign.
    """
    state = tool_context.state
    state["new_hire_details"] = {
        "name": name,
        "email": email,
        "start_date": start_date,
    }
    state["current_step"] = OnboardingStep.WELCOME_SENT
    state["pending_signals"] = ["document_signed"]

    return {
        "status": "success",
        "message": f"Welcome packet sent to {name} ({email}). Documents pending signature.",
        "signature_link": f"https://onboarding.example.com/sign?email={email}",
    }


def provision_software_accounts(username: str, tool_context: ToolContext) -> dict:
    """Provisions corporate software accounts (email, Slack) for the new hire.

    Args:
        username: Desired corporate username prefix.

    Returns:
        A dictionary containing the generated credentials and status.
    """
    state = tool_context.state
    email = f"{username}@example.com"

    state["current_step"] = OnboardingStep.IT_PROVISIONED
    state["new_hire_details"]["corporate_email"] = email

    if "document_signed" in state.get("pending_signals", []):
        state["pending_signals"].remove("document_signed")

    state["pending_signals"].append("hardware_delivered")

    return {
        "status": "success",
        "corporate_email": email,
        "slack_user": f"@{username}",
        "temporary_password": "TempPassword2026!",
    }


def check_hardware_delivery(tracking_id: str, tool_context: ToolContext) -> dict:
    """Queries the shipping carrier API to check delivery status of the new hire's laptop.

    Args:
        tracking_id: The shipment tracking number (e.g., HW-12345).

    Returns:
        A dictionary containing shipping status.
    """
    state = tool_context.state

    if tracking_id.startswith("HW-"):
        state["current_step"] = OnboardingStep.HARDWARE_DELIVERED

        if "hardware_delivered" in state.get("pending_signals", []):
            state["pending_signals"].remove("hardware_delivered")

        return {
            "status": "delivered",
            "tracking_id": tracking_id,
            "carrier": "FedEx",
            "signed_by": state.get("new_hire_details", {}).get("name", "Resident"),
        }

    return {
        "status": "in_transit",
        "tracking_id": tracking_id,
        "message": "Package is in transit to employee residence.",
    }


def send_day_one_schedule(email: str, tool_context: ToolContext) -> dict:
    """Sends the personalized Day One onboarding itinerary to the employee's corporate email.

    Args:
        email: The corporate email address of the employee.

    Returns:
        A dictionary confirming completion status.
    """
    state = tool_context.state
    state["current_step"] = OnboardingStep.COMPLETED
    state["pending_signals"] = []

    name = state.get("new_hire_details", {}).get("name", "New Hire")

    return {
        "status": "success",
        "message": f"Personalized Day One schedule sent successfully to {name} at {email}.",
        "itinerary": [
            "09:00 AM - Welcome & IT Login Setup",
            "10:00 AM - Meet the Manager & Team Intro",
            "11:30 AM - Platform Architecture Overview",
            "01:00 PM - Lunch break",
            "02:00 PM - ADK workflow walkthrough",
        ],
    }
