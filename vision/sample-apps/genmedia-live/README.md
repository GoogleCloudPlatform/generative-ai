# GenMedia Live

Author: [Wafae Bakkali](https://github.com/WafaeBakkali)

**Real-time multimodal creation enabled by extending the Gemini Live API with image and video generation tools.**

GenMedia Live enables multimodal AI creation by extending the [Gemini Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/live-api) capabilities to image and video generation using Gemini Pro Image and Veo through function calling.

You can interact with voice or text to:
- **Generate images** from descriptions or edit existing ones
- **Create videos** from text prompts or animate images
- **Create short movies** by combining multiple video clips
- **Ask questions** about what you show on camera or upload
- **Extract frames** from videos for further editing

Users can reference previously generated images, or use images from their camera, screen share, or upload images from the UI as reference.

## Features

- **Voice Interaction**: Real-time voice conversations with the Gemini Live API
- **Text Input**: Type messages as an alternative to voice
- **Camera**: Share your camera for visual context
- **Screen Share**: Share your screen for visual context
- **Image Upload**: Upload images from your device as reference
- **Image Generation**: Create and edit images using Gemini Pro Image
- **Video Generation**: Generate videos with Veo, including image-to-video
- **Frame Extraction**: Extract frames from videos using ffmpeg
- **Video Combining**: Merge multiple videos into one using ffmpeg
- **Session Management**: 30-minute conversation history with automatic reconnection

## Prerequisites

- Python 3.10+
- Google Cloud project with Vertex AI API enabled
- ffmpeg (for video operations)

### Installing ffmpeg

**Linux (Ubuntu/Debian):**
```bash
sudo apt update && sudo apt install ffmpeg
```

**macOS:**
```bash
brew install ffmpeg
```

**Windows:**
Download from [ffmpeg.org](https://ffmpeg.org/download.html) and add to PATH.

## Setup

1. Clone the repository:
```bash
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
cd generative-ai/vision/sample-apps/genmedia-live
```

2. Create and activate virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python app.py
```

5. Open http://localhost:8080 in your browser.

## Authentication

GenMedia Live requires users to authenticate with their own Google Cloud credentials.

### Steps to Authenticate:

1. **Enter your Project ID** in the sidebar
2. **Click "Open Cloud Shell"** - this opens Google Cloud Shell in a new tab
3. **Run the command** in Cloud Shell:
   ```bash
   gcloud auth print-access-token
   ```
4. **Copy the token** and paste it in the "Paste Token" field
5. **Click "Validate & Connect"**

If validation succeeds, you'll see "Connected!" and can start using the app.

> **Note**: Access tokens expire after ~1 hour. You'll need to generate a new token if your session expires.

## Usage

1. Complete authentication (see above)
2. Click **Voice** to start a voice conversation, or type in the text box
3. Click **Camera** to share your camera as visual context
4. Click **Screen** to share your screen as visual context
5. Use **Upload** to add reference images from your device
6. Ask GenMedia Live to generate images or videos

## Project Structure

```
genmedia-live/
├── app.py                 # Flask backend
├── index.html             # Main page
├── style.css              # Global styles
├── requirements.txt       # Python dependencies
├── outputs/               # Generated files
│   ├── images/
│   └── videos/
└── src/
    ├── main.js            # App initialization
    ├── ui.js              # UI utilities
    └── features/
        ├── genmedia-chat.js       # Voice chat functionality
        └── templates/
            └── genmedia-chat.html
```

## Deployment

### Cloud Run

```bash
gcloud run deploy genmedia-live \
  --source . \
  --region us-central1 \
  --allow-unauthenticated
```

## License

Licensed under the [Apache License, Version 2.0](https://www.apache.org/licenses/LICENSE-2.0).
