# Finvest Spanner Demo App

**Authors:** [Anirban Bagchi](https://github.com/anirbanbagchi1979) and [Derek Downey](https://github.com/dtest)

<img align="right" style="padding-left: 10px;" src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/Finvest-white.jpg" width="35%" alt="Finvest Logo"> 

Consider a modern financial services company where I am a financial advisor. Finding the right financial investments can be challenging because of the complex nature of investments from structured data such as expense ratios, fund returns, to complex data such as asset holdings, their industry sectors, and more unstructured data, such as investment philosophy and client’s investment goals. Let me show you how Spanner makes this process easy by combining these diverse data structures into a single multi-model platform.

The client wants me to find assets for funds in North America and Europe that invest in derivatives. I select North America and Europe and put in derivatives as my search term. Spanner runs a relational and text search to return a list of funds.

Next, the client wants to narrow this list to specific fund managers. I don’t know the exact name, so I put in Liz Peters, and Spanner performs a fuzzy match(Full Text Search - Substring Match) of the name Liz Peters to find funds managed by Elizabeth Peterson.

Among these funds, the client wants to choose from socially responsible funds. Next, I check the box for vector search, and now I can see ESG funds because Spanner performed a KNN vector search to match the search term “socially responsible” with “environmental, social and governance”.

Finally, before I recommend a fund, I also want to check the exposure to a particular sector. This can be complex because funds can invest in other funds, called fund of funds which makes it hard to compute this. Spanner performs a graph search using this asset knowledge graph. By traversing the funds and its holdings which could also be funds and their holdings, Spanner can compute the client’s exposure to a particular sector. I can see the funds that have exposure of 20% or more in the technology sector.

With the power of Spanner’s multimodel support, I can run complex workloads on a single database for relational, analytical, text and vector use cases with virtually unlimited scale, five nines of availability—including enterprise security and governance for mission critical workloads.

This demo highlights [Spanner](https://cloud.google.com/spanner),  integration with [Vertex AI LLMs](https://cloud.google.com/model-garden?hl=en) for both embeddings and text completion models. You will learn how Spanner can help with usecases where you run Full Text Search, Approximate Nearest neighbor search and vector similarity search. 

## Tech Stack

The Finvest Spanner demo application was built using:

- [Spanner](https://cloud.google.com/spanner) 
- [Vertex AI](https://cloud.google.com/vertex-ai?hl=en) LLMs ([textembeddings-gecko@003](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/text-embeddings) and [text-bison@002](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/text))
- [App Engine](https://cloud.google.com/appengine)
- [Dataflow](https://cloud.google.com/dataflow?)
- [Streamlit](https://streamlit.io/)


## Deploying the Finvest Spanner Demo Application

1. Login to the [Google Cloud Console](https://console.cloud.google.com/).

1. [Create a new project](https://developers.google.com/maps/documentation/places/web-service/cloud-setup) to host the demo and isolate it from other resources in your account.

1. [Switch](https://cloud.google.com/resource-manager/docs/creating-managing-projects#identifying_projects) to your new project.

1. [Activate Cloud Shell](https://cloud.google.com/shell/docs/using-cloud-shell) and confirm your project by running the following commands. Click **Authorize** if prompted.

   ```bash
   gcloud auth list
   gcloud config list project
   ```

1. Clone this repository and navigate to the project root:



2. Create a Spanner instance
   https://console.cloud.google.com/spanner/instances/new

3. Import the data into the Spanner instance
   https://cloud.google.com/spanner/docs/import#import-database
   3.1 
4. When prompted, enter a password you will remember for the AlloyDB postgres user and the pgAdmin demo user. **Remember these passwords - you will need them later**.

1. Grab some coffee or tea. The script will provision all the necessary back-end resources, which usually takes about 30-35 minutes.

1. When prompted (after about 30 minutes), enter the `configId` for the Vertex AI Agent Builder widget. Retrieve the `configId` by following these steps:

   - Navigate to Vertex AI Agent Builder in the console.
   - **IMPORTANT:** Click to accept terms and activate the API.
   - Click `Apps` in the left hand navigation to view the list of apps.
   - Click into the `search-prospectus` app.
   - Select `Integration` from the left-hand menu.
   - Scroll down until you see the `configId` for the gen-search-widget.
   - Copy just the UUID without the quotes (i.e. `4205ae6a-434e-695e-aee4-58f500bd9000`).
   - Keep this window open. You will need it in the next step.

1. When the build is complete, it will display a URL where you can access the UI. In the same interface where you copied the `configId`, add the domain (without the leading `https://` or trailing slash) as an allowed domain for the widget. Be sure to click `Save`. Example: `genwealth-420u2zdq69-uc.a.run.app`

1. You can now choose to explore the demo environment from the front end or the back end (or both).

   - [Front End Demo Walkthrough](./walkthroughs/frontend-demo-walkthrough.md)
   - [Back End Demo Walkthrough](./walkthroughs/backend-demo-walkthrough.md)

### Troubleshooting



## Architecture

### Database



#### Schema


### Frontend

The frontend application is Angular Material using TypeScript, which is built and statically served from the root `/` by express as well:





## Purpose and Extensibility

The purpose of this repo is to help you provision an isolated demo environment that highlights the Generative AI capabilities of AlloyDB AI and Vertex AI. While the ideas in this repo can be extended for many real-world use cases, the demo code itself is overly permissive and has not been hardened for security or reliability. The sample code in this repo is provided on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, and it should NOT be used for production use cases without doing your own testing and security hardening.

## Clean Up

Be sure to delete the resources you no longer need when you're done with the demo. If you created a new project for the lab as recommended, you can delete the whole project using the command below in your Cloud Shell session (NOT the pgadmin VM).

**DANGER: Be sure to set PROJECT_ID to the correct project, and run this command ONLY if you are SURE there is nothing in the project that you might still need. This command will permanently destroy everything in the project.**

```bash
# Set your project id
PROJECT_ID='YOUR PROJECT ID HERE'
gcloud projects delete ${PROJECT_ID}
```
