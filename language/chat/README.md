# palm-vertex-ai-chatbot
An example chatbot app with Gradio that uses the PaLM API from Vertex AI in
Google Cloud

![Chatbot app powered by the PaLM API in Google Cloud](images/chatbot.png)

## Usage

1. Clone this repository and `cd` into the `language/chat/` directory.

2. Install the required dependencies:

   ```
   pip install -r requirements.txt
   ```

3. Set up authentication in Google Cloud using your
   [preferred method](https://googleapis.dev/python/google-api-core/latest/auth.html).
   For example, you can use `gcloud auth` to generate credentials for client
   libraries, as in:

   ```
   gcloud auth application-default login
   ```

4. Run the app:

   ```
   python app.py
   ```

5. Navigate to `http://127.0.0.1:8080/` in your browser.

6. Start chatting with your PaLM-powered chatbot!

## Deploy to Cloud Run

The above steps allow you to test and use the chatbot app on your local machine.
You can use a fully managed service such as Cloud Run to publish your app.

1. From this directory, run the following command using the
   [gcloud CLI](https://cloud.google.com/sdk/gcloud):

   ```
   gcloud run deploy chatbot-app --source . --allow-unauthenticated --region us-central1
   ```

2. After a couple of minutes, your chatbot app will be deployed on Cloud Run,
   and you can access the app via a URL similar to:

   [`https://chatbot-app-r5gdynozbq-uc.a.run.app/`](https://chatbot-app-r5gdynozbq-uc.a.run.app/)
