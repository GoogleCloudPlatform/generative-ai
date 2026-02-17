# Usage & API

The application exposes a single primary endpoint for the WebSocket connection and several internal tools.

## 🔌 WebSocket API

The core interaction happens over a secure WebSocket connection.

**Endpoint:** `ws://localhost:8081/api/websocket/{session_id}`

### Protocol Messages

The protocol uses a simple JSON envelope for all messages:

```json
{
  "mime_type": "string",
  "data": "string | object"
}
```

#### Client -> Server
*   **Audio (User Speech):**
    *   `mime_type`: `audio/pcm;rate=16000`
    *   `data`: Base64 encoded PCM audio (16kHz, Mono, 16-bit).
*   **Text (Chat Input):**
    *   `mime_type`: `text/plain`
    *   `data`: "Hello, advisor."

#### Server -> Client
*   **Audio (Agent Speech):**
    *   `mime_type`: `audio/pcm`
    *   `data`: Base64 encoded PCM audio (24kHz, Mono, 16-bit).
*   **Control Signals:**
    *   `{"turn_complete": true}`
    *   `{"interrupted": true}`
*   **Visual Tools:**
    *   `mime_type`: `application/json`
    *   `data`: `{ "type": "appointment_scheduler", ... }`

---

## 🔊 Audio Requirements

To ensure proper communication with the Gemini Live API, the frontend MUST adhere to the following audio formats. Mismatches will result in distorted audio or connection failures.

| Direction | Format | Sample Rate | Channels |
| :--- | :--- | :--- | :--- |
| **Input** (Microphone) | Linear PCM (16-bit) | **16,000 Hz** | Mono |
| **Output** (Playback) | Linear PCM (16-bit) | **24,000 Hz** | Mono |

*Note: The frontend architecture splits the `AudioContext` to handle these two different sample rates simultaneously.*

---

## 🧰 Agent Tools

The agent is equipped with the following capabilities:

### 1. RAG Search (`search_financial_documents`)
Queries indexed PDF documents in Vertex AI Search.
*   **Trigger:** "How do 529 plans work?" or "What are the risks of bonds?"
*   **Source:** `/src/backend/data/*.pdf` (Uploaded to GCS during setup).

### 2. Market Data (`get_market_summary_data`)
Provides real-time (simulated) market snapshots.
*   **Trigger:** "How is the market doing?"
*   **Data:** S&P 500, NASDAQ, Dow Jones.

### 3. Appointment Scheduler
Displays an interactive calendar widget.
*   **Trigger:** "I'd like to book an appointment."

### 4. Financial Summary
Displays a visual breakdown of the user's assets.
*   **Trigger:** "Show me my account summary."
