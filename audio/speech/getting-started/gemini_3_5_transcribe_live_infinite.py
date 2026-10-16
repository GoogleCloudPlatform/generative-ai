"""Stream simulated microphone audio to Gemini 3.5 Transcribe Live infinitely.

Simulates live microphone input by reading raw PCM audio from a file on a
background producer thread and streaming chunks in real time to the Gemini Live
API (`gemini-3.5-transcribe-live`). Supports infinite streaming by
starting a new Live session whenever `STREAMING_LIMIT` is reached and replaying
unfinalized audio chunks across the stream boundary.

Prerequisites:
    pip install google-genai

Authentication (Application Default Credentials):
    gcloud auth application-default login

Usage:
    export GOOGLE_CLOUD_PROJECT="your-project-id"   # or edit PROJECT_ID below
    export AUDIO_PATH="your-audio-file.wav" # must be a wav file or a raw LINEAR16 without a header
    python gemini_3_5_transcribe_live_infinite.py
"""

import asyncio
from collections.abc import Callable, Iterable, Iterator
import os
import queue
import shutil
import signal
import threading
import time
from typing import Any
import wave
import certifi
from google import genai
from google.genai import types

# Point it at certifi's bundle if not already set.
os.environ.setdefault("SSL_CERT_FILE", certifi.where())

# --- Project / client setup -------------------------------------------------
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "[your-project-id]")
LOCATION = os.environ.get("GOOGLE_CLOUD_REGION", "global")
DEFAULT_AUDIO_PATH = "sample_audio.wav"
AUDIO_PATH = os.environ.get("AUDIO_PATH", DEFAULT_AUDIO_PATH)
client = genai.Client(enterprise=True, project=PROJECT_ID, location=LOCATION)
MODEL_ID_LIVE = "gemini-3.5-transcribe-live"
STREAMING_LIMIT = 20_000
SEND_SAMPLE_RATE = 16_000
CHANNELS = 1
BYTES_PER_SAMPLE = 2
BLOCK_DURATION = 0.1
DEFAULT_CHUNK_SIZE = int(
    SEND_SAMPLE_RATE * CHANNELS * BYTES_PER_SAMPLE * BLOCK_DURATION
)
_WAV_HEADER_SIZE = 44


def get_current_time() -> int:
  """Returns current time in milliseconds."""
  return int(round(time.time() * 1000))


def _parse_offset_ms(offset: str | None) -> int | None:
  """Parses a protobuf Duration string (e.g. `'2.5s'`) into milliseconds."""
  if not offset:
    return None
  stripped = offset.strip()
  if stripped.endswith("s"):
    stripped = stripped[:-1]
  try:
    return int(round(float(stripped) * 1000))
  except ValueError:
    return None


def resolve_audio_path(path: str) -> str:
  """Expands a workspace-relative audio file path into an absolute path."""
  if os.path.isabs(path) or "://" in path:
    return path
  workspace_dir = os.environ.get("BUILD_WORKSPACE_DIRECTORY", "")
  if workspace_dir:
    candidate = os.path.join(workspace_dir, path)
    if os.path.exists(candidate):
      return candidate
  return path


def read_pcm_without_header(path: str) -> bytes:
  """Reads raw audio bytes from `path`, stripping a WAV header if present.
  Args:
    path: Filesystem path to the audio file.
  Returns:
    Raw audio payload bytes without a RIFF/WAVE header.
  """
  with open(path, "rb") as audio_file:
    raw_bytes = audio_file.read()
  if raw_bytes.startswith(b"RIFF"):
    try:
      with wave.open(path, "rb") as wav_reader:
        return wav_reader.readframes(wav_reader.getnframes())
    except wave.Error:
      return raw_bytes[_WAV_HEADER_SIZE:]
  return raw_bytes


def detect_wav_sample_rate(
    path: str, default_rate: int = SEND_SAMPLE_RATE
) -> int:
  """Detects the sample rate in Hz from a WAV file header, or `default_rate`."""
  try:
    with open(path, "rb") as audio_file:
      header_prefix = audio_file.read(4)
    if header_prefix == b"RIFF":
      with wave.open(path, "rb") as wav_reader:
        framerate = wav_reader.getframerate()
        if framerate > 0:
          return framerate
  except (OSError, wave.Error):
    pass
  return default_rate


def simulate_microphone_stream(
    path: str,
    *,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_delay_sec: float = BLOCK_DURATION,
    sleep_fn: Callable[[float], None] = time.sleep,
) -> Iterator[bytes]:
  """Simulates a live microphone generator producing audio on a separate thread.

  Reads raw PCM audio from `path` (stripping any WAV header) and runs a
  background producer thread that emits `chunk_size`-byte chunks at
  `chunk_delay_sec` intervals, yielding chunks as they arrive.

  Args:
    path: Filesystem path to the audio file.
    chunk_size: Maximum size of each yielded audio chunk in bytes.
    chunk_delay_sec: Delay in seconds between chunks on the producer thread to
      simulate real-time microphone capture.
    sleep_fn: Sleep function used by the producer thread between chunks.

  Yields:
    Raw audio byte chunks of up to `chunk_size` bytes.
  """
  raw_bytes = read_pcm_without_header(path)
  chunk_queue: queue.Queue[bytes | BaseException | None] = queue.Queue()
  stop_event = threading.Event()

  def _produce_chunks() -> None:
    try:
      for offset in range(0, len(raw_bytes), chunk_size):
        if stop_event.is_set():
          break
        if offset > 0 and chunk_delay_sec > 0:
          sleep_fn(chunk_delay_sec)
        if stop_event.is_set():
          break
        chunk_queue.put(raw_bytes[offset : offset + chunk_size])
    except BaseException as err:  # pylint: disable=broad-except
      chunk_queue.put(err)
    finally:
      chunk_queue.put(None)

  producer_thread = threading.Thread(
      target=_produce_chunks,
      name="simulated-microphone-producer",
      daemon=True,
  )
  producer_thread.start()
  try:
    while True:
      queued_chunk = chunk_queue.get()
      if queued_chunk is None:
        break
      if isinstance(queued_chunk, BaseException):
        raise queued_chunk
      yield queued_chunk
  finally:
    stop_event.set()


class ResumableMicrophoneStream:
  """Manages simulated microphone audio and bridging state across restarts."""

  def __init__(
      self,
      rate: int = SEND_SAMPLE_RATE,
      chunk_size: int = DEFAULT_CHUNK_SIZE,
      *,
      audio_path: str = AUDIO_PATH,
      audio_stream: Iterable[bytes] | None = None,
      chunk_delay_sec: float = BLOCK_DURATION,
      streaming_limit: int = STREAMING_LIMIT,
      loop: asyncio.AbstractEventLoop | None = None,
  ):
    """Initializes the resumable microphone stream.

    Args:
      rate: Sampling rate in Hz.
      chunk_size: Audio chunk size in bytes.
      audio_path: Audio file path used when `audio_stream` is None.
      audio_stream: Optional iterable of raw PCM byte chunks, or None to read
        from `audio_path` via `simulate_microphone_stream`.
      chunk_delay_sec: Delay in seconds between chunks when reading from a file.
      streaming_limit: Maximum duration of a single stream in milliseconds
        before starting a new stream.
      loop: Optional running asyncio event loop, or None to resolve on enter.
    """
    resolved_path = resolve_audio_path(audio_path)
    if audio_stream is None and rate == SEND_SAMPLE_RATE:
      detected_rate = detect_wav_sample_rate(resolved_path, default_rate=rate)
      if detected_rate != rate:
        if chunk_size == DEFAULT_CHUNK_SIZE:
          chunk_size = int(
              detected_rate * CHANNELS * BYTES_PER_SAMPLE * BLOCK_DURATION
          )
        rate = detected_rate
    self._rate = rate
    self.rate = rate
    self.chunk_size = chunk_size
    self.streaming_limit = streaming_limit
    self._audio_path = resolved_path
    self._audio_stream = audio_stream
    self._chunk_delay_sec = chunk_delay_sec
    self._loop = loop
    self.audio_queue: asyncio.Queue[bytes | None] = asyncio.Queue()
    self.closed = True
    self.start_time = get_current_time()
    self.restart_counter = 0
    self.audio_input: list[bytes] = []
    self.last_audio_input: list[bytes] = []
    self.result_end_time = 0
    self.is_final_end_time = 0
    self.final_request_end_time = 0
    self.bridging_offset = 0
    self.last_transcript_was_final = False
    self.new_stream = True
    self.session_stop_event: asyncio.Event | None = None
    self._mic_stop_event = threading.Event()
    self._feeder_thread: threading.Thread | None = None

  def __enter__(self) -> "ResumableMicrophoneStream":
    """Starts the background feeder thread and opens the stream."""
    self.closed = False
    if self._loop is None:
      self._loop = asyncio.get_running_loop()
    loop = self._loop
    if self._audio_stream is not None:
      mic_stream = self._audio_stream
    else:
      mic_stream = simulate_microphone_stream(
          resolve_audio_path(self._audio_path),
          chunk_size=self.chunk_size,
          chunk_delay_sec=self._chunk_delay_sec,
      )

    self._feeder_thread = threading.Thread(
        target=self._feed_audio_queue,
        args=(mic_stream, loop),
        name="simulated-microphone-feeder",
        daemon=True,
    )
    self._feeder_thread.start()
    return self

  def _feed_audio_queue(
      self,
      mic_stream: Iterable[bytes],
      loop: asyncio.AbstractEventLoop,
  ) -> None:
    """Reads chunks from `mic_stream` and forwards them into `audio_queue`."""
    iterator = iter(mic_stream)
    try:
      for chunk in iterator:
        if self._mic_stop_event.is_set():
          break
        loop.call_soon_threadsafe(self.audio_queue.put_nowait, bytes(chunk))
    finally:
      close_fn = getattr(iterator, "close", None)
      if callable(close_fn):
        close_fn()
      loop.call_soon_threadsafe(self.audio_queue.put_nowait, None)

  def close(self) -> None:
    """Signals the microphone stream and active session to stop."""
    self.closed = True
    self._mic_stop_event.set()
    if self._loop is not None:
      self._loop.call_soon_threadsafe(self.audio_queue.put_nowait, None)
      if self.session_stop_event is not None:
        self._loop.call_soon_threadsafe(self.session_stop_event.set)

  async def aclose(self) -> None:
    """Closes the microphone stream and waits for the feeder thread to exit."""
    self.close()
    if self._feeder_thread is not None:
      await asyncio.to_thread(self._feeder_thread.join, 1.0)

  def __exit__(self, exc_type: Any, value: Any, traceback: Any) -> None:
    """Closes the microphone stream and releases resources."""
    del exc_type, value, traceback
    self.close()
    if self._feeder_thread is not None:
      self._feeder_thread.join(timeout=1.0)

  def consume_bridged_audio(self) -> list[bytes]:
    """Returns unfinalized audio chunks from the previous stream for replay.

    Computes the slice of `last_audio_input` after `final_request_end_time`
    (adjusted by `bridging_offset`), updates `bridging_offset`, and clears
    `new_stream`.

    Returns:
      List of raw PCM byte chunks to replay at the start of the new stream.
    """
    bridged: list[bytes] = []
    if self.new_stream and self.last_audio_input:
      chunk_time = self.streaming_limit / len(self.last_audio_input)
      if chunk_time != 0:
        if self.bridging_offset < 0:
          self.bridging_offset = 0
        if self.bridging_offset > self.final_request_end_time:
          self.bridging_offset = self.final_request_end_time
        chunks_from_ms = round(
            (self.final_request_end_time - self.bridging_offset) / chunk_time
        )
        self.bridging_offset = round(
            (len(self.last_audio_input) - chunks_from_ms) * chunk_time
        )
        bridged.extend(self.last_audio_input[chunks_from_ms:])
      self.new_stream = False
    return bridged


async def _get_next_chunk_or_stop(
    audio_queue: asyncio.Queue[bytes | None],
    session_stop_event: asyncio.Event | None,
) -> tuple[bytes | None, bool]:
  """Dequeues the next chunk or returns `(None, True)` if `session_stop_event` fires."""
  if session_stop_event is None:
    return await audio_queue.get(), False
  if session_stop_event.is_set():
    return None, True
  get_task = asyncio.create_task(audio_queue.get())
  stop_task = asyncio.create_task(session_stop_event.wait())
  done, pending = await asyncio.wait(
      [get_task, stop_task], return_when=asyncio.FIRST_COMPLETED
  )
  for task in pending:
    task.cancel()
  if get_task in done:
    return get_task.result(), False
  return None, True


async def send_microphone_audio(
    session: Any,
    audio_queue: asyncio.Queue[bytes | None],
    stream: ResumableMicrophoneStream | None = None,
    session_stop_event: asyncio.Event | None = None,
) -> None:
  """Streams PCM audio chunks from `audio_queue` to `session`.

  When `stream` is provided, replays any bridged unfinalized chunks from the
  previous stream first, records newly sent chunks in `stream.audio_input`, and
  stops the current session when `stream.streaming_limit` is reached or `None`
  is dequeued.

  Args:
    session: Active Gemini Live async session supporting `send_realtime_input`.
    audio_queue: Queue yielding raw PCM audio byte chunks, terminated by `None`.
    stream: Optional `ResumableMicrophoneStream` tracking infinite streaming
      state across session restarts.
    session_stop_event: Optional event signaling that the current session should
      stop sending and rotate or close.
  """
  rate = stream.rate if stream is not None else SEND_SAMPLE_RATE
  mime_type = f"audio/pcm;rate={rate}"
  batch_max_chunks = 10
  try:
    if stream is not None:
      bridged_chunks = stream.consume_bridged_audio()
      for i, chunk in enumerate(bridged_chunks):
        if session_stop_event is not None and session_stop_event.is_set():
          break
        stream.audio_input.append(chunk)
        await session.send_realtime_input(
            audio=types.Blob(data=chunk, mime_type=mime_type)
        )
        if (i + 1) % batch_max_chunks == 0:
          await asyncio.sleep(0.05)
    while True:
      if (
          stream is not None
          and get_current_time() - stream.start_time > stream.streaming_limit
      ):
        if session_stop_event is not None:
          session_stop_event.set()
        break

      audio_chunk, stopped = await _get_next_chunk_or_stop(
          audio_queue, session_stop_event
      )
      if stopped:
        break
      if audio_chunk is None:
        if stream is not None:
          stream.closed = True
        if session_stop_event is not None:
          session_stop_event.set()
        break
      if stream is not None:
        stream.audio_input.append(audio_chunk)
      await session.send_realtime_input(
          audio=types.Blob(data=audio_chunk, mime_type=mime_type)
      )
  except Exception as e:  # pylint: disable=broad-exception-caught
    print(f"\nError streaming audio: {e}")
  finally:
    await session.send_realtime_input(audio_stream_end=True)


def _resolve_result_end_time_ms(
    transcription: types.Transcription,
    stream: ResumableMicrophoneStream,
) -> int:
  """Determines the result end offset in milliseconds within the current stream."""
  offset_ms = _parse_offset_ms(getattr(transcription, "end_offset", None))
  if offset_ms is not None:
    return offset_ms
  return stream.bridging_offset + max(0, get_current_time() - stream.start_time)


async def receive_streaming_messages(
    session: Any,
    transcript_buffer: list[str],
    stream: ResumableMicrophoneStream | None = None,
    session_stop_event: asyncio.Event | None = None,
) -> None:
  """Receives live transcription messages from `session` and prints updates.

  Args:
    session: Active Gemini Live async session supporting `receive()`.
    transcript_buffer: List to which finalized transcript segments are appended.
    stream: Optional `ResumableMicrophoneStream` tracking timing and rotation
      state across session restarts.
    session_stop_event: Optional event signaled when `stream.streaming_limit` is
      exceeded so the sender coroutine can rotate to a new stream.
  """
  clear_line = "\r\x1b[2K"
  last_interim = ""
  try:
    while True:
      turn_completed = False
      async for message in session.receive():
        if (
            stream is not None
            and getattr(message, "voice_activity", None) is not None
        ):
          voice_activity = message.voice_activity
          if (
              voice_activity.voice_activity_type
              == types.VoiceActivityType.ACTIVITY_END
          ):
            activity_offset_ms = _parse_offset_ms(
                getattr(voice_activity, "audio_offset", None)
            )
            if activity_offset_ms is not None:
              stream.result_end_time = max(
                  stream.result_end_time, activity_offset_ms
              )
              if stream.last_transcript_was_final:
                stream.is_final_end_time = activity_offset_ms
        if not message.server_content:
          continue
        server_content = message.server_content
        if server_content.turn_complete or server_content.generation_complete:
          turn_completed = True
        interim = server_content.interim_input_transcription
        if interim and interim.text:
          last_interim = interim.text
          if stream is not None:
            stream.result_end_time = _resolve_result_end_time_ms(
                interim, stream
            )
            stream.last_transcript_was_final = False
          width = shutil.get_terminal_size((80, 20)).columns
          line = interim.text
          if len(line) >= width:
            line = "…" + line[-(width - 2) :]
          print(f"{clear_line}{line}", end="", flush=True)

        # Final result: commit it permanently on its own line.
        final = server_content.input_transcription
        if final and final.text:
          last_interim = ""
          if stream is not None:
            stream.result_end_time = _resolve_result_end_time_ms(final, stream)
            stream.is_final_end_time = stream.result_end_time
            stream.last_transcript_was_final = True
          transcript_buffer.append(final.text)
          print(f"{clear_line}{final.text}", flush=True)
        if (
            stream is not None
            and stream.closed
            and (
                server_content.turn_complete
                or server_content.generation_complete
            )
        ):
          break
      if (
          not turn_completed
          or session_stop_event is None
          or session_stop_event.is_set()
      ):
        break
  except Exception as e:  # pylint: disable=broad-exception-caught
    print(f"\nError transcribing audio: {e}")
  finally:
    if last_interim:
      transcript_buffer.append(last_interim)
      if stream is not None:
        stream.is_final_end_time = stream.result_end_time
        stream.last_transcript_was_final = True
async def _watch_stop_event(
    stream: ResumableMicrophoneStream,
    stop_event: asyncio.Event,
    record_seconds: float | None,
) -> None:
  """Waits for `stop_event` or `record_seconds` and closes `stream`."""
  if record_seconds is not None:
    try:
      await asyncio.wait_for(stop_event.wait(), timeout=record_seconds)
    except asyncio.TimeoutError:
      stop_event.set()
  else:
    await stop_event.wait()
  stream.close()


async def streaming_main(
    config: types.LiveConnectConfig,
    record_seconds: float | None = None,
    *,
    audio_path: str = AUDIO_PATH,
    audio_stream: Iterable[bytes] | None = None,
    chunk_size: int = DEFAULT_CHUNK_SIZE,
    chunk_delay_sec: float = BLOCK_DURATION,
    streaming_limit: int = STREAMING_LIMIT,
) -> str:
  """Simulates live microphone audio and streams it infinitely to Gemini Live.

  Starts a new Gemini Live session whenever `streaming_limit` (in milliseconds)
  is exceeded, replaying unfinalized audio chunks from the previous session so
  no audio is lost across stream restarts.

  Args:
    config: `LiveConnectConfig` for the Gemini Live session.
    record_seconds: Optional duration in seconds to stream before stopping, or
      None to stream until the audio stream finishes or is interrupted by
      `SIGINT`.
    audio_path: Path to the audio file used to simulate microphone input when
      `audio_stream` is None.
    audio_stream: Optional iterable of raw PCM byte chunks. When None,
      `simulate_microphone_stream` is used to read from `audio_path`.
    chunk_size: Audio chunk size in bytes when reading from `audio_path`.
    chunk_delay_sec: Delay in seconds between chunks when reading from
      `audio_path`.
    streaming_limit: Maximum duration of a single stream in milliseconds before
      rotating to a new stream.

  Returns:
    The space-joined finalized transcript text across all streams.
  """
  transcript_buffer: list[str] = []
  stop_event = asyncio.Event()
  loop = asyncio.get_running_loop()

  try:
    loop.add_signal_handler(signal.SIGINT, stop_event.set)  # Ctrl+C -> stop
  except NotImplementedError:
    pass

  mic_manager = ResumableMicrophoneStream(
      SEND_SAMPLE_RATE,
      chunk_size,
      audio_path=audio_path,
      audio_stream=audio_stream,
      chunk_delay_sec=chunk_delay_sec,
      streaming_limit=streaming_limit,
      loop=loop,
  )

  with mic_manager as stream:
    watch_task = asyncio.create_task(
        _watch_stop_event(stream, stop_event, record_seconds)
    )
    try:
      while not stream.closed:
        print(
            f"\n{stream.streaming_limit * stream.restart_counter}: NEW REQUEST"
        )
        print("Connecting... waiting for setup_complete.")
        async with client.aio.live.connect(
            model=MODEL_ID_LIVE, config=config
        ) as session:
          print("Setup complete — streaming audio (press Ctrl+C to stop).")
          session_stop_event = asyncio.Event()
          stream.session_stop_event = session_stop_event
          stream.start_time = get_current_time()
          stream.audio_input = []
          recv_task = asyncio.create_task(
              receive_streaming_messages(
                  session, transcript_buffer, stream, session_stop_event
              )
          )
          send_task = asyncio.create_task(
              send_microphone_audio(
                  session, stream.audio_queue, stream, session_stop_event
              )
          )

          await send_task
          try:
            await asyncio.wait_for(recv_task, timeout=5.0)
          except asyncio.TimeoutError:
            recv_task.cancel()

        if stream.result_end_time > 0:
          stream.final_request_end_time = stream.is_final_end_time
        else:
          stream.final_request_end_time = 0
        stream.result_end_time = 0
        stream.is_final_end_time = 0
        stream.last_audio_input = stream.audio_input
        stream.audio_input = []
        stream.restart_counter += 1

        if not stream.last_transcript_was_final:
          print()
        stream.new_stream = True
    finally:
      watch_task.cancel()
      await stream.aclose()

  print("\n\nFinal transcript:\n" + " ".join(transcript_buffer))
  return " ".join(transcript_buffer)


if __name__ == "__main__":
  _live_config = types.LiveConnectConfig(
      response_modalities=["TEXT"],
      input_audio_transcription=types.AudioTranscriptionConfig(),
  )
  asyncio.run(streaming_main(_live_config))
