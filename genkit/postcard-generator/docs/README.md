# Postcard Generator Documentation

This guide walks you through how to demonstrate this app and showcase the Google Cloud & Firebase features that power it.

If you are not familiar with [Firebase Genkit](https://firebase.google.com/docs/genkit), [Firebase App Hosting](https://firebase.google.com/docs/app-hosting), and [Next.js](https://nextjs.org), I recommend you familiarise yourself before continuing this document.

## Overview

This demo has two parts: a webapp and a Genkit development environment. Both use the same code, but have different aspects to demo. The most important thing is that it's the same codebase for both - just different tools to interact suitable for different personas and tasks.

## Instructions

### TL;DR

#### Setup

Regardless of your use-case, you should run these steps:

```sh
export PROJECT_ID="my-project-id"
cd terraform
terraform init && terraform apply -var="project_id=${PROJECT_ID}"
cd ..
npm install
```

#### Running in Genkit

```sh
export PROJECT_ID="my-project-id"
npx genkit@latest start
```

Then navigate to [localhost:4000](http://localhost:4000).

#### Running the App Locally

```sh
export PROJECT_ID="my-project-id"
npm run dev
```

#### Deploying to Firebase App Hosting

```sh
export PROJECT_ID="my-project-id"
cd terraform
terraform init && terraform apply -var="project_id=${PROJECT_ID}"
cd ..
npx firebase-tools@latest apphosting:backends:create --project="${PROJECT_ID}"
npx firebase-tools@latest apphosting:secrets:grantaccess NEXT_PUBLIC_GOOGLE_MAPS_PUBLIC_API_KEY --project "${PROJECT_ID}" --backend postcards
npx firebase-tools@latest apphosting:secrets:grantaccess GOOGLE_MAPS_API_SERVER_KEY --project "${PROJECT_ID}" --backend postcards
```

### Step 1 - Setup

Refer to the [Setup Documentation](setup.md) to configure your project including provisioning API keys and secrets.

### (Optional) Step 2 - Deploy to Firebase App Hosting

Refer to the [Deployment Documentation](deploy.md) to deploy the App to Firebase App Hosting

### Step 3 - Demo

Refer to the [Demo Guide](demo.md) for instructions on how to show this demo.

## Target Audience

Aimed at developers / practitioners who are looking to build and productionise AI apps. It can be expanded to showcase those looking for a modern app hosting platform (e.g. to compete with Vercel) or for those looking to understand Google Cloud's developer tools.

PRs welcome to add extra features such as logging / monitoring / etc.

### Features / Technologies Used

1. [Firebase App Hosting](https://firebase.google.com/docs/app-hosting)
2. [Cloud Run](https://cloud.google.com/run)
3. [Vertex AI](https://cloud.google.com/vertex-ai)
4. [Google Maps API](https://developers.google.com/maps)
5. [Firebase Genkit](https://firebase.google.com/docs/genkit)
