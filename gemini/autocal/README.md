# AutoCal

|           |                                                                                               |
| --------- | --------------------------------------------------------------------------------------------- |
| Author(s) | [Stephanie Anani](https://github.com/stephanieanani), [Matt Day](https://github.com/mattsday) |

Screenshot to Calendar Magic with Gemini 2.0 Flash

![AutoCal Preview](complete.webp)

AutoCal is a web application that leverages the power of Gemini 2.0 Flash to automatically extract event information from screenshots and add them to your calendar. It simplifies the process of scheduling by eliminating the need for manual data entry.

## Project Structure

There are two versions of Autocal:

- [v1 - A streamlit app](apps/autocal-legacy/) - this is a standalone application
- **v2** - A Nextjs and Python app - this comprises of a number of services:
  1. [Auth Blocking](services/auth-blocking/) - to control access to the app
  2. [Frontend UI](apps/autocal/) - a Nextjs / MUI frontend for the user to interact with
  3. [Backend Image Processor](services/image-processor/) - a Python Cloud Function to process and handle images

## v2 Features

- **Async Screenshot Processing:** Upload a screenshot of a schedule or event list and have it asynchronously processed in the background
- **Gemini 2.0 Integration:** Uses Gemini 2.0 Flash to intelligently parse and understand the event details within the screenshot.
- **Automatic Event Extraction:** Extracts key information like event name, date, time, and location.
- **Calendar Integration:** The extracted information is added to your calendar

## Getting Started

### Prerequisites

You will require a Google Cloud Project with billing enabled to use this app.

### Setup

#### Part 1 - Run Terraform

Terraform will provision much of the underlying infrastructure and dependencies required by both v1 and v2 of this app.

The `terraform` directory includes all of the steps you will need to provision the infrastructure and app.

See [terraform/README.md](terraform/README.md) for instructions on how to do this.

#### Part 2 - Configure Auth

You will need to create an OAuth 2 application in the Google Cloud console. You can do so here in the [Credentials](https://console.cloud.google.com/apis/credentials) page. Take a note of the `Client ID` and `Client Secret`.

You will also need to create a 32-character secret key for use in Firestore to encrypt user sessions. This should be kept secret.

Take a note of these for the [Deploying section](#part-4---deploy-the-app-to-firebase-app-hosting) below.

Once created, you can edit the `.env` file in the autocal app directory.

```sh
cp .env.example .env
# Make edits to .env as needed
npm install
npm run dev
```

#### Part 3 - Coinfigure Firebase

You will need to update [apps/autocal/libs/firebase/config.ts](apps/autocal/libs/firebase/config.ts) to reflect your configuration, which you can find in [the Firebase console](https://console.firebase.google.com/) under Settings, "Your Apps".

For example:

```ts
export const firebaseConfig = {
  apiKey: "AIzaSyDYvf_kZcvo0ktBx8LjUQo3RKXFaCksl4U",
  authDomain: "autocal-448710.firebaseapp.com",
  projectId: "autocal-448710",
  storageBucket: "autocal-448710-assets-bu84",
  messagingSenderId: "406699036396",
  appId: "1:406699036396:web:eb9f5e2b8ffa9457871fc9",
  measurementId: "G-B9EK3RGL1S",
};
```

**Important:** Ensure the `export` keyword is there.

#### Part 4 - Deploy the App to Firebase App Hosting

Once setup, you can deploy the app using the following instructions.

First supply your CLIENT_SECRET and ENCRYPTION_KEY secrets to Firebase App Hosting (you should have configured these in [Setup](#setup):

```sh
export PROJECT_ID=PROJECT_ID
firebase apphosting:secrets:set CLIENT_SECRET --project "${PROJECT_ID}"
firebase apphosting:secrets:set ENCRYPTION_KEY --project "${PROJECT_ID}"
```

Then edit [apphosting.yaml](apphosting.yaml) and change your `NEXT_PUBLIC_CLIENT_ID` to the correct value.

Finally. create the hosting backend:

```sh
firebase apphosting:backends:create --project "${PROJECT_ID}" --location europe-west4
```

#### Part 5 - CORS Configuration

Finally, Google Cloud Storage uses [CORS](https://cloud.google.com/storage/docs/using-cors) to protect assets. To update the configuration, take a note of your application URL created with Terraform and update [utils/cors/cors.json](utils/cors/cors.json). Then run the [cors.sh](utils/cors/cors.sh) script with the name of your firebase config bucket in the environment variable `BUCKET_NAME`.
