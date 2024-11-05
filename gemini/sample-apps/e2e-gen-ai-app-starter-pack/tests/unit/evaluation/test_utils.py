# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# pylint: disable=R0801

import os

from app.eval.utils import generate_multiturn_history, load_chats
import pandas as pd
import pytest

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


@pytest.mark.asyncio
async def test_generate_multiturn_history() -> None:
    """Tests multi turn evaluation including tool calls in the conversation."""
    # Load test data
    chats = load_chats(os.path.join(CURRENT_DIR, "data", "tool_call_chat.yaml"))
    df = pd.DataFrame(chats)

    # Generate multi-turn history
    result_df = generate_multiturn_history(df)

    # Test overall structure
    assert len(result_df) == 2, "Expected 2 turns in the conversation"
    assert isinstance(result_df, pd.DataFrame), "Result should be a DataFrame"

    # Test first turn
    assert (
        result_df["conversation_history"][0] == []
    ), "First turn should have empty conversation history"
    assert (
        result_df["human_message"][0]["content"][0]["text"] == "Explain what's MLOps"
    ), "Incorrect first human message"
    assert (
        "MLOps is a set" in result_df["ai_message"][0]["content"]
    ), "AI response for MLOps explanation not found"

    # Test second turn
    assert (
        len(result_df["conversation_history"][1]) == 4
    ), "Second turn should have 4 messages in conversation history"
    assert (
        result_df["human_message"][1]["content"][0]["text"]
        == "How can I evaluate my models?"
    ), "Incorrect second human message"
    assert (
        "Model evaluation depends heavily on the type of model"
        in result_df["ai_message"][1]["content"]
    ), "Expected content not found in second AI response"

    # Test tool call presence
    assert (
        result_df["conversation_history"][1][1]["tool_calls"][0]["name"]
        == "retrieve_docs"
    ), "Incorrect tool call name"

    # Test conversation flow
    assert (
        result_df["conversation_history"][1][0]["type"] == "human"
    ), "First message in history should be human"
    assert (
        result_df["conversation_history"][1][-1]["type"] == "ai"
    ), "Last message in history should be AI"
