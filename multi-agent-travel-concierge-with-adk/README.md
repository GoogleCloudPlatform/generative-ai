# Quickbot - Multi Agent Travel Concierge (ADK + Agent Engine)

Quickbot Multi Agent Travel Concierge is a sophisticated application designed to deliver highly personalized travel experiences. Leveraging an [Agent Development Kit (ADK)](https://google.github.io/adk-docs/) and powerful [Agent Engine](https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/overview) capabilities, this system orchestrates multiple specialized intelligent agents to provide comprehensive support throughout the user’s journey – from initial planning and booking to real-time itinerary alerts and in-trip assistance. It features a user-friendly frontend and a robust backend API to manage agent interactions and deliver a seamless travel planning and support experience.
This Template is taken from the official [Agent Garden samples](https://github.com/google/adk-samples/tree/main), the [Travel Concierge MultiAgent](https://github.com/google/adk-samples/tree/main/agents/travel-concierge) is implemented adding a backend with ADK and a nice Angular Frontend to interact with it in an easy and straightforward way. 

## Overview

This project provides an advanced framework for a travel concierge service powered by a multi-agent system. By utilizing an Agent Development Kit (ADK), developers can easily create, deploy, and manage specialized agents (e.g., for flights, accommodations, local activities, transportation, real-time alerts). The core Agent Engine orchestrates these agents, enabling them to collaborate and intelligently respond to user needs, offering personalized recommendations and proactive support. The architecture is designed with a decoupled frontend and backend, ensuring scalability and maintainability for a rich user experience.

## Demo
Here's a look at our Travel Concierge MultiAgent in action!

<video controls autoplay loop muted width="100%" style="max-width: 1200px;">
<source src="./assets/quickbot-adk-travel-multiagent.mp4" type="video/mp4">
Your browser does not support the video tag. You can <a href="./assets/quickbot-adk-travel-multiagent.mp4">download the video here</a>.
</video>

## Prerequisites

Before you begin, ensure you have the following installed:

*   **Docker and Docker Compose v2:** Essential for the containerized deployment.
    *   Verify your Docker Compose version with `docker compose version`. If you have an older `docker-compose` (with a hyphen), you might need to upgrade to use `docker compose` in the commands.
*   **Google Cloud SDK (`gcloud` CLI):** May be required if any agents or the Agent Engine interact with Google Cloud services (e.g., for data storage, specific APIs, or managed services).
*   **Python 3.x:** For backend development (if not using Docker).
*   **Node.js and npm (or yarn):** For frontend development (if not using Docker).

## Getting Started

You have two main options to get the application running:

### Option 1: Using Docker Compose (Recommended for Quick Start)

This is the **simplest way to get the entire application (frontend and backend) up and running!** You just need to run `docker compose up` after initial setup. See the next steps:

1.  **Ensure Docker and Docker Compose v2 are installed and running.**

2.  **Authenticate with Google Cloud (if applicable):**
    If your agents or the Agent Engine need to interact with Google Cloud services, you may need to provide Google Cloud credentials. For local development with ADC:
    ```bash
    gcloud auth application-default login
    gcloud config set project <your-gcp-project-id> # If using a specific GCP project
    gcloud auth application-default set-quota-project <your-gcp-project-id> # If using a specific GCP project

    # Verify your configuration
    gcloud auth list
    gcloud config list project
    ```
    The `docker-compose.yml` file can be configured to mount these local credentials into the backend container.
    > **Windows Users:** The path to ADC might differ. Adjust volume mounts in `docker-compose.yml` if needed.
    > **Note:** Ensure any required APIs are enabled in your Google Cloud project if used.

3.  **Build Docker Images:**
    Build the Docker images for the frontend and backend services:
    ```bash
    docker compose build
    ```
    The backend will be configured using environment variables (see "Environment Variables" section), including any necessary API keys for travel services, ADK configurations, or Agent Engine settings.

4.  **Run the application:**
    After building the images, start the services:
    ```bash
    docker compose up
    ```
    The frontend should typically be available at `http://localhost:4200` (or as configured) and the backend API at `http://localhost:8080`.

### Option 2: Manual Setup (for Development and Customization)

Follow these steps if you prefer to run the frontend and backend services manually on your local machine.

**A. Backend Setup**

1.  **Navigate to the `backend/` directory.**
    ```bash
    cd backend
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    # Check if you are already in an environment
    pip -V

    # If not, create and activate (for Linux/macOS)
    python3 -m venv .venv
    source .venv/bin/activate

    # Install requirements
    pip3 install -r requirements.txt
    ```
    > **VS Code Tip:** If VS Code doesn't recognize your virtual environment, press `Ctrl + Shift + P` (or `Cmd + Shift + P` on Mac), type "Python: Select Interpreter", choose "Enter interpreter path...", and then find and select `.venv/bin/python` inside your `backend` directory.

3.  **Setup Google Cloud (`gcloud`) credentials (if applicable):**
    If your backend, agents, or Agent Engine interact with GCP, ensure you're authenticated.
    ```bash
    gcloud auth login # Login with your user account
    gcloud config set project <your-gcp-project-id> # If using a specific GCP project

    # For services using Application Default Credentials (ADC) locally
    gcloud auth application-default login
    gcloud auth application-default set-quota-project <your-gcp-project-id> # If using a specific GCP project

    # Verify configuration
    gcloud auth list
    gcloud config list project
    ```

4.  **Configure Environment Variables:**
    Backend configuration is managed via environment variables. Create a `.local.env` file in the `backend/` directory (copy from `.local.env.example` if one exists). This file should be in `.gitignore`.

    *   **For Mac/Windows (or zsh console on Linux):**
        Source the variables directly (from the `backend/` directory):
        ```bash
        . ./.local.env
        ```
    *   **For Linux (bash):**
        Open `backend/.venv/bin/activate` and append the `export` commands from your `backend/.local.env` file after the `PATH` export section. For example:
        ```sh
        # ... existing activate script content ...
        _OLD_VIRTUAL_PATH="$PATH"
        PATH="$VIRTUAL_ENV/bin:$PATH"
        export PATH

        # Quickbot env variables (copied from .local.env)
        export ENVIRONMENT="development"
        export FRONTEND_URL="http://localhost:4200"
        # ADK, Agent Engine, and Travel API variables
        # export ADK_CONFIG_PATH="/path/to/adk_config.json"
        # export AGENT_ENGINE_ENDPOINT="http://localhost:xxxx/api/agent-engine" # Or other config
        # export FLIGHT_API_KEY="your_flight_api_key"
        # export HOTEL_API_KEY="your_hotel_api_key"
        # export WEATHER_API_KEY="your_weather_api_key"
        # ... other necessary agent or backend variables ...
        ```
    Verify the variables are set by running `env` in your activated terminal.

5.  **Run the setup script (if applicable):**
    This script might perform initial configurations for the ADK, Agent Engine, or agent registration.
    ```bash
    # from the backend/ directory
    python3 setup.py
    ```

6.  **Run the backend application:**
    ```bash
    # from the backend/ directory
    uvicorn main:app --reload --port 8080
    ```

**B. Frontend Setup**

(These instructions assume a typical TypeScript/Angular frontend. Adjust as necessary based on your `frontend/README.md`.)

1.  **Navigate to the `frontend/` directory.**
    ```bash
    cd frontend
    ```
2.  **Install dependencies:**
    ```bash
    npm install
    ```
3.  **Environment Variables (if applicable):**
    The frontend might require its own environment configuration (e.g., via a `.env` file or Angular's `environment.ts` files for API endpoints). Check the `frontend/` directory or its `README.md` for specific instructions.
4.  **Run the frontend application:**
    ```bash
    npm start
    # Or, for many Angular projects:
    # ng serve
    ```
    The application will typically be available at `http://localhost:4200`.

## Project Structure (highlighting important parts)
```text
multi-agent-travel-concierge-with-adk/
├── backend/                # Python backend (FastAPI/Uvicorn) for agent orchestration/API
│   ├── .venv/              # Python virtual environment (gitignored)
│   ├── .local.env          # Local environment variables (gitignored)
│   ├── main.py             # Main application file (e.g., FastAPI app)
│   ├── requirements.txt    # Backend dependencies
│   ├── setup.py            # Backend setup script (e.g., ADK init, agent registration)
│   └── README.md           # Backend-specific instructions
├── frontend/               # TypeScript frontend (Angular) for UI
│   ├── node_modules/       # Node.js dependencies (gitignored)
│   ├── src/                # Frontend source code
│   ├── package.json        # Frontend dependencies and scripts
│   ├── tsconfig.json       # TypeScript configuration
│   └── README.md           # Frontend-specific instructions
├── docker-compose.yml      # Docker Compose configuration for all services
└── README.md               # This file: Root project README
```

## Environment Variables

Configuration for both frontend and backend is primarily managed through environment variables.

*   **Backend:**
    *   When running manually, backend environment variables are typically defined in `backend/.local.env`.
    *   When running with Docker, these variables are usually passed into the backend container via the `docker-compose.yml` file (often referencing a `.env` file at the root or `backend/` directory).
    *   **Please consult your `docker-compose.yml` for the definitive list of required backend environment variables.**:
        *   `IS_FIRST_DEPLOYMENT`: Whether to deploy the resources or not when running docker compose.
        *   `_PROJECT_ID`: Your Google Cloud Project ID (if any GCP services are used by agents or the engine).
        *   `_REGION`: Your Google Cloud region.
        *   `ENVIRONMENT`: Application environment (e.g., `development`, `production`).
        *   `FRONTEND_URL`: URL of the frontend application (e.g., `http://localhost:4200`).
        *   *(Add/remove/modify based on your actual `docker-compose.yml` and backend needs)*
    *   Consult `backend/README.md` or `backend/.local.env.example` for a complete and accurate list and details on agent-specific configurations.

*   **Frontend:**
    *   Frontend environment variables (e.g., API endpoint URLs) are usually managed within the frontend's build system (e.g., Angular's `environment.ts` files or a `.env` file in the `frontend/` directory).
    *   Consult `frontend/README.md` for specific details.

## Code Styling & Commit Guidelines

To maintain code quality and consistency across the project:

*   **TypeScript (Frontend):** We follow the Angular Coding Style Guide by leveraging Google's TypeScript Style Guide using `gts`. This includes a formatter, linter, and automatic code fixer.
*   **Python (Backend):** We adhere to the Google Python Style Guide, using tools like `pylint` and `black` for linting and formatting.
*   **Commit Messages:** We suggest following Angular's Commit Message Guidelines to create clear and descriptive commit messages.

### Frontend (TypeScript with `gts`)

(Assumes setup within the `frontend/` directory)

1.  **Initialize `gts` (if not already done in the project):**
    Navigate to `frontend/` and run:
    ```bash
    npx gts init
    ```
    This will set up `gts` and create necessary configuration files (like `tsconfig.json`). Ensure your `tsconfig.json` (or a related `gts` config file like `.gtsrc`) includes an extension for `gts` defaults, typically:
    ```json
    {
      "extends": "./node_modules/gts/tsconfig-google.json"
      // ... other configurations
    }
    ```
2.  **Check for linting issues:**
    (This assumes a `lint` script is defined in `frontend/package.json`, e.g., `"lint": "gts lint"`)
    ```bash
    # from frontend/ directory
    npm run lint
    ```
3.  **Fix linting issues automatically (where possible):**
    (This assumes a `fix` script is defined in `frontend/package.json`, e.g., `"fix": "gts fix"`)
    ```bash
    # from frontend/ directory
    npm run fix
    ```

### Backend (Python with `pylint` and `black`)

(Assumes setup within the `backend/` directory and its virtual environment activated)

1.  **Ensure Dependencies are Installed:**
    Add `pylint` and `black` to your `backend/requirements.txt` file if not already present:
    ```
    pylint
    black
    ```
    Then install them within your virtual environment:
    ```bash
    # from backend/ directory, with .venv activated
    pip install pylint black
    # or pip install -r requirements.txt
    ```
2.  **Configure `pylint`:**
    It's recommended to have a `.pylintrc` file in your `backend/` directory to configure `pylint` rules. You can generate one if it doesn't exist:
    ```bash
    # from backend/ directory
    pylint --generate-rcfile > .pylintrc
    ```
    Customize this file according to your project's needs and the Google Python Style Guide.
3.  **Check for linting issues with `pylint`:**
    Navigate to the `backend/` directory and run:
    ```bash
    # from backend/ directory
    pylint .
    # Or specify modules/packages: pylint agents/ adk_components/ agent_engine/ travel_services/
    ```
4.  **Format code with `black`:**
    To automatically format all Python files in the `backend/` directory and its subdirectories:
    ```bash
    # from backend/ directory
    python -m black . --line-length=80
    ```
