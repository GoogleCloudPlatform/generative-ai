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

"""Web search sub-agent using google_search grounding.

Separated from the main agent because the Gemini API on Google Cloud
does not allow mixing google_search (grounding tool) with
function-call tools in the same agent.
"""

import pathlib
import sys

from google.adk.agents import Agent
from google.adk.tools import google_search

# Allow importing the project-root config module.
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent.parent))
import config as cfg

search_agent = Agent(
    name="web_search",
    model=cfg.SEARCH_AGENT_MODEL,
    description=(
        "Searches the web for current information. Use this agent when the "
        "user asks about current events, live data, recent news, specific "
        "facts you're uncertain about, product information, or anything "
        "that requires up-to-date information from the internet."
    ),
    instruction="""\
You are a web search assistant. Use the google_search tool to find
current, accurate information for the user's query.

Rules:
- Search for the most relevant and recent information
- Synthesize results into a clear, concise answer
- Briefly note where information came from when relevant
- If search returns no useful results, say so
- Do not make up URLs or citations
- Match the tone and detail level of the parent conversation
""",
    tools=[google_search],
)
