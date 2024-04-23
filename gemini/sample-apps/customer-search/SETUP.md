# Deployment Guide

This deployment guide assumes existence of three users for demonstrating the various features and functionalities. Following are the user specific data which is setup in this guide:

- Login details in Firebase
- Financial data in BigQuery

## Prerequisites

- [Create a GCP project](https://developers.google.com/workspace/guides/create-project) - Preferrable to have a new GCP project, to prevent conflicts when using Terraform.
- [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project)
- [Create an API key for Maps API](https://developers.google.com/maps/documentation/embed/get-api-key#console)

## Deploy GCP Resources through Terraform

1. Open CloudShell in the created GCP Project. \***\*Note: User should have Owner/Editor permissions on the project.\*\***

2. Clone this repository

3. Add variables values in `variables.tfvars` file.

   > project = "{YOUR-PROJECT-ID}"\
   > user_email = "{YOUR-EMAIL-ID}" #should be the owner/editor of the project\
   > maps_api_key = "{YOUR-MAPS-API-KEY}"

4. In the CloudShell command line, run `make deploy` to deploy required resources.

## Configure DialogFlow

[Open dialogflow cx](https://dialogflow.cloud.google.com/cx/projects) and create a custom agent.

- Choose build your own
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image16.png)
- Click on import flow and add `CymBuddy_new.json` file present in `cymbuddy_search_setup/files`
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image9.png)
- From the Default Start Flow add a transition to the Default Start Flow of the imported flow using the **Default Welcome intent**
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image14.png)
- Copy the agent id after enabling unauthenticated API
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image3.png)
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image11.png)
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image13.png)

## Configure Firebase

Open the [Firebase console](https://console.firebase.google.com/). A firebase project would be present with the same project name as the GCP project created.

- Open the Authentication page.
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image1.png)
- Choose Email/Password as the sign-in method
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image17.png)
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image6.png)
- Add the following users
  > email:password
  > <ayushisharma.cb@gmail.com> : 123456.cb
  > <ishanjoshi.cb@gmail.com> : 123456.cb
  > <pandeychulbul.cb@gmail.com> : 123456.cb
  > ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image12.png)
- Copy the firebase config under web app in Project Setting
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image15.png)
  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image10.png)

Now we need to add the UIDs created to the DummyBankDataset.Customer table.

- [Execute the following query](https://cloud.google.com/bigquery/docs/running-queries#console) for each user
  > UPDATE \`{YOUR-PROJECT-ID}.DummyBankDataset.Customer` SET firebase_uid = {USER-FIREBASE-UID} WHERE First_Name = {USER-FIRST-NAME}
  > #if user email id is <ayushisharma.cb@gmail.com> then First_Name is Ayushi

## Deploy Website

Create a `.env` file under `files/CymbalBankWebDeployed` with the following variables

> PROJECT_ID={YOUR-PROJECT-ID}
>
> DF_AGENT_ID={DF-AGENT-ID} #use the agent id copied when configuring dialogflow
>
> #copy the following urls from output_urls.txt file
> CREDIT_CARD_IMAGEN_URL={credit-card-imagen_url}
> RAG_QA_CHAIN_URL_TRANSLATE={translate_url}
> USER_LOGIN_URL={user-login_url}
>
> #firebase config  
> API_KEY={apiKey}
> AUTH_DOMAIN={authDomain}
> STORAGE_BUCKET={storageBucket}
> MESSAGING_SENDER_ID={messagingSenderId}
> APP_ID={appId}
> MEASUREMENT_ID="" #this can be empty

In the CloudShell command line, run `make deploy_website`

## Initialize Search and Train BQML models

- Download and upload the `files/init_bqml_and_vector_search.ipynb` to Colab Enterprise in Vertex AI

- Create and Connect to a Runtime.

- Execute the code cell with the pip commands and restart the session.

- Execute the remaining cells.
  **Note: Replace the website urls in `load_website_content()` function with the urls of the website that you deployed in the previous step. Include all pages you want to be searchable.**
