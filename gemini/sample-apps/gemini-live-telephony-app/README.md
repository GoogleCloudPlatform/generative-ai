# AI Care Assistant

## Overview

This project provides a comprehensive architectural blueprint and implementation for a real-time, bidirectional voice-to-AI application. It integrates Twilio for telephony, a FastAPI backend for real-time processing, and the Google Gemini Live API for conversational AI. The application is designed for low-latency, high-fidelity conversational experiences, addressing challenges in system-level integration, audio transcoding, and deployment on Google Cloud Run.

Key design decisions include the use of `python-samplerate` for high-quality streaming audio resampling and a Cloud Run deployment strategy that mitigates cold starts (`min-instances=1`) and manages state using session affinity for in-memory DSP state.

<p align="center">
  <b></b> Click the image below to watch the video! </b>
</p>
<a href="https://www.youtube.com/watch?v=sboxrNY57uA">
  <img 
    src="https://img.youtube.com/vi/sboxrNY57uA/maxresdefault.jpg" 
    alt="Demo Video" 
    style="width:50%; margin: 0 auto; display: block;"
  >
</a>

## Special Notes

For a detailed understanding of the system's architecture, including component breakdowns, data flow, technical justifications, step-by-step guide on the implementation process, including project setup, code structure, and deployment instructions, please refer to the `design_doc.md` file.

## Google Cloud and Gemini Setup

1.  **Set up a Google Cloud Project:**
    - Go to the [Google Cloud Console](https://console.cloud.google.com/) and create a new project.
    - Make sure to enable the Vertex AI API for your project.

2.  **Authenticate with your Google Cloud Platform account:**
    - In your local terminal, authenticate your Google Cloud account by running:
      ```bash
      gcloud auth login
      gcloud auth application-default login # for providing credentials to applications and code
      ```

## Quickstart (For local testing)

This project is implemented using Python 3.12.

1.  **Create and activate a virtual environment:**
    ```bash
    python3.12 -m venv venv
    source venv/bin/activate
    ```

2.  **Install the necessary packages:**
    ```bash
    pip install -r requirements.txt
    ```

3.  **Set environment variables:**
    Set your environment variables by creating a **.env file** in the project directory by utilizing the **.env.example file**


4.  **Install the ngrok:**
    To install ngrok on Linux, you can follow these steps:

   - ***Download ngrok:***
      Open your web browser and go to the ngrok download page (https://ngrok.com/download). Download the Linux version.

   - ***Unzip the file:***
      Open a terminal and navigate to your Downloads directory (or wherever you saved the file). Then unzip it:
        unzip /path/to/ngrok-v3-stable-linux-amd64.zip
      (Replace /path/to/ with the actual path to the downloaded file).

   - ***Move ngrok to your PATH:***
      To make ngrok accessible from any directory, move it to a directory that's already in your system's PATH, such as /usr/local/bin

   - ***Signup and get your authtoken and execute the following command:***
      ```bash
        ngrok config add-authtoken $YOUR_AUTHTOKEN
      ```

   - Verify by running the **ngrok --version**


5. **Expose Your Local Server with ngrok:**
    open another terminal and run ngrok to create a public URL that tunnels to your local port 8000.

    ```bash
        ngrok http 8000
    ```   
    ngrok will give you a public **Forwarding URL**, which will look something like **https://<random-string>.ngrok-free.dev**


6. **Update Environment Variable:**
      You need to set the SERVICE_URL as an environment variable to the ngrok forwarding URL. Update your SERVICE_URL in your .env file
  This is critical because your application uses this URL to tell Twilio where to connect the WebSocket.
    ```bash
        SERVICE_URL=https://<random-string>.ngrok-free.dev
    ```

7.  **Run the FastAPI App Locally:**
      Start the application on your another terminal in your local machine after updating .env file with SERVICE_URL.
      ```bash
        uvicorn main:app --host 0.0.0.0 --port 8000
      ```

8.  **Set up a Twilio Trial Account:**
    - Create a free trial account at [Twilio](https://www.twilio.com/try-twilio).
    - Once your account is created, you will get a trial phone number and free credits to get started.

9. **Configure Twilio Webhook:**
    - Go to your Twilio phone number's configuration in the Twilio console.
    - Update the "A CALL COMES IN" webhook URL to point to your ngrok URL, followed by the /twiml endpoint (e.g., https://<random-string>.ngrok-free.dev/twiml).

Now, wait for around 2 mins and call your Twilio number, Twilio will send the webhook to the public ngrok URL, which will forward it to your locally running application. This allows you to test the entire end-to-end flow and see logs in real-time in your local terminal for debugging.

## Deployment on Google Cloud Platform

**Important Note on IAM Permissions:** Before deploying, ensure your Google Cloud account has the necessary IAM permissions for Cloud Run and Cloud Build Service account. Specifically, you will need roles such as `Cloud Run Invoker`,..etc

The `deploy.sh` script automates the process of building the container image, pushing it to Google Container Registry, and deploying it to Cloud Run.


1.  **Update `deploy.sh`:**
    - Open the `deploy.sh` file.
    - Replace `[YOUR_PROJECT_ID]` with your Google Cloud Project ID.

2.  **Configure Docker (optional):**
    - Ensure you have Docker configured to work with `gcloud`:
      ```bash
      gcloud auth configure-docker
      ```

3.  **Run the Deployment Script:**
    - Execute the `deploy.sh` script from your terminal:
      ```bash
      bash deploy.sh
      ```
    - The script will build and push the container, then deploy the service to Cloud Run. It will output the `Service URL` upon completion.

4.  **Configure Twilio Webhook:**
    - Copy the `Service URL` from the output of the deployment script.
    - Go to your Twilio phone number's configuration in the Twilio Console.
    - Set the "A CALL COMES IN" webhook to the deployed service URL, followed by `/twiml` (e.g., `https://<your-service-url>.a.run.app/twiml`), and set the method to `HTTP POST`.
    - Save the Twilio configuration.

Your AI Care Assistant is now deployed and ready to receive calls.

Made by [Vishnu Vardhan Reddy Kanamata Reddy](https://github.com/KVishnuVardhanR)
