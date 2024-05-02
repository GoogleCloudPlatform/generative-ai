# SETUP

## Set up the Project in your own environment

### Prerequisites

- As a prerequisite for the agent-assist demo, you would need a gmail/google account for managing meets and calendar events and would require to enable the [Google Calendar API](https://developers.google.com/calendar/api/guides/overview) and the [Google Mail API](https://developers.google.com/gmail/api/guides) for the same. The steps to enable the required apis can be found in the following links:

  > - [Calendar API](https://developers.google.com/calendar/api/quickstart/python)
  > - [Gmail API](https://developers.google.com/gmail/api/quickstart/python)

    <br/>

- You will need to follow the steps given in the links above to generate the `credential.json` files for both. After that you will also need to replace the [backend/src/cal_token.json](backend/src/cal_token.json) and [backend/src/mail_token.json](backend/src/mail_token.json) with the two respective `credential.json` you just generated. Make sure you keep the names same.

- You will also need to generate an app password for your mailing account. Follow these [steps](https://support.google.com/mail/answer/185833?hl=en) to generate an app password.

### Steps to set up the project

1. Setup [Gcloud CLI](https://cloud.google.com/sdk/gcloud), login to your google user account and select the project you want to deploy the app to.
   Install the Gcloud CLI using the following [steps](https://cloud.google.com/sdk/docs/install-sdk).

2. In order to use the various services you will need throughout this project, you will enable a few APIs. Do so by launching the following command in your terminal:

   ```bash
   gcloud services enable aiplatform.googleapis.com artifactregistry.googleapis.com autoscaling.googleapis.com bigquery.googleapis.com bigquerydatapolicy.googleapis.com bigquerymigration.googleapis.com bigquerystorage.googleapis.com calendar-json.googleapis.com chat.googleapis.com cloudapis.googleapis.com cloudbuild.googleapis.com cloudfunctions.googleapis.com cloudidentity.googleapis.com cloudresourcemanager.googleapis.com cloudtrace.googleapis.com compute.googleapis.com container.googleapis.com containerfilesystem.googleapis.com containerregistry.googleapis.com deploymentmanager.googleapis.com dns.googleapis.com drive.googleapis.com eventarc.googleapis.com iam.googleapis.com iamcredentials.googleapis.com iap.googleapis.com logging.googleapis.com monitoring.googleapis.com networkconnectivity.googleapis.com oslogin.googleapis.com people.googleapis.com redis.googleapis.com run.googleapis.com runtimeconfig.googleapis.com securetoken.googleapis.com servicemanagement.googleapis.com serviceusage.googleapis.com source.googleapis.com sourcerepo.googleapis.com storage.googleapis.com testing.googleapis.com texttospeech.googleapis.com workstations.googleapis.com
   ```

3. Update the fields

   `PROJECT_ID`: Google cloud project ID,

   `LOCATION`: Location where the project is hosted,

   `company_email`: Your company email which you will be using to manage meets and emails,

   `mail_password`: app password you generated in prerequisite step

   in [backend/src/config.py](backend/src/config.py) file.

4. Run the following command from the root directory of the repository to deploy your app to cloud run.

   ```bash
   npm run build --prefix frontend
   cp -r frontend/build/ backend/src/build
   gcloud run deploy agent-assist --source backend --port 8000 --region asia-south1 --platform managed --allow-unauthenticated
   ```

5. See the Google Cloud Run Service named **agent-assist** in the Console and open the URL for the service given there.
