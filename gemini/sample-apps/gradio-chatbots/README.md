# Gemini-PRO & Gemini-PRO-Vision API Demo with Gradio Chatbots

This repository contains a Gradio demo implementation for interacting with the Gemini-PRO and Gemini-PRO-Vision models. It provides an easy-to-use interface for text and image processing using Google's generative AI models - Gemini Pro and Gemini-Vision.

## Overview

The `gemini-pro-and-vision.ipynb` and `gemini-pro-and-vision.py` files in this repository form the core of the demo. The Python script uses Gradio to create an interactive web interface where users can input text and upload images to see how the Gemini models respond.

### Features

- **Text Processing**: Enter text and see how the Gemini-PRO model processes it.
- **Image Processing**: Upload an image and observe the response from the Gemini-PRO-Vision model.
- **Interactive Chatbot**: Keep track of interactions with a multimodal chatbot.

## Getting Started

### Prerequisites

To run this demo, you will need:

- Python 3.x
- Access to Google's generative AI models (requires API key)
- Gradio library
- Gradio multimodalchatbot library

### Installation

1. Clone this repository:
   ```
   git clone https://github.com/GoogleCloudPlatform/generative-ai.git
   ```
2. Install the required packages:
   ```
   pip3 install google.generativeai gradio gradio_multimodalchatbot PIL
   ```

### API Key Configuration

Set your Google API key as an environment variable:

```bash
export GOOGLE_API_KEY="your-google-gemini-API-key"
```

### Running the Demo

To run the demo, execute the Python script:

```bash
python gemini-pro-and-vision.py
```

The Gradio interface will be hosted locally and accessible via a web browser.

## Usage

1. **Text Interaction**: Type your text into the textbox and submit to see the model's response.
2. **Image Upload**: Click 'Upload Image' to select an image file and view the model's response to the image.
3. **Chatbot**: The chatbot section will display the interaction history.

## Colab Notebook

For a cloud-based experience, you can also access the Colab notebook:

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/yvrjsharma/AI_workflows/blob/main/gemini_pro_and_vision.ipynb)


## Acknowledgements

- Google Generative AI models
- Gradio Library
