"""Stream live microphone audio to Gemini 3.5 Transcribe (Live API).

Prerequisites:
    pip install google-genai sounddevice
    # macOS also needs PortAudio for sounddevice:
    brew install portaudio

Authentication (Application Default Credentials):
    gcloud auth application-default login

Usage:
    export GOOGLE_CLOUD_PROJECT="your-project-id"   # or edit PROJECT_ID below
    python gemini_3_5_transcribe_live.py
"""

import asyncio
import os
import shutil
import signal

import certifi
import sounddevice as sd

from google import genai
from google.genai import types

# Point it at certifi's bundle if not already set.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# --- Project / client setup -------------------------------------------------
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "[your-project-id]")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "global")

client = genai.Client(enterprise=True, project=PROJECT_ID, location=LOCATION)

MODEL_ID_LIVE = "gemini-3.5-transcribe-live-preview"

SEND_SAMPLE_RATE = 16000
CHANNELS = 1
BLOCK_DURATION = 0.1


async def send_microphone_audio(session, audio_queue):
    mime_type = f"audio/pcm;rate={SEND_SAMPLE_RATE}"
    try:
        while True:
            data = await audio_queue.get()
            if data is None:
                break
            await session.send_realtime_input(
                audio=types.Blob(data=data, mime_type=mime_type)
            )
    except Exception as e:
        print(f"\nError streaming microphone audio: {e}")
    finally:
        await session.send_realtime_input(audio_stream_end=True)


async def receive_streaming_messages(session, transcript_buffer):
    CLEAR_LINE = "\r\x1b[2K"
    try:
        async for message in session.receive():
            if not message.server_content:
                continue
            server_content = message.server_content
            interim = server_content.interim_input_transcription
            if interim and interim.text:
                width = shutil.get_terminal_size((80, 20)).columns
                line = interim.text
                if len(line) >= width:
                    line = "…" + line[-(width - 2):]
                print(f"{CLEAR_LINE}{line}", end="", flush=True)

            # Final result: commit it permanently on its own line.
            final = server_content.input_transcription
            if final and final.text:
                transcript_buffer.append(final.text)
                print(f"{CLEAR_LINE}{final.text}", flush=True)
    except Exception as e:
        print(f"\nError transcribing audio: {e}")


async def streaming_main(config, record_seconds=None):
    transcript_buffer = []
    audio_queue = asyncio.Queue()
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()

    try:
        loop.add_signal_handler(signal.SIGINT, stop_event.set)  # Ctrl+C -> stop
    except NotImplementedError:
        pass

    def mic_callback(indata, frames, time_info, status):
        if status:
            print(status, flush=True)
        # Called on a separate thread, so hop back onto the event loop safely.
        loop.call_soon_threadsafe(audio_queue.put_nowait, bytes(indata))

    blocksize = int(SEND_SAMPLE_RATE * BLOCK_DURATION)

    print("Connecting... waiting for setup_complete.")
    async with client.aio.live.connect(model=MODEL_ID_LIVE, config=config) as session:
        print("Setup complete — start speaking (press Ctrl+C to stop).")

        recv_task = asyncio.create_task(
            receive_streaming_messages(session, transcript_buffer)
        )

        # Only now start capturing the mic and streaming it to the session.
        with sd.RawInputStream(
            samplerate=SEND_SAMPLE_RATE,
            blocksize=blocksize,
            channels=CHANNELS,
            dtype="int16",
            callback=mic_callback,
        ):
            send_task = asyncio.create_task(send_microphone_audio(session, audio_queue))

            # Wait until the user stops (or the time limit elapses).
            if record_seconds is not None:
                try:
                    await asyncio.wait_for(stop_event.wait(), timeout=record_seconds)
                except asyncio.TimeoutError:
                    pass
            else:
                await stop_event.wait()

            await audio_queue.put(None)  # tell the sender to finish -> audio_stream_end
            await send_task

            try:
                await asyncio.wait_for(recv_task, timeout=5.0)
            except asyncio.TimeoutError:
                recv_task.cancel()

    print("\n\nFinal transcript:\n" + " ".join(transcript_buffer))
    return " ".join(transcript_buffer)


if __name__ == "__main__":
    config = types.LiveConnectConfig(
        response_modalities=["TEXT"],
        input_audio_transcription=types.AudioTranscriptionConfig(),
    )
    asyncio.run(streaming_main(config))
