# Project Livewire - Local Setup Guide

This guide provides detailed instructions for setting up and running Project Livewire on your local machine for development and testing.

## Prerequisites

Before you begin, ensure you have the following installed and configured:

1.  **Python:** Version 3.8 or higher. ([Download](https://www.python.org/downloads/))
2.  **pip:** Python package installer (usually included with Python).
3.  **Git:** For cloning the repository. ([Download](https://git-scm.com/))
4.  **API Keys:**
    *   **Google Gemini API Key:** Required for interacting with the Gemini model.
        *   Get one from [Google AI Studio](https://makersuite.google.com/app/apikey).
    *   **OpenWeather API Key:** Required *only* if you want to use the weather tool.
        *   Get one from [OpenWeatherMap](https://openweathermap.org/api).
5.  **Deployed Cloud Functions (Optional but Recommended):**
    *   For tool integration (weather, calendar), you need the corresponding Google Cloud Functions deployed.
    *   Follow the [Cloud Functions Setup Guide](../cloud-functions/README.md) to deploy them.
    *   Note down the **HTTP Trigger URLs** for each function you deploy.
6.  **Google Cloud SDK (`gcloud`) (Optional):**
    *   Needed if you want to use Google Cloud Secret Manager locally via Application Default Credentials (ADC).
    *   [Install Guide](https://cloud.google.com/sdk/docs/install)
    *   Authenticate: `gcloud auth application-default login`

## Setup Steps

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/heiko-hotz/project-livewire.git
    cd project-livewire
    ```

2.  **Backend Configuration (`.env` file):**
    *   Navigate to the server directory:
        ```bash
        cd server
        ```
    *   Copy the example environment file:
        ```bash
        cp .env.example .env
        ```
    *   Edit the `.env` file using a text editor (like `nano`, `vim`, or VS Code):
        ```bash
        nano .env
        ```
    *   **Fill in the required values:**
        *   `GOOGLE_API_KEY`: **Required** if *not* using Vertex AI or ADC. Paste your Gemini API key here.
        *   `WEATHER_FUNCTION_URL`: **Required** for the weather tool. Paste the trigger URL of your deployed `get-weather-tool` function.
        *   `CALENDAR_FUNCTION_URL`: **Required** for the calendar tool. Paste the trigger URL of your deployed `get-calendar-tool` function.
        *   `OPENWEATHER_API_KEY`: **Required** if *not* storing it in Secret Manager and accessing via ADC. Paste your OpenWeather API key here.
    *   **Optional/Advanced Configuration:**
        *   `PROJECT_ID`: Your Google Cloud Project ID. Required if using Vertex AI or accessing secrets via ADC.
        *   `VERTEX_LOCATION`: Google Cloud region (e.g., `us-central1`). Required if using Vertex AI.
        *   `VERTEX_API=true`: Set to `true` to use the Vertex AI endpoint instead of the Google AI Developer endpoint. Requires `PROJECT_ID` and `VERTEX_LOCATION` to be set, and appropriate authentication (usually ADC).
        *   `GOOGLE_APPLICATION_CREDENTIALS`: Path to your service account key file (JSON). Use this for explicit service account authentication, often used with ADC for Secret Manager access. If `gcloud auth application-default login` was used, this might not be needed.
        *   `LOG_LEVEL`: Set logging verbosity (e.g., `DEBUG`, `INFO`, `WARNING`). Defaults to `INFO`.

3.  **Install Backend Dependencies:**
    *   Make sure you are still in the `server/` directory.
    *   (Optional but recommended) Create and activate a virtual environment:
        ```bash
        python3 -m venv venv
        source venv/bin/activate # Linux/macOS
        # venv\Scripts\activate # Windows
        ```
    *   Install required packages:
        ```bash
        pip install -r requirements.txt
        ```

4.  **Start the Backend Server:**
    *   While in the `server/` directory:
        ```bash
        python server.py
        ```
    *   The server will start, usually listening on `0.0.0.0:8081`. Look for the log message `Running websocket server on 0.0.0.0:8081...`. Keep this terminal running.

5.  **Start the Frontend Server:**
    *   Open a **new terminal window/tab**.
    *   Navigate to the client directory:
        ```bash
        cd ../client # Or navigate from the project root: cd project-livewire/client
        ```
    *   Start a simple Python HTTP server:
        ```bash
        python -m http.server 8000
        ```
    *   This server serves the HTML, CSS, and JavaScript files. Keep this terminal running.

6.  **Access the Application:**
    *   Open your web browser.
    *   Navigate to the **Development UI:** `http://localhost:8000/index.html`
    *   Or navigate to the **Mobile UI:** `http://localhost:8000/mobile.html`

## Testing the Connection

1.  Open your browser's developer console (usually F12).
2.  Check the "Console" tab for any errors, especially WebSocket connection errors.
3.  Look for a "WebSocket connection established" or similar message from the client-side JavaScript.
4.  Try clicking the microphone button (or play button on mobile) and speaking, or typing a message in the text input (dev UI).
5.  Observe the terminal running the `server.py` script for log messages indicating client connections and messages being processed.

## Troubleshooting

*   **`Connection refused` errors (WebSocket):**
    *   Ensure the backend server (`server.py`) is running in the other terminal.
    *   Verify the WebSocket URL in the client JavaScript (`client/src/api/gemini-api.js`) matches where the server is listening (default `ws://localhost:8081`).
*   **`ModuleNotFoundError`:** Make sure you installed dependencies using `pip install -r requirements.txt` in the `server/` directory (and activated your virtual environment if you created one).
*   **API Key Errors / Authentication Errors:**
    *   Double-check the `GOOGLE_API_KEY` in your `.env` file.
    *   If using Vertex AI or ADC, ensure `PROJECT_ID` is correct and your environment is properly authenticated (`gcloud auth application-default login` or `GOOGLE_APPLICATION_CREDENTIALS`).
    *   Check server logs for specific authentication failure messages.
*   **Tool Function Errors (e.g., Weather):**
    *   Verify the `*_FUNCTION_URL`s in your `.env` file are correct and point to your *deployed* Cloud Functions.
    *   Ensure the Cloud Functions themselves are working correctly (test them directly using `curl` as shown in the [Cloud Functions README](../cloud-functions/README.md#testing-the-functions)).
    *   Check if the necessary API keys (like `OPENWEATHER_API_KEY`) are correctly configured either in `.env` or accessible via Secret Manager/ADC.
*   **Port Conflicts:** If `8081` or `8000` are already in use, the servers might fail to start. Stop the conflicting process or configure the servers/client to use different ports (requires code changes).
*   **Microphone/Webcam Access Denied:** Ensure you grant permission in your browser when prompted. Check browser settings if you previously denied access.