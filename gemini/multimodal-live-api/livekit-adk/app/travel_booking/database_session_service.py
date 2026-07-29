import json
import logging
import sqlite3
from typing import Any, Dict, List, Optional
from datetime import datetime, timezone

from google.adk.events.event import Event
from google.adk.sessions import BaseSessionService, Session
from google.adk.sessions.base_session_service import GetSessionConfig, ListSessionsResponse
from pydantic import BaseModel

class ListEventsResponse(BaseModel):
    events: List[Event]


logger = logging.getLogger(__name__)

class DatabaseSessionService(BaseSessionService):
    """
    An ADK SessionService that persists sessions and events to a local SQLite database.
    This replicates the behavior of the Java fk-agent-java DatabaseSessionService.
    """

    def __init__(self, db_path: str = "sessions.db"):
        super().__init__()
        # Strip prefixes if provided to match Java behavior
        if db_path.startswith("sqlite:///"):
            self.db_path = db_path[len("sqlite:///"):]
        elif db_path.startswith("jdbc:sqlite:"):
            self.db_path = db_path[len("jdbc:sqlite:"):]
        else:
            self.db_path = db_path
            
        self._init_db()

    def _init_db(self):
        """Initialize the SQLite tables."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS sessions (
                        id TEXT PRIMARY KEY,
                        app_name TEXT,
                        user_id TEXT,
                        state TEXT,
                        last_update_time TEXT
                    )
                ''')
                cursor.execute('''
                    CREATE TABLE IF NOT EXISTS events (
                        id TEXT PRIMARY KEY,
                        session_id TEXT,
                        event_data TEXT,
                        timestamp TEXT,
                        FOREIGN KEY(session_id) REFERENCES sessions(id)
                    )
                ''')
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to initialize database: {e}")
            raise RuntimeError(f"Failed to initialize database: {e}")

    async def create_session(
        self, app_name: str, user_id: str, state: Optional[Dict[str, Any]] = None, session_id: Optional[str] = None
    ) -> Session:
        import uuid
        actual_id = session_id if session_id else str(uuid.uuid4())
        actual_state = state if state is not None else {}
        state_json = json.dumps(actual_state)
        now_iso = datetime.now(timezone.utc).isoformat()

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT OR REPLACE INTO sessions (id, app_name, user_id, state, last_update_time) VALUES (?, ?, ?, ?, ?)",
                    (actual_id, app_name, user_id, state_json, now_iso)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to create session in DB: {e}")
            raise

        return Session(
            id=actual_id,
            app_name=app_name,
            user_id=user_id,
            state=actual_state,
            last_update_time=datetime.now(timezone.utc)
        )

    async def get_session(
        self, app_name: str, user_id: str, session_id: str, config: Optional[GetSessionConfig] = None
    ) -> Optional[Session]:
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT state, last_update_time FROM sessions WHERE id = ? AND app_name = ? AND user_id = ?",
                    (session_id, app_name, user_id)
                )
                row = cursor.fetchone()
                
                if row:
                    state_json, last_update_time_str = row
                    state = json.loads(state_json)
                    last_update_time = datetime.fromisoformat(last_update_time_str)
                    
                    # Note: We omit event loading here for brevity, typically handled by list_events
                    # In python ADK, events are usually fetched separately
                    
                    return Session(
                        id=session_id,
                        app_name=app_name,
                        user_id=user_id,
                        state=state,
                        last_update_time=last_update_time
                    )
                return None
        except sqlite3.Error as e:
            logger.error(f"Failed to get session from DB: {e}")
            raise

    async def append_event(self, session: Session, event: Event) -> Event:
        if event.partial:
            return event
            
        # Standard state update logic would happen here if we tracked memory
        import uuid
        event_id = event.id if hasattr(event, 'id') and event.id else str(uuid.uuid4())
        
        # Serialize event using pydantic
        try:
            event_data = event.model_dump_json(exclude_none=True)
        except Exception:
             event_data = json.dumps(event) # Fallback if not pydantic
             
        now_iso = datetime.now(timezone.utc).isoformat()
        
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                # Update Session State
                state_json = json.dumps(session.state)
                cursor.execute(
                    "UPDATE sessions SET state = ?, last_update_time = ? WHERE id = ?",
                    (state_json, now_iso, session.id)
                )
                
                # Insert Event
                cursor.execute(
                    "INSERT INTO events (id, session_id, event_data, timestamp) VALUES (?, ?, ?, ?)",
                    (event_id, session.id, event_data, now_iso)
                )
                conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Failed to append event to DB: {e}")
            raise
            
        return event

    async def list_sessions(self, app_name: str, user_id: str) -> ListSessionsResponse:
        sessions = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT id, state, last_update_time FROM sessions WHERE app_name = ? AND user_id = ?",
                    (app_name, user_id)
                )
                for row in cursor.fetchall():
                    s_id, state_json, last_update_time_str = row
                    sessions.append(Session(
                        id=s_id,
                        app_name=app_name,
                        user_id=user_id,
                        state=json.loads(state_json),
                        last_update_time=datetime.fromisoformat(last_update_time_str)
                    ))
        except sqlite3.Error as e:
            logger.error(f"Failed to list sessions: {e}")
            raise
            
        return ListSessionsResponse(sessions=sessions)

    async def list_events(self, app_name: str, user_id: str, session_id: str) -> ListEventsResponse:
        events = []
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT event_data FROM events WHERE session_id = ? ORDER BY timestamp ASC",
                    (session_id,)
                )
                for row in cursor.fetchall():
                    event_json = row[0]
                    try:
                        # Attempt to parse back to ADK Event object
                        event = Event.model_validate_json(event_json)
                        events.append(event)
                    except Exception as parse_e:
                        logger.error(f"Failed to parse event JSON: {parse_e}")
        except sqlite3.Error as e:
            logger.error(f"Failed to list events: {e}")
            raise
            
        return ListEventsResponse(events=events)

    async def delete_session(self, app_name: str, user_id: str, session_id: str) -> None:
         try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute("DELETE FROM events WHERE session_id = ?", (session_id,))
                cursor.execute("DELETE FROM sessions WHERE id = ? AND app_name = ? AND user_id = ?", (session_id, app_name, user_id))
                conn.commit()
         except sqlite3.Error as e:
            logger.error(f"Failed to delete session: {e}")
            raise
