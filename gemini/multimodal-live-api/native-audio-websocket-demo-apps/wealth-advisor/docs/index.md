# Overview

The **Financial Advisor** application is a multimodal AI agent that provides real-time financial guidance using the **Gemini Live API**.

It is designed to demonstrate a **secure, server-to-server** integration pattern where sensitive credentials and business logic are isolated in a Python backend, while the frontend handles high-performance audio streaming.

## 🏗️ Architecture

The application implements a "Double Proxy" pattern to facilitate secure local development that mirrors a production Private Cloud Run environment.

### 1. Frontend (Next.js)
*   **Audio Capture:** Uses the `AudioWorklet` API to capture microphone input.
*   **Sample Rate Splitting:**
    *   **Input (Microphone):** 16kHz (Required by Gemini Live).
    *   **Output (Speaker):** 24kHz (High-quality voice output).
*   **Streaming:** Sends PCM audio data over a WebSocket connection to the backend.

### 2. Backend (FastAPI)
*   **Security:** Acts as a trusted intermediary. It holds the Google Cloud Service Account keys and manages the session with the Gemini Live API.
*   **Session Management:** Maintains the state of the conversation and user context.
*   **Tool Execution:** Executes server-side tools (like RAG Search or Market Data lookups) and returns the results to the model.

### 3. Gemini Live API
*   **Multimodal:** Processes audio directly without intermediate Speech-to-Text (STT) or Text-to-Speech (TTS) services.
*   **Real-time:** Supports full-duplex streaming, allowing for natural interruptions and turn-taking.

---

## ⚡ Key Capabilities

*   **Natural Voice Interaction:** Talk to the advisor naturally. The model detects when you stop speaking (VAD) and replies instantly.
*   **RAG (Retrieval Augmented Generation):** The agent can "read" from a library of PDF financial documents (indexed in **Vertex AI Search**) to provide grounded answers.
*   **Rich UI Tools:** The agent can push visual elements to the client, such as:
    *   **Appointment Scheduler:** A calendar widget for booking meetings.
    *   **Financial Summary:** A visual breakdown of the user's accounts.
    *   **Market Data:** Real-time stock performance charts.

## 📁 Project Structure

```text
├── src/
│   ├── backend/      # FastAPI application (Python)
│   ├── frontend/     # Next.js application (TypeScript)
│   └── scripts/      # Infrastructure & Setup scripts
├── docs/             # Documentation
├── .task/            # Taskfile definition scripts
└── Taskfile.yaml     # Main entry point for commands
```
