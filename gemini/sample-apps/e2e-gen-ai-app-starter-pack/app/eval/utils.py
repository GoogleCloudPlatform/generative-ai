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

from concurrent.futures import ThreadPoolExecutor
from functools import partial
import glob
import logging
from typing import Any, Callable, Dict, Iterator, List

import nest_asyncio
import pandas as pd
from tqdm import tqdm
import yaml

nest_asyncio.apply()


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


def pairwise(iterable: List[Any]) -> Iterator[tuple[Any, Any]]:
    """Creates an iterable with tuples paired together
    e.g s -> (s0, s1), (s2, s3), (s4, s5), ...
    """
    a = iter(iterable)
    return zip(a, a)


def _process_conversation(row: Dict[str, List[str]]) -> List[Dict[str, Any]]:
    """Processes a single conversation row to extract messages and build conversation history."""
    conversation_history: List[Dict] = []
    messages = []
    # Most human-ai interactions are composed of a human message followed by an ai message.
    # But when there's a tool call, the interactions are as follows:
    # - human message
    # - ai message with empty content and tool_calls set
    # - tool message with tool call arguments
    # - ai message with non-empty content and tool_calls empty.
    # In any case the human message is the first in the set and the final answer is the last in the set.
    for message in row["messages"]:
        if message["type"] == "human":
            messages_since_last_human_message = []
        messages_since_last_human_message.append(message)
        if message["type"] == "ai" and ('tool_calls' not in message or len(message['tool_calls']) == 0):
                # This ai message is the final answer to the human message
                messages.append(
                    {
                        "human_message": messages_since_last_human_message[0],
                        "ai_message": messages_since_last_human_message[-1],
                        "conversation_history": conversation_history.copy(),
                    }
                )
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
                                                  up to and including the current turn.
    """
    processed_messages = df.apply(_process_conversation, axis=1).explode().tolist()
    return pd.DataFrame(processed_messages)

def _retrieve_all_messages(row: tuple[int, Dict[str, Any]]) -> List[Any]:
    """Extracts conversation history and the current human message from the row,
    and appends the current human message to the history.

    Args:
        row (tuple[int, Dict[str, Any]]): A tuple containing the index and a dictionary
          with message data, including:
                   - "conversation_history" (List[str]): Optional. List of previous
                      messages in the conversation.
                   - "human_message" (str): The current human message.

    Returns:
        dict[str, Any]: A dict with a key 'messages' and a value containing a list of messages.
        The list contains the conversation history and the current human message.
    """
    _, row_contents = row
    all_messages = (
        row_contents["conversation_history"].copy() if "conversation_history" in row_contents else []
    )
    all_messages.append(row_contents["human_message"])
    return   {"messages": all_messages}


def batch_generate_messages(
    messages: pd.DataFrame,
    runnable: Callable[[List[Dict[str, Any]]], Dict[str, Any]],
    max_workers: int = 4,
) -> pd.DataFrame:
    """Generates AI responses to user messages using a provided runnable.

    Processes a Pandas DataFrame containing conversation histories and user messages, utilizing
    the specified runnable to predict AI responses in parallel.

    Args:
        messages (pd.DataFrame): DataFrame with a 'conversation_history' and 'human_message' columns. Each row
            represents a conversation. The 'conversation_history' column contains a list of messages in the format:

            ```
            [
                {"type": "human", "content": "user's message"},
                {"type": "ai", "content": "AI's response"},
                ...
            ]
            ```
        The 'human_message' column has the following format:
        ```
        {"type": "human", "content": "current user's message"}
        ```

        runnable (Callable[[List[Dict[str, Any]]], Dict[str, Any]]): Runnable object
          (e.g., LangChain Chain) used
            for response generation. It should accept a list of messages in a `batch` function and return 
            a structure containing 'content' containing the AI's response and 'usage_metadata' with optional response metadata.
            Note: for LangGraph chains, this method needs to be updated as the batch method doesn't return the AI's response, but the whole chat history per row.

        max_workers (int, optional): Number of worker processes for parallel
            prediction. Defaults to 4.

    Returns:
        pd.DataFrame: DataFrame with the original 'conversation_history' and 'human_message' columns and two new
            columns: 'response' containing the predicted AI responses, and
            'response_obj' containing optional response metadata.

    Example:
        ```python
        import pandas as pd


        messages_df = pd.DataFrame({
            "human_message": 
            [
                {"type": "human", "content": "What's the weather today?"},
                {"type": "human", "content": "What are the ingredients of pizza?"},
            ],
            "conversation_history":
            [   [
                    {"type": "human", "content": "Tell me a joke."},
                    {"type": "ai", "content": "Why did the scarecrow win an award?"},
                    {"type": "human", "content": "I don't know, why?"}
                ],
                []
            ] 
        })

        responses_df = batch_generate_messages(messages_df, my_runnable)
        ```
    """
    logging.info("Executing batch invocation")
    to_query = []
    for _, row_contents in messages.iterrows():
        all_messages = (
            row_contents["conversation_history"].copy() if "conversation_history" in row_contents else []
        )
        all_messages.append(row_contents["human_message"])
        to_query.append({"messages": all_messages})
    responses = runnable.batch(to_query)
    print(responses)
    # Note: if nuning a LangGraph chain, this code needs to be modified to grab the last message from the message history:
    # messages["response"] = [item.content for item in responses['messages'][-1]] 
    # messages["response_obj"] = [item.usage_metadata for item in responses['messages'][-1]] 
    messages["response"] = [item.content for item in responses] 
    messages["response_obj"] = [item.usage_metadata for item in responses] 
    return messages
