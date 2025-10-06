# Welcome to the SQL Talk app tutorial

## Overview

This app demonstrates the power of Gemini's function calling capabilities,
enabling users to query and understand their BigQuery databases using natural
language.

### Tutorial

You can follow the steps in this tutorial to run your own version of the SQL
Talk app and make changes to the live app using the Cloud Shell Editor in your
own Google Cloud project.

### Ready?

Let's get started!

## Configuration

### Configure your project

To configure your Google Cloud project to use with this sample app, run the
following command and replace `YOUR_PROJECT_ID` with your own Google Cloud
project ID.:

```bash
gcloud config set project YOUR_PROJECT_ID
```

You can locate your project ID by visiting the
[Dashboard in the Google Cloud Console](https://console.cloud.google.com/home/dashboard).

## Setup

### Running the app

To set up your Cloud Shell environment and start the sample app, run the
following command:

```bash
bash setup.sh
```

This script will:

- Enable the Vertex AI and BigQuery APIs
- Install Python and packages
- Start the SQL Talk app

### App is ready

Once the app is running, you'll see output in the terminal window similar to the
following:

```markdown
You can now view your Streamlit app in your browser.

Network URL: http://10.88.0.3:8080
External URL: http://34.69.5.212:8080
```

### Access the app

In the Cloud Shell Editor toolbar, click the `Web Preview` icon, then select the
option to `Preview on port 8080`. You should see a running version of the app
and interact with it as usual.

## Modify the app

### Testing changes

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

### Extending the app

Consider adding and modifying the available functions to perform:

- Data visualization: Create charts/graphs to summarize the findings
- Other database integrations: Support for PostgreSQL, MySQL, etc.
- APIs: Connect to weather APIs, translation services, and more.

## Conclusion

Congratulations! You've successfully ran and edited the SQL Talk app.

### Cleaning up

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

### Additional resources

You can learn more about function calling in Gemini with these guides and resources:

- [Documentation on function calling in Gemini](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling)
- [Codelab on How to Interact with APIs Using Function Calling in Gemini](https://codelabs.developers.google.com/codelabs/gemini-function-calling)
- [Sample notebook for Function Calling with the Gemini API](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb)
