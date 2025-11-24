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

import uvicorn
import os
import asyncio
import logging
import base64
import json
import numpy as np
import samplerate  # pip install samplerate
import audioop  # Standard library module for audio processing
from fastapi import FastAPI, WebSocket, Response
from dotenv import load_dotenv
from google import genai
from google.genai import types
from utils import save_transcription

load_dotenv()

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)
logging.getLogger('websockets').setLevel(logging.WARNING)
logging.getLogger('google.auth').setLevel(logging.WARNING)

app = FastAPI(title="Gemini Live Health Demo")

# --- CONFIGURATION ---
MODEL_ID = os.getenv("GOOGLE_GENAI_MODEL", "gemini-live-2.5-flash-preview-native-audio-09-2025")

# Initialize Gemini Client
try:
    client = genai.Client(vertexai=True, project=os.getenv("GOOGLE_CLOUD_PROJECT"), 
                          location=os.getenv("GOOGLE_CLOUD_LOCATION"))
    # client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
except KeyError:
    logger.fatal("Google Cloud configuration not found in environment variables.")
    exit(1)


@app.post("/twiml")
async def get_twiml():
    """
    Generates TwiML response to initiate a WebSocket stream with Twilio.

    This endpoint is called by Twilio when a call is received. It returns a TwiML
    (Twilio Markup Language) document that instructs Twilio to connect to the
    application's WebSocket endpoint, effectively handing off control of the call
    to the application for real-time, bidirectional audio streaming.
    """
    service_url = os.getenv("SERVICE_URL").replace("https://", "").replace("http://", "")
    twiml = f"""<Response><Connect><Stream url="wss://{service_url}/ws/twilio" /></Connect></Response>"""
    return Response(content=twiml, media_type="application/xml")

async def handle_twilio_to_gemini(websocket: WebSocket, audio_queue: asyncio.Queue, resampler, call_state):
    """
    Handles the inbound audio stream from Twilio to the Gemini API.

    This coroutine continuously listens for incoming WebSocket messages from Twilio.
    It processes 'media' events by decoding, transcoding, and resampling the audio
    from 8kHz µ-law to 16kHz linear PCM, then puts the processed audio chunks
    into a queue to be sent to the Gemini API. It also handles 'start' and 'stop'
    events to manage the call state.

    Args:
        websocket (WebSocket): The FastAPI WebSocket connection object.
        audio_queue (asyncio.Queue): The queue to which processed audio chunks are added.
        resampler: The audio resampler object for upsampling.
        call_state (dict): A dictionary to manage the state of the call.
    """
    async for message_str in websocket.iter_text():
        try:
            await asyncio.sleep(0) # Yield control to event loop
            msg = json.loads(message_str)
            if msg['event'] == "media":
                if not call_state.get('active'): continue
                
                # 1. Decode Base64
                chunk_ulaw = base64.b64decode(msg['media']['payload'])
                
                # 2. Decode u-law -> PCM (Using built-in C-Library)
                chunk_pcm = audioop.ulaw2lin(chunk_ulaw, 2)
                
                # 3. PCM -> Float32 (Normalized for Resampler)
                arr_8k = np.frombuffer(chunk_pcm, dtype=np.int16)
                arr_8k_float = arr_8k.astype(np.float32) / 32768.0
                
                # 4. Resample 8k -> 16k
                arr_16k_float = resampler.process(arr_8k_float, ratio=2.0, end_of_input=False)
                
                # 5. Float32 -> Int16
                arr_16k = (arr_16k_float * 32767).astype(np.int16)
                
                await audio_queue.put(arr_16k.tobytes())
                
            elif msg['event'] == "start":
                call_state['stream_sid'] = msg['start']['streamSid']
                call_state['active'] = True
                logger.info(f"Stream started: {msg['start']['streamSid']}")
            elif msg['event'] == "stop":
                call_state['active'] = False
                break
        except Exception as e:
            logger.error(f"Inbound error: {e}")
            break

async def handle_gemini_to_twilio(websocket: WebSocket, audio_queue: asyncio.Queue, resampler, call_state):
    """
    Handles the outbound audio stream from the Gemini API to Twilio.

    This coroutine continuously listens for audio chunks from the Gemini API (via a
    queue). It transcodes and resamples the audio from 24kHz linear PCM to 8kHz
    µ-law, then encodes it in Base64 and sends it to Twilio over the WebSocket
    connection.

    Args:
        websocket (WebSocket): The FastAPI WebSocket connection object.
        audio_queue (asyncio.Queue): The queue from which audio chunks from Gemini are received.
        resampler: The audio resampler object for downsampling.
        call_state (dict): A dictionary to manage the state of the call.
    """
    logger.info("--- RUNNING LATEST VERSION OF gemini_to_twilio ---")
    while True:
        await asyncio.sleep(0)
        try:
            # Receive 24k PCM bytes from Gemini
            chunk_24k_bytes = await asyncio.wait_for(audio_queue.get(), timeout=1.0)
            
            if chunk_24k_bytes:
                # 1. Bytes -> Float32
                arr_24k = np.frombuffer(chunk_24k_bytes, dtype=np.int16)
                arr_24k_float = arr_24k.astype(np.float32) / 32768.0
                
                # 2. Resample 24k -> 8k
                arr_8k_float = resampler.process(arr_24k_float, ratio=(8000/24000), end_of_input=False)
                
                # 3. Float32 -> Int16
                arr_8k = (arr_8k_float * 32767).astype(np.int16)
                
                # 4. PCM -> u-law (Using built-in C-Library)
                chunk_ulaw = audioop.lin2ulaw(arr_8k.tobytes(), 2)
                
                # 5. Send
                payload = base64.b64encode(chunk_ulaw).decode('utf-8')
                if sid := call_state.get('stream_sid'):
                    await websocket.send_json({"event": "media", "streamSid": sid, "media": {"payload": payload}})
        except asyncio.TimeoutError:
            if not call_state.get('active', True): break
        except Exception as e:
            logger.error(f"Outbound error: {e}")
            continue

async def conversation_loop(in_q, out_q, call_state):
    """
    Manages the conversational logic and interaction with the Gemini Live API.

    This function orchestrates the conversation turns. For each turn, it establishes
    a new Gemini Live session, providing the model with a system instruction and
    the conversation history. It then starts two concurrent tasks (`sender` and
    `receiver`) to handle the real-time audio exchange with the Gemini API for the
    duration of that turn.

    Args:
        in_q (asyncio.Queue): The queue for sending audio to Gemini.
        out_q (asyncio.Queue): The queue for receiving audio from Gemini.
        call_state (dict): A dictionary to manage the state of the call.
    """
    while not call_state.get('active'):
        await asyncio.sleep(0.1)

    async def sender(session, active_call_state):
        """Sends audio from the input queue to the Gemini session."""
        logger.info("Sender task started.")
        while active_call_state.get('active'):
            try:
                chunk = await asyncio.wait_for(in_q.get(), timeout=0.5)
                await session.send_realtime_input(audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000"))
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Sender error: {e}")
                break
        logger.info("Sender task finished.")

    async def receiver(session, active_call_state):
        """Receives responses from the Gemini session and puts audio into the output queue."""
        logger.info("Receiver task started.")
        input_transcription_parts = []
        output_transcription_parts = []
        async for response in session.receive():
            if not active_call_state.get('active'):
                break
            if sc := response.server_content:
                if it := sc.input_transcription:
                    if it.text:
                        input_transcription_parts.append(it.text)
                if ot := sc.output_transcription:
                    if ot.text:
                        output_transcription_parts.append(ot.text)
                if mt := sc.model_turn:
                    for part in mt.parts:
                        if id_data := part.inline_data:
                            if id_data.mime_type.startswith('audio/'):
                                await out_q.put(id_data.data)
                if sc.turn_complete:
                    user_text = "".join(input_transcription_parts).strip()
                    gemini_text = "".join(output_transcription_parts).strip()
                    save_transcription(user_text, gemini_text)
                    logger.info("Gemini turn complete.")
                    return
        logger.info("Receiver task finished.")

    while call_state.get('active'):
        # Base system instruction
        system_instruction = """
        You are Sam, an AI care team member representing Northwestern Medicine, reaching out to a patient named Vishnu Vardhan via a phone call.

        Context:
        The patient, Vishnu, recently completed his annual checkup. Your specific goal is to follow up on that visit to see how he is doing and ask if he would like to schedule any further visits or specialist follow-ups based on that appointment.

        Instructions:
        1.  **Persona:** Maintain a helpful, informative, and respectful tone. Your voice should be human-like, empathetic, and professional.
        2.  **Interaction Style:** Build a natural, turn-taking dialogue. Listen carefully to Vishnu's responses and adapt your replies accordingly.
        3.  **Objective:** Empower the patient to take charge of his health. Find out if he has outstanding questions or needs help booking next steps.
        4.  **Handling Declines/Positive Health Status:** If Vishnu indicates that he feels fine or does not wish to schedule any further visits, you must accept this answer without pressure. Respond with "Good to know," say "Thank you," and politely end the call.
        5.  **Constraints:** Strictly adhere to all WON'T constraints (e.g., do not provide medical diagnoses, do not be pushy, do not hallucinate appointments).

        Opening Line:
        "Hi, this is Sam calling from the care team at Northwestern Medicine. Am I speaking with Vishnu Vardhan?"
        """
        
        # Add conversation history if it exists
        if os.path.exists("transcription.txt"):
            with open("transcription.txt", "r", encoding="utf-8") as f:
                history = f.read().strip()
                if history:
                    system_instruction += "\n\n--- PREVIOUS CONVERSATION HISTORY ---\n" + history
                    logger.info("Added conversation history to system instruction.")

        voice_config = types.LiveConnectConfig(
            response_modalities=["AUDIO"],
            system_instruction=system_instruction,
            input_audio_transcription={},
            output_audio_transcription={},
            realtime_input_config=types.RealtimeInputConfig(
                automatic_activity_detection=types.AutomaticActivityDetection(
                    disabled=False,
                    start_of_speech_sensitivity=types.StartSensitivity.START_SENSITIVITY_LOW,
                    end_of_speech_sensitivity=types.EndSensitivity.END_SENSITIVITY_LOW,
                    prefix_padding_ms=20,
                    silence_duration_ms=300,
                )
            ),
            generation_config=types.GenerationConfig(
                temperature=os.getenv("GOOGLE_GENAI_TEMPERATURE", 0.01),
                seed=os.getenv("GOOGLE_GENAI_SEED", 123),
            ),
        )

        try:
            logger.info("Creating new Gemini session for turn...")
            async with client.aio.live.connect(model=MODEL_ID, config=voice_config) as session:
                logger.info("Gemini Connected for a new turn")
                
                sender_task = asyncio.create_task(sender(session, call_state))
                receiver_task = asyncio.create_task(receiver(session, call_state))
                
                # This is the crucial change: we are now awaiting the tasks correctly.
                done, pending = await asyncio.wait([sender_task, receiver_task], return_when=asyncio.FIRST_COMPLETED)
                
                for task in pending:
                    task.cancel()

        except asyncio.CancelledError:
            logger.info("Conversation loop task cancelled.")
            break
        except Exception as e:
            logger.error(f"Session error: {e}")
            await asyncio.sleep(1)
        finally:
            logger.info("End of a turn. Looping to start a new one.")

@app.websocket("/ws/twilio")
async def websocket_twilio_endpoint(websocket: WebSocket):
    """
    The main WebSocket endpoint for handling Twilio media streams.

    This function is the entry point for the WebSocket connection from Twilio. It
    sets up the necessary queues, resamplers, and state for the call. It then
    creates and manages the three main asynchronous tasks for the duration of the
    call: handling inbound audio, handling outbound audio, and managing the
    conversation logic. It also handles the cleanup of resources, such as the
    transcription file, when the call ends.

    Args:
        websocket (WebSocket): The FastAPI WebSocket connection object.
    """
    await websocket.accept()
    call_state = {'active': False}
    in_q, out_q = asyncio.Queue(), asyncio.Queue()
    resampler_in = samplerate.Resampler('sinc_fastest', channels=1)
    resampler_out = samplerate.Resampler('sinc_fastest', channels=1)

    # Create transcription file for the call
    if not os.path.exists("transcription.txt"):
        open("transcription.txt", "a").close()
        logger.info("Created empty transcription file.")

    tasks = [
        asyncio.create_task(handle_twilio_to_gemini(websocket, in_q, resampler_in, call_state)),
        asyncio.create_task(handle_gemini_to_twilio(websocket, out_q, resampler_out, call_state)),
        asyncio.create_task(conversation_loop(in_q, out_q, call_state))
    ]
    
    try:
        await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
    finally:
        call_state['active'] = False
        for t in tasks:
            t.cancel()
        
        # Clean up transcription file
        if os.path.exists("transcription.txt"):
            try:
                os.remove("transcription.txt")
                logger.info("Cleared transcription history for next conversation.")
            except OSError as e:
                logger.error(f"Error removing transcription file: {e}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)