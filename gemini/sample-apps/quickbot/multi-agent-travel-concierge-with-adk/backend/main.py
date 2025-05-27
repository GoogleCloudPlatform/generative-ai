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

import sys
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from src.controller.chats import router as chat_router
from src.controller.intents import router as intent_router
from src.controller.models import router as model_router
from google.cloud import speech
from os import getenv
import logging

logging.basicConfig(level=logging.INFO, stream=sys.stderr)
logging.info("Test message")

app = FastAPI()


def configure_cors(app):
    """Configures CORS middleware based on the environment."""
    environment = getenv("ENVIRONMENT")
    allowed_origins = []

    if environment == "production":
        frontend_url = getenv("FRONTEND_URL")
        if not frontend_url:
            raise ValueError("FRONTEND_URL environment variable not set in production")
        allowed_origins.append(frontend_url)
    elif environment == "development":
        allowed_origins.append("*")  # Allow all origins in development
    else:
        raise ValueError(
            f"Invalid ENVIRONMENT: {environment}. Must be 'production' or 'development'"
        )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=allowed_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )


# Create a route to handle GET requests on root
@app.get("/")
async def root():
    return "You are calling Quick Bot Backend"


# Create a route to handle GET requests on /version
@app.get("/api/version")
def version():
    return "v0.0.1"


@app.post("/api/audio_chat")
async def audio_chat(audio_file: UploadFile = File(...)):
    client = speech.SpeechClient()
    audio_content = await audio_file.read()
    audio = speech.RecognitionAudio(content=audio_content)
    config = speech.RecognitionConfig(
        language_code="en-US",
        sample_rate_hertz=48000,
        model="default",
        audio_channel_count=1,
        enable_word_confidence=True,
        enable_word_time_offsets=True,
    )

    operation = client.long_running_recognize(config=config, audio=audio)

    print("Waiting for operation to complete...")
    response = operation.result(timeout=90)
    print(response)

    text = ""
    for result in response.results:
        print("Transcript: {}".format(result.alternatives[0].transcript))
        text = result.alternatives[0].transcript

    return text, 200


configure_cors(app)

app.include_router(chat_router)
app.include_router(intent_router)
app.include_router(model_router)
