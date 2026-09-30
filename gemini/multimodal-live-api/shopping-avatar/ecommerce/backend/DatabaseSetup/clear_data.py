# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import os
import sys

# Resolve parent directory path to import the local modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import logging
from google.cloud import spanner
import json
import urllib.request
import urllib.parse
from auth import AuthService
from config import settings

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SpannerClear")

def clear_gcs_bucket(bucket_name: str, prefix: str = "products/"):
    try:
        auth_svc = AuthService()
        token = auth_svc.get_token()
    except Exception as e:
        logger.error(f"Failed to fetch GCS auth token: {e}")
        return

    list_url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o?prefix={urllib.parse.quote(prefix)}"
    headers = {"Authorization": f"Bearer {token}"}
    req = urllib.request.Request(list_url, headers=headers, method="GET")
    
    try:
        logger.info(f"Listing objects in GCS bucket '{bucket_name}' under prefix '{prefix}'...")
        with urllib.request.urlopen(req) as res:
            data = json.loads(res.read().decode("utf-8"))
            items = data.get("items", [])
            
        if not items:
            logger.info(f"No objects found in GCS bucket '{bucket_name}' with prefix '{prefix}'.")
            return
            
        logger.info(f"Deleting {len(items)} objects from GCS bucket '{bucket_name}'...")
        for item in items:
            name = item["name"]
            encoded_name = urllib.parse.quote(name, safe="")
            delete_url = f"https://storage.googleapis.com/storage/v1/b/{bucket_name}/o/{encoded_name}"
            del_req = urllib.request.Request(delete_url, headers=headers, method="DELETE")
            try:
                with urllib.request.urlopen(del_req) as del_res:
                    logger.info(f"Deleted blob: gs://{bucket_name}/{name}")
            except Exception as del_err:
                logger.error(f"Failed to delete blob '{name}': {del_err}")
                
    except Exception as e:
        logger.error(f"Failed to list/clear GCS bucket '{bucket_name}': {e}")

def main():
    project_id = settings.google_cloud_project or settings.vertex_project_id
    instance_id = settings.spanner_instance
    database_id = settings.spanner_database
    
    if not project_id:
        logger.error("GCP Project ID must be specified in environment or .env file.")
        return

    logger.info(f"Connecting to Spanner database '{database_id}' on instance '{instance_id}'...")
    spanner_client = spanner.Client(project=project_id)
    instance = spanner_client.instance(instance_id)
    database = instance.database(database_id)
    
    if not database.exists():
        logger.error(f"Database '{database_id}' does not exist.")
        return

    # Delete order_items/reviews first, then orders, customers, and products to respect interleaving cascade
    tables = ["shopping_carts", "order_items", "orders", "reviews", "customers", "products"]

    def delete_all_data(transaction):
        for table in tables:
            logger.info(f"Clearing table '{table}'...")
            dml = f"DELETE FROM {table} WHERE true"
            try:
                row_count = transaction.execute_update(dml)
                logger.info(f"Cleared {row_count} rows from '{table}'.")
            except Exception as e:
                logger.error(f"Failed to clear table '{table}': {e}")

    try:
        database.run_in_transaction(delete_all_data)
        logger.info("Database tables cleared successfully.")
        
        # Clear GCS bucket images as well
        bucket_name = settings.gcs_bucket_name
        if bucket_name:
            clear_gcs_bucket(bucket_name)
        else:
            logger.warning("GCS_BUCKET_NAME not specified. Skipping bucket clear.")
    except Exception as e:
        logger.error(f"Transaction failed: {e}")

if __name__ == "__main__":
    main()
