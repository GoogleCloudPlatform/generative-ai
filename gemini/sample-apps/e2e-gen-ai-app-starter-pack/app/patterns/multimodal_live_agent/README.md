# Multimodal Live Agent

This pattern showcases a real-time conversational RAG agent powered by Google Gemini. The agent handles audio, video, and text interactions while leveraging tool calling with a vector DB for grounded responses.

![live_api_diagram](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_diagram.png)

**Key components:**

- **Python Backend** (in `app/` folder): A production-ready server built with [FastAPI](https://fastapi.tiangolo.com/) and [google-genai](https://googleapis.github.io/python-genai/) that features:

  - **Real-time bidirectional communication** via WebSockets between the frontend and Gemini model
  - **Integrated tool calling** with vector database support for contextual document retrieval
  - **Production-grade reliability** with retry logic and automatic reconnection capabilities
  - **Deployment flexibility** supporting both AI Studio and Vertex AI endpoints
  - **Feedback logging endpoint** for collecting user interactions

- **React Frontend** (in `frontend/` folder): Extends the [Multimodal live API Web Console](https://github.com/google-gemini/multimodal-live-api-web-console), with added features like **custom URLs** and **feedback collection**.

![live api demo](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/e2e-gen-ai-app-starter-pack/live_api_pattern_demo.gif)

## Usage

You can use this pattern in two ways:

1. As a standalone template for rapid prototyping (⚡ 1 minute setup!)
2. As part of the [starter pack](https://goo.gle/e2e-gen-ai-app-starter-pack) for production deployment with Terraform and CI/CD. The pattern comes with comprehensive unit and integration tests.

### Standalone Usage

#### Prerequisites

Before you begin, ensure you have the following installed: [Python 3.10+](https://www.python.org/downloads/), [Poetry](https://python-poetry.org/docs/#installation), [Node.js](https://nodejs.org/) (including npm), [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)

#### Download the Pattern

Download the Multimodal Live Agent pattern using `gsutil` CLI:

```bash
gsutil cp gs://e2e-gen-ai-app-starter-pack/multimodal-live-agent.zip . && unzip multimodal-live-agent.zip && cd multimodal-live-agent
```

#### Backend Setup

1. **Set your default Google Cloud project and region:**

   ```bash
   export PROJECT_ID="your-gcp-project"

   gcloud auth login --update-adc
   gcloud config set project $PROJECT_ID
   gcloud auth application-default set-quota-project $PROJECT_ID
   ```

   <details>
   <summary><b>For AI Studio setup:</b></summary>

   ```bash
   export VERTEXAI=false
   export GOOGLE_API_KEY=your-google-api-key
   ```

   </details>

2. **Install Dependencies:**

   Install the required Python packages using Poetry:

   ```bash
   poetry install
   ```

3. **Run the Backend Server:**

   Start the FastAPI server:

   ```bash
   poetry run uvicorn app.server:app --host 0.0.0.0 --port 8000 --reload
   ```

#### Frontend Setup

1. **Install Dependencies:**

   In a separate terminal, install the required Node.js packages for the frontend:

   ```bash
   npm --prefix frontend install
   ```

2. **Start the Frontend:**

   Launch the React development server:

   ```bash
   npm --prefix frontend start
   ```

   This command starts the frontend application, accessible at `http://localhost:3000`.

#### Interact with the Agent

Once both the backend and frontend are running, click the play button in the frontend UI to establish a connection with the backend. You can now interact with the Multimodal Live Agent! You can try asking questions such as "Using the tool you have, define Governance in the context MLOPs" to allow the agent to use the [documentation](https://cloud.google.com/architecture/deploy-operate-generative-ai-applications) it was provided to.

#### Remote deployment in Cloud Run

You can quickly test the application in [Cloud Run](https://cloud.google.com/run). Ensure your service account has the `roles/aiplatform.user` role to access Gemini.

1. **Deploy:**

   ```bash
   export REGION="your-gcp-region"

   gcloud run deploy genai-app-sample \
     --source . \
     --project $PROJECT_ID \
     --memory "4Gi" \
     --region $REGION
   ```

2. **Access:** Use [Cloud Run proxy](https://cloud.google.com/sdk/gcloud/reference/run/services/proxy) for local access. The backend will be accessible at `http://localhost:8000`:

   ```bash
   gcloud run services proxy genai-app-sample --port 8000 --project $PROJECT_ID --region $REGION
   ```

   You can then use the same frontend setup described above to interact with your Cloud Run deployment.

### Integrating with the Starter Pack

This pattern is designed for seamless integration with the [starter pack](https://goo.gle/e2e-gen-ai-app-starter-pack). The starter pack offers a streamlined approach to setting up and deploying multimodal live agents, complete with robust infrastructure and CI/CD pipelines.

### Getting Started

1. **Download the Starter Pack:**

   Obtain the starter pack using the following command:

   ```bash
   gsutil cp gs://e2e-gen-ai-app-starter-pack/app-starter-pack.zip . && unzip app-starter-pack.zip && cd app-starter-pack
   ```

2. **Prepare the Pattern:**

   Run the provided script to prepare the multimodal live agent pattern:

   ```bash
   python app/patterns/multimodal_live_agent/utils/prepare_pattern.py
   ```

   The script will organize the project structure for you. The current readme will be available in the root folder with the name `PATTERN_README.md`.

3. **Set up CI/CD:**

   Refer to the instructions in `deployment/readme.md` for detailed guidance on configuring the CI/CD pipelines.

#### Current Limitations and Future Enhancements

We are actively developing and improving this pattern. Currently, the following limitations are known:

- **Observability:** Comprehensive observability features are not yet fully implemented.
- **Load Testing:** Load testing capabilities are not included in this version.

## Your Feedback Matters

We highly value your feedback and encourage you to share your thoughts and suggestions. Your input helps us prioritize new features and enhancements. Please reach out to us at <a href="mailto:e2e-gen-ai-app-starter-pack@google.com">e2e-gen-ai-app-starter-pack@google.com</a> to let us know what features you'd like to see implemented or any other feedback you may have.

## Additional Resources for Multimodal Live API

Explore these resources to learn more about the Multimodal Live API and see examples of its usage:

- [Project Pastra](https://github.com/heiko-hotz/gemini-multimodal-live-dev-guide/tree/main): a comprehensive developer guide for the Gemini Multimodal Live API.
- [Google Cloud Multimodal Live API demos and samples](https://github.com/GoogleCloudPlatform/generative-ai/tree/main/gemini/multimodal-live-api): Collection of code samples and demo applications leveraging multimodal live API in Vertex AI
- [Gemini 2 Cookbook](https://github.com/google-gemini/cookbook/tree/main/gemini-2): Practical examples and tutorials for working with Gemini 2
- [Multimodal Live API Web Console](https://github.com/google-gemini/multimodal-live-api-web-console): Interactive React-based web interface for testing and experimenting with Gemini Multimodal Live API.
