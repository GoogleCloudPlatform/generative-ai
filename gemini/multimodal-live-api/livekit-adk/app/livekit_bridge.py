import asyncio
import logging
import os
from typing import Optional
import json

from google.adk.runners import Runner
from google.adk.agents.live_request_queue import LiveRequestQueue
from google.adk.agents.run_config import RunConfig, StreamingMode
from google.adk.sessions import InMemorySessionService
from google.genai import types
from dotenv import load_dotenv
load_dotenv()

from travel_booking import agent

try:
    from livekit import api, rtc
except ImportError:
    rtc = None
    api = None

logger = logging.getLogger(__name__)


class LiveKitSessionManager:
    """Manages the LiveKit room session."""

    def __init__(self):
        self.url = os.getenv("LIVEKIT_URL")
        self.api_key = os.getenv("LIVEKIT_API_KEY")
        self.api_secret = os.getenv("LIVEKIT_API_SECRET")
        self.room: Optional[rtc.Room] = None

    async def connect(self, room_name: str, participant_name: str):
        """Connect to a LiveKit room."""
        if not rtc:
            logger.error("LiveKit SDK not installed")
            return

        logger.info(f"Connecting to LiveKit room: {room_name}")
        self.room = rtc.Room()

        # Generate a token for the participant
        token = self._generate_token(room_name, participant_name)

        try:
            await self.room.connect(self.url, token)
            logger.info(f"Connected to room: {self.room.name}")
        except Exception as e:
            logger.error(f"Failed to connect to LiveKit: {e}")
            raise

    def _generate_token(self, room_name: str, participant_name: str) -> str:
        """Generate a token for the participant."""
        if not api:
            logger.warning("LiveKit API module not available, returning dummy token")
            return "dummy_token"

        grant = api.VideoGrants(room_join=True, room=room_name)
        token = api.AccessToken(self.api_key, self.api_secret).with_grants(grant).with_identity(participant_name)
        return token.to_jwt()

    async def disconnect(self):
        """Disconnect from the room."""
        if self.room:
            await self.room.disconnect()
            logger.info("Disconnected from LiveKit room")


class LiveKitGeminiBridge:
    """Bridges LiveKit audio tracks to Gemini via ADK directly."""

    def __init__(self, room: rtc.Room, runner: Optional[Runner] = None, user_id: str = "livekit-user", session_id: str = "livekit-session"):
        self.room = room
        self.live_request_queue = LiveRequestQueue()
        self.runner = runner or Runner(app_name="livekit-adk", agent=agent.root_agent, session_service=InMemorySessionService(), auto_create_session=True)
        self.user_id = user_id
        self.session_id = session_id
        self._running = False
        
        # Initialize audio source for downstream (Gemini -> LiveKit)
        # Assuming 24kHz, mono PCM (Gemini Live API default)
        if rtc:
            self.audio_source = rtc.AudioSource(sample_rate=24000, num_channels=1)
            self.audio_track = rtc.LocalAudioTrack.create_audio_track("agent_voice", self.audio_source)
        else:
            self.audio_source = None
            self.audio_track = None
            
        self._user_speaking = False
        self._audio_buffer = bytearray()

    async def start(self):
        """Start the bridge."""
        self._running = True
        
        # Start downstream task to read from ADK
        asyncio.create_task(self._read_adk_events())
        
        self.room.on("track_subscribed", self._on_track_subscribed)
        self.room.on("track_published", self._on_track_published)
        self.room.on("active_speakers_changed", self._on_active_speakers_changed)
        
        # Handle existing tracks from participants already in the room
        for participant_id, participant in self.room.remote_participants.items():
            for track_id, publication in participant.track_publications.items():
                if publication.kind == rtc.TrackKind.KIND_AUDIO and publication.is_published:
                    logger.info(f"Found existing audio track from {participant.identity}, subscribing...")
                    publication.set_subscribed(True)
        
        # Publish the agent's audio track to the room
        if self.room and self.audio_track:
            await self.room.local_participant.publish_track(self.audio_track)
            logger.info("Published agent audio track to room")
            
        logger.info("LiveKitGeminiBridge started")

    def _on_track_published(
        self,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        """Handle new track published by remote participant."""
        if publication.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(f"Track published by {participant.identity}: {publication.sid}, subscribing...")
            publication.set_subscribed(True)

    def _on_track_subscribed(
        self,
        track: rtc.Track,
        publication: rtc.TrackPublication,
        participant: rtc.RemoteParticipant,
    ):
        """Handle new subscribed track."""
        if track.kind == rtc.TrackKind.KIND_AUDIO:
            logger.info(
                f"Subscribed to audio track from {participant.identity}"
            )
            # Start a task to read from this track and push to queue
            asyncio.create_task(self._read_audio_track(track))
            
    def _on_active_speakers_changed(self, speakers):
        """Handle active speakers changed event to send VAD signals."""
        # Assuming the user is the only remote participant for now
        remote_speakers = [s for s in speakers if s.identity != self.room.local_participant.identity]
        
        if remote_speakers:
            # User started speaking!
            if not self._user_speaking:
                self._user_speaking = True
                logger.info("User started speaking (VAD)")
                # Gemini Live automatic activity detection is enabled, so we do not send explicit activity control.
                # self.live_request_queue.send_activity_start()
        else:
            # User stopped speaking!
            if self._user_speaking:
                self._user_speaking = False
                logger.info("User stopped speaking (VAD)")
                # Gemini Live automatic activity detection is enabled, so we do not send explicit activity control.
                # self.live_request_queue.send_activity_end()

    async def _read_audio_track(self, track: rtc.Track):
        """Read audio data from track and send to Gemini via WebSocket."""
        audio_stream = rtc.AudioStream(track)
        async for frame in audio_stream:
            if not self._running:
                break
                
            actual_frame = frame.frame if hasattr(frame, 'frame') else frame
            
            if hasattr(actual_frame, 'data'):
                audio_data = actual_frame.data
            elif hasattr(frame, 'data'):
                audio_data = frame.data
            else:
                logger.warning("Could not extract audio data from frame object")
                continue
                
            if isinstance(audio_data, memoryview):
                audio_data = bytes(audio_data)
                
            # Simple downsampling from 48kHz to 16kHz by taking every 3rd sample
            # Assuming 16-bit PCM (2 bytes per sample)
            downsampled_data = bytearray()
            for i in range(0, len(audio_data), 6):
                downsampled_data.extend(audio_data[i:i+2])
                
            # Buffer audio data before sending to reduce WebSocket overhead
            self._audio_buffer.extend(downsampled_data)
            
            if len(self._audio_buffer) >= 640: # 20ms of audio at 16kHz 16-bit mono
                logger.debug(f"Sending {len(self._audio_buffer)} bytes of buffered audio to ADK")
                logger.info(f"[GEMINI-BIDI-MONITOR] USER_INPUT: AUDIO ({len(self._audio_buffer)} bytes)")
                audio_blob = types.Blob(mime_type="audio/pcm;rate=16000", data=bytes(self._audio_buffer))
                try:
                    self.live_request_queue.send_realtime(audio_blob)
                except Exception as send_err:
                    logger.debug(f"Skipping audio frame during handoff/reconnect: {send_err}")
                self._audio_buffer.clear()

    async def _read_adk_events(self):
        """Read events from ADK run_live and send to LiveKit."""
        run_config = RunConfig(
            streaming_mode=StreamingMode.BIDI,
            response_modalities=["AUDIO"],
            input_audio_transcription=types.AudioTranscriptionConfig(),
            output_audio_transcription=types.AudioTranscriptionConfig(),
            session_resumption=types.SessionResumptionConfig(),
            enable_affective_dialog=True
        )
        APP_NAME = "livekit-adk"
        while self._running:
            try:
                # ==============================================================
                # [GEMINI-BIDI-MONITOR] CONNECTION_OPEN, HISTORY & INSTRUCTIONS
                # ==============================================================
                logger.info(f"[GEMINI-BIDI-MONITOR] CONNECTION_OPEN - User: {self.user_id}, Session: {self.session_id}")
                
                instructions = getattr(self.runner.agent, 'instruction', 'None')
                logger.info(f"[GEMINI-BIDI-MONITOR] SYSTEM_INSTRUCTIONS:\n{instructions}")
                
                recent_session = await self.runner.session_service.get_session(
                    app_name=APP_NAME, user_id=self.user_id, session_id=self.session_id
                )

                logger.info(f"Starting runner.run_live in bridge for user={self.user_id}, session={self.session_id}")
                async for event in self.runner.run_live(
                    user_id=self.user_id,
                    session_id=self.session_id,
                    live_request_queue=self.live_request_queue,
                    run_config=run_config,
                ):
                    if not self._running:
                        break

                    if event.usage_metadata:
                        logger.info(
                            f"[GEMINI-BIDI-MONITOR] USAGE: Input tokens: {event.usage_metadata.prompt_token_count}, "
                            f"Candidate tokens: {event.usage_metadata.candidates_token_count}"
                        )

                    # Extract transcription or message strings to broadcast to the frontend UI
                    # Only broadcast finalized transcription texts to prevent visual duplication in client bubbles
                    text_to_send = None
                    if not getattr(event, 'partial', False):
                        if getattr(event, 'input_transcription', None):
                            t = event.input_transcription
                            txt = getattr(t, 'text', '') or getattr(t, 'transcription', '')
                            if txt:
                                logger.info(f"[GEMINI-BIDI-MONITOR] USER_INPUT: TRANSCRIPT (\"{txt}\")")
                                text_to_send = json.dumps({"sender": "You", "text": txt})
                    elif getattr(event, 'output_transcription', None):
                        t = event.output_transcription
                        txt = getattr(t, 'text', '') or getattr(t, 'transcription', '')
                        if txt:
                            logger.info(f"[GEMINI-BIDI-MONITOR] MODEL_OUTPUT: TRANSCRIPT (\"{txt}\")")
                            text_to_send = json.dumps({"sender": "Agent", "text": txt})
                            
                    if event.content and event.content.parts:
                        for part in event.content.parts:
                            if getattr(part, 'text', None) and not text_to_send and not getattr(event, 'partial', False):
                                logger.info(f"[GEMINI-BIDI-MONITOR] MODEL_OUTPUT: TEXT (\"{part.text}\")")
                                text_to_send = json.dumps({"sender": "Agent", "text": part.text})
                            if getattr(part, 'inline_data', None) and part.inline_data.mime_type.startswith("audio/"):
                                audio_data = part.inline_data.data
                                if audio_data:
                                    logger.info(f"[GEMINI-BIDI-MONITOR] MODEL_OUTPUT: AUDIO ({len(audio_data)} bytes)")
                                    await self.send_audio(audio_data)
                                    
                    if text_to_send and self.room and self.room.local_participant:
                        try:
                            await self.room.local_participant.publish_data(text_to_send.encode('utf-8'), topic="transcription")
                        except Exception as exception:
                            logger.debug(f"Could not publish DataChannel message: {exception}")
            except Exception as e:
                logger.error(f"Error in _read_adk_events: {e}")
                if not self._running:
                    break
                # Pause briefly before reconnecting/resuming to allow backend state transfer to complete
                await asyncio.sleep(0.5)


    async def send_audio(self, data: bytes):
        """Send audio data from Gemini back to the LiveKit room."""
        if not self._running or not self.audio_source:
            return
        
        # Convert raw PCM bytes to AudioFrame
        # 16-bit audio has 2 bytes per sample
        samples_per_channel = len(data) // 2
        frame = rtc.AudioFrame(
            data=data,
            sample_rate=24000,
            num_channels=1,
            samples_per_channel=samples_per_channel
        )
        await self.audio_source.capture_frame(frame)
        logger.debug(f"Sent {len(data)} bytes of audio to LiveKit")

    async def stop(self):
        """Stop the bridge."""
        self._running = False
        logger.info(f"[GEMINI-BIDI-MONITOR] CONNECTION_CLOSE - User: {self.user_id}, Session: {self.session_id}")
        logger.info("LiveKitGeminiBridge stopped")
