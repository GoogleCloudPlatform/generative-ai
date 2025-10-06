# Function Calling Service

This project demonstrates how to use the [Function Calling](https://cloud.google.com/vertex-ai/generative-ai/docs/multimodal/function-calling) service in a [Cloud Run](https://cloud.google.com/run) service. More generally, it shows how you can migrate notebook code to a [Python Flask application](https://flask.palletsprojects.com/en/3.0.x/) running as a Cloud Run service.

It wraps the address lookup tool in the [Introduction to Function Calling notebook](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb) as a Cloud Run service.

## Prerequisites

- Set your Google Cloud Project through an environment variable `GOOGLE_CLOUD_PROJECT`.

## Test

- Install the dependencies with `pip install -r requirements.txt`
- Run `python main.py` to locally run the development server to run this Flask application.

## Deployment

Use `gcloud run deploy` to deploy the application to a Cloud Run service.

## Acknowledgments

This project includes [highlight.js](https://highlightjs.org/) (Version 11.9.0), licensed under the [BSD License](https://github.com/highlightjs/highlight.js/blob/main/LICENSE).
