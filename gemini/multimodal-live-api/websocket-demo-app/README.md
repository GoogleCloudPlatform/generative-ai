# Multimodal Live API Demo

In this tutorial, you will be building a web application that enables you to use your voice and camera to talk to Gemini 2.0 through the [Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).

The [Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live) is a low-latency bidirectional streaming API that supports audio and video streaming inputs and can output audio.

## Architecture

- **Backend (Python WebSockets Server):** Handles authentication and acts as an intermediary between your frontend and the Gemini API.
- **Frontend (HTML/JavaScript):** Provides the user interface and interacts with the backend via WebSockets.

## Pre-requisites

While some web development experience, particularly with localhost, port numbers, and the distinction between WebSockets and HTTP requests, can be beneficial for this tutorial, don't worry if you're not familiar with these concepts. We'll provide guidance along the way to ensure you can successfully follow along.

### File Structure

- `backend/main.py`: The Python backend code
- `backend/requirements.txt`: Lists the required Python dependencies

- `frontend/index.html`: The frontend HTML app
- `frontend/script.js`: Main frontend JavaScript code
- `frontend/gemini-live-api.js`: Script for interacting with the Gemini API
- `frontend/live-media-manager.js`: Script for handling media input and output
- `frontend/pcm-processor.js`: Script for processing PCM audio
- `frontend/cookieJar.js`: Script for managing cookies

![Demo](https://storage.googleapis.com/cloud-samples-data/generative-ai/image/demo-UI.png)

## Setup instructions

You can set up this app locally or via Cloud Shell.

### Setup locally

1. Clone the repository and cd into the correct directory

    ```sh
    git clone https://github.com/GoogleCloudPlatform/generative-ai.git
    cd generative-ai/gemini/multimodal-live-api/websocket-demo-app
    ```

1. Create a new virtual environment and activate it:

    ```sh
    python3 -m venv env
    source env/bin/activate
    ```

1. Install dependencies:

    ```sh
    pip3 install -r backend/requirements.txt
    ```

1. Start the Python WebSocket server:

    ```sh
    python3 backend/main.py
    ```

1. Start the frontend:

    - Navigate to `script.js` on line 9, `const PROXY_URL = "wss://[THE_URL_YOU_COPIED_WITHOUT_HTTP]";` and replace `PROXY_URL` value with `ws://localhost:8000`. It should look like: `const PROXY_URL = "ws://localhost:8000";`. Note the absence of the second "s" in "wss" as "ws" indicates a non-secure WebSocket connection.
    - Right below on line 10, update `PROJECT_ID` with your Google Cloud project ID.
    - Save the changes you've made to `script.js`
    - Now make sure to open a **separate** terminal window from the backend to run this command (keep the backend server running in the first terminal).

    ```sh
    cd frontend
    python3 -m http.server
    ```

1. Point your browser to the demo app UI based on the output of the terminal. (e.g., it may be `http://localhost:8000`, or it may use a different port.)

1. Get your Google Cloud access token:
   Run the following command in a terminal with gcloud installed to set your project, and to retrieve your access token.

    ```sh
    gcloud components update
    gcloud components install beta
    gcloud config set project YOUR-PROJECT-ID
    gcloud auth print-access-token
    ```

1. Copy the access token from the previous step into the UI that you have open in your browser.

1. Enter the model ID in the UI:
   Replace `YOUR-PROJECT-ID` in the input with your Google Cloud Project ID.

1. Connect and interact with the demo:

    - After entering your Access Token and Model ID, press the connect button to connect your web app. Now you should be able to interact with Gemini 2.0 with the Multimodal Live API.

1. To interact with the app, you can do the following:

    - Text input: You can write a text prompt to send to the model by entering your message in the box and pressing the send arrow. The model will then respond via audio (turn up your volume!).
    - Voice input: Press the microphone button to stop speaking. The model will respond via audio. If you would like to mute your microphone, press the button with a slash through the microphone.
    - Video input: The model will also capture your camera input and send it to Gemini. You can ask questions about current or previous video footage. For more details on how this works, visit the [documentation page for the Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).

### Setup in Cloud Shell

1. Open [Cloud Shell](https://cloud.google.com/shell/docs/editor-overview)

1. Upload the frontend and backend folders to your Cloud Shell Editor project. Alternatively, you can clone the repository and cd into the correct directory:

    ```sh
    git clone https://github.com/GoogleCloudPlatform/generative-ai.git
    cd generative-ai/gemini/multimodal-live-api/websocket-demo-app
    ```

1. Open two new terminal windows.
1. Navigate to whichever folder in Cloud Shell you uploaded the code files to (i.e., using `cd your_folder_name`)

1. Install dependencies: In one of the terminal windows run:

    ```sh
    pip3 install -r backend/requirements.txt
    ```

1. Start the Python WebSocket server in one terminal.

    ```sh
    python3 backend/main.py
    ```

1. In order for index.html to work properly, you will need to update the app URL inside script.js to point to the correct proxy server URL you just set up in the previous step. To do so:

    - Click on Web Preview (to the right of the Open Terminal button near the top)
    - Click "Preview on port 8080" (the port where you've setup the proxy server in the previous step)
    - Copy the URL, but make sure to discard everything at the end after "cloudshell.dev/"
    - Navigate to `const PROXY_URL = "wss://your websocket server";` in `frontend/script.js` on line 8
    - Replace `wss://your websocket server` with `wss://[THE_URL_YOU_COPIED_WITHOUT_HTTP]`. For example, it should look like: `const PROXY_URL = "wss://8080-cs-123456789-default.cs-us-central1-abcd.cloudshell.dev";`
    - Replace `your project id` with your project ID on line 9, for the `const PROJECT_ID`
    - save the changes you've made to script.js

1. Start the frontend:
   In the second terminal window, run the command below. Keep the backend server running in the first terminal.
   (Make sure you have navigated to the folder containing the code files, i.e. using `cd frontend`)

    ```sh
    cd frontend
    python3 -m http.server
    ```

1. Test the demo app:

    - Navigate to the Web Preview button again
    - Click on "Change port"
    - Change Preview Port to 8000, and then click on "Change and Preview". This should open up a new tab with the UI.

1. Going back to the tab with the Cloud Shell Editor, connect to the application by running the following command in a new terminal window:

    ```sh
    gcloud config set project YOUR-PROJECT-ID
    gcloud auth print-access-token
    ```

    - Copy your access token and paste it in the Access Token field in the UI.
    - In the second field of the UI, labeled Project ID, add your Google Cloud Project ID
    - Press the "Connect" button. Now you should be able to interact with Gemini 2.0 with the Multimodal Live API.

1. To interact with the app, you can do the following:

    - Text input: You can write a text prompt to send to the model by entering your message in the box and pressing the send arrow. The model will then respond via audio (turn up your volume!).
    - Voice input: Press the pink microphone button and start speaking. The model will respond via audio. If you would like to mute your microphone, press the button with a slash through the microphone.
    - Video input: The model will also capture your camera input and send it to Gemini. You can ask questions about current or previous video footage. For more details on how this works, visit the [documentation page for the Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).

### Setup in Cloud Run

1. Clone the repository and cd into the correct directory

    ```sh
    git clone https://github.com/GoogleCloudPlatform/generative-ai.git
    cd generative-ai/gemini/multimodal-live-api/websocket-demo-app
    ```

1. Modify the frontend code to point the WebSocket endpoint to the same container:

    - Navigate to the `script.js` file on line 9, `const PROXY_URL = "wss://[THE_URL_YOU_COPIED_WITHOUT_HTTP]";` and replace `PROXY_URL` value with `/ws`. It should look like: `const PROXY_URL = "/ws";`. Note the absence of the second "s" in "wss" as "ws" indicates a non-secure WebSocket connection. And there is no host part as it will use the same container as the frontend and backend.
    - Right below on line 10, update `PROJECT_ID` with your Google Cloud project ID.
    - Save the changes you've made to `script.js`

1. Deploy the code to Cloud Run using the following `gcloud` command:

    ```sh
    gcloud run deploy --project=YOUR-PROJECT-ID \
    --region=us-central1 \
    --source=./ \
    --allow-unauthenticated \
    --port=8000  \
    gemini-live-demo
    ```

1. Last step command will output a link for the deployment if it run successfully. Copy the link to your browser and navigate to the demo app UI.

1. Get your Google Cloud access token: Run the following command in a terminal with gcloud installed to set your project, and to retrieve your access token.

    ```sh
    gcloud components update
    gcloud components install beta
    gcloud config set project YOUR-PROJECT-ID
    gcloud auth print-access-token
    ```

1. Copy the access token from the previous step into the UI that you have open in your browser.

1. Enter the model ID in the UI:
   Replace `YOUR-PROJECT-ID` in the input with your Google Cloud Project ID.

1. Connect and interact with the demo:

    - After entering your Access Token and Model ID, press the connect button to connect your web app. Now you should be able to interact with Gemini 2.0 with the Multimodal Live API.

1. To interact with the app, you can do the following:

    - Text input: You can write a text prompt to send to the model by entering your message in the box and pressing the send arrow. The model will then respond via audio (turn up your volume!).
    - Voice input: Press the microphone button to stop speaking. The model will respond via audio. If you would like to mute your microphone, press the button with a slash through the microphone.
    - Video input: The model will also capture your camera input and send it to Gemini. You can ask questions about current or previous video footage. For more details on how this works, visit the [documentation page for the Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).
