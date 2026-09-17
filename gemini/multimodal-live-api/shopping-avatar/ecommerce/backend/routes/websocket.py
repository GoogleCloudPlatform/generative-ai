# Copyright 2026 Google LLC
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

import json
import logging
import asyncio
import websockets
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from config import settings
from services import auth_svc, VERTEX_PROJECT_ID, VERTEX_LOCATION

logger = logging.getLogger("ecommerce-routes-websocket")
router = APIRouter()

@router.websocket("/api/live-avatar")
@router.websocket("/api/live-avatar/{path:path}")
async def live_avatar_proxy(client_ws: WebSocket, path: str = ""):
    """
    WebSocket endpoint that acts as a secure, authenticated proxy between the React
    client and Google's Gemini Live BidiGenerateContent WebSocket API.
    """
    await client_ws.accept()
    logger.info(f"Client WebSocket connection upgraded for path: {path}")

    # 1. Resolve Auth token and Upstream target for Cloud / Vertex AI
    use_vertex = True
    model_location = VERTEX_LOCATION or "global"
    host = f"{model_location}-aiplatform.googleapis.com" if model_location != "global" else "aiplatform.googleapis.com"
    target_url = f"wss://{host}/ws/google.cloud.aiplatform.v1beta1.LlmBidiService/BidiGenerateContent"
    token = auth_svc.get_token()
    target_url += f"?access_token={token}"

    try:
        # 2. Establish connection to Google upstream
        logger.info(f"Connecting to Gemini Live API: {target_url.split('?')[0]}")
        async with websockets.connect(
            target_url,
            max_size=None,
            ping_interval=20,
            ping_timeout=20
        ) as upstream_ws:
            logger.info("Connected to Gemini Live Upstream successfully")

            # Channel setup status
            is_setup_done = False

            async def client_to_upstream():
                nonlocal is_setup_done
                try:
                    async for message in client_ws.iter_text():
                        # Intercept setup to qualify model path with Project/Location coordinates
                        if use_vertex and not is_setup_done:
                            try:
                                data = json.loads(message)
                                if "setup" in data:
                                    logger.info(f"RAW CLIENT SETUP: {json.dumps(data)}")
                                    setup_cfg = data["setup"]
                                    if "model" in setup_cfg:
                                        raw_model = setup_cfg["model"]
                                        
                                        # Extract core model name
                                        model_name_only = raw_model
                                        if "publishers/google/models/" in model_name_only:
                                            model_name_only = model_name_only.split("publishers/google/models/")[-1]
                                        elif "models/" in model_name_only:
                                            model_name_only = model_name_only.split("models/")[-1]
                                            
                                        qualified_model = f"projects/{VERTEX_PROJECT_ID}/locations/{model_location}/publishers/google/models/{model_name_only}"
                                        setup_cfg["model"] = qualified_model
                                    
                                    # Ensure single snake_case field for avatar_config to avoid oneof collision
                                    avatar_obj = setup_cfg.pop("avatarConfig", None) or setup_cfg.get("avatar_config")
                                    if avatar_obj:
                                        avatar_name = (
                                            avatar_obj.get("avatarName")
                                            or avatar_obj.get("avatar_name")
                                            or "Vera"
                                        )
                                        setup_cfg["avatar_config"] = {"avatar_name": avatar_name}
                                        
                                        avatar_voices = {
                                            "Vera": "Aoede", "Kira": "Kore", "Ingrid": "Aoede",
                                            "Sam": "Charon", "Jay": "Fenrir", "Paul": "Puck",
                                            "Ben": "Charon", "Kai": "Fenrir", "Carmen": "Kore",
                                            "Leo": "Puck", "Piper": "Aoede"
                                        }
                                        voice_name = avatar_voices.get(avatar_name, "Aoede")

                                        gen_cfg = setup_cfg.pop("generationConfig", None) or setup_cfg.get("generation_config", {})
                                        gen_cfg.pop("responseModalities", None)
                                        gen_cfg["response_modalities"] = ["VIDEO"]
                                        
                                        speech_cfg = gen_cfg.pop("speechConfig", None) or gen_cfg.get("speech_config", {})
                                        speech_cfg["voice_config"] = {"prebuilt_voice_config": {"voice_name": voice_name}}
                                        gen_cfg["speech_config"] = speech_cfg
                                        setup_cfg.pop("speechConfig", None)
                                        setup_cfg.pop("speech_config", None)
                                        
                                        setup_cfg["generation_config"] = gen_cfg
                                    
                                    message = json.dumps(data)
                                    logger.info(f"QUALIFIED UPSTREAM SETUP: {message}")
                                    is_setup_done = True
                            except Exception as parse_err:
                                logger.warning(f"Failed to inspect setup model path: {parse_err}")
                        
                        await upstream_ws.send(message)
                except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
                    logger.info("Client to upstream connection closed gracefully.")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Client to Upstream error: {e}")

            async def upstream_to_client():
                try:
                    async for message in upstream_ws:
                        # Forward upstream messages directly to browser client
                        if isinstance(message, bytes):
                            await client_ws.send_bytes(message)
                        else:
                            await client_ws.send_text(message)
                except (WebSocketDisconnect, websockets.exceptions.ConnectionClosed):
                    logger.info("Upstream to client connection closed gracefully.")
                except asyncio.CancelledError:
                    pass
                except Exception as e:
                    logger.error(f"Upstream to Client error: {e}")

            # Run loops concurrently and terminate both as soon as one completes or closes
            t_client = asyncio.create_task(client_to_upstream())
            t_upstream = asyncio.create_task(upstream_to_client())
            
            done, pending = await asyncio.wait(
                [t_client, t_upstream],
                return_when=asyncio.FIRST_COMPLETED
            )
            for p in pending:
                p.cancel()

    except Exception as e:
        logger.error(f"Failed to proxy connection: {str(e)}")
        try:
            await client_ws.close(code=1011, reason=str(e))
        except Exception:
            pass
