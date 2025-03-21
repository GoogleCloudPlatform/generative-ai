# AutoCal Legacy

Automate Calendar Event Creation from Images

AutoCal is a Streamlit application that leverages Gemini 2.0 Flash to automatically extract event details from images (like screenshots of event listings) and add them to your Google Calendar.

## Features

- **Image Upload:** Upload images of event listings directly through the Streamlit interface.
- **AI-Powered Analysis:** Uses Gemini 2.0 Flash to analyze the image and extract key event information, including:
  - Event summary
  - Location
  - Start time (with date and time zone)
  - End time (calculated based on duration or assumed to be one hour if not specified)
  - Description
- **Google Calendar Integration:** Automatically creates a new event in your Google Calendar with the extracted details.
- **Cloud Storage:** Uploads the image to Google Cloud Storage for processing.
- **Firestore:** The image processing service uses Firestore to store the state of the image processing.

## How It Works

1. **Image Upload:** You upload an image containing event details (e.g., a screenshot of a concert listing, a flyer, etc.).
2. **Cloud Storage:** The image is uploaded to a Google Cloud Storage bucket.
3. **Gemini Analysis:** The app sends the image and a detailed prompt to the Gemini AI model. The prompt instructs Gemini to extract the event information and format it as JSON.
4. **Event Creation:** The app parses the JSON response from Gemini and uses the Google Calendar API to create a new event in your calendar.
5. **Firestore:** The image processing service uses Firestore to store the state of the image processing.

## Prerequisites

- **Google Cloud Project:** You need a Google Cloud project with the following APIs enabled:
  - Cloud Storage API
  - Vertex AI API
  - Calendar API
- **Service Account:** A service account with the necessary permissions to access Cloud Storage, Vertex AI, and Firestore.
- **Google Calendar API Credentials:**
  - `credentials.json`: A file containing your Google Calendar API credentials.
- **Python Environment:** Python 3.9+ with the required libraries installed (see "Installation").
- **Environment Variables:**
  - `BUCKET_NAME`: The name of your Google Cloud Storage bucket.
  - `GOOGLE_APPLICATION_CREDENTIALS`: The path to your service account key file.

## Installation

1. **Clone the Repository:**

   ```bash
   git clone <your-repository-url>
   cd <your-repository-directory>
   ```

2. **Install Dependencies:**

   ```bash
   pip install -r requirements.txt
   ```

3. **Set up Google Cloud Credentials:**

   - Download your Google Calendar API credentials and save it as `credentials.json` in the project root directory.
   - Create a `.env` file and add the `BUCKET_NAME` variable.

4. **Run the app:**

    ```bash
    streamlit run autocal-gemini-2.py
    ```

## Usage

1. Open the Streamlit app in your browser.
2. Upload an image of an event listing using the file uploader.
3. Click the "Add to Calendar" button.
4. The app will analyze the image, extract the event details, and create a new event in your Google Calendar.
5. You will be prompted to authorize the app to access your Google Calendar.

