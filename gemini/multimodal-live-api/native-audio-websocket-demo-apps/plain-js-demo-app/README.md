# Gemini Live API - Vanilla JS

WebSocket client for Google's Gemini Live API with audio/video streaming support. No frameworks, just vanilla JavaScript.

## Quick Start

```bash
# Install dependencies
pip3 install -r requirements.txt

# Authenticate with Google Cloud
gcloud auth application-default login

# Start server (serves UI + WebSocket proxy)
python3 server.py

# Open browser
open http://localhost:8000
```

## Features

- **Real-time audio/video streaming** to Gemini
- **Custom tools** (alerts, CSS injection)
- **Device selection** for mic/camera
- **Auto-authentication** via proxy server
- **Zero config** - proxy URL pre-configured

## Project Structure

```
/
├── server.py      # WebSocket proxy + HTTP server
├── requirements.txt     # Python dependencies
└── frontend/
    ├── index.html      # UI
    ├── geminilive.js   # Gemini API client
    ├── mediaUtils.js   # Audio/video streaming
    ├── tools.js        # Custom tool definitions
    └── script.js       # App logic
```

## Core APIs

### GeminiLive Client

```javascript
const client = new GeminiLiveAPI(proxyUrl, projectId, model);
client.addFunction(toolInstance); // Add custom tools
client.connect(accessToken); // Connect (token optional with proxy)
client.sendText("Hello"); // Send text
client.sendAudioMessage(base64); // Send audio
client.sendImageMessage(base64); // Send image
```

### Media Streaming

```javascript
// Audio streaming
const audioStreamer = new AudioStreamer(client);
await audioStreamer.start(deviceId); // Optional device ID

// Video streaming
const videoStreamer = new VideoStreamer(client);
await videoStreamer.start({ fps: 1, deviceId: "..." });

// Audio playback
const player = new AudioPlayer();
await player.play(base64PCM);
```

### Custom Tools

```javascript
class MyTool extends FunctionCallDefinition {
  constructor() {
    super("tool_name", "description", parameters, required);
  }

  functionToCall(params) {
    // Tool implementation
  }
}
```

## Configuration Options

- **Model**: `gemini-live-2.5-flash-preview-native-audio-09-2025` (default)
- **Voice**: Puck, Charon, Kore, Fenrir, Aoede
- **Response**: Audio, text, or both
- **Tools**: Custom functions or Google grounding

## Development

The proxy server handles:

- Google Cloud authentication
- WebSocket proxying to Gemini API
- Static file serving from `frontend/`
