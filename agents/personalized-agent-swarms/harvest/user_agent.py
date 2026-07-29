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

"""Simulated user agent for conversation harvesting.

Creates an LLM-powered agent that role-plays as a specific user persona,
generating realistic follow-up messages in multi-turn conversations.
"""

import config as cfg
from google import genai

_SYSTEM_PROMPT = """\
You are role-playing as a real person with this profile:
{persona}

You are having a conversation with an AI assistant. Your current goal is: {intent}

This is turn {turn_number} of the conversation. The assistant just said:
---
{assistant_response}
---

Generate your next message using the "{follow_up_strategy}" strategy:
- "clarify": Ask for more specific detail on one point the assistant mentioned
- "deep_dive": Ask the assistant to expand on a sub-topic or go deeper
- "pivot": Shift to a related but different aspect of your goal
- "correct": Redirect the assistant — "actually I meant..." or "no, that's not what I need"

Rules:
- Stay in character. Match the persona's communication style and expertise level.
- Write ONLY the user's message. No meta-commentary, no "User:" prefix.
- Be realistic: sometimes brief ("got it, what about X?"), sometimes detailed.
- Do NOT break character or mention AI/simulation.
- Keep it under 100 words unless the persona would naturally write more.
"""


class UserAgent:
    """Simulates a user with a specific persona and conversation strategy."""

    def __init__(
        self,
        persona: str,
        intent: str,
        follow_up_strategy: str,
        client: genai.Client,
        model: str = cfg.USER_SIM_MODEL,
    ):
        """Initialize the user agent.

        Args:
            persona: Full persona description from profiles.json.
            intent: The user's goal for this scenario.
            follow_up_strategy: One of "clarify", "deep_dive", "pivot", "correct".
            client: Google Cloud genai client.
            model: Model to use for generation.
        """
        self.persona = persona
        self.intent = intent
        self.follow_up_strategy = follow_up_strategy
        self.client = client
        self.model = model

    async def generate_follow_up(
        self, assistant_response: str, turn_number: int
    ) -> str:
        """Generate the user's next message given the assistant's response.

        Args:
            assistant_response: The assistant's last response.
            turn_number: Current turn number (2, 3, 4, ...).

        Returns:
            The simulated user's next message as a string.
        """
        prompt = _SYSTEM_PROMPT.format(
            persona=self.persona,
            intent=self.intent,
            turn_number=turn_number,
            assistant_response=assistant_response,
            follow_up_strategy=self.follow_up_strategy,
        )

        response = await self.client.aio.models.generate_content(
            model=self.model,
            contents=prompt,
            config=genai.types.GenerateContentConfig(
                temperature=0.9,
                max_output_tokens=256,
            ),
        )
        return response.text.strip()
