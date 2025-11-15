# Implementation Plan: Gemini Live Telephony Application

This document outlines the step-by-step process to create the Gemini Live Telephony application, a real-time, bidirectional voice-to-AI system integrating Twilio, FastAPI, and Google Gemini Live on Cloud Run.

## 1. Project Setup and Dependencies

- **Initialize Project:** Set up a Python project with a virtual environment.
- **Install Dependencies:** Install necessary Python libraries as listed in `requirements.txt`:
  - `fastapi`: For the web server.
  - `uvicorn`: As the ASGI server.
  - `python-dotenv`: To manage environment variables.
  - `google-generativeai`: The Google Gemini SDK.
  - `numpy`: For numerical operations on audio data.
  - `samplerate`: For high-quality audio resampling.
  - `audioop`: For µ-law and linear PCM audio conversions.
- **Environment Configuration:** Create a `.env` file to store sensitive information like `GEMINI_API_KEY` and other gemini configurations.

## 2. FastAPI Server Implementation (`main.py`)

- **Create `main.py`:** This will be the entry point for the FastAPI application.
- **Implement `/twiml` Endpoint:**
  - Create an HTTP POST endpoint that responds to Twilio's webhook.
  - This endpoint will generate and return a TwiML response with the `<Connect><Stream>` verb, pointing to the WebSocket endpoint.
- **Implement `/ws/twilio` WebSocket Endpoint:**
  - This will be the core of the application, handling the bidirectional audio stream.
  - It will manage the WebSocket lifecycle: connection, message handling, and disconnection.
  - It will use `asyncio.create_task` to run three concurrent tasks:
    1. `handle_twilio_to_gemini`: Processes audio from Twilio to Gemini.
    2. `handle_gemini_to_twilio`: Processes audio from Gemini to Twilio.
    3. `conversation_loop`: Manages the conversation logic with the Gemini API.

## 3. Audio Transcoding Pipeline (`main.py`)

- **Inbound (Twilio to Gemini):**
  - **Base64 Decoding:** Decode the Base64 payload from Twilio media messages.
  - **µ-law to PCM:** Convert the 8kHz µ-law audio to 16-bit linear PCM using `audioop.ulaw2lin`.
  - **Upsampling:** Upsample the 8kHz PCM to 16kHz PCM using the `samplerate` library.
- **Outbound (Gemini to Twilio):**
  - **Downsampling:** Downsample the 24kHz PCM audio from Gemini to 8kHz PCM using `samplerate`.
  - **PCM to µ-law:** Convert the 8kHz linear PCM to µ-law using `audioop.lin2ulaw`.
  - **Base64 Encoding:** Encode the µ-law audio to Base64 to be sent back to Twilio.

## 4. Gemini Live Integration (`main.py`)

- **Initialize Gemini Client:** Set up the Gemini client with the API key from environment variables.
- **`conversation_loop` Function:**
  - **System Instruction:** Define a detailed system instruction for the Gemini model, including persona, context, and constraints.
  - **Conversation History:** Read the `transcription.txt` file to provide the previous conversation history to the model for context.
  - **`LiveConnectConfig`:** Configure the Gemini session with the system instruction, audio settings, and real-time input configuration.
  - **Session Management:** Create a new Gemini Live session for each turn of the conversation.
  - **Sender/Receiver Tasks:** Use `asyncio` tasks to concurrently send audio to and receive audio/transcription from the Gemini session.

## 5. Utility Functions (`utils.py`)

- **`save_transcription` Function:**
  - Create a function to append the user and Gemini transcriptions to a file named `transcription.txt`.
  - This file will serve as a simple, file-based method for maintaining conversation history during a single call.

## 6. State Management

- **In-memory State:** Use a Python dictionary (`call_state`) to manage the active state of the call within a single Cloud Run instance.
- **File-based Conversation History:**
  - At the start of a call, create a `transcription.txt` file.
  - Throughout the call, append transcriptions to this file.
  - At the end of the call, delete the `transcription.txt` file to clear the history for the next call.
- **Note on Production Systems:** For a production-grade application, this file-based approach should be replaced with a more robust solution like Google Memorystore (Redis) to handle horizontal scaling and state persistence.

## 7. Containerization and Deployment

- **Create `Dockerfile`:**
  - Use a slim Python base image.
  - Install system dependencies like `libsamplerate0`.
  - Install Python dependencies from `requirements.txt`.
  - Use `uvicorn` to run the application.
- **Create `deploy.sh`:**
  - Write a shell script to automate the process of building the Docker image and deploying it to Google Cloud Run.
- **Deploy to Cloud Run:**
  - Configure the Cloud Run service with the following settings, as seen in `deploy.sh`:
    - `--min-instances=1`: This is crucial for a low-latency application to avoid "cold starts," ensuring that an instance is always running and ready to accept calls.
    - `--timeout=3600`: Sets a long request timeout (1 hour) to accommodate long-running WebSocket connections for phone calls.
    - `--memory=2Gi` and `--cpu=2`: Allocates sufficient resources for the CPU-intensive audio resampling tasks.
    - `--session-affinity`: Ensures that requests from the same client (Twilio, in this case) are routed to the same Cloud Run instance, which is important for maintaining the WebSocket connection.
    - `--concurrency=1`: This is a critical setting for this application. Since a single instance handles a single, stateful phone call at a time, setting concurrency to 1 ensures that each instance is dedicated to a single call. This prevents issues with managing multiple concurrent calls on a single instance.
    - `--no-cpu-throttling`: The audio resampling process is CPU-intensive and sensitive to latency. Disabling CPU throttling ensures that the instance has access to the full allocated CPU, which is essential for real-time audio processing and maintaining a smooth, low-latency conversation.
    - `--set-env-vars`: Passes the necessary environment variables (`GEMINI_API_KEY` and `SERVICE_URL`) to the container.