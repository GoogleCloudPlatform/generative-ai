FROM python:3.9

WORKDIR /app
COPY ./application_default_credentials.json /app/credentials.json
ENV GOOGLE_APPLICATION_CREDENTIALS=/app/credentials.json
ENV GOOGLE_CLOUD_PROJECT=genai-mlops-tune-and-eval