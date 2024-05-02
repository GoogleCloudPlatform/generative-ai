# Fashion Trends Prediction using Streamlit Framework and Vertex AI tools

| | | |
|-|-|-|
|Author(s) | [Devika Mittal](https://github.com/devikamittal19) | [Shubham Saurav](https://github.com/shubhgoogle) |

This Cloud Run application helps fashion retailers to stay ahead of the fashion curve and predict upcoming trends by analyzing fashion trends that are popular on Instagram among celebrities and influencers, because these trends are likely to become popular in the mainstream soon.

It uses the [Streamlit Framework](https://streamlit.io/) and Generative AI models from Vertex AI to predict fashion trends.

## Application Screenshots

Choose a file if you want to run on your own JSON data or skip this option if you want to run on the default data.
Choose the country and category of outfit for which you need to get the predicted fashion trends.

<img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app_screenshots/image1.png" width="70%" alt="Choosing fields">

Click on any of the predicted item to see a generated image with some similar outfits.

<img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app_screenshots/image2.png" width="70%" alt="example trend">
<img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app_screenshots/image3.png" width="70%" alt="another example">

Go to the "Overall trends across attributes" tab to see the trends in the order of their predicted popularity across different features of the outfit category.

<img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app_screenshots/image4.png" width="70%" alt="overall trends across attributes">

For the selected country: 'India', one gets relevant fashion news articles.

<img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app_screenshots/image5.png" width="70%" alt="relevant articles when India is chosen as country">

Finally, there's a chatbot that has the predicted fashion trends data as context and can be used to answer queries related to that. It can also be used to generate and edit images of different outfits.

<img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app_screenshots/image6.png" width="70%" alt="chatbot">

## Technical Implementation

<img src="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/fashion-trends-prediction/app_screenshots/image7.png" width="70%" alt="flow diagram">

### Broad Implementation Steps

1. **Data Extraction and Processing** -
    * **From social media** - For each country in list, the latest 20 posts from top 50 influencers and celebrities’ Instagram profiles are scraped using Instagram Graph API. Using VertexAI’s Gemini multimodal, attributes are generated for each image.
    * **From news sites** - Fashion news articles are scraped from Vogue India site. Using VertexAI language model, the articles are summarized.

    This data consisting of image attributes for the Instagram images and articles are stored.

2. **Prediction** -
    * The user is asked to choose the country and the category of clothes (eg. pants, jackets, etc.).
    * Using UMAP and HDBScan, all the outfits for that country and category are clustered. Representative items from the top (biggest size) clusters are returned. These are the trending items as they are worn by many influencers and celebrities.

3. **Image Generation** - For the returned outfit names, images are generated using VertexAI Imagen.

4. **Displaying supporting articles** - For explainability, news articles related to the results are displayed to the user. This is done using hybrid search. An ensemble retriever made of keyword-based BM25 and sentence transformer is used to retrieve relevant articles.

5. **Chatbot** - Vertex AI's language model is given the relevant content from the JSON file as context and used to answer user queries. It is integrated with Imagen so user can generate and edit images in the chat interface itself.

6. **Deployment** - The UI is designed using Streamlit and the application is deployed using cloud run.

## Run the Application locally (on Cloud Shell)

> NOTE: **Before you move forward, ensure that you have followed the instructions in [SETUP.md](../SETUP.md).**
> Additionally, ensure that you have cloned this repository and you are currently in the `fashion-trends-prediction` folder. This should be your active working directory for the rest of the commands.

To run the Streamlit Application locally (on cloud shell), we need to perform the following steps:

1. Setup the Python virtual environment and install the dependencies:

   In Cloud Shell, execute the following commands:

   ```bash
   python3 -m venv fashion-trends-env
   source fashion-trends-env/bin/activate
   pip install -r requirements.txt
   ```

2. Your application requires access to two variables:

   * `PROJECT_ID` : This the Google Cloud project ID.
   * `LOCATION` : This is the region in which you are deploying your Cloud Run app. For e.g. us-central1.

   These variables are needed since the Vertex AI initialization needs the Google Cloud project ID and the region - `vertexai.init(project=PROJECT_ID, location=LOCATION)`.

   In the app/config.py file, set PROJECT_ID and LOCATION.

3. To run the application locally, execute the following command:

   In Cloud Shell, execute the following command:

   ```bash
   cd app
   streamlit run Home.py \
     --browser.serverAddress=localhost \
     --server.enableCORS=false \
     --server.enableXsrfProtection=false \
     --server.port 8501
   ```

The application will startup and you will be provided a URL to the application. Use Cloud Shell's [web preview](https://cloud.google.com/shell/docs/using-web-preview) function to launch the preview page. You may also visit that in the browser to view the application.

## Build and Deploy the Application to Cloud Run

> NOTE: **Before you move forward, ensure that you have followed the instructions in [SETUP.md](../SETUP.md).**
> Additionally, ensure that you have cloned this repository and you are currently in the `fashion-trends-prediction` folder. This should be your active working directory for the rest of the commands.

To deploy the Streamlit Application in [Cloud Run](https://cloud.google.com/run/docs/quickstarts/deploy-container), we need to perform the following steps:

1. Your Cloud Run app requires access to two environment variables:

   * `PROJECT_ID` : This the Google Cloud project ID.
   * `LOCATION` : This is the region in which you are deploying your Cloud Run app. For e.g. us-central1.

   These variables are needed since the Vertex AI initialization needs the Google Cloud project ID and the region -
   `vertexai.init(project=PROJECT_ID, location=LOCATION)`

   In Cloud Shell, execute the following commands:

   ```bash
   export PROJECT_ID='<Your GCP Project Id>'  # Change this
   export LOCATION='us-central1'             # If you change this, make sure the region is supported.
   ```

2. Set the mode to 1 in the app/config.py file.

3. Now you can build the Docker image for the application and push it to Artifact Registry. To do this, you will need one environment variable set that will point to the Artifact Registry name. Included in the script below is a command that will create this Artifact Registry repository for you.

   In Cloud Shell, execute the following commands:

   ```bash
   export AR_REPO='<REPLACE_WITH_YOUR_AR_REPO_NAME>'  # Change this
   export SERVICE_NAME='fashion-trends-prediction' # This is the name of our Application and Cloud Run service. Change it if you'd like.

   #make sure you are in the active directory for 'fashion-trends-prediction'
   gcloud artifacts repositories create "$AR_REPO" --location="$LOCATION" --repository-format=Docker
   gcloud auth configure-docker "$LOCATION-docker.pkg.dev"
   gcloud builds submit --tag "$LOCATION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME"
   ```

4. The final step is to deploy the service in Cloud Run with the image that we had built and had pushed to the Artifact Registry in the previous step:

   In Cloud Shell, execute the following command:

   ```bash
   gcloud run deploy "$SERVICE_NAME" \
     --port=8501 \
     --image="$LOCATION-docker.pkg.dev/$PROJECT_ID/$AR_REPO/$SERVICE_NAME" \
     --allow-unauthenticated \
     --region=$LOCATION \
     --platform=managed  \
     --project=$PROJECT_ID \
     --set-env-vars=GCP_PROJECT=$PROJECT_ID,GCP_REGION=$LOCATION
   ```

On successful deployment, you will be provided a URL to the Cloud Run service. You can visit that in the browser to view the Cloud Run application that you just deployed. Choose the functionality that you would like to check out and the application will prompt the Vertex AI Gemini API and display the responses.

### How to create and run on your own data

The current data is created by scraping posts from Instagram influencers and celebrities. It is stored in Google Cloud Storage and the exact path is specified in the app/config.py file as `config['Data']['current_data']`. The code uses the file stored in this location to generate trend predictions.

If you want to create your own data (a different source from Instagram or a different set of accounts and posts), then replace the file at the location specified in `config['Data']['current_data']` or upload your file on the UI itself.

The file app/data_prep/create_new_data.py can be used to generate the new data file in the required format. The data file is created locally and again either upload it to gcs and update the path in `config['Data']['current_data']` or upload this file on the UI itself. Add your Instagram account username and password in the app/config.py file before starting to scrape Instagram.

Required JSON format -

```json
{

    "finaldata": {
        "country1": {
            "category1": ["outfit1", "outfit2", "outfit3", ...],
            "category2": [],
            ...
        },
        "country2": {},
        ...
    },

    "top_categories": {
        "country1": ["category1", "category2", ...],
        "country2": [],
        ...
    },

    "articles": [["article_link", "article_summary"],
        ...
    ]
}
```

To extend this, one can use Cloud Scheduler to do the scraping periodically (since we want the data to not be stale for this usecase) and store the results in a Cloud Storage bucket from where they will be read to predict upcoming trends.
