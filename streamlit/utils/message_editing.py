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
# fmt: off

from typing import Any


class MessageEditing:
    """Provides methods for editing, refreshing, and deleting chat messages."""

    @staticmethod
    def edit_message(st: Any, button_idx: int, message_type: str) -> None:
        """Edit a message in the chat history."""
        button_id = f"edit_box_{button_idx}"
        if message_type == "human":
            messages = st.session_state.user_chats[st.session_state["session_id"]][
                "messages"
            ]
            st.session_state.user_chats[st.session_state["session_id"]][
                "messages"
            ] = messages[:button_idx]
            st.session_state.modified_prompt = st.session_state[button_id]
        else:
            st.session_state.user_chats[st.session_state["session_id"]]["messages"][
                button_idx
            ]["content"] = st.session_state[button_id]

    @staticmethod
    def refresh_message(st: Any, button_idx: int, content: str) -> None:
        """Refresh a message in the chat history."""
        messages = st.session_state.user_chats[st.session_state["session_id"]][
            "messages"
        ]
        st.session_state.user_chats[st.session_state["session_id"]][
            "messages"
        ] = messages[:button_idx]
        st.session_state.modified_prompt = content

    @staticmethod
    def delete_message(st: Any, button_idx: int) -> None:
        """Delete a message from the chat history."""
        messages = st.session_state.user_chats[st.session_state["session_id"]][
            "messages"
        ]
        st.session_state.user_chats[st.session_state["session_id"]][
            "messages"
        ] = messages[:button_idx]
