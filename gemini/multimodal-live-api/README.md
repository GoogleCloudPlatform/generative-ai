# Multimodal Live API

The [Multimodal Live API](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/multimodal-live) is a low-latency bidirectional streaming API that supports text, audio and video input, with audio and text output. This capability allows for natural, human-like conversations, giving you the option to interrupt the model at any point in the interaction. The model's abilities are further enhanced through video understanding, enabling you to share live video input and screencasts so that Gemini can reason across this information and respond to questions. You can also provide system instructions to better control the model's output.

## Demo

The following video demonstrating the Multimodal Live API shows an example use case of conversing with the model. This demo app can be run locally or via Cloud Shell so that you can test your own use cases. Instructions to get this application running are in the `websocket-demo-app` directory.

[![Demo Video](https://img.youtube.com/vi/_vc8sXog2ek/hqdefault.jpg)](https://www.youtube.com/watch?v=_vc8sXog2ek&t=1s)

## Getting Started

### Intro Notebooks

1. [Multimodal Live API](intro_multimodal_live_api.ipynb): Directly access the Multimodal Live API. This notebook will demonstrate text-to-text generation, as well as text-to-audio generation.

2. [Multimodal Live API via Gen AI SDK](intro_multimodal_live_api_genai_sdk.ipynb): Use this tutorial to access the Multimodal Live API using the Google Gen AI SDK in Vertex AI. You'll see examples of text-to-text generation and text-to-audio generation.

### Use Cases

1. [Interactive Loan Application Assistant](real_time_rag_bank_loans_gemini_2_0.ipynb): This notebook provides a comprehensive demonstration of how Gemini 2.0 can act as your personal file assistant across various storage platforms. It empowers users to seamlessly understand and interact with their loan documents.

2. [Real-time RAG for Retail](real_time_rag_retail_gemini_2_0.ipynb): Users will learn to develop a real-time Retrieval Augmented Generation (RAG) system leveraging the Multimodal Live API for a retail use-case. This system will generate audio and text responses grounded in provided documents.

### Demo App

1. [Demo Web Application](websocket-demo-app/README.md): Build a web application that enables you to use your voice and camera to talk to Gemini 2.0 through the Multimodal Live API.
