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
# pylint: disable=E0611

from datetime import datetime
import os
from typing import Dict

from langchain_core.chat_history import BaseChatMessageHistory
from utils.title_summary import chain_title
import yaml


class LocalChatMessageHistory(BaseChatMessageHistory):
    """Manages local storage and retrieval of chat message history."""

    def __init__(
        self,
        user_id: str,
        session_id: str = "default",
        base_dir: str = ".streamlit_chats",
    ) -> None:
        self.user_id = user_id
        self.session_id = session_id
        self.base_dir = base_dir
        self.user_dir = os.path.join(self.base_dir, self.user_id)
        self.session_file = os.path.join(self.user_dir, f"{session_id}.yaml")

        os.makedirs(self.user_dir, exist_ok=True)

    def get_session(self, session_id: str) -> None:
        """Updates the session ID and file path for the current session."""
        self.session_id = session_id
        self.session_file = os.path.join(self.user_dir, f"{session_id}.yaml")

    def get_all_conversations(self) -> Dict[str, Dict]:
        """Retrieves all conversations for the current user."""
        conversations = {}
        for filename in os.listdir(self.user_dir):
            if filename.endswith(".yaml"):
                file_path = os.path.join(self.user_dir, filename)
                with open(file_path, "r") as f:
                    conversation = yaml.safe_load(f)
                    if not isinstance(conversation, list) or len(conversation) > 1:
                        raise ValueError(
                            f"""Invalid format in {file_path}.
                        YAML file can only contain one conversation with the following
                        structure.
                          - messages:
                              - content: [message text]
                              - type: (human or ai)"""
                        )
                    conversation = conversation[0]
                    if "title" not in conversation:
                        conversation["title"] = filename
                conversations[filename[:-5]] = conversation
        return dict(
            sorted(conversations.items(), key=lambda x: x[1].get("update_time", ""))
        )

    def upsert_session(self, session: Dict) -> None:
        """Updates or inserts a session into the local storage."""
        session["update_time"] = datetime.now().isoformat()
        with open(self.session_file, "w") as f:
            yaml.dump(
                [session],
                f,
                allow_unicode=True,
                default_flow_style=False,
                encoding="utf-8",
            )

    def set_title(self, session: Dict) -> None:
        """
        Set the title for the given session.

        This method generates a title for the session based on its messages.
        If the session has messages, it appends a special message to prompt
        for title creation, generates the title using a title chain, and
        updates the session with the new title.

        Args:
            session (dict): A dictionary containing session information,
                            including messages.

        Returns:
            None
        """
        if session["messages"]:
            messages = session["messages"] + [
                {
                    "type": "human",
                    "content": "End of conversation - Create one single title",
                }
            ]
            # Remove the tool calls from conversation
            messages = [
                msg
                for msg in messages
                if msg["type"] in ("ai", "human") and msg["content"]
            ]

            title = chain_title.invoke(messages).content.strip()
            session["title"] = title
            self.upsert_session(session)

    def clear(self) -> None:
        """Removes the current session file if it exists."""
        if os.path.exists(self.session_file):
            os.remove(self.session_file)
