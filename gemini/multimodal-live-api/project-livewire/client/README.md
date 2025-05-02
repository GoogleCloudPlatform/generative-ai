# Project Livewire - Client Application

This README provides details about the client-side component of Project Livewire. The client is a web application built with Vanilla JavaScript, HTML, and CSS, designed to interact with the backend server and Google's Gemini API to provide a multimodal chat experience.

## Overview

The client application is responsible for:

- **User Interface (UI):** Providing a responsive and intuitive web interface for users to interact with the AI. This includes both a development UI (`index.html`) and a mobile-optimized UI (`mobile.html`).
- **Input Handling:** Capturing user inputs including:
    - Voice input via microphone using WebAudio API.
    - Text input from text fields.
    - Webcam and screen sharing video streams via MediaStream API.
- **Output Rendering:** Displaying AI responses, including:
    - Text responses in a chat-like interface.
    - Audio responses played back using WebAudio API.
    - Video streams from webcam and screen sharing.
- **WebSocket Communication:** Establishing and managing a WebSocket connection with the backend server (`server` component) to send user inputs and receive AI responses in real-time.
- **Media Processing:** Handling audio recording, audio streaming, and video capture for multimedia interactions.

## Key Components

The `client` directory is structured into several key components:

- **`index.html`**: The main HTML file for the **development user interface**. This UI includes more detailed logging and debugging features for development and testing.
- **`mobile.html`**: The HTML file for the **production, mobile-optimized user interface**. This UI is designed for a cleaner and more streamlined user experience, especially on mobile devices.
- **`styles/`**: Contains CSS stylesheets for both the development (`style.css`) and mobile (`mobile-style.css`) UIs.
- **`src/`**:  Holds all the JavaScript source code, organized into subdirectories:
    - **`api/`**:  Contains modules for API communication:
        - **`gemini-api.js`**:  Handles WebSocket connection and communication with the backend server. Manages sending different types of messages (audio, text, image, end signals) and receiving responses.
    - **`audio/`**:  Contains modules for audio processing:
        - **`audio-recorder.js`**:  Handles audio recording from the microphone using WebAudio API, including starting, stopping, muting, and unmuting recording. Emits 'data' events with base64 encoded audio chunks.
        - **`audio-recording-worklet.js`**:  An AudioWorklet processor for efficient real-time audio processing and chunking.
        - **`audio-streamer.js`**:  Handles streaming and playback of audio received from the server using WebAudio API. Manages audio buffer queue, playback, and stopping/resuming audio.
        - **`audioworklet-registry.js`**:  Manages registration of AudioWorklet modules.
    - **`media/`**:  Contains modules for media handling:
        - **`media-handler.js`**:  Manages webcam and screen sharing functionalities using MediaStream API. Includes starting/stopping media streams, capturing video frames, and switching cameras.
    - **`utils/`**:  Contains utility functions:
        - **`utils.js`**:  Includes helper functions like `audioContext()` for creating and resuming AudioContext, and `base64ToArrayBuffer()` for converting base64 strings to ArrayBuffers.
- **`assets/`**: Contains static assets such as images, icons, and favicons used in the UI.
- **`cloudbuild.yaml`**:  Cloud Build configuration file for deploying the client application to Google Cloud Run.
- **`Dockerfile`**: Dockerfile for building the client application's container image.
- **`nginx.conf`**: Nginx configuration file for serving the client application from within a Docker container.

## Technologies Used

The client application leverages the following web technologies:

- **Vanilla JavaScript (ES6+):** For all client-side logic, interaction handling, and API communication.
- **HTML5:** For structuring the user interface (both development and mobile UIs).
- **CSS3:** For styling the user interface and ensuring responsiveness (using `style.css` and `mobile-style.css`).
- **WebAudio API:** For capturing audio from the microphone, processing audio data, and playing back audio responses.
- **MediaStream API (getUserMedia, getDisplayMedia):** For accessing webcam and screen sharing video streams.
- **WebSocket API:** For establishing and maintaining real-time, bidirectional communication with the backend server.
- **EventEmitter3:** A lightweight JavaScript library for event handling, used for communication between audio components.
- **Material Symbols Outlined (Google Fonts):** For icons used in the user interface.
- **nginx:alpine:**  Base image for the Docker container, providing an efficient and lightweight web server for serving static files.

## Project Structure

```
client/
├── assets/
│   └── ... (images, icons, favicon)
├── src/
│   ├── api/
│   │   └── gemini-api.js
│   ├── audio/
│   │   ├── audio-recorder.js
│   │   ├── audio-recording-worklet.js
│   │   ├── audio-streamer.js
│   │   └── audioworklet-registry.js
│   ├── media/
│   │   └── media-handler.js
│   └── utils/
│       └── utils.js
├── styles/
│   ├── mobile-style.css
│   └── style.css
├── index.html
├── mobile.html
├── cloudbuild.yaml
├── Dockerfile
├── nginx.conf
└── README.md  (This file)
```

## Development

### Local Development Setup

To develop and test the client application locally, you will need:

1.  **A running backend server:**  Follow the instructions in the main project README or the `server/README.md` to set up and run the backend server locally. Ensure the server is accessible at `ws://localhost:8081` (or the endpoint configured in `client/src/api/gemini-api.js` if you are using a different setup).
2.  **A simple HTTP server:**  You can use Python's built-in simple HTTP server to serve the client files. Navigate to the `client/` directory in your terminal and run:
    ```bash
    python -m http.server 8000
    ```
    This will start a server on `http://localhost:8000`.

### Running the Development UI and Mobile UI

- **Development UI:** Open your web browser and navigate to `http://localhost:8000/index.html`. This UI is useful for debugging and testing features, as it provides more detailed logging and UI elements for monitoring the WebSocket connection and function calls.
- **Mobile UI:** Open your web browser and navigate to `http://localhost:8000/mobile.html` or `http://localhost:8000/mobile.html?mobile=true` (to force mobile view even on desktop). This UI provides a cleaner interface optimized for mobile devices and touch interactions.

### Development UI Features

The development UI (`index.html`) includes features to aid in debugging and testing:

- **Detailed WebSocket connection status:** Displays information about the WebSocket connection state and any connection errors in the browser's developer console.
- **Function call monitoring and logging:** Logs function calls and API responses in the output chat area, providing insights into tool usage and data flow.
- **Text input options:** Allows for testing text-based interactions without relying on voice input, simplifying testing of text-based features.
- **Enhanced error reporting and visualization:** Displays more verbose error messages in the UI and browser console to help identify and resolve issues quickly.

### Production UI Features

The mobile-optimized production UI (`mobile.html`) focuses on:

- **Clean, minimal interface:**  Provides a streamlined and uncluttered UI optimized for voice-first interaction and mobile use.
- **Optimized for touch interactions:** UI elements and controls are designed for easy touch input on mobile devices.
- **Streamlined error handling and recovery:**  Presents user-friendly error messages and attempts to handle connection issues gracefully.
- **Optimized performance for mobile devices:** Uses efficient JavaScript code and minimal dependencies to ensure smooth performance on mobile browsers.

## Troubleshooting

### Common Issues and Troubleshooting Steps

- **WebSocket Connection Failures:**
    - **Verify WebSocket URL:** Double-check that the WebSocket URL in `client/src/api/gemini-api.js` is correctly configured to point to your running backend server (e.g., `ws://localhost:8081` for local development, or your Cloud Run backend URL for deployed setups).
    - **Check Backend Service:** Ensure the backend server is running and accessible. Check its logs for any errors.
    - **CORS Errors (Browser Console):** If you see CORS-related errors in the browser's developer console, it might indicate a configuration issue on the backend server side. Ensure the backend is configured to handle requests from `http://localhost:8000` (or your client's origin).
    - **Firewall/Network Issues:** Check if any firewalls or network configurations are blocking WebSocket connections between the client and server.

- **API Errors or Unexpected Behavior:**
    - **Check Browser Developer Console (Network Tab, Console Tab):** Inspect the browser's developer console for any JavaScript errors, WebSocket errors, or network requests that are failing.
    - **Server Logs:** Examine the backend server logs for any errors or exceptions occurring during request processing or Gemini API interactions.
    - **API Key Configuration:** Verify that API keys are correctly configured in the backend server's environment variables or Secret Manager (if deployed on Google Cloud).
    - **Quota Limits:** If you are encountering errors related to API quotas, check your Google Cloud project's API usage and quota limits in the Google Cloud Console.

- **Audio or Video Issues:**
    - **Permissions:** Ensure that the browser has been granted permission to access the microphone and webcam. Check browser settings and prompts for media permissions.
    - **Device Availability:** Verify that the microphone and webcam are properly connected and functioning on your system.
    - **Audio Context State:** If audio playback is not working, check the browser's developer console for any WebAudio API errors related to AudioContext state or audio buffer processing.

## Further Information

For more detailed information about the backend server, tool integrations, and deployment to Google Cloud, refer to the following README files:

- **Main Project README (`README.md` in the project root):** Provides a high-level overview of the entire project, including architecture and getting started instructions.
- **Server README (`server/README.md`):**  Details the server-side component, its architecture, configuration, and deployment.
- **Cloud Functions README (`cloud-functions/README.md`):** Explains the setup and deployment of the Cloud Function tools.
