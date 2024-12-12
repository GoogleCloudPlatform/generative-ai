# Multimodal Live API Demo

This tutorial guides you through building a web application that allows you to interact with [Gemini 2.0 Flash Experimental](https://blog.google/technology/google-deepmind/google-gemini-ai-update-december-2024/#ceo-message) using your voice and camera. This is achieved through the [Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live), a low-latency bidirectional streaming API that supports audio and video input and can output audio.

## Pre-requisites

* A Google Cloud project
* Foundational knowledge of Web development

**Note:** Familiarity with web development concepts, including localhost, port numbers, and the distinctions between websockets and HTTP requests, is beneficial for those interested in contributing code. However, it is not mandatory for completing the tutorial.

## Demo Architecture

* **Frontend (HTML/JavaScript):** A web page that serves as the user interface and communicates with the backend through WebSockets.
* **Backend (Python WebSockets Server):** Manages user authentication and acts as a bridge between the frontend and the Gemini API.

### File Structure

- [index.html](/gemini/multimodal-live-api/websocket-demo-app/index.html): The frontend HTML+JS+CSS app
- [pcm-processor.js](/gemini/multimodal-live-api/websocket-demo-app/pcm-processor.js): Script used by `index.html` page for processing audio
- [main.py](/gemini/multimodal-live-api/websocket-demo-app/main.py): The Python backend code
- [requirements.txt](/gemini/multimodal-live-api/websocket-demo-app/requirements.txt): Lists the required Python dependencies

![Demo](https://storage.googleapis.com/cloud-samples-data/generative-ai/image/demo-UI.png)

## Setup instructions

You can set up this app in your local environment or use [Cloud Shell Editor](https://shell.cloud.google.com/).

### Preparation

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
   pip3 install -r requirements.txt
   ```

1. Get your Google Cloud access token:
   Run the following command in a terminal with gcloud installed to set your project, and to retrieve your access token.

   ```sh
   gcloud config set project YOUR-PROJECT-ID
   gcloud auth print-access-token
   ```

### Running locally

1. Start the Python WebSocket server:

   ```sh
   python3 main.py
   ```

1. Start the frontend:
   Make sure to open a **new** terminal window to run this command. Keep the backend server running in the first terminal.

   ```sh
   python3 -m http.server
   ```

1. Point your browser to the demo app UI based on the output of the terminal. (E.g., it may be http://localhost:8000, or it may use a different port.)

1. Copy the access token from the previous step into the UI that you have open in your browser.

1. Enter the model ID in the UI:
   Replace `YOUR-PROJECT-ID` in the input with your credentials

1. Connect and interact with the demo:

- After entering your Access Token and Model ID, press the connect button to connect your web app. Now you should be able to interact with Gemini 2.0 with the Multimodal Live API.

1. To interact with the app, you can do the following:

- Text input: You can write a text prompt to send to the model by entering your message in the box and pressing the send arrow. The model will then respond via audio (turn up your volume!).
- Voice input: Press the pink microphone button and start speaking. The model will respond via audio. If you would like to mute your microphone, press the button with a slash through the microphone.
- Video input: The model will also capture your camera input and send it to Gemini. You can ask questions about current or previous video footage. For more details on how this works, visit the [documentation page for the Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).

### Running in Cloud Shell

1. In a new terminal window run following command to Start the Python WebSocket server in one terminal.

   ```sh
   python3 main.py
   ```

1. In order for index.html to work properly, you will need to update the app URL inside index.html to point to the correct proxy server URL you just set up in the previous step. To do so:

- Click on Web Preview (to the right of the Open Terminal button near the top)
- Click "Preview on port 8080" (the port where you've setup the proxy server in the previous step)
- Copy the URL, but make sure to discard everything at the end after "cloudshell.dev/"
- Navigate to `const URL = "ws://localhost:8080";` in `index.html` on line 116
- Replace `ws://localhost:8080` with `wss://[THE_URL_YOU_COPIED_WITHOUT_HTTP]`. For example, it should look like: `const URL = "wss://8080-cs-123456789-default.cs-us-central1-abcd.cloudshell.dev";`
- save the changes you've made to index.html

1. Start the frontend:
   In the second terminal window, run the command below. Keep the backend server running in the first terminal.
   (Make sure you have navigated to the folder containing the code files, i.e. using `cd your_folder_name`)

```sh
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
- In the second field with the model ID, change `YOUR-PROJECT-ID` to your actual Google Cloud project ID.
  For example, it should look like: `projects/my-project-id/locations/us-central1/publishers/google/models/gemini-2.0-flash-exp`
- Press the "Connect" button. Now you should be able to interact with Gemini 2.0 with the Multimodal Live API.

1. To interact with the app, you can do the following:

- Text input: You can write a text prompt to send to the model by entering your message in the box and pressing the send arrow. The model will then respond via audio (turn up your volume!).
- Voice input: Press the pink microphone button and start speaking. The model will respond via audio. If you would like to mute your microphone, press the button with a slash through the microphone.
- Video input: The model will also capture your camera input and send it to Gemini. You can ask questions about current or previous video footage. For more details on how this works, visit the [documentation page for the Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).
