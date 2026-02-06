# Google Cloud Wealth Advisor - Architecture & Design

## 🏛 System Overview

The Google Cloud Wealth Advisor is an advanced, voice-first conversational AI application designed to provide personalized financial guidance. It leverages a **"Thick Server"** architecture powered by the **Google Agent Development Kit (ADK)** to ensure secure, stateful, and enterprise-grade interactions.

### High-Level Architecture

```mermaid
graph TD
    User["User (Browser/Microphone)"] <-->|WebSocket /ws| Proxy[FastAPI Backend]
    Proxy <-->|Google ADK| Agent[AI Agent Logic]
    Agent <-->|Gemini Live API| LLM["Google Gemini 2.5 Flash"]

    subgraph "Backend Services"
        Agent -- "Reads/Writes" --> Firestore[("Firestore User Data")]
        Agent -- "RAG Search" --> Vertex AI [Vertex AI Search]
        Agent -- "Tools" --> PythonTools[Python Tools]
    end

    subgraph "Frontend Experience"
        User -- "Sees" --> UI[React/Next.js UI]
        User -- "Hears" --> Audio[PCM Audio Stream]
    end
```

## 🏗 Architectural Decision: The "Thick Server" Pattern

This application adopts a **Server-Centric** (or "Thick Server") architecture. While direct-to-LLM patterns are often suitable for rapid prototyping and lightweight interfaces, enterprise-grade financial applications require stricter controls over data flow, security, and state management.

| Feature | ⚡️ Direct-to-LLM Pattern | 🛡 Server-Centric Pattern (This Project) |
| :--- | :--- | :--- |
| **Security** | Logic & prompts often visible in client-side code. | **Secure:** Business logic & system instructions remain protected on the backend. |
| **State** | Often transient or client-managed. | **Persistent:** Sessions are managed centrally (e.g., Firestore) ensuring continuity across devices. |
| **Capabilities** | Constrained by browser security context. | **Powerful:** Secure access to internal databases, RAG pipelines, and private APIs. |
| **Protocol** | Raw LLM event streams. | **Structured:** A typed, stable JSON protocol that decouples the UI from model implementation details. |

## 🧩 Key Components

### 1. Frontend (Next.js & React)
*   **Role:** The presentation layer responsible for capturing user audio, rendering the UI, and playing back agent responses.
*   **Audio Handling:** Uses `AudioWorklet` for low-latency PCM audio capture (16kHz) and playback (24kHz).
*   **Visual Rendering:** Interprets structured JSON commands from the backend to display rich UI elements (graphs, tables, alerts) instead of just plain text.
*   **Protocol:** Communicates exclusively via a single WebSocket connection.

### 2. Backend (FastAPI & Python)
*   **Role:** The secure orchestrator of the application. It does not just pass messages; it understands them.
*   **API Framework:** **FastAPI** handles the WebSocket upgrade and routing.
*   **Agent Engine:** **Google ADK** manages the conversation loop, state, and tool execution.
*   **Protocol Translator:** Wraps raw Gemini events into a custom, frontend-friendly JSON envelope (see Protocol section below).

### 3. Intelligence Layer (Gemini & ADK)
*   **Model:** Powered by **Gemini 2.0 Flash**, optimized for speed and multimodal interaction.
*   **State Management:** Uses `InMemorySessionService` (extensible to Redis/Firestore) to remember user context across turns.
*   **Tooling:** secure Python functions that can:
    *   Query a user's portfolio from Firestore.
    *   Search financial documents (RAG) via Vertex AI.
    *   Trigger UI updates on the client.

## 🔌 The Communication Protocol

The application uses a custom JSON-based WebSocket protocol to standardize communication between the Frontend and Backend.

**Envelope Structure:**
Every message sent to the client follows this format:

```json
{
  "mime_type": "application/json",  // or "audio/pcm", "text/plain"
  "data": { ... }                   // The payload
}
```

### Message Types

| Mime Type | Data Content | Direction | Description |
| :--- | :--- | :--- | :--- |
| `audio/pcm` | Base64 Encoded Bytes | Bidirectional | Raw audio chunks (16kHz in, 24kHz out). |
| `text/plain` | String | Bidirectional | User text input or Agent text transcript. |
| `application/json` | JSON Object | Agent -> Client | Structured commands (Tools, UI Updates, Control Signals). |

### Control Signals & Visuals

Special control signals are sent as `application/json` to drive the UI:

*   **Interruption:** `{ "interrupted": true }` - Tells frontend to stop audio playback immediately.
*   **Turn Complete:** `{ "turn_complete": true }` - Signals the agent is done speaking.
*   **Visuals:**
    ```json
    {
      "type": "financial_summary_visual",
      "data": { "total_assets": 150000, ... }
    }
    ```
    *Sent when the agent wants to show a specific component (e.g., a chart) instead of just speaking.*

## ☁️ Google Cloud Infrastructure

The solution relies on the following Google Cloud services:

*   **Cloud Run:** Serverless hosting for both Frontend (Next.js) and Backend (FastAPI containers).
*   **Firestore:** NoSQL database for storing user profiles and session history.
*   **Vertex AI Search:** Enterprise search engine for retrieving financial document insights (RAG).
*   **Secret Manager:** Secure storage for API keys and configuration secrets.
*   **Vertex AI API:** The underlying access point for Gemini models.
