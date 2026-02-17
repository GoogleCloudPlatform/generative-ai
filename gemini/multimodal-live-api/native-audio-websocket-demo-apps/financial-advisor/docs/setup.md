# Setup & Development Guide

This guide covers how to set up the Google Cloud Financial Advisor project locally for development.

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

1.  **Python 3.12+**
2.  **Node.js 18+** & `npm`
3.  **Google Cloud SDK (`gcloud` CLI)**
4.  **`uv`**: A fast Python package installer and resolver.
    ```bash
    curl -LsSf https://astral.sh/uv/install.sh | sh
    ```
5.  **`task`**: A task runner / build tool (simpler Make).
    ```bash
    sh -c "$(curl --location https://taskfile.dev/install.sh)" -- -d -b /usr/local/bin
    ```

## 🔐 Authentication & Google Cloud Setup

The application relies on Google Cloud services (Vertex AI, Firestore). You must be authenticated to run it.

1.  **Login to Google Cloud:**
    ```bash
    gcloud auth login
    gcloud auth application-default login
    ```
    *This creates a local credential file that the backend uses automatically.*

2.  **Set Project Context:**
    ```bash
    gcloud config set project YOUR_PROJECT_ID
    ```

3.  **Enable Required APIs:**
    The application needs several APIs enabled. You can use the helper task:
    ```bash
    task infra:enable-apis
    ```
    *Or manually enable: `aiplatform.googleapis.com`, `firestore.googleapis.com`, `secretmanager.googleapis.com`.*

## 🚀 Running Locally (The "Happy Path")

We use `Taskfile` to simplify complex commands.

### 1. Install Dependencies
This single command installs both Python (backend) and Node.js (frontend) dependencies.

```bash
task install
```

### 2. Run the Application
Start both the Backend (FastAPI) and Frontend (Next.js) in development mode.

```bash
task dev
```

*   **Frontend:** [http://localhost:3000](http://localhost:3000)
*   **Backend API:** [http://localhost:8000](http://localhost:8000)
*   **API Docs:** [http://localhost:8000/docs](http://localhost:8000/docs)

### 3. Running Components Individually
If you prefer to run them in separate terminals:

*   **Backend Only:**
    ```bash
    task run-backend
    ```
*   **Frontend Only:**
    ```bash
    task run-frontend
    ```

## 🧪 Testing

We use `pytest` for the backend.

```bash
# Run all tests
task test

# Run specific test file
uv run pytest src/backend/tests/test_websocket_interruption.py
```

## 🐳 Running with Docker (Production-like)

To simulate the production environment or if you prefer containers:

1.  **Build Containers:**
    ```bash
    task docker:build
    ```

2.  **Run Containers:**
    ```bash
    task docker:run
    ```

*Note: You may need to pass your Google Credentials to the container if not running on Cloud Run.*

## 🛠 Troubleshooting

### Microphone / Audio Issues
*   **"Microphone Permission Denied":**
    *   Browsers often block microphone access on non-secure origins. Ensure you are accessing via `http://localhost:3000` (which is treated as secure).
    *   Check your browser settings to allow microphone access for localhost.
*   **"No Audio Output":**
    *   Check your system volume.
    *   Verify the backend logs to see if `audio/pcm` chunks are being sent.

### Authentication Errors
*   **"Default CredentialsError":**
    *   Run `gcloud auth application-default login` again.
    *   Ensure the quota project is set: `gcloud auth application-default set-quota-project YOUR_PROJECT_ID`.

### WebSocket Disconnects
*   **"WebSocket Error 1006":**
    *   Often implies a backend crash. Check the backend terminal logs.
    *   Verify the Gemini API Key or Quota is valid in your Google Cloud project.
