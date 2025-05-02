# Cloud Function Tools for Project Livewire

This directory contains Google Cloud Functions that provide tool functionalities for the Project Livewire application. These functions are designed to be called by the backend server to extend the capabilities of the Gemini AI model, such as providing weather information and accessing calendars.

## Tools Overview

This directory is organized into the following tool categories:

### Weather Tools
- **`get-weather-tool`**:  Retrieves current weather data for a specified location.

### Calendar Tools
- **`get-calendar-tool`**: Fetches the next upcoming calendar appointment from a configured Google Calendar.

## Prerequisites

Before deploying and using these Cloud Functions, ensure you have the following prerequisites in place:

1. **Google Cloud Project Setup**:
   - You need a Google Cloud Project. If you don't have one, create a project at [Google Cloud Console](https://console.cloud.google.com).
   - Set your project ID in your gcloud configuration:
     ```bash
     # Set your project ID
     export PROJECT_ID=your-project-id
     gcloud config set project \$PROJECT_ID
     ```

2. **Enable Required Google Cloud APIs**:
   - Enable the following APIs for your project using the gcloud CLI:
     ```bash
     gcloud services enable \\
       cloudfunctions.googleapis.com \\
       secretmanager.googleapis.com \\
       calendar-json.googleapis.com # Required for Calendar Tool
     ```

3. **Install Google Cloud SDK (gcloud CLI)**:
   - Make sure you have the Google Cloud SDK installed. You can find installation instructions at [Google Cloud SDK Install](https://cloud.google.com/sdk/docs/install).
   - Authenticate the SDK with your Google Cloud account:
     ```bash
     gcloud init
     gcloud auth login
     ```

## Secret Management Setup

The Cloud Functions use Google Cloud Secret Manager to securely store API keys and service account credentials. You need to set up Secret Manager and grant access to the Cloud Functions' service accounts.

1. **Create Service Accounts for Cloud Functions**:
   - Create dedicated service accounts for each function type to follow the principle of least privilege.
     ```bash
     # Create service account for weather functions
     gcloud iam service-accounts create weather-function-sa \\
         --description="Service account for Weather Cloud Functions" \\
         --display-name="Weather Function SA"

     # Create service account for calendar function
     gcloud iam service-accounts create calendar-function-sa \\
         --description="Service account for Calendar Cloud Function" \\
         --display-name="Calendar Function SA"
     ```

2. **Grant Secret Manager Access to Service Accounts**:
   - Give each service account the "Secret Manager Secret Accessor" role so they can retrieve secrets.
     ```bash
     # Grant access to weather function service account
     gcloud projects add-iam-policy-binding \$PROJECT_ID \\
         --member="serviceAccount:weather-function-sa@\$PROJECT_ID.iam.gserviceaccount.com" \\
         --role="roles/secretmanager.secretAccessor"

     # Grant access to calendar function service account
     gcloud projects add-iam-policy-binding \$PROJECT_ID \\
         --member="serviceAccount:calendar-function-sa@\$PROJECT_ID.iam.gserviceaccount.com" \\
         --role="roles/secretmanager.secretAccessor"
     ```

3. **Store API Keys and Credentials in Secret Manager**:
   - Store the OpenWeather API key and the Calendar service account key in Secret Manager.

     ```bash
     # Store OpenWeather API key
     echo -n "your-openweather-api-key" | \\
       gcloud secrets create OPENWEATHER_API_KEY \\
       --data-file=- \\
       --replication-policy="automatic"

     # Store Calendar service account key (after downloading from Google Cloud Console - see Calendar Tool Setup below)
     gcloud secrets create CALENDAR_SERVICE_ACCOUNT \\
       --data-file=path/to/service-account-key.json \\
       --replication-policy="automatic"
     ```
     **Important**: Replace `path/to/service-account-key.json` with the actual path to your downloaded Calendar service account key file.

## Weather Tools Setup

Follow these steps to set up and deploy the Weather Cloud Functions.

1. **Get OpenWeather API Key**:
   - Sign up for an account at [OpenWeatherMap](https://openweathermap.org/api) and obtain an API key.
   - Store this API key in Secret Manager as `OPENWEATHER_API_KEY` as described in the Secret Management Setup section.

2. **Deploy Weather Functions**:
   - Navigate to the `cloud-functions/weather-tools/` directory.
   - Deploy the `get-weather-tool` function:
     ```bash
     gcloud functions deploy get-weather-tool \\
         --runtime python310 \\
         --trigger-http \\
         --entry-point=get_weather \\
         --service-account="weather-function-sa@\$PROJECT_ID.iam.gserviceaccount.com" \\
         --source=get-weather-tool \\
         --region=us-central1
     ```
     **Note**: Replace `us-central1` with your desired Google Cloud region if needed.

## Calendar Tool Setup

To use the Calendar Tool, you need to configure a service account, share your Google Calendar, and then deploy the Cloud Function.

1. **Create and Download Service Account Key**:
   - Go to [Google Cloud Console](https://console.cloud.google.com) > "IAM & Admin" > "Service Accounts".
   - Select the `calendar-function-sa` service account you created earlier.
   - Go to the "Keys" tab.
   - Click "Add Key" > "Create New Key".
   - Choose "JSON" as the key type and click "Create".
   - Download the JSON key file to your local machine. **Securely store this file.**
   - Move the downloaded service account key file to a secure location and note its path.

2. **Share Calendar with Service Account**:
   - Go to [calendar.google.com](https://calendar.google.com) and log in with the Google account that owns the calendar you want to use.
   - Find your calendar in the left sidebar.
   - Click the three dots next to your calendar name and select "Settings and sharing".
   - Under "Share with specific people and groups", click "Add people and groups".
   - In the "People and groups" field, enter the email address of the `calendar-function-sa` service account. You can find this email address in the downloaded JSON key file (it's the `client_email` field) or in the Google Cloud Console under "Service Accounts".
   - In the "Permissions" dropdown, select "See all event details".
   - Click "Send".

3. **Get Calendar ID**:
   - In the same "Settings and sharing" page for your calendar, scroll down to the "Integrate calendar" section.
   - Copy your "Calendar ID". You will need this when deploying the Calendar function or when configuring the backend server to use this function.

4. **Store Calendar Service Account Key in Secret Manager**:
   - As described in the "Secret Management Setup" section, store the contents of the downloaded JSON key file in Secret Manager under the secret name `CALENDAR_SERVICE_ACCOUNT`.

5. **Deploy Calendar Function**:
   - Navigate to the `cloud-functions/calendar-tools/` directory.
   - Deploy the `get-calendar-tool` function, replacing `your.calendar.id@gmail.com` with your actual Calendar ID obtained in the previous step:
     ```bash
     gcloud functions deploy get-calendar-tool \\
         --runtime python310 \\
         --trigger-http \\
         --entry-point=get_calendar \\
         --service-account="calendar-function-sa@\$PROJECT_ID.iam.gserviceaccount.com" \\
         --source=get-calendar-tool \\
         --region=us-central1 \\
         --set-env-vars CALENDAR_ID=your.calendar.id@gmail.com
     ```
     **Note**: Replace `us-central1` with your desired Google Cloud region if needed.

## Testing the Functions

After deploying the functions, you can test them using `curl` commands to ensure they are working correctly. Replace `YOUR_FUNCTION_URL` with the actual trigger URL of your deployed Cloud Functions. You can find the function URL in the Google Cloud Console or by using the `gcloud functions describe` command.

### Weather Functions

- **Test `get-weather-tool` with city name**:
  ```bash
  curl "YOUR_FUNCTION_URL/get-weather-tool?city=London"
  ```
- **Test `get-weather-tool` with latitude and longitude**:
  ```bash
  curl "YOUR_FUNCTION_URL/get-weather-tool?lat=51.5074&lon=-0.1278"
  ```

### Calendar Function

- **Test `get-calendar-tool` (if `CALENDAR_ID` is set as environment variable during deployment)**:
  ```bash
  curl "YOUR_FUNCTION_URL/get-calendar-tool"
  ```
- **Test `get-calendar-tool` with specific calendar ID as a parameter**:
  ```bash
  curl "YOUR_FUNCTION_URL/get-calendar-tool?calendar_id=your.calendar@gmail.com"
  ```
  Replace `your.calendar@gmail.com` with your actual Calendar ID.

## Project Structure

The `cloud-functions/` directory has the following structure:

```
cloud-functions/
├── weather-tools/
│   ├── get-weather-tool/
│   │   ├── main.py
│   │   └── requirements.txt
└── calendar-tools/
    └── get-calendar-tool/
        ├── main.py
        └── requirements.txt
```

Each tool resides in its own subdirectory and contains:
- `main.py`: The Python code for the Cloud Function.
- `requirements.txt`: Python dependencies for the function.

## Security Notes

- **Never commit API keys or service account credentials directly into your code or version control.**
- **Always use Google Cloud Secret Manager to store sensitive credentials.** This ensures that your keys are encrypted and securely managed.
- **Grant the least necessary permissions to your service accounts.**  Each Cloud Function should only have the permissions it absolutely needs.
- **Consider adding authentication and authorization mechanisms** to your Cloud Functions if they handle sensitive data or operations.
- **Regularly rotate API keys and service account credentials** as a security best practice.
- **Monitor Cloud Function access logs** for any suspicious or unauthorized activity.
