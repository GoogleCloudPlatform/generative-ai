# Travel Booking Multi-Agent Assistant (LiveKit ADK)

An enterprise-grade multi-agent voice orchestrator system built on **Google's Agent Development Kit (ADK)** and **LiveKit**. This application establishes a low-latency WebRTC-to-Gemini-Live bridge allowing users to naturally converse with specialized travel agents to search, book, and manage flights and hotels in a single session.

---

## 1. System Architecture & Flow

The system coordinates high-performance WebRTC audio streams, translates them into real-time bidirectional ADK session events, and communicates with Gemini Live API models.

```
                    ┌───────────────────────────────────────┐
                    │             Client Browser            │
                    └───────────────────────────────────────┘
                       ▲                                 │
            WebRTC     │ (Render Audio /                 │ (User Audio /
          DataChannel  │  Data Transcription)            │  WebRTC Media)
                       │                                 ▼
┌──────────────────────┼───────────────────────────────────────────────────────┐
│                      │             LiveKit Server                        │
│                      │                                                       │
│                      └──────────────┬───────────────▲────────────────────────┘
│                                     │               │
│                      Audio Frames   │               │ Audio Frames
│                      (Gemini -> LK) │               │ (LK -> Gemini)
│                                     ▼               │
│            ┌────────────────────────────────────────┴────────────┐           │
│            │               FastAPI Application Server            │           │
│            │                                                     │           │
│            │   ┌─────────────────────────────────────────────┐   │           │
│            │   │          app/livekit_bridge.py              │   │           │
│            │   │  - Converts 48kHz LK Audio -> 16kHz PCM     │   │           │
│            │   │  - Feeds LiveRequestQueue                   │   │           │
│            │   └──────────────────────┬──────────────────────┘   │           │
│            │                          │                          │           │
│            │                          ▼                          │           │
│            │               ┌─────────────────────┐               │           │
│            │               │  LiveRequestQueue   │               │           │
│            │               └──────────┬──────────┘               │           │
│            │                          │                          │           │
│            │                          ▼                          │           │
│            │               ┌─────────────────────┐               │           │
│            │               │     ADK Runner      │               │           │
│            │               └──────────┬──────────┘               │           │
│            └──────────────────────────┼──────────────────────────┘           │
└───────────────────────────────────────┼──────────────────────────────────────┘
                                        │
                                        │ Bidirectional WebSockets (v1alpha)
                                        ▼
                    ┌───────────────────────────────────────┐
                    │          Gemini Live API              │
                    │     (gemini-live-2.5-flash)           │
                    └───────────────────────────────────────┘
```

### Protocol Lifecycle:
1. **Session Establishment**: Client requests a token from `/token`, triggering the background instantiation of the `LiveKitGeminiBridge`.
2. **WebRTC Join**: The client browser joins the LiveKit room. The `LiveKitGeminiBridge` also connects a virtual audio participant into the room.
3. **Upstream Pipeline (User -> gemini)**:
   - Client streams user audio to the LiveKit Room using **WebRTC**.
   - `LiveKitGeminiBridge` subscribes to the track, extracts the 48kHz frames, downsamples to **16kHz mono PCM**, and pushes them to the ADK `LiveRequestQueue`.
   - The ADK `Runner` streams the queue content to Gemini Live API via an underlying **secure WebSocket connection (`bidiGenerateContent` protocol)**.
4. **Downstream Pipeline (Gemini -> User)**:
   - Gemini responds in real-time with audio buffers and textual transcriptions via the secure WebSocket.
   - ADK `Runner` intercepts the events and passes them to the bridge.
   - The bridge pushes the audio (resampled to 24kHz) back into LiveKit via the LocalAudioTrack, and publishes transcription text through WebRTC **DataChannels**.

---

## 2. The Booking Agents (Multi-Agent Orchestrator)

Inside the `app/travel_booking/` package, we implement a **three-tier hierarchical multi-agent orchestrator**:

```
                             ┌──────────────────────┐
                             │ session_orchestrator │
                             │  (Central Router)    │
                             └──────────┬───────────┘
                                        │
                     ┌──────────────────┴──────────────────┐
                     ▼                                     ▼
          ┌─────────────────────┐               ┌─────────────────────┐
          │  FlightBookingAgent │◀─────────────▶│  HotelBookingAgent  │
          │ (Flight search/book)│   A2A Transfer│ (Hotel search/book) │
          └─────────────────────┘               └─────────────────────┘
```

1. **Session Orchestrator** (`app/travel_booking/agent.py`):
   - The root agent. Listens to the user's intent and delegates control to the specialist sub-agents (`FlightBookingAgent` or `HotelBookingAgent`) via ADK's native agent-routing tool calls.
2. **FlightBookingAgent** (`app/travel_booking/agents/flight_booking.py`):
   - Specialized in travel search and reservations.
   - Equipped with 3 mock tools: `search_flights`, `book_flight`, `cancel_flight`.
   - Configured with `HotelBookingAgent` as a sub-agent to enable a direct, silent handoff when the user switches context to hotel bookings.
3. **HotelBookingAgent** (`app/travel_booking/agents/hotel_booking.py`):
   - Specialized in lodging discovery and booking.
   - Equipped with 3 mock tools: `search_hotels`, `book_hotel`, `cancel_hotel`.

---

## 3. LiveKit Bridge & Configuration Overview

### `app/livekit_bridge.py` Overview
This class acts as the low-latency audio converter and routing engine.
- **Audio Buffering & Downsampling**: Standardizes LiveKit's high-fidelity audio stream (downsamples 48kHz stereo to 16kHz mono PCM) and sends it in small, optimized 20ms buffers (640 bytes) to reduce WebSocket latency.
- **Realtime Event Mapping**: Listens to `runner.run_live` event generators, translates model text outputs and prints them to the server console, and publishes data events onto WebRTC DataChannels.

### Runner Configuration (`app/main.py`)
- The `Runner` is configured with standard `InMemorySessionService` or `DatabaseSessionService` to persist dialogue histories.
- Integrated with a custom **`SessionResumptionIsolationPlugin`**: Clears the transparency resumption handles when transferring between sub-agents, preventing key-based Gemini API errors during sub-agent handoffs.

```python
runner = Runner(
    app_name="livekit-adk",
    agent=agent.root_agent,
    session_service=session_service,
    auto_create_session=True,
    plugins=[SessionResumptionIsolationPlugin()]
)
```

### Run Configuration (`app/livekit_bridge.py`)
Configured specifically to handle high-performance native audio models over WebRTC:
```python
run_config = RunConfig(
    streaming_mode=StreamingMode.BIDI,
    response_modalities=["AUDIO"],
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    session_resumption=types.SessionResumptionConfig(),
    enable_affective_dialog=True
)
```
- **`response_modalities=["AUDIO"]`**: Crucial for native audio Gemini models; enforces direct-to-audio responses to ensure natural voice cadence.
- **`output_audio_transcription`**: Tells Gemini to send text transcripts along with the audio stream so the bridge can display them on the UI.

---

## 4. Configuration & Run Instructions

### 1. Environment Setup (`app/.env`)
Create a file named `app/.env` inside the project. Configure the variables:

```bash

# Model selection
DEMO_AGENT_MODEL="gemini-live-2.5-flash-native-audio"

# LiveKit Settings (Local development values)
USE_LIVEKIT=true
LIVEKIT_URL=ws://localhost:7880
LIVEKIT_API_KEY=devkey
LIVEKIT_API_SECRET=secret
```

### 2. Installing & Running LiveKit (macOS)

For local development, you need a running LiveKit server instance. On macOS, install and run it using Homebrew:

```bash
# Install LiveKit Server
brew install livekit

# Start the server in development mode
livekit-server --dev
```

The `--dev` flag automatically starts the server on `localhost:7880` using the default credentials:
- **API Key**: `devkey`
- **API Secret**: `secret`

*(These credentials match the default `.env` template above.)*

### 3. Launching the Application

Ensure you are running commands using the project's virtual environment.

**Step 1: Sync dependencies**
```bash
uv sync
```

**Step 2: Start the Dev Server**
Navigate into the `app` folder and run:
```bash
uv run --project .. python3 -m uvicorn main:app --reload
```

The application starts a FastAPI server listening at `http://127.0.0.1:8000/static/livekit`. Open this URL in your browser to interact with the voice assistant!

---
