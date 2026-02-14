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
from google.genai import types
from utils.live_api_config import get_live_connect_config

logger = logging.getLogger(__name__)

async def run_gemini_session(client, model_id, in_q, out_q, call_state):
    """Handles Gemini flow with persistent connection and session extension."""
    while not call_state.get("active"):
        await asyncio.sleep(0.1)

    session_handle = None
    
    # 10ms of silence at 16kHz (320 bytes for 16-bit PCM)
    silent_chunk = b'\x00' * 320

    while call_state.get("active"):
        try:
            logger.info(f"Connecting to Gemini (Resumption: {session_handle is not None}, Handle: {session_handle})...")
            
            config = get_live_connect_config(session_handle)

            async with client.aio.live.connect(model=model_id, config=config) as session:
                logger.info("Gemini Connected.")
                
                async def sender_loop():
                    while call_state.get("active"):
                        try:
                            chunk = await asyncio.wait_for(in_q.get(), timeout=0.01)
                            await session.send_realtime_input(
                                audio=types.Blob(data=chunk, mime_type="audio/pcm;rate=16000")
                            )
                        except asyncio.TimeoutError:
                            continue
                        except Exception as e:
                            logger.error(f"Sender error: {e}")
                            break

                async def heartbeat_loop():
                    while call_state.get("active"):
                        try:
                            await session.send_realtime_input(
                                audio=types.Blob(data=silent_chunk, mime_type="audio/pcm;rate=16000")
                            )
                            await asyncio.sleep(5)
                        except Exception as e:
                            logger.error(f"Heartbeat error: {e}")
                            break

                sender_task = asyncio.create_task(sender_loop())
                heartbeat_task = asyncio.create_task(heartbeat_loop())

                while call_state.get("active"):
                    try:
                        message = await asyncio.wait_for(session.receive().__anext__(), timeout=0.01)
                        
                        if message.session_resumption_update:
                            update = message.session_resumption_update
                            if update.new_handle:
                                session_handle = update.new_handle
                                logger.info(f"!!! SAVED HANDLE: {session_handle} !!!")

                        if message.server_content:
                            if message.server_content.model_turn:
                                for part in message.server_content.model_turn.parts:
                                    if part.inline_data:
                                        await out_q.put(part.inline_data.data)
                            
                            if message.server_content.turn_complete:
                                logger.info("[Session] Turn complete. Keeping session alive...")

                    except asyncio.TimeoutError:
                        continue
                    except StopAsyncIteration:
                        logger.warning("[Session] Server closed the stream.")
                        break 
                    except Exception as e:
                        logger.error(f"Receiver error: {e}")
                        break

                sender_task.cancel()
                heartbeat_task.cancel()

        except Exception as e:
            logger.error(f"Session error: {e}")
            if not call_state.get("active"): break
            await asyncio.sleep(2)

    logger.info("Session cycle completed.")
