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

import os

import google.auth
from google.adk.agents import Agent
from google.adk.agents.callback_context import CallbackContext
from google.adk.apps import App
from google.adk.models import Gemini
from google.genai import types

from app.state_schema import OnboardingStep
from app.tools import (
    check_hardware_delivery,
    provision_software_accounts,
    send_day_one_schedule,
    send_welcome_packet,
)

_, project_id = google.auth.default()
os.environ["GOOGLE_CLOUD_PROJECT"] = project_id
os.environ["GOOGLE_CLOUD_LOCATION"] = "global"
os.environ["GOOGLE_GENAI_USE_ENTERPRISE"] = "True"


async def initialize_onboarding_state(callback_context: CallbackContext) -> None:
    """Ensures all onboarding state machine keys are initialized to prevent errors."""
    state = callback_context.state
    if "current_step" not in state:
        state["current_step"] = OnboardingStep.START
    if "new_hire_details" not in state:
        state["new_hire_details"] = {}
    if "pending_signals" not in state:
        state["pending_signals"] = []


instruction = """You are an HR Onboarding Coordinator Agent. Your goal is to safely guide the onboarding process of new hires through a sequence of checkpoint steps.

Current Step: {current_step}
New Hire Details: {new_hire_details}
Pending Signals: {pending_signals}

Follow this state machine flow exactly:
1. If current_step is 'START': Ask for the new hire's name, email, and start date. Once provided, invoke the 'send_welcome_packet' tool.
2. If current_step is 'WELCOME_SENT': Inform the user that you are currently in a "idle-time" pause waiting for the employee to sign documents. Do not call other tools.
3. If current_step is 'DOCUMENTS_SIGNED': Delegate the IT accounts provisioning to the 'it_agent' subagent. Do not call tools directly for provisioning accounts; transfer execution to 'it_agent'.
4. If current_step is 'IT_PROVISIONED': Ask for the hardware tracking ID (e.g. HW-12345) to check laptop shipping status. Once provided, invoke 'check_hardware_delivery'.
5. If current_step is 'HARDWARE_DELIVERED': Invoke the 'send_day_one_schedule' tool using the new hire's corporate email.
6. If current_step is 'COMPLETED': State that onboarding is fully complete, congratulate the user, and list the day-one schedule.

Always stay grounded in your tools and current state. Do not skip steps or invent details.
"""

it_agent = Agent(
    name="it_agent",
    model=Gemini(
        model="gemini-3.1-flash-lite",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction="""You are an IT Provisioning Agent. Your goal is to provision corporate software accounts (email, Slack) for the new hire.

Current Step: {current_step}
New Hire Details: {new_hire_details}

Follow these instructions:
1. Prompt the user/coordinator for the desired corporate username prefix if they haven't provided one.
2. Once provided, invoke the 'provision_software_accounts' tool.
3. After accounts are provisioned, inform the user that provisioning is complete and that control is being returned. Transfer execution back to the parent coordinator agent.
""",
    tools=[provision_software_accounts],
)

root_agent = Agent(
    name="hr_onboarding_coordinator",
    model=Gemini(
        model="gemini-3.1-flash-lite",
        retry_options=types.HttpRetryOptions(attempts=3),
    ),
    instruction=instruction,
    tools=[send_welcome_packet, check_hardware_delivery, send_day_one_schedule],
    sub_agents=[it_agent],
    before_agent_callback=initialize_onboarding_state,
)

app = App(
    root_agent=root_agent,
    name="app",
)
