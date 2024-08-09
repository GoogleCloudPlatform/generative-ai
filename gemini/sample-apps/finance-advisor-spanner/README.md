# Finvest Spanner Demo App

**Authors:** [Anirban Bagchi](https://github.com/anirbanbagchi1979) and [Derek Downey](https://github.com/dtest)

<img align="right" style="padding-left: 10px;" src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/Finvest-white.jpg" width="35%" alt="Finvest Logo">

Consider a modern financial services company where I am a financial advisor. Finding the right financial investments can be challenging because of the complex nature of investments from structured data such as expense ratios, fund returns, to complex data such as asset holdings, their industry sectors, and more unstructured data, such as investment philosophy and client's investment goals. Let me show you how Spanner makes this process easy by combining these diverse data structures into a single multi-model platform.

The client wants me to find assets for funds in North America and Europe that invest in derivatives. I select North America and Europe and put in derivatives as my search term. Spanner runs a relational and text search to return a list of funds.

Next, the client wants to narrow this list to specific fund managers. I don't know the exact name, so I put in Liz Peters, and Spanner performs a fuzzy match(Full Text Search - Substring Match) of the name Liz Peters to find funds managed by Elizabeth Peterson.

Among these funds, the client wants to choose from socially responsible funds. Next, I check the box for vector search, and now I can see ESG funds because Spanner performed a KNN vector search to match the search term "socially responsible" with "environmental, social and governance".

Finally, before I recommend a fund, I also want to check the exposure to a particular sector. This can be complex because funds can invest in other funds, called fund of funds which makes it hard to compute this. Spanner performs a graph search using this asset knowledge graph. By traversing the funds and its holdings which could also be funds and their holdings, Spanner can compute the client's exposure to a particular sector. I can see the funds that have exposure of 20% or more in the technology sector.

With the power of Spanner's multimodel support, I can run complex workloads on a single database for relational, analytical, text and vector use cases with virtually unlimited scale, five nines of availability—including enterprise security and governance for mission critical workloads.

This demo highlights [Spanner](https://cloud.google.com/spanner), integration with [Vertex AI LLMs](https://cloud.google.com/model-garden?hl=en) for both embeddings and text completion models. You will learn how Spanner can help with use cases where you run Full Text Search, Approximate Nearest Neighbor search and vector similarity search.

## Tech Stack

The Finvest Spanner demo application was built using:

- [Spanner](https://cloud.google.com/spanner)
- [Vertex AI](https://cloud.google.com/vertex-ai?hl=en) LLMs ([textembeddings-gecko@004](https://cloud.google.com/vertex-ai/generative-ai/docs/model-reference/text-embeddings) )
- [Cloud Run](https://cloud.google.com/run)
- [Dataflow](https://cloud.google.com/dataflow?)
- [Streamlit](https://streamlit.io/)

## Deploying the Finvest Spanner Demo Application

1. Login to the [Google Cloud Console](https://console.cloud.google.com/).

2. [Create a new project](https://developers.google.com/maps/documentation/places/web-service/cloud-setup) to host the demo and isolate it from other resources in your account.

3. [Switch](https://cloud.google.com/resource-manager/docs/creating-managing-projects#identifying_projects) to your new project.

4. [Activate Cloud Shell](https://cloud.google.com/shell/docs/using-cloud-shell) and confirm your project by running the follow4ng commands. Click **Authorize** if prompted.

   ```bash
   gcloud auth list
   gcloud config list project
   ```

5. Clone this repository and navigate to the project root:

   ```bash
   cd
   git clone https://github.com/GoogleCloudPlatform/generative-ai.git
   cd generative-ai/gemini/sample-apps/finance-advisor-spanner/
   ```

6. Create a Spanner instance
   <https://console.cloud.google.com/spanner/instances/new>

   > Note the instance Name

7. Import the data into the Spanner instance
   <https://cloud.google.com/spanner/docs/import#import-database>
   The bucket which has the Spanner export is in this public GCS Bucket

   `https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/spanner-fts-mf-data-export/`

   > Note the Database Name

   The import process will run and import the database into a new Spanner database.

8. Run Additional DDL statements for the database to have all the necessary components.
   The DDL statements are in [Schema-Operations.sql](./Schema-Operations.sql) file in this directory.

   Change the endpoint as per your project and the spanner instance location

   ```sql
   ALTER MODEL EmbeddingsModel SET OPTIONS (
      endpoint = '//aiplatform.googleapis.com/projects/'YOUR PROJECT ID HERE'/locations/'YOUR SPANNER INSTANCE LOCATION HERE'/publishers/google/models/text-embedding-003'
      )
      ;
   ```

   Next run the rest of DDL statements without any change

9. In Cloud Shell:

   Open `.env` file in the same directory using vi or other Editor

   Edit the following fields with the instance name from Step 6 and database name from Step 7

   ```bash
   instance_id='YOUR INSTANCE ID'
   database_id='YOUR DATABASE ID'
   ```

10. Now Build & Deploy the application:

    Build:

    ```bash
    gcloud builds submit --tag gcr.io/'YOUR PROJECT ID HERE'/finance-advisor-app
    ```

    Deploy:

    ```bash
    gcloud run deploy finance-advisor-app --image gcr.io/'YOUR PROJECT ID HERE'/finance-advisor-app --platform managed    --region 'YOUR SPANNER REGION' --allow-unauthenticated
    ```

### Troubleshooting

### Frontend

The frontend application is Streamlit running on CloudRun

## Purpose and Extensibility

The purpose of this repository is to help you provision an isolated demo environment that highlights the Full Text Search, Semantic Search and Graph capabilities of Spanner. While the ideas in this repository can be extended for many real-world use cases, the demo code itself is overly permissive and has not been hardened for security or reliability. The sample code in this repository is provided on an "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, and it should NOT be used for production use cases without doing your own testing and security hardening.

## Clean Up

Be sure to delete the resources you no longer need when you're done with the demo. If you created a new project for the lab as recommended, you can delete the whole project using the command below in your Cloud Shell session (NOT the pgadmin VM).

**DANGER: Be sure to set PROJECT_ID to the correct project, and run this command ONLY if you are SURE there is nothing in the project that you might still need. This command will permanently destroy everything in the project.**

```bash
# Set your project id
PROJECT_ID='YOUR PROJECT ID HERE'
gcloud projects delete ${PROJECT_ID}
```
