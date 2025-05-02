# Project Livewire - Server Component

This README provides detailed information about the server-side component of Project Livewire. This server is a Python-based WebSocket application built using `websockets` and `google-genai` libraries. It acts as a proxy and tool handler for Google's Gemini 2.0 Flash (experimental) model and manages real-time communication between the client and the Gemini API.

## Overview

The server component is the core backend logic of Project Livewire and is responsible for:

- **WebSocket Communication:** Establishes and manages bidirectional, real-time communication with client applications (frontend UI) using WebSockets.
- **Gemini API Interaction:**  Connects to and manages sessions with the Gemini Multimodal Live API to process user inputs (text, audio, video) and receive AI-generated responses.
- **Tool Handling & Function Calling:**  Implements a tool handling mechanism to route function calls initiated by Gemini to appropriate tools (like weather, calendar, etc.). These tools are implemented as separate Google Cloud Functions and are securely invoked via HTTP requests.
- **Session Management:** Maintains session state for each connected client to ensure conversational context is preserved across multiple interactions.
- **Configuration Management:**  Handles loading and managing API keys, Cloud Function URLs, and server settings from environment variables and Google Cloud Secret Manager for secure and flexible configuration.

This server is designed for deployment on Google Cloud Run to leverage its scalability and managed environment. However, it can also be run locally for development, testing, and experimentation.

## Getting Started

This section guides you through setting up the server component for both local development and deployment to Google Cloud.

### Prerequisites

1. **Local Development Environment:**
   - **Python 3.11+**:  Required for running the server. Download from [python.org](https://www.python.org/downloads/).
   - **pip**: Python package installer (usually included with Python installations).

2. **Google Cloud Setup (for Cloud Run deployment):**
   - **Google Cloud Project:**
     - Create a project at [Google Cloud Console](https://console.cloud.google.com).
     - Set your project ID in gcloud CLI: `gcloud config set project YOUR_PROJECT_ID`
   - **Enable Google Cloud APIs:**
     - Enable the following APIs in your Google Cloud project:
        - Secret Manager API
        - Cloud Run API
        - Cloud Build API
        - Cloud Functions API
        - (Optional, if using Vertex API) Vertex AI API
   - **Google Cloud SDK (gcloud CLI):**
     - Install the SDK: [Google Cloud SDK Install](https://cloud.google.com/sdk/docs/install).
     - Initialize and authenticate gcloud:
       ```bash
       gcloud init
       gcloud auth login
       ```

3. **API Keys and Secrets:**
   - **Google Gemini API Key:**
     - Obtain an API key from [Google AI Studio](https://makersuite.google.com/app/apikey).
     - Securely store this key in Google Cloud Secret Manager as `GOOGLE_API_KEY` (recommended for production) or as an environment variable (for local development).
   - **OpenWeather API Key (optional, for weather tools):**
     - Sign up for an account at [OpenWeather](https://openweathermap.org/api) and get an API key.
     - Store it in Secret Manager as `OPENWEATHER_API_KEY` or as an environment variable.

4. **Service Account Setup:**
   - **For Cloud Run Deployment:**
     - Create a service account in Google Cloud Console for the Cloud Run service.
     - Grant this service account the `Secret Manager Secret Accessor` IAM role (`roles/secretmanager.secretAccessor`) to allow it to access API keys from Secret Manager.
     - When deploying to Cloud Run, configure your service to use this service account.
   - **For Local Development (optional, for Secret Manager access):**
     - Create a service account key file in Google Cloud Console (JSON format).
     - Download the key file and store it securely on your local machine.
     - Set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to the path of this key file. This enables Application Default Credentials (ADC) and allows your local server to authenticate with Google Cloud services like Secret Manager.

5. **Cloud Functions (Tool Implementations):**
   - Deploy the necessary tool functions as Google Cloud Functions. Refer to the `cloud-functions/README.md` in the project root for detailed instructions on deploying weather and calendar tools.
   - After deployment, note down the trigger URLs of your deployed Cloud Functions. These URLs will be needed for server configuration.

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/heiko-hotz/project-livewire.git
   cd project-livewire/server
   ```

2. **Create a virtual environment (recommended):**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Linux/macOS
   venv\\Scripts\\activate     # On Windows
   ```

3. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

### Configuration

The server's configuration is managed through a combination of Google Cloud Secret Manager (preferred for production) and environment variables.

1. **Google Cloud Secret Manager (Production):**
   - **Purpose:** Securely stores sensitive information like API keys and optionally Cloud Function URLs.
   - **Required Secrets:**
     - `GOOGLE_API_KEY` (Google Gemini API key)
     - `OPENWEATHER_API_KEY` (OpenWeather API key, if using weather tools)
   - **Authentication (Cloud Run):** When deployed to Cloud Run with a service account that has the `Secret Manager Secret Accessor` role, the server automatically authenticates and retrieves secrets from Secret Manager.
   - **Authentication (Local Development - Optional):** For local testing with Secret Manager, set the `GOOGLE_APPLICATION_CREDENTIALS` environment variable to point to your service account key file.

2. **Environment Variables:**
   - **Purpose:** Configure Cloud Function URLs, project settings, logging level, and provide fallback API keys for local development.
   - **Configuration File:** Create a `.env` file in the `server/` directory to define environment variables. Example `.env` content:

     ```
     PROJECT_ID=your-gcp-project-id
     LOG_LEVEL=INFO

     # Cloud Function URLs (replace with your actual function URLs)
     WEATHER_FUNCTION_URL=https://REGION-PROJECT_ID.cloudfunctions.net/get-weather-tool
     CALENDAR_FUNCTION_URL=https://REGION-PROJECT_ID.cloudfunctions.net/get-calendar-tool

     # Optional: API keys as fallbacks for local development (if not using Secret Manager locally)
     GOOGLE_API_KEY=your_gemini_api_key
     OPENWEATHER_API_KEY=your_openweather_api_key

     # Optional: Explicitly specify service account key for local Secret Manager access
     # GOOGLE_APPLICATION_CREDENTIALS=path/to/service-account-key.json
     ```

   - **Important:** Add `.env` to `.gitignore` and `.dockerignore` to prevent committing sensitive information.

**Configuration Loading Priority:**

The server prioritizes configuration sources in the following order:

1. **Google Cloud Secret Manager:** If accessible (especially in Cloud Run environments), secrets from Secret Manager take precedence.
2. **Environment Variables:** Environment variables, including those defined in the `.env` file, are used if Secret Manager is not accessible or if a specific configuration is not found in Secret Manager.
3. **`LOG_LEVEL`**: The logging level is always loaded from environment variables (defaults to `INFO` if not set).

### Running the Server

#### Local Development

1. **Configure `.env**:** Ensure your `.env` file is properly configured with necessary environment variables, including API keys and Cloud Function URLs.
2. **Start the server:**
   ```bash
   python server.py
   ```
   The server will start and listen for WebSocket connections on `0.0.0.0:8081`.

#### Deployment to Google Cloud Run

1. **Build and deploy using Cloud Build:**
   ```bash
   gcloud builds submit --config server/cloudbuild.yaml
   ```
   This command uses the `cloudbuild.yaml` configuration file located in the `server/` directory to build a Docker image of the server and deploy it to Google Cloud Run.

2. **Retrieve the deployed service URL:**
   After successful deployment, get the URL of your Cloud Run service:
   ```bash
   gcloud run services describe livewire-backend --platform managed --region us-central1 --format 'value(status.url)'
   ```

3. **Get the Frontend URL:**
   Similarly, you can get the URL of the frontend service:
   ```bash
   # List all Cloud Run services to find the frontend service name
   gcloud run services list

   # Get the frontend URL (replace 'livewire-frontend' with your frontend service name if different)
   gcloud run services describe livewire-frontend --platform managed --region us-central1 --format 'value(status.url)'
   ```

   You can access the web application by opening the frontend URL in your browser.

#### Testing the Deployed Server

You can easily test your deployed WebSocket server using `wscat`, a command-line tool for testing WebSocket connections.

1. **Install wscat:**
   ```bash
   npm install -g wscat
   ```

2. **Save and prepare the server URL:**
   ```bash
   # Save the Cloud Run URL to a variable
   export CLOUD_RUN_URL=$(gcloud run services describe livewire-backend --platform managed --region us-central1 --format 'value(status.url)')
   
   # Print the URL to verify (should start with https://)
   echo $CLOUD_RUN_URL
   ```

3. **Connect to your deployed server:**
   ```bash
   # Connect using the saved URL, replacing https:// with wss://
   # For macOS:
   wscat -c "$(echo $CLOUD_RUN_URL | sed 's|https:|wss:|')"
   
   # For Linux:
   wscat -c "$(echo $CLOUD_RUN_URL | sed 's/https:/wss:/')"
   ```

   Or manually specify the URL:
   ```bash
   # Replace YOUR_CLOUD_RUN_URL with your actual Cloud Run URL, changing https:// to wss://
   wscat -c wss://YOUR_CLOUD_RUN_URL
   ```

4. **Send a test message:**
   Once connected, you can send a simple JSON message to test the server:
   ```json
   {"type": "text", "data": "Hello, are you there?"}
   ```

   The server should respond with a message from the Gemini model. The response will be an audio in base64 encoded format.


## Architecture and Components

```
server/
├── core/
│   ├── gemini_client.py     # Gemini API client initialization and session creation
│   ├── session.py           # Manages client session state and active sessions
│   ├── tool_handler.py      # Handles tool execution and routing to Cloud Functions
│   └── websocket_handler.py # WebSocket connection handling and message processing
├── config/
│   └── system-instructions.txt # System instructions for the Gemini model
├── config.py                # Configuration loading and management
├── Dockerfile               # Dockerfile for containerizing the server application
├── cloudbuild.yaml          # Cloud Build configuration for deployment to Cloud Run
├── requirements.txt         # Python dependencies for the server application
└── server.py               # Main entry point to start the WebSocket server
```

**Key Components:**

- **`core/` Directory:**
    - **`gemini_client.py`**:  Handles the initialization of the Google Gemini API client and the creation of Gemini Live Sessions. It manages authentication and endpoint selection (Dev API or Vertex AI).
    - **`session.py`**:  Implements session management logic, including creating, storing, retrieving, and removing client sessions.  Maintains session-specific state like conversation history and tool execution status.
    - **`tool_handler.py`**:  Responsible for executing tools by making HTTP requests to configured Google Cloud Functions based on function calls requested by the Gemini model.
    - **`websocket_handler.py`**:  Handles WebSocket connections from clients, manages message reception and sending, orchestrates interaction with the Gemini API client and tool handler, and manages session lifecycle.
- **`config/` Directory:**
    - **`system-instructions.txt`**:  Contains system-level instructions provided to the Gemini model to guide its behavior and tool usage.
- **`config.py`**:  Loads and manages server configuration from environment variables and Google Cloud Secret Manager. Defines API endpoints, model settings, Cloud Function URLs, and tool configurations.
- **Root Directory Files:**
    - **`Dockerfile`**:  Defines the Docker image for the server application, including the base image, dependencies, and startup command.
    - **`cloudbuild.yaml`**:  Configuration file for Google Cloud Build, used to automate the process of building the Docker image and deploying the server to Cloud Run.
    - **`requirements.txt`**:  Lists all Python package dependencies required by the server application.
    - **`server.py`**:  The main entry point script that starts the WebSocket server using the `websockets` library and sets up the asyncio event loop.

**Note:** Tool implementations (weather, calendar, etc.) are intentionally separated as Google Cloud Functions, located in the `cloud-functions/` directory at the project root. This modular design promotes scalability, maintainability, and independent deployment of tools.

## Modifying Tools

To add or modify tools (i.e., functionalities exposed to the Gemini model through function calling), you typically need to make changes in the following parts of the server component:

1. **Cloud Function Implementation (in `cloud-functions/`):**
   - Implement or modify the tool's logic as a Google Cloud Function within the `cloud-functions/` directory. Ensure it's deployed and you have its function URL.

2. **Server Configuration (in `config/config.py`):**
   - **`CLOUD_FUNCTIONS` dictionary**: Add or update the entry for your tool, mapping a tool name (used in code) to its Cloud Function URL (obtained after deployment).
   - **`CONFIG['tools']`**:  Modify the `function_declarations` within the `CONFIG['tools']` list. Add a new function declaration for your tool, specifying:
     - `name`: The function name that Gemini will use to call the tool. This name should match the key you used in the `CLOUD_FUNCTIONS` dictionary.
     - `description`: A clear description of what the tool does. This helps Gemini understand when to use it.
     - `parameters`: Define the parameters the function accepts. This is crucial for Gemini to correctly call the tool with the necessary information.

3. **Environment Variables (`.env` file):**
   - Add or update the environment variable in your `.env` file that corresponds to the Cloud Function URL of your new or modified tool.  The variable name should be consistent with what you used in `config/config.py` (e.g., `YOUR_NEW_TOOL_URL`).

4. **System Instructions (in `config/system-instructions.txt`):**
   - Update the `system-instructions.txt` file to inform the Gemini model about the newly available tool and provide rules or guidelines on when and how to use it.  Clearly describe the tool and its purpose to the AI.

**Important:**  No modifications are generally required in `tool_handler.py` itself.  The tool handler is designed to dynamically execute tools based on the configuration defined in `config.py`.

## Troubleshooting

### Common Issues and Troubleshooting Tips

- **Connection Issues:**
    - **Server Logs:** Check the server logs for any errors during startup or runtime. Look for messages indicating WebSocket connection problems or exceptions.
    - **Network Connectivity:** Verify network connectivity between the client and the server. Ensure no firewalls or network policies are blocking WebSocket connections on port 8081 (or the port you configured).
    - **Client-Side Configuration:** Double-check the WebSocket URL configured in the client application (`client/src/api/gemini-api.js`) to ensure it correctly points to your running server.

- **API Key Errors:**
    - **Secret Manager Configuration:** If using Secret Manager, verify that the service account running the server (especially in Cloud Run) has the `Secret Manager Secret Accessor` role. Check Secret Manager in Google Cloud Console to confirm that secrets like `GOOGLE_API_KEY` and `OPENWEATHER_API_KEY` are correctly created and their values are set.
    - **Environment Variables:** If using environment variables for API keys (primarily for local development), ensure they are correctly defined in your `.env` file and that the server is loading them properly.
    - **Server Logs:** Look for error messages in the server logs related to API key retrieval or authentication failures.

- **Tool Execution Errors:**
    - **Cloud Function URLs:** Verify that the Cloud Function URLs in your `.env` file and `config/config.py` are correct and that the functions are deployed and accessible at those URLs.
    - **Cloud Function Logs:** Check the logs of your Google Cloud Functions for any errors or exceptions occurring during tool execution. Cloud Function logs are essential for debugging issues within the tool implementations themselves.
    - **Permissions (Cloud Functions):** Ensure that the service accounts used by your Cloud Functions have the necessary permissions to access external APIs or Google Cloud services they rely on (e.g., Calendar API, external Weather API).
    - **Parameter Passing:** Verify that the parameters being passed to the Cloud Functions from the server are in the expected format and contain all required information. Check server logs and Cloud Function logs to trace parameter data flow.

- **Quota Exceeded Errors:**
    - **Google Cloud Console:** Monitor API usage in the Google Cloud Console for your project. Check for quota limits that might be exceeded for the Gemini API, Cloud Functions, or any other Google Cloud services being used.
    - **Error Messages:** Look for specific error messages in the server logs or client-side UI that indicate quota exceeded issues. Implement retry mechanisms or error handling to gracefully manage quota limits if necessary.

For more in-depth troubleshooting, consult the main project documentation, examine detailed logs from both the server and client applications, and consider opening an issue in the project repository on GitHub with specific details about the problem you are encountering.
