# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Streamlit demo page builder to avoid duplicating code."""

import logging
from typing import Generator, Protocol
import uuid

from concierge_ui import auth, remote_settings
from langgraph.pregel import remote
import streamlit as st

logger = logging.getLogger(__name__)


class ChatHandler(Protocol):  # pylint: disable=too-few-public-methods
    """Protocol defining the interface for a chat handler."""

    def __call__(
        self,
        graph: remote.RemoteGraph,
        message: str,
        thread_id: str,
    ) -> Generator[str, None, None]:
        """
        Handles a chat message.

        Args:
            graph: The remote graph client to query the agent.
            message: The chat message.
            thread_id: The ID of the chat thread.

        Returns:
            A generator yielding the response chunks.
        """


def build_demo_page(
    title: str,
    icon: str,
    description: str,
    chat_handler: ChatHandler,
    config: remote_settings.RemoteAgentConfig,
) -> None:
    """
    Builds a demo page for a chat application using Streamlit.

    Args:
        chat_handler: A callable that handles chat messages.
        config: Configuration settings for the remote agent.
    """

    graph = remote.RemoteGraph(
        title,
        url=str(config.base_url),
        headers=auth.get_auth_headers(config),
    )

    st.set_page_config(page_title=title, page_icon=icon)
    st.title(title)
    st.sidebar.header(title)

    if description:
        st.markdown(description)

    thread_key = f"{config.agent_id}-thread"
    messages_key = f"{config.agent_id}-messages"

    # Set session ID
    if thread_key not in st.session_state:
        st.session_state[thread_key] = uuid.uuid4().hex

    # Initialize chat history
    if messages_key not in st.session_state:
        st.session_state[messages_key] = []

    if st.button("New Session", type="primary", icon="🔄"):
        st.session_state[thread_key] = uuid.uuid4().hex
        st.session_state[messages_key] = []

    st.markdown(f"Thread ID: {st.session_state[thread_key]}")

    # Display chat messages from history on app rerun
    for message in st.session_state[messages_key]:
        with st.chat_message(message["role"]):
            st.write(message["content"])

    # Accept user input
    if prompt := st.chat_input("What is up?"):
        # Add user message to chat history
        st.session_state[messages_key].append({"role": "user", "content": prompt})

        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)

        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            response = st.write_stream(
                chat_handler(
                    graph=graph,
                    message=prompt,
                    thread_id=st.session_state[thread_key],
                )
            )

        # Add assistant response to chat history
        st.session_state[messages_key].append(
            {"role": "assistant", "content": response}
        )
