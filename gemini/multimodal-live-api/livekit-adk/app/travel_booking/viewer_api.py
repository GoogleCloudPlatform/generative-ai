from fastapi import FastAPI
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pathlib import Path
import json

from .database_session_service import DatabaseSessionService

# Create a dedicated FastAPI router/app for the viewer
viewer_app = FastAPI(title="Session Viewer API")

# Initialize the DatabaseSessionService pointing to the sqlite DB
# Adjust the path as needed for where your DB lives
db_service = DatabaseSessionService(db_path="sessions.db")

# Serve the static HTML file
static_dir = Path(__file__).parent / "static"
viewer_app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

@viewer_app.get("/", response_class=HTMLResponse)
async def root():
    """Serve the session viewer HTML page."""
    html_path = static_dir / "session-viewer.html"
    if html_path.exists():
        return html_path.read_text()
    return "Session viewer HTML not found in static directory."

@viewer_app.get("/api/sessions")
async def get_sessions(app_name: str = "livekit-adk", user_id: str = "default_user"):
    """
    Returns a list of session IDs to populate the sidebar.
    Note: The UI expects a flat list of strings.
    """
    try:
        response = await db_service.list_sessions(app_name=app_name, user_id=user_id)
        # The UI expects an array of session ID strings
        session_ids = [session.id for session in response.sessions]
        return JSONResponse(content=session_ids)
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)

@viewer_app.get("/logs/sessions/{session_id}.jsonl")
async def get_session_events_jsonl(session_id: str, app_name: str = "livekit-adk", user_id: str = "default_user"):
    """
    The UI expects a JSONL file format where each line is a JSON event object.
    We fetch the events from the DB and stream them back as JSONL text.
    """
    try:
        response = await db_service.list_events(app_name=app_name, user_id=user_id, session_id=session_id)
        
        # Convert ADK Events into the format the UI expects.
        # The Java UI expects a 'type' field (beforeModel, afterModel, etc.)
        # We try to map Python ADK events to this format.
        
        jsonl_lines = []
        for event in response.events:
            # We dump the raw event and add a 'type' field based on author/content
            # This is a basic mapping to make the UI work
            event_dict = event.model_dump(exclude_none=True)
            
            # Synthesize a 'type' for the UI based on the event author/action
            ui_type = "unknown"
            if event.author == "user":
                ui_type = "beforeModel"
            elif event.author == "model":
                 ui_type = "afterModel"
                 # Add some UI specific fields if possible
                 event_dict['response'] = event_dict.get('content', {})
            elif getattr(event, 'actions', None) and getattr(event.actions, 'function_call', None):
                 ui_type = "beforeTool"
            
            event_dict['type'] = ui_type
            
            # Provide a timestamp in format UI expects
            if hasattr(event, 'timestamp'):
                event_dict['timestamp'] = event.timestamp
            
            jsonl_lines.append(json.dumps(event_dict))
            
        return HTMLResponse(content="\n".join(jsonl_lines), media_type="text/plain")
        
    except Exception as e:
        return JSONResponse(content={"error": str(e)}, status_code=500)
