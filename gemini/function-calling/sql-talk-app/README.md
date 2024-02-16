# SQL Talk: Natural Language to BigQuery with Gemini's Function Calling

## Overview

This app demonstrates the power of
[Gemini's function calling](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling)
capabilities, enabling users to query and understand their
[BigQuery](https://cloud.google.com/bigquery) databases using natural language.
Forget complex SQL syntax – interact with your data conversationally.

Function calling in Gemini lets developers create a description of a function in
their code, then pass that description to a language model in a request. The
response from the model includes the name of a function that matches the
description and the arguments to call it with.

Try using the demo app now! [https://sql-talk-r5gdynozbq-uc.a.run.app/](https://sql-talk-r5gdynozbq-uc.a.run.app/)

![SQL Talk Demo App](sql-talk.png)

## Prerequisites

- A Google Cloud project with billing enabled
- A BigQuery dataset (we used the
  [`thelook_ecommerce` public dataset](https://console.cloud.google.com/marketplace/product/bigquery-public-data/thelook-ecommerce))
- APIs for Vertex AI and BigQuery enabled
- Familiarity with Python and SQL concepts

## Run the app locally

1. Clone this repository
2. `cd` into the `gemini/function-calling/sql-talk-app` directory
3. Install dependencies with `pip install -r requirements.txt`
4. Run the app with `streamlit run app.py`
5. Navigate to the app in your browser at a URL similar to `http://localhost:8501`

## Configuring a service account

When deploying this app to Cloud Run, it is recommended that you [create a
service account](https://cloud.google.com/iam/docs/service-accounts-create) to
attach the following roles to, which are the permissions required for the app to
read data from BigQuery, run BigQuery jobs, and use resources in Vertex AI:

- [BigQuery Data Viewer](https://cloud.google.com/bigquery/docs/access-control#bigquery.dataViewer) (`roles/bigquery.dataViewer`)
- [BigQuery Job User](https://cloud.google.com/bigquery/docs/access-control#bigquery.jobUser) (`roles/bigquery.jobUser`)
- [Vertex AI User](https://cloud.google.com/vertex-ai/docs/general/access-control#aiplatform.user) (`roles/aiplatform.user`)

## Deploy the app to Cloud Run

To deploy this app to
[Cloud Run](https://cloud.google.com/run/docs/deploying-source-code), run the
following command to have the app built with Cloud Build and deployed to Cloud
Run, replacing the `service-account` and `project` values with your own values,
similar to:

```shell
gcloud run deploy sql-talk --allow-unauthenticated --region us-central1 --service-account sql-talk@koverholt-devrel-355716.iam.gserviceaccount.com --source .
```

## Access the deployed app

After deploying your app, you should can visit the app URL, which should be
similar to:

[https://sql-talk-r5gdynozbq-uc.a.run.app/](https://sql-talk-r5gdynozbq-uc.a.run.app/)

Congratulations, you've successfully deployed the SQL Talk demo app!

## Extending the app

Try rewrite the function definitions and application code to try new things!
Consider adding tools to perform:

- Data visualization: Create charts/graphs to summarize the findings
- Other database integrations: Support for PostgreSQL, MySQL, etc.
- APIs: Connect to weather APIs, translation services, and more.

## Additional resources

You can learn more about function calling in Gemini with these guides and
resources:

- [Documentation on function calling in Gemini](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/function-calling)
- [Codelab on How to Interact with APIs Using Function Calling in Gemini](https://codelabs.developers.google.com/codelabs/gemini-function-calling)
- [Sample notebook for Function Calling with the Gemini API](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/function-calling/intro_function_calling.ipynb)
