# Enhanced Vision Assistant

## Overview

The Enhanced Vision Assistant is an AI-powered solution designed to help visually impaired individuals navigate their surroundings safely. By combining Google Cloud's Vision API, Gen AI with Gemini Pro, and Text-to-Speech capabilities, this application provides real-time environmental awareness through audio guidance.

|           |                                         |
| --------- | --------------------------------------- |
| Author(s) | [Prajwal](https://github.com/iprajwaal) |

## 🎥 Demo Video

[YouTube Video](https://youtu.be/Jpili5kx3hA)

## Features

- **Real-time object detection** using Google Cloud Vision API
- **Intelligent scene analysis** with Google Gen AI and Gemini Pro
- **Natural language navigation guidance** prioritized by urgency
- **Audio feedback** through Google Text-to-Speech
- **Obstacle tracking** and movement prediction
- **Dynamic priority system** for focusing on the most relevant hazards

## How It Works

1. The camera captures the user's environment in real-time.
2. Cloud Vision API detects objects and their positions.
3. The system estimates depth and analyzes potential hazards.
4. Gemini Pro processes the scene and generates natural language guidance.
5. Audio instructions are delivered through text-to-speech, prioritized by urgency.

## Prerequisites

- Google Cloud account with billing enabled.
- The following APIs enabled:
  - [Google AI (Generative AI) API](https://console.cloud.google.com/flows/enableapi?apiid=generativelanguage.googleapis.com)
  - [Cloud Vision API](https://console.cloud.google.com/flows/enableapi?apiid=vision.googleapis.com)
  - [Cloud Text-to-Speech API](https://console.cloud.google.com/flows/enableapi?apiid=texttospeech.googleapis.com)
- Python 3.8 or higher.
- Webcam or camera device.
- Speaker for audio output.

## Installation

1. Clone the repository:

   ```bash
   git clone https://colab.research.google.com/github/GoogleCloudPlatform/generative-ai
   cd vision/use-cases/vision-assistant
   ```

2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your Google Cloud credentials:
   - Create a service account with access to Vision API, Text-to-Speech API, and Gen AI API.
   - Download the service account key as JSON.
   - Set the environment variable:

     ```bash
     export GOOGLE_APPLICATION_CREDENTIALS="/path/to/your-service-account-key.json"
     ```

## Usage

1. Open the Jupyter notebook:

   ```bash
   jupyter notebook enhanced_vision_assistant.ipynb
   ```

2. Follow the cells in the notebook to:
   - Set up your Google Cloud project information.
   - Initialize the necessary clients.
   - Run the Enhanced Vision Assistant.

3. When running the assistant:
   - A window will open showing the camera feed with detected objects.
   - Audio guidance will be provided based on the scene analysis.
   - Press 'q' to quit the application.

## Customization

The Enhanced Vision Assistant can be customized in several ways:

- **Hazard weights**: Modify the `hazard_weights` dictionary in the `AgentMind` class to change how different objects are prioritized.
- **Detection interval**: Adjust the `DETECTION_INTERVAL` parameter to change how frequently the system analyzes the scene.
- **Voice settings**: Customize the voice by changing the parameters in the `speak` method.

## Troubleshooting

- **Camera access issues**: Ensure your camera is properly connected and not in use by another application.
- **API errors**: Verify that your Google Cloud APIs are enabled and your credentials are correctly set up.
- **Audio problems**: Check that your audio output device is working and properly configured.

## Acknowledgments

- Google Cloud Platform for providing the AI services.
- The open-source community for the various libraries used in this project.
- Everyone working to improve accessibility technology for visually impaired individuals.