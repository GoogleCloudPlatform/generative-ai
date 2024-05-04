# Deployment Guide

This deployment guide assumes existence of three users for demonstrating the various features and functionalities. Following are the user specific data which is setup in this guide:

- Login details in Firebase
- Financial data in BigQuery

## Prerequisites

- [Create a Google Cloud project](https://developers.google.com/workspace/guides/create-project) - Preferrable to create a new Google Cloud project to prevent conflicts when using Terraform.

- [Enable billing](https://cloud.google.com/billing/docs/how-to/modify-project)

- [Create an API key for Maps API](https://developers.google.com/maps/documentation/embed/get-api-key#console)

## Deploy Google Cloud Resources through Terraform

1. Open Cloud Shell in the created Google Cloud Project.
  **Note: User should have Owner/Editor permissions on the project.**

2. Clone this repository

3. Add variables values in `variables.tfvars` file.

   ```text
   project = "{YOUR-PROJECT-ID}"\
   user_email = "{YOUR-EMAIL-ID}" #should be the owner/editor of the project\
   maps_api_key = "{YOUR-MAPS-API-KEY}"
   ```

4. In the Cloud Shell command line, run `make deploy`. This command will create GCS buckets, BigQuery Datasets and Tables, and Cloud Functions.

## Configure DialogFlow CX

[Open Dialogflow CX](https://dialogflow.cloud.google.com/cx/projects) and create a custom agent.

- Choose build your own

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image16.png)

- Click on View all agents and choose restore for the agent you just created.

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image18.png)

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image19.png)

- Upload the file `exported_agent_cymbuddy.blob`

- Copy the agent id after enabling unauthenticated API

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image3.png)

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image11.png)

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image13.png)

Now execute `CymBuddy.ipynb` to update the webhook URIs to the URIs of the Cloud functions deployed in [Deploy Google Cloud Resources through Terraform](#deploy-google-cloud-resources-through-terraform)

## Configure Firebase

Open the [Firebase console](https://console.firebase.google.com/). A firebase project would be present with the same project name as the Google Cloud project created.

- Open the Authentication page.

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image1.png)

- Choose Email/Password as the sign-in method

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image17.png)

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image6.png)

- Add the following users

  ```text
  EMAIL:PASSWORD

  ayushisharma.cb@gmail.com  : 123456.cb
  ishanjoshi.cb@gmail.com    : 123456.cb
  pandeychulbul.cb@gmail.com : 123456.cb
  ```

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image12.png)

- Copy the firebase config under web app in Project Setting

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image15.png)

  ![df init](https://storage.googleapis.com/github-repo/generative-ai/sample-apps/customer-search/images/image10.png)

Now we need to add the UIDs created to the DummyBankDataset.Customer table, which is created in BigQuery by [Deploy Google Cloud Resources through Terraform](#deploy-google-cloud-resources-through-terraform).

- [Execute the following query](https://cloud.google.com/bigquery/docs/running-queries#console) for each user

  ``` sql
  /*
  Replace USER-FIRST-NAME based on the following data:

  EMAIL:USER-FIRST-NAME

  ayushisharma.cb@gmail.com  : Ayushi
  ishanjoshi.cb@gmail.com    : Ishan
  pandeychulbul.cb@gmail.com : Chulbul

  */
  UPDATE `{YOUR-PROJECT-ID}.DummyBankDataset.Customer` SET firebase_uid = {USER-FIREBASE-UID} WHERE First_Name = {USER-FIRST-NAME}
  ```

## Deploy Website

Add the variable values in `.env` file under `CymbalBankWebDeployed` using the following:

- output_urls.txt file generated after [Deploy Google Cloud Resources through Terraform](#deploy-google-cloud-resources-through-terraform) completes
- DialogFlow CX Agent ID copied in [Configure DialogFlow CX](#configure-dialogflow-cx)
- Firebase web app configuration copied in [Configure Firebase](#configure-firebase)

In the Cloud Shell command line, run `make deploy_website`

## Initialize Search and Train BQML models

- Run `init_bqml_and_vector_search.ipynb`

  **Note: Replace the website url in `load_website_content()` function with the url of the website that you deployed in [Deploy Website](#deploy-website)**
  