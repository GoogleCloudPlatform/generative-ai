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

import glob
from typing import Any, Dict, List

import pandas as pd
import yaml


def load_chats(path: str) -> List[Dict[str, Any]]:
    """
    Loads a list of chats from a directory or file.

    Args:
        path (str): The path to the directory or file containing the chats.

    Returns:
        List[Dict[str, Any]]: A list of chats.
    """

    chats: List[Dict[str, Any]] = []
    for file_path in glob.glob(path):
        with open(file_path) as f:
            chats_in_file = yaml.safe_load(f)
            chats = chats + chats_in_file
    return chats


def _process_conversation(row: Dict[str, List[Dict[str, Any]]]) -> List[Dict[str, Any]]:
    """Processes a single conversation row to extract messages and build conversation history.
    Most human-ai interactions are composed of a human message followed by an ai message.
    But when there's a tool call, the interactions are as follows:
    - human message
    - ai message with empty content and tool_calls set
    - tool message with tool call arguments
    - ai message with non-empty content and tool_calls empty.
    In any case the human message is the first in the set and the final answer is the last in the set.
    """
    conversation_history: List[Dict] = []
    messages: List[Dict[str, Any]] = []
    messages_since_last_human_message: List[Dict[str, Any]] = []

    for message in row["messages"]:
        if message["type"] == "human":
            # Reset for new human message
            messages_since_last_human_message = []

        # Add current message to temporary storage
        messages_since_last_human_message.append(message)

        # Check if this is a final AI response (not a tool call)
        if message["type"] == "ai" and (
            "tool_calls" not in message or len(message["tool_calls"]) == 0
        ):
            # Process the completed exchange
            messages.append(
                {
                    "human_message": messages_since_last_human_message[
                        0
                    ],  # First message is human
                    "ai_message": messages_since_last_human_message[
                        -1
                    ],  # Last message is AI's final response
                    "conversation_history": conversation_history.copy(),  # Include previous conversation
                }
            )

            # Update overall conversation history
            conversation_history.extend(messages_since_last_human_message)
    return messages


def generate_multiturn_history(df: pd.DataFrame) -> pd.DataFrame:
    """Processes a DataFrame of conversations to create a multi-turn history.

    This function iterates through a DataFrame where each row represents a conversation.
    It extracts human and AI messages from the "messages" column and structures them
    into a new DataFrame. Each row in the output DataFrame represents a single turn
    in a conversation, including the human message, AI message, and the conversation
    history up to that point.

    Args:
        df (pd.DataFrame): A DataFrame where each row represents a conversation.
                           The DataFrame should have a column named "messages" containing
                           a list of alternating human and AI messages.

    Returns:
        pd.DataFrame: A DataFrame where each row represents a single turn in a conversation.
                      The DataFrame has the following columns:
                          - human_message: The human message in that turn.
                          - ai_message: The AI message in that turn.
                          - conversation_history: A list of all messages in the conversation
                                                  up to the current turn (excluded).
    """
    processed_messages = df.apply(_process_conversation, axis=1).explode().tolist()
    return pd.DataFrame(processed_messages)
