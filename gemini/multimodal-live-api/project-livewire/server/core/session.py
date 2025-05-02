# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
Session management for Gemini Multimodal Live Proxy Server
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
import asyncio

@dataclass
class SessionState:
    """Tracks the state of a client session"""
    is_receiving_response: bool = False
    interrupted: bool = False
    current_tool_execution: Optional[asyncio.Task] = None
    current_audio_stream: Optional[Any] = None
    genai_session: Optional[Any] = None
    received_model_response: bool = False  # Track if we've received a model response in current turn

# Global session storage
active_sessions: Dict[str, SessionState] = {}

def create_session(session_id: str) -> SessionState:
    """Create and store a new session"""
    session = SessionState()
    active_sessions[session_id] = session
    return session

def get_session(session_id: str) -> Optional[SessionState]:
    """Get an existing session"""
    return active_sessions.get(session_id)

def remove_session(session_id: str) -> None:
    """Remove a session"""
    if session_id in active_sessions:
        del active_sessions[session_id] 