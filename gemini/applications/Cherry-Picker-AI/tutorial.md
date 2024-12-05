# CherryPicker.AI 🍒

![Image of the Logo for the CherryPicker.AI Application: Perry the Cherry](https://media.licdn.com/dms/image/v2/D5622AQG9ymz2uaew4g/feedshare-shrink_800/feedshare-shrink_800/0/1730653525795?e=1735776000&v=beta&t=-ZTrGHhoqK1XDOTNJWcDrHHQMuVaOxaSWQIotsr7pBc)

## Overview

This app is a machine learning tool that can analyze images of produce and provide feedback on its quality. It also will generate a personalized advertisements for poorly rated produce based on sponsor grocery stores (based on the type of produce they are looking for).

* Here is a link to a video demo of the application. (Send to Github Generative AI Team to create shareable link)
* This application was originally demo'ed on [November 5th, 2024](https://www.youtube.com/live/MJBqVVkRbNM?si=DdZK_Ry3cCj1p1-T).

The app was built in 24 hours using a variety of technologies like Project IDX, Google Gemini, Python, Flask, ChromaDB, Vertex AI, Vuetify.

### Tutorial

You can follow the steps in this tutorial to run your own version of the CherryPicker.ai app and make changes to the live app using the Cloud Shell Editor in your
own Google Cloud project.

### Ready?

Let's get started!

## Configuration

### Configure your project

To configure your Google Cloud project to use with this sample app, run the
following command and replace `YOUR_PROJECT_ID` with your own Google Cloud
project ID:

```bash
gcloud config set project YOUR_PROJECT_ID
```

You can locate your project ID by visiting the
[Dashboard in the Google Cloud Console](https://console.cloud.google.com/home/dashboard).

## Setup

### Creating your Gemini API Key

Get your Gemini API key by:
- Selecting "Add Gemini API" in the "Project IDX" panel in the sidebar
- Or by visiting [https://g.co/ai/idxGetGeminiKey](https://g.co/ai/idxGetGeminiKey)

### Running the app

!IMPORTANT! During the setup script you will be prompted for a Gemini API key.

To set up your Cloud Shell environment and start the sample app, run the
following command:

```bash
bash setup.sh
```

This script will:

- Enable the Vertex AI API
- Install npm and yarn dependencies
- Install required Python packages
- Starts the CherryPicker.ai app

## App is ready

Once the app is running, you'll see output in the terminal window similar to the
following:

```markdown
 * Serving Flask app 'main'
 * Debug mode: off
WARNING: This is a development server. Do not use it in a production deployment. Use a production WSGI server instead.
 * Running on http://127.0.0.1:8080
```

### Access the app

In the Cloud Shell Editor toolbar, click the `Web Preview` icon, then select the
option to `Preview on port 8080`. You should see a running version of the app
and interact with it as usual.

## [needs edit] Modify the app

### [needs edit] Testing changes

Now that you have the app running, let's make a simple change to the app such as
changing the app title from:

```python
st.title("SQL Talk with BigQuery")
```

to:

```python
st.title("Hello from SQL Talk with BigQuery")
```

Then refresh the web app, and you should see the new title displayed.

### [needs edit] Extending the app

Consider adding and modifying the available functions to perform:

- Data visualization: Create charts/graphs to summarize the findings
- Other database integrations: Support for PostgreSQL, MySQL, etc.
- APIs: Connect to weather APIs, translation services, and more.

## [needs edit] Conclusion

Congratulations! You've successfully ran and edited the SQL Talk app.

### [needs edit] Cleaning up

You can perform the following cleanup to avoid incurring charges to your Google
Cloud account for the resources used in this tutorial:

- Delete the sample dataset in BigQuery
- Delete the data transfer job in BigQuery
- Disable the
  [Vertex AI API](https://console.cloud.google.com/apis/library/aiplatform.googleapis.com)
  and
  [BigQuery API](https://console.cloud.google.com/apis/library/bigquery.googleapis.com)

To avoid unnecessary Google Cloud charges, use the
[Google Cloud console](https://console.cloud.google.com/) to delete your project
if you do not need it.

### [needs edit] Additional resources

You can learn more about function calling in Gemini with these guides and resources:

- [Documentation on function calling in Gemini](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling)
- [Codelab on How to Interact with APIs Using Function Calling in Gemini](https://codelabs.developers.google.com/codelabs/gemini-function-calling)
- [Sample notebook for Function Calling with the Gemini API](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb)