# Copyright 2025 Google LLC
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


import warnings
from backend.app_settings import get_application_settings
from google.adk.agents import Agent
from google.adk.tools import load_artifacts
from google.adk.tools.agent_tool import AgentTool

# Import tools
from . import tools
from .rag_agent_financial_planning import rag_agent_financial_planning
from .stock_performance_agent import stock_performance_agent

# Import the new Market Agent
from .market_agent import market_research_agent

warnings.filterwarnings("ignore", category=UserWarning, module=".*pydantic.*")

app_settings = get_application_settings()


def create_root_agent(prompt: str) -> Agent:
    """Creates the root agent with a dynamic prompt."""
    return Agent(
        name="financial_advisor_agent",
        model=app_settings.voice.model_id,
        description="An AI agent that uses its tools to provide personalized, client-tailored financial guidance and assitance.",
        instruction=prompt,
        tools=[
            # Core Business Logic Tools
            AgentTool(agent=market_research_agent),
            tools.appointment_scheduler,
            tools.agent_execution_confirmation_notification,
            tools.generate_financial_summary_visual,
            tools.display_cd_information,
            # Data Retrieval Tools (Flattened)
            AgentTool(agent=rag_agent_financial_planning),
            AgentTool(agent=stock_performance_agent),
            # System Tools
            load_artifacts,
        ],
    )
