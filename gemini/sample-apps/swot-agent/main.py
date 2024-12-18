# Copyright 2024 Google, LLC.
# This software is provided as-is, without warranty
# or representation for any use or purpose.
# Your use of it is subject to your agreement with Google.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#    http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
from collections import defaultdict
import logging
import os
import random
import time
from typing import Any, Dict, Final

from agent import SwotAgentDeps, SwotAnalysis, run_agent
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
import uvicorn

# Configure logging
logging.basicConfig(level=logging.INFO)

# Constants
ANALYZING_MESSAGE: Final = "Analyzing..."
ANALYSIS_COMPLETE_MESSAGE = "Analysis complete!"

# Define default development key as a constant
DEFAULT_DEV_KEY: Final = "your-placeholder-development-key-123"

# Get secret key with warning if using default
SECRET_KEY = os.environ.get("APP_SECRET_KEY", DEFAULT_DEV_KEY)

if SECRET_KEY == DEFAULT_DEV_KEY:
    logging.warning(
        "Using default development secret key. "
        "Set APP_SECRET_KEY environment variable in production!"
    )

# Store running tasks and status messages
running_tasks = set()
status_store: Dict[str, list] = defaultdict(list)
result_store: Dict[str, Any] = {}

app = FastAPI()
app.add_middleware(
    SessionMiddleware,
    secret_key=SECRET_KEY,
    session_cookie="swot_session",
    max_age=3600,
    same_site="lax",
    https_only=False,
)

templates = Jinja2Templates(directory="templates")


@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request) -> HTMLResponse:
    """Serves the index page."""
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/analyze", response_class=HTMLResponse)
async def analyze_url(request: Request, url: str = Form(...)) -> HTMLResponse:
    """Analyzes the given URL using the SWOT analysis agent."""
    # Generate a unique ID for this analysis session
    session_id = str(id(request))
    request.session["analysis_id"] = session_id
    request.session["start_time"] = asyncio.get_event_loop().time()

    # Clear previous status messages for this session
    status_store[session_id] = []
    result_store[session_id] = None

    status_store[session_id].append(ANALYZING_MESSAGE)

    logging.info(f"Starting new analysis with session ID: {session_id}")

    # Start the analysis task in the background
    task = asyncio.create_task(run_agent_with_progress(session_id, url))
    running_tasks.add(task)
    task.add_done_callback(running_tasks.discard)

    # Updated response to render ONLY the status div and not the full page
    return templates.TemplateResponse(
        "status.html",
        {"request": request, "messages": [ANALYZING_MESSAGE], "result": False},
    )


@app.get("/status", response_class=HTMLResponse)
async def get_status(request: Request) -> HTMLResponse:
    """Returns the current status messages."""
    session_id = request.session.get("analysis_id")
    if not session_id:
        return templates.TemplateResponse(
            "status.html",
            {"request": request, "messages": [], "result": False},
        )

    messages = status_store.get(session_id, [])
    # Check if analysis is complete by looking for the final message
    result = ANALYSIS_COMPLETE_MESSAGE in messages

    logging.info(f"Status check - Session ID: {session_id}, Messages: {messages}")

    response = templates.TemplateResponse(
        "status.html",
        {
            "request": request,
            "messages": messages,
            "result": result,
        },
    )

    return response


@app.get("/result", response_class=HTMLResponse)
async def get_result(request: Request) -> HTMLResponse:
    """Returns the SWOT analysis result."""
    session_id = request.session.get("analysis_id")

    if session_id and session_id in result_store:
        result = result_store[session_id]
    else:
        result = None

    return templates.TemplateResponse(
        "result.html",
        {"request": request, "result": result},
    )


async def run_agent_with_progress(session_id: str, url: str) -> None:
    """Runs the agent and provides progress updates."""
    try:
        # Create a custom deps object that uses the session_id
        deps = SwotAgentDeps(
            request=None,
            update_status_func=lambda request, msg: update_status(session_id, msg),
        )
        result = await run_agent(url=url, deps=deps)

        if not isinstance(result, Exception):
            logging.info(f"Successfully analyzed URL: {url}")
            result_store[session_id] = result

    except Exception as e:  # noqa: W0718
        logging.error(f"An unexpected error occurred: {e}")
        await update_status(session_id, f"Unexpected error: {e}")
        raise


def emulate_tool_completion(session_id: str, message: str) -> None:
    """Pydantic AI doesn't provide a post-processing hook, so we need to emulate one."""

    # Sleep a random amount of time between 0 and 5 seconds
    time.sleep(random.randint(0, 5))
    status_store[session_id].append(message)


async def update_status(session_id: str, message: Any) -> None:
    """Updates status messages and handles SWOT analysis results."""
    logging.info(f"Updating status for session {session_id}: {message}")

    # Handle SWOT analysis result
    if isinstance(message, SwotAnalysis):
        result_store[session_id] = message.model_dump()
        status_store[session_id].append(ANALYSIS_COMPLETE_MESSAGE)
        return

    # Handle string messages
    if isinstance(message, str):
        # Instantly store first status message, emulate tool completion for others
        if message == ANALYSIS_COMPLETE_MESSAGE:
            status_store[session_id].append(message)
        else:
            loop = asyncio.get_running_loop()
            await loop.run_in_executor(
                None, emulate_tool_completion, session_id, message
            )

    logging.info(
        f"Status messages for session {session_id}: {status_store[session_id]}"
    )


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
