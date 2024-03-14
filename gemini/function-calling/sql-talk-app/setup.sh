#!/usr/bin/env bash

# Enable Vertex AI and BigQuery
gcloud services enable aiplatform.googleapis.com
gcloud services enable bigquery.googleapis.com

# Install Python
export PYTHON_PREFIX=~/miniconda
curl -LO https://repo.anaconda.com/miniconda/Miniconda3-py311_24.1.2-0-Linux-x86_64.sh
bash Miniconda3-py311_24.1.2-0-Linux-x86_64.sh -fbp ${PYTHON_PREFIX}

# Install packages
${PYTHON_PREFIX}/bin/pip install -r requirements.txt

# Run app
${PYTHON_PREFIX}/bin/streamlit run app.py --server.enableCORS=false --server.enableXsrfProtection=false --server.port 8080
