# Generative AI App Builder - Enterprise Search Demo

This demo illustrates how to search through a corpus of unstructrued contract documents using [Generative AI App Builder: Enterprise Search][1].

Additional features include how to search the public Cloud Knowledge Graph using the [Enterprise Knowledge Graph][3] API.

## Architecture

### Google Cloud Products Used

- [Generative AI App Builder: Enterprise Search][1]
- [Cloud Run][2]
- [Enterprise Knowledge Graph][3]

[1]: https://cloud.google.com/generative-ai-app-builder/docs/overview
[2]: https://cloud.google.com/run
[3]: https://cloud.google.com/enterprise-knowledge-graph/docs/overview

## Setup

- Follow steps in [Get started with Enterprise Search](https://cloud.google.com/generative-ai-app-builder/docs/try-enterprise-search) for Unstructured Data
  - Sample Data Sources used in the deployed demo:
    - [Contract Understanding Atticus Dataset (CUAD)](https://www.atticusprojectai.org/cuad)
      - `gs://cloud-samples-data/gen-app-builder/search/CUAD_v1`
    - [Alphabet Earnings Reports](https://abc.xyz/investor/)
      - `gs://cloud-samples-data/gen-app-builder/search/alphabet-investor-pdfs`
  - Copy the `configId` from the `<gen-search-widget>` in the `Integration > Widget` tab in the Cloud Console.
    - ![configId](img/configId.png)

- Follow steps in [Get started with Enterprise Search](https://cloud.google.com/generative-ai-app-builder/docs/try-enterprise-search) for Websites
  - [Google Cloud site](https://cloud.google.com)
    - `https://cloud.google.com`

- Deploy using Cloud Run

### Dependencies

1. [Install Python](https://www.python.org/downloads/)
2. Install the [Google Cloud SDK](https://cloud.google.com/sdk/docs/install)
3. Install the prerequisites:
   - `pip install -r requirements.txt`
4. Run `gcloud init`, create a new project, and
   [enable billing](https://cloud.google.com/billing/docs/how-to/modify-project#enable_billing_for_a_project)
5. Enable the Generative AI App Builder API:
   - `gcloud services enable discoveryengine.googleapis.com`
6. Enable the Enterprise Knowledge Graph API:
   - `gcloud services enable enterpriseknowledgegraph.googleapis.com`
7. Setup application default authentication, run:
   - `gcloud auth application-default login`

### Demo Deployment

1. Update the `consts.py` file with your own `PROJECT_ID` and `LOCATION`.
   - Add the `configId` for your own Contract Search Engine to `CONTRACT_SEARCH_CONFIG_ID`
   - Add the `configId` for your own Finance Search Engine to `FINANCE_SEARCH_CONFIG_ID`
   - Add the `datastore_id` for your Website Search Engine to `WEBSITE_SEARCH_ENGINE_ID`

1. Deploy the Cloud Run app in your project.

   - `gcloud run deploy genappbuilder-demo --source .`

1. Visit the deployed web page
   - Example: [`https://genappbuilder-demo-lnppzg3rxa-uc.a.run.app`](https://genappbuilder-demo-lnppzg3rxa-uc.a.run.app)

## Usage

Try example queries with each search engine:

- [Contract][contract] - `What is the SLA?`
- [Finance][finance] - `What was Google's revenue in 2021?`
- [Web Search - Custom UI][websearch] - `Document AI`
- [Enterprise Knowledge Graph][ekg] - `Google`

---

> Copyright 2023 Google LLC
> Author: Holt Skinner @holtskinner

[contract]: https://genappbuilder-demo-lnppzg3rxa-uc.a.run.app/
[finance]: https://genappbuilder-demo-lnppzg3rxa-uc.a.run.app/finance
[websearch]: https://genappbuilder-demo-lnppzg3rxa-uc.a.run.app/search
[ekg]: https://genappbuilder-demo-lnppzg3rxa-uc.a.run.app/ekg
