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
import logging
import os
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from typing import Any, Callable, Dict, Iterator, List

import nest_asyncio
import pandas as pd
import yaml
from tqdm import tqdm

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
    for path in glob.glob(path):
        with open(path) as f:
            chats_in_file = yaml.safe_load(f)
            chats = chats + chats_in_file
    return chats


def pairwise(iterable: List[Any]) -> Iterator[tuple[Any, Any]]:
    """Creates an iterable with tuples paired together
    e.g s -> (s0, s1), (s2, s3), (s4, s5), ...
    """
    a = iter(iterable)
    return zip(a, a)


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
    processed_messages = []
    for _, row in df.iterrows():
        conversation_history: List[str] = []
        for human_message, ai_message in pairwise(row["messages"]):
            message = {
                "human_message": human_message,
                "ai_message": ai_message,
                "conversation_history": conversation_history,
            }
            conversation_history = conversation_history + [human_message, ai_message]
            processed_messages.append(message)

    return pd.DataFrame(processed_messages)


def generate_message(row: tuple[int, Dict[str, Any]], callable: Any) -> Dict[str, Any]:
    """Generates a response message using a given callable and updates the row dictionary.

    This function takes a row dictionary containing message data and a callable object.
    It extracts conversation history and the current human message from the row,
    then uses the callable to generate a response based on the conversation history.
    The generated response content and usage metadata are then added to the original
    message dictionary within the row.

    Args:
        row (tuple[int, Dict[str, Any]]): A tuple containing the index and a dictionary
          with message data, including:
                   - "conversation_history" (List[str]): Optional. List of previous
                      messages
                        in the conversation.
                   - "human_message" (str): The current human message.
        callable (Any): A callable object that takes a dictionary with a "messages" key
                        and returns a response object with "content" and
                        "usage_metadata" attributes.

    Returns:
        Dict[str, Any]: The updated row dictionary with the generated response added to the message.
              The message will now contain:
              - "response" (str): The generated response content.
              - "response_obj" (Any): The usage metadata of the response from the callable.
    """
    index, message = row
    messages = (
        message["conversation_history"] if "conversation_history" in message else []
    )
    messages.append(message["human_message"])
    input_callable = {"messages": messages}
    response = callable.invoke(input_callable)
    message["response"] = response.content
    message["response_obj"] = response.usage_metadata
    return message


def batch_generate_messages(
    messages: pd.DataFrame,
    callable: Callable[[List[Dict[str, Any]]], Dict[str, Any]],
    max_workers: int = 4,
) -> pd.DataFrame:
    """Generates AI responses to user messages using a provided callable.

    Processes a Pandas DataFrame containing conversation histories and user messages, utilizing
    the specified callable to predict AI responses in parallel.

    Args:
        messages (pd.DataFrame): DataFrame with a 'messages' column. Each row
            represents a conversation and contains a list of dictionaries, where
              each dictionary
            represents a message turn in the format:

            ```json
            [
                {"type": "human", "content": "user's message"},
                {"type": "ai", "content": "AI's response"},
                {"type": "human", "content": "current user's message"},
                ...
            ]
            ```

        callable (Callable[[List[Dict[str, Any]]], Dict[str, Any]]): Callable object
          (e.g., LangChain Chain) used
            for response generation. It should accept a list of message dictionaries
            (as described above) and return a dictionary with the following structure:

            ```json
            {
                "response": "AI's response",
                "response_obj": { ... } # optional response metadata
            }
            ```

        max_workers (int, optional): Number of worker processes for parallel
            prediction. Defaults to 4.

    Returns:
        pd.DataFrame: DataFrame with the original 'messages' column and two new
            columns: 'response' containing the predicted AI responses, and
            'response_obj' containing optional response metadata.

    Example:
        ```python
        import pandas as pd

        messages_df = pd.DataFrame({
            "messages": [
                [
                    {"type": "human", "content": "What's the weather today?"}
                ],
                [
                    {"type": "human", "content": "Tell me a joke."},
                    {"type": "ai", "content": "Why did the scarecrow win an award?"},
                    {"type": "human", "content": "I don't know, why?"}
                ]
            ]
        })

        responses_df = batch_generate_messages(my_callable, messages_df)
        ```
    """
    logging.info("Executing batch scoring")
    predicted_messages = []
    with ThreadPoolExecutor(max_workers) as pool:
        partial_func = partial(generate_message, callable=callable)
        for message in tqdm(
            pool.map(partial_func, messages.iterrows()), total=len(messages)
        ):
            predicted_messages.append(message)
    return pd.DataFrame(predicted_messages)


def save_df_to_csv(df: pd.DataFrame, dir_path: str, filename: str) -> None:
    """Saves a pandas DataFrame to directory as a CSV file.

    Args:
        df: The DataFrame to save.
        filename: The desired filename. Should end in `.csv`.
        dir_path: The desired dir_path.
    """

    filepath = os.path.join(dir_path, filename)
    os.makedirs(dir_path, exist_ok=True)
    df.to_csv(filepath, index=False)
    logging.info(f"DataFrame saved to: {filepath}")


def import_llm_chain(llm_chain_path: str) -> Any:
    """Dynamically imports the specified LLM chain class."""
    llm_chain_module, llm_chain_name = llm_chain_path.rsplit(".", 1)
    module = __import__(llm_chain_module, fromlist=[llm_chain_name])
    llm_chain = getattr(module, llm_chain_name)
    return llm_chain


def prepare_metrics(metrics: List[str]) -> List[Any]:
    """Prepares the list of metrics for evaluation, handling custom metrics."""
    metrics_evaluation = []
    for metric in metrics:
        if metric.startswith("custom:"):
            *module_path, metric_name = metric.removeprefix("custom:").split(".")
            metrics_evaluation.append(
                __import__(".".join(module_path), fromlist=[metric_name]).__dict__[
                    metric_name
                ]
            )
        else:
            metrics_evaluation.append(metric)
    return metrics_evaluation
