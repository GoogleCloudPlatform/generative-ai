# palm-vertex-ai-chatbot
An example chatbot app with Gradio that uses the PaLM API from Vertex AI in
Google Cloud

![Chatbot app powered by the PaLM API in Google Cloud](images/chatbot.png)

## Usage

1. Clone this repository and `cd` into the directory.

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
