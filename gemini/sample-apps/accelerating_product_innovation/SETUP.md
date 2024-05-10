# Setup Steps

The solution supports both local execution and deployment to Cloud Run environments.

## Running Locally

1. **Clone Repository**: Clone the repository containing the solution's code to your local machine.
2. **Install Dependencies**: Navigate to the project directory and install dependencies from requirements.txt using pip.
3. **Set Environment Variables**: Create a `.env` file in the project directory and populate it with necessary environment variables:

   ```plaintext
   PROJECT_ID=<Your_Google_Cloud_Project_ID>
   LOCATION=<Desired_Location>
   REGION=<Desired_Google_Cloud_Project_Region>
   YOUR_EMAIL=<Your_Email_Address_Associated_With_Google_Cloud_Project>
   PROJECT_NUMBER=<Your_Google_Cloud_Project_Number>
   ```

4. **Run the Application**: Execute the following command to run the application locally:

   ```bash
   python -m streamlit run app/Home.py
   ```

5. **Access the Application**: Once the application is running locally, access it through a web browser using the specified local host address and port.

## Deployment Steps

Follow the below steps to deploy the solution to Cloud Run environment.

### Google Cloud Storage Setup

1. **Create Bucket**: Manually create GCS bucket 'product_innovation_bucket' using either the GCP Console or command-line tools (gsutil). The bucket is necessary for:

   - `document_uploads`: Stores market research, surveys, trend reports, etc.
   - `generated_products`: Stores output images, descriptions, etc.
   - `image_edits`: Stores intermediate/modified images during the regeneration process.

   **Using the GCP Console (Web Interface):**

   - Navigate to the [Google Cloud Storage section](https://console.cloud.google.com/storage/browser) of your GCP console.
   - Click on the "Create Bucket" button.
   - Provide the following details:
     - **Name**: Enter 'product_innovation_bucket' as bucket name.
     - **Location**: Choose a region closest to where your solution will operate for best performance.
     - **Storage Class**: Select the class based on frequency of access and cost considerations.
     - **Advanced Settings**: Adjust encryption, access control, etc., if necessary.
   - Click "Create".

   **Using the 'gsutil' Command-Line Tool:**

   - Ensure that you have the gcloud SDK installed and 'gsutil' configured.
   - Run the following command in your terminal, replacing `<region>` with your desired bucket location:

     ```bash
     gsutil mb -l <region> gs://product_innovation_bucket
     ```

### Environment Setup

1. Ensure that the `configure_resources.sh` script is in the directory containing the solution's code.
2. Create a `.env` file within the same directory and populate it with the same values as mentioned above.
3. Create a `.env` file in the 'cloud_functions' directory and populate it with necessary environment variables as mentioned above.

### Execute the Script

- Open a terminal and navigate to the directory containing the script and `env.txt` file.
- Run the script `configure-resources.sh` using the command:

  ```bash
  sh configure-resources.sh
  ```

- The script will:
  - Parse `.env` to obtain project details.
  - Initialize gcloud and set project configuration.
  - Set up a service account with necessary IAM roles.
  - Deploy Cloud Functions (`imagen-call`, `gemini-call`, `text-embedding`).
  - Capture URLs for deployed Cloud Functions.
  - Deploy the main application to Cloud Run.
  - Ensure that the service account has been created and manually grant the following roles to the created service account `retail-accelerating-prod-i-982@[PROJECT_ID].iam.gserviceaccount.com`:
    - Service account user
    - Cloud Run Admin
    - Cloud Storage Admin
