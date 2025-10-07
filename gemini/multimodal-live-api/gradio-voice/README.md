# Gemini Voice Chat Demo

A low-latency bidirectional streaming pure-python application that enables voice conversations with Gemini using Gradio. This demo showcases real-time audio streaming capabilities, allowing natural conversations where you can speak with Gemini and receive audio responses back.

## Features

- Real-time audio streaming using WebRTC
- Voice-to-voice conversations with Gemini
- Multiple voice options for Gemini's responses
- Simple web interface built with Gradio
- Low-latency bidirectional communication

## Prerequisites

Before running the application, you need to:

1. Enable Vertex AI in your Google Cloud Project

   - Visit [Enable Vertex AI](https://console.cloud.google.com/flows/enableapi?apiid=aiplatform.googleapis.com)

2. Set up authentication
   - Configure default credentials following [Google Cloud Authentication Guide](https://cloud.google.com/docs/authentication/provide-credentials-adc#how-to)

## Installation

1. Clone this repository:

   ```bash
   git clone git@github.com:GoogleCloudPlatform/generative-ai.git
   cd generative-ai/gemini/multimodal-live-api/gradio-voice
   ```

2. Install the required dependencies:

   ```bash
   pip install -r requirements.txt
   ```

The main dependencies are:

- `fastrtc`
- `librosa`
- `google-genai`

## Usage

1. Run the application:

   ```bash
   python app.py
   ```

2. Open your web browser and navigate to the local Gradio interface (typically `http://localhost:7860`)

3. Configure the application:

   - Enter your Google Cloud Project ID
   - Select your preferred region (default: us-central1)
   - Choose a voice for Gemini (options: Puck, Charon, Kore, Fenrir, Aoede)
   - Click "Submit"

4. Start the conversation:
   - Click the record button to start speaking
   - Listen to Gemini's responses through your speakers

## Configuration Options

### Regions

The application supports any Google Cloud regions, with presets for:

- us-central1 (default)
- us-east5
- us-south1
- us-west4
- us-east4
- us-east1
- us-west1

Additional locations can be found in the [Vertex AI documentation](https://cloud.google.com/vertex-ai/generative-ai/docs/learn/locations#united-states).

### Voice Options

Gemini can respond using different voice personalities:

- Puck (default)
- Charon
- Kore
- Fenrir
- Aoede

## Technical Details

The application uses:

- Gradio for the web interface
- WebRTC for real-time audio streaming
- Google Gen AI SDK for Gemini integration
- Vertex AI for model hosting and inference

The audio streaming implementation uses:

- 16kHz input sample rate
- 24kHz output sample rate
- PCM audio format
- Base64 encoding for audio transmission

## Deployment Notes

For deploying behind a firewall, you may need to modify the WebRTC configuration. See the [Gradio WebRTC deployment documentation](https://fastrtc.org/deployment/) for more details.
