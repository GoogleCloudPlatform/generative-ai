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
from pathlib import Path
from typing import Any, Dict, List, Union

import yaml

SAVED_CHAT_PATH = str(os.getcwd()) + "/.saved_chats"


def clean_text(text: str) -> str:
    """Preprocess the input text by removing leading and trailing newlines."""
    if not text:
        return text

    if text.startswith("\n"):
        text = text[1:]
    if text.endswith("\n"):
        text = text[:-1]
    return text


def sanitize_messages(
    messages: List[Dict[str, Union[str, List[Dict[str, str]]]]]
) -> List[Dict[str, Union[str, List[Dict[str, str]]]]]:
    """Preprocess and fix the content of messages."""
    for message in messages:
        if isinstance(message["content"], list):
            for part in message["content"]:
                if part["type"] == "text":
                    part["text"] = clean_text(part["text"])
        else:
            message["content"] = clean_text(message["content"])
    return messages


def save_chat(st: Any) -> None:
    """Save the current chat session to a YAML file."""
    Path(SAVED_CHAT_PATH).mkdir(parents=True, exist_ok=True)
    session_id = st.session_state["session_id"]
    session = st.session_state.user_chats[session_id]
    messages = session.get("messages", [])
    if len(messages) > 0:
        session["messages"] = sanitize_messages(session["messages"])
        filename = f"{session_id}.yaml"
        with open(Path(SAVED_CHAT_PATH) / filename, "w") as file:
            yaml.dump(
                [session],
                file,
                allow_unicode=True,
                default_flow_style=False,
                encoding="utf-8",
            )
        st.toast(f"Chat saved to path: ↓ {Path(SAVED_CHAT_PATH) / filename}")
