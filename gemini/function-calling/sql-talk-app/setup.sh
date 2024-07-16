#!/usr/bin/env bash

# Enable Vertex AI and BigQuery
gcloud services enable aiplatform.googleapis.com
gcloud services enable bigquery.googleapis.com
gcloud services enable bigquerydatatransfer.googleapis.com

# Copy public dataset
bq mk --force=true --dataset thelook_ecommerce
bq mk \
  --transfer_config \
  --data_source=cross_region_copy \
  --target_dataset=thelook_ecommerce \
  --display_name='SQL Talk Sample Data' \
  --schedule_end_time="$(date -u -d '5 mins' +%Y-%m-%dT%H:%M:%SZ)" \
  --params='{
      "source_project_id":"bigquery-public-data",
      "source_dataset_id":"thelook_ecommerce",
      "overwrite_destination_table":"true"
      }'

# Install Python
export PYTHON_PREFIX=~/miniforge
curl -Lo ~/miniforge.sh https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh
bash ~/miniforge.sh -fbp ${PYTHON_PREFIX}
rm -rf ~/miniforge.sh

# Install packages
${PYTHON_PREFIX}/bin/pip install -r requirements.txt

# Run app
${PYTHON_PREFIX}/bin/streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false --server.port 8080
