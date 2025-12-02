# Gemini Live API React Demo

A React-based client for Google's Gemini Live API, featuring real-time audio/video streaming and a WebSocket proxy for secure authentication.

## Quick Start

### 1. Backend Setup

Install Python dependencies and start the proxy server:

```bash
# Install dependencies
pip install -r requirements.txt

# Authenticate with Google Cloud
gcloud auth application-default login

# Start the proxy server
python server.py
```

### 2. Frontend Setup

In a new terminal, start the React application:

Ensure you have Node.js and npm installed. If not, download and install them from [nodejs.org](https://nodejs.org/en/download/).

```bash
# Install Node modules
npm install

# Start development server
npm run dev
```

Open [http://localhost:5173](http://localhost:5173) to view the app.

## Features

- **Real-time Streaming**: Audio and video streaming to Gemini.
- **React Components**: Modular UI with `LiveAPIDemo.jsx`.
- **Secure Proxy**: Python backend handles Google Cloud authentication.
- **Custom Tools**: Support for defining client-side tools.
- **Media Handling**: dedicated audio capture and playback processors.

## Project Structure

```
/
├── server.py           # WebSocket proxy & auth handler
├── src/
│   ├── components/
│   │   └── LiveAPIDemo.jsx  # Main application logic
│   ├── utils/
│   │   ├── gemini-api.js    # Gemini WebSocket client
│   │   └── media-utils.js   # Audio/Video processing
│   └── App.jsx              # Root component
└── public/
    └── audio-processors/    # Audio worklets
```

## Core APIs

### GeminiLiveAPI

Located in `src/utils/gemini-api.js`, this class manages the WebSocket connection.

```javascript
import { GeminiLiveAPI } from "./utils/gemini-api";

const client = new GeminiLiveAPI(
  "ws://localhost:8080",
  "your-project-id",
  "gemini-2.0-flash-exp"
);

client.connect();
client.sendText("Hello Gemini");
```

### Media Integration

The app uses AudioWorklets for low-latency audio processing:

- `capture.worklet.js`: Handles microphone input.
- `playback.worklet.js`: Handles PCM audio output.

## Configuration

- **Model**: Defaults to `gemini-live-2.5-flash-preview-native-audio-09-2025`
- **Voice**: Configurable in `LiveAPIDemo.jsx` (Puck, Charon, etc.)
- **Proxy Port**: Default `8080` (set in `server.py`)
