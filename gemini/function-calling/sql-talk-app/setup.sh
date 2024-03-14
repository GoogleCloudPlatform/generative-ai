#!/usr/bin/env bash

# Enable Vertex AI and BigQuery
gcloud services enable aiplatform.googleapis.com
gcloud services enable bigquery.googleapis.com

# Copy public dataset
bq mk --dataset thelook_ecommerce
bq mk \
  --transfer_config \
  --data_source=cross_region_copy \
  --target_dataset=thelook_ecommerce \
  --display_name='SQL Talk Sample Data' \
  --schedule_end_time=$(date -u -d '5 mins' +%Y-%m-%dT%H:%M:%SZ) \
  --params='{
      "source_project_id":"bigquery-public-data",
      "source_dataset_id":"thelook_ecommerce",
      "overwrite_destination_table":"true"
      }'

# Install Python
export PYTHON_PREFIX=~/miniconda
curl -LO https://repo.anaconda.com/miniconda/Miniconda3-py311_24.1.2-0-Linux-x86_64.sh
bash Miniconda3-py311_24.1.2-0-Linux-x86_64.sh -fbp ${PYTHON_PREFIX}

# Install packages
${PYTHON_PREFIX}/bin/pip install -r requirements.txt

# Run app
${PYTHON_PREFIX}/bin/streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false --server.port 8080
