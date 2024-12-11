# Multimodal Live API Demo

In this tutorial, you will be building a web application that enables you to use your voice and camera to talk to Gemini 2.0 through the [Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).

The [Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live) is a low-latency bidirectional streaming API that supports audio and video streaming inputs and can output audio.

## Architecture

- **Backend (Python WebSockets Server):** Handles authentication and acts as an intermediary between your frontend and the Gemini API.
- **Frontend (HTML/JavaScript):** Provides the user interface and interacts with the backend via WebSockets.

## Pre-requisites

Some web development experience is required to follow this tutorial, especially working with localhost, understanding port numbers, and the difference between websockets and http requests.

### File Structure

- main.py: The Python backend code
- index.html: The frontend HTML+JS+CSS app
- pcm-processor.js: Script for processing audio
- requirements.txt: Lists the required Python dependencies

![Demo](https://storage.googleapis.com/cloud-samples-data/generative-ai/image/demo-UI.png)

## Setup instructions

You can set up this app locally or via Cloud Shell.

### Setup locally

1. Clone the repository and cd into the correct directory

```sh
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
cd gemini/multimodal-live-api/websocket-demo-app
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

1. Get your Google Cloud access token:
   Run the following command in a terminal with gcloud installed to set your project, and to retrieve your access token.

```sh
gcloud config set project YOUR-PROJECT-ID
gcloud auth print-access-token
```

1. Copy the access token from the previous step into the UI that you have open in your browser.

1. Enter the model ID in the UI:
   Replace `YOUR-PROJECT-ID` in the input with your credentials

1. Connect and interact with the demo:

- After entering your Access Token and Model ID, press the connect button to connect your web app. Now you should be able to interact with Gemini 2.0 with the Multimodal Live API.

1. To interact with the app, you can do the following:

- Text input: You can write a text prompt to send to the model by entering your message in the box and pressing the send arrow. The model will then respond via audio (turn up your volume!).
- Voice input: Press the pink microphone button and start speaking. The model will respond via audio. If you would like to mute your microphone, press the button with a slash through the microphone.
- Video input: The model will also capture your camera input and send it to Gemini. You can ask questions about current or previous video footage. For more details on how this works, visit the [documentation page for the Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live).

### Setup in Cloud Shell

1. Open [Cloud Shell](https://cloud.google.com/shell/docs/editor-overview)

1. Upload `main.py`, `index.html`, `pcm-processor.js`, and `requirements.txt` to your Cloud Shell Editor project. Alternatively, you can clone the repository and cd into the correct directory:

```sh
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
cd gemini/multimodal-live-api/websocket-demo-app
```

1. Open two new terminal windows.
1. Navigate to whichever folder in Cloud Shell you uploaded the code files to (i.e., using `cd your_folder_name`)

1. Install dependencies: In one of the terminal windows run:

```sh
pip3 install -r requirements.txt
```

1. Start the Python WebSocket server in one terminal.

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
