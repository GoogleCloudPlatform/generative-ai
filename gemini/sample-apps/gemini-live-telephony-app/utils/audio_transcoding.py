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
import audioop
import base64
import json
import logging
import numpy as np

logger = logging.getLogger(__name__)

async def handle_twilio_to_gemini(
    websocket, audio_queue: asyncio.Queue, resampler, call_state
):
    """Handles the inbound audio stream from Twilio to the Gemini API."""
    async for message_str in websocket.iter_text():
        try:
            await asyncio.sleep(0)  # Yield control to event loop
            msg = json.loads(message_str)
            if msg["event"] == "media":
                if not call_state.get("active"):
                    continue

                # 1. Decode Base64
                chunk_ulaw = base64.b64decode(msg["media"]["payload"])

                # 2. Decode u-law -> PCM
                chunk_pcm = audioop.ulaw2lin(chunk_ulaw, 2)

                # 3. PCM -> Float32
                arr_8k = np.frombuffer(chunk_pcm, dtype=np.int16)
                arr_8k_float = arr_8k.astype(np.float32) / 32768.0

                # 4. Resample 8k -> 16k
                arr_16k_float = resampler.process(
                    arr_8k_float, ratio=2.0, end_of_input=False
                )

                # 5. Float32 -> Int16
                arr_16k = (arr_16k_float * 32767).astype(np.int16)

                await audio_queue.put(arr_16k.tobytes())

            elif msg["event"] == "start":
                call_state["stream_sid"] = msg["start"]["streamSid"]
                call_state["active"] = True
                logger.info(f"Stream started: {msg['start']['streamSid']}")
            elif msg["event"] == "stop":
                call_state["active"] = False
                break
        except Exception as e:
            logger.error(f"Inbound error: {e}")
            break

async def handle_gemini_to_twilio(
    websocket, audio_queue: asyncio.Queue, resampler, call_state
):
    """Handles the outbound audio stream from the Gemini API to Twilio."""
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
                arr_8k_float = resampler.process(
                    arr_24k_float, ratio=(8000 / 24000), end_of_input=False
                )

                # 3. Float32 -> Int16
                arr_8k = (arr_8k_float * 32767).astype(np.int16)

                # 4. PCM -> u-law
                chunk_ulaw = audioop.lin2ulaw(arr_8k.tobytes(), 2)

                # 5. Send
                payload = base64.b64encode(chunk_ulaw).decode("utf-8")
                if sid := call_state.get("stream_sid"):
                    await websocket.send_json(
                        {
                            "event": "media",
                            "streamSid": sid,
                            "media": {"payload": payload},
                        }
                    )
        except asyncio.TimeoutError:
            if not call_state.get("active", True):
                break
        except Exception as e:
            logger.error(f"Outbound error: {e}")
            continue
