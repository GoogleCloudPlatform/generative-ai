# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import asyncio
import logging
import os

import samplerate  # pip install samplerate
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, Response, WebSocket
from google import genai
from utils.audio_transcoding import handle_gemini_to_twilio, handle_twilio_to_gemini
from utils.live_api import run_gemini_session

load_dotenv()

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)
logging.getLogger("websockets").setLevel(logging.WARNING)
logging.getLogger("google.auth").setLevel(logging.WARNING)

app = FastAPI(title="Gemini Live Health Demo")

# --- CONFIGURATION ---
MODEL_ID = os.getenv("GOOGLE_GENAI_MODEL", "gemini-live-2.5-flash-native-audio")

# Initialize Gemini Client
try:
    client = genai.Client(
        vertexai=True,
        project=os.getenv("GOOGLE_CLOUD_PROJECT"),
        location=os.getenv("GOOGLE_CLOUD_LOCATION"),
    )
    # client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    logger.fatal("Google Cloud configuration not found in environment variables.")
    exit(1)


@app.post("/twiml")
async def get_twiml():
    """Generates TwiML response to initiate a WebSocket stream with Twilio."""
    service_url = (
        os.getenv("SERVICE_URL").replace("https://", "").replace("http://", "")
    )
    twiml = f"""<Response><Connect><Stream url="wss://{service_url}/ws/twilio" /></Connect></Response>"""
    return Response(content=twiml, media_type="application/xml")


@app.websocket("/ws/twilio")
async def websocket_twilio_endpoint(websocket: WebSocket):
    """The main WebSocket endpoint for handling Twilio media streams."""
    await websocket.accept()
    call_state = {"active": False}
    in_q, out_q = asyncio.Queue(), asyncio.Queue()
    resampler_in = samplerate.Resampler("sinc_fastest", channels=1)
    resampler_out = samplerate.Resampler("sinc_fastest", channels=1)

    tasks = [
        asyncio.create_task(
            handle_twilio_to_gemini(websocket, in_q, resampler_in, call_state)
        ),
        asyncio.create_task(
            handle_gemini_to_twilio(websocket, out_q, resampler_out, call_state)
        ),
        asyncio.create_task(
            run_gemini_session(client, MODEL_ID, in_q, out_q, call_state)
        ),
    ]

    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        call_state["active"] = False
        for t in tasks:
            t.cancel()


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
