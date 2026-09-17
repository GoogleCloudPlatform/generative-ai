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
import logging
import argparse
from google.cloud import spanner
from google.api_core.exceptions import AlreadyExists
from google.cloud.spanner_admin_instance_v1 import Instance as InstancePB
from google.cloud.spanner_v1._helpers import _metadata_with_prefix

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("SpannerSetup")

# Resolve parent directory path to import the Settings config module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import settings

def main():
    parser = argparse.ArgumentParser(description="Manage Cloud Spanner instance and database.")
    parser.add_argument("--delete", action="store_true", help="Delete the Spanner instance (caution: this deletes all databases and data).")
    args = parser.parse_args()

    project_id = settings.google_cloud_project or settings.vertex_project_id
    instance_id = settings.spanner_instance
    database_id = settings.spanner_database
    region = settings.spanner_location
    
    if not project_id:
        logger.error("GCP Project ID must be specified in environment or .env file.")
        return

    logger.info(f"Connecting to Spanner client for project: {project_id}")
    spanner_client = spanner.Client(project=project_id)
    
    # 1. Resolve Instance details
    instance_config = f"projects/{project_id}/instanceConfigs/regional-{region}"
    instance = spanner_client.instance(
        instance_id,
        configuration_name=instance_config,
        display_name="E-Commerce Instance",
        processing_units=100
    )
    
    if args.delete:
        logger.info(f"Checking if Spanner Instance '{instance_id}' exists to delete...")
        if instance.exists():
            logger.info(f"Deleting Spanner Instance '{instance_id}'...")
            try:
                instance.delete()
                logger.info(f"Spanner Instance '{instance_id}' deleted successfully.")
            except Exception as e:
                logger.error(f"Failed to delete Spanner Instance: {e}")
        else:
            logger.info(f"Spanner Instance '{instance_id}' does not exist.")
        return
    
    logger.info(f"Checking if Spanner Instance '{instance_id}' exists...")
    if not instance.exists():
        logger.info(f"Creating Spanner Instance '{instance_id}' in region '{region}' with 100 Processing Units and ENTERPRISE edition...")
        try:
            api = spanner_client.instance_admin_api
            instance_pb = InstancePB(
                name=instance.name,
                config=instance.configuration_name,
                display_name=instance.display_name,
                processing_units=instance._processing_units,
                labels=instance.labels,
                edition=InstancePB.Edition.ENTERPRISE
            )
            metadata = _metadata_with_prefix(instance.name)
            operation = api.create_instance(
                parent=spanner_client.project_name,
                instance_id=instance.instance_id,
                instance=instance_pb,
                metadata=metadata
            )
            operation.result(timeout=300)
            logger.info("Spanner Instance created successfully.")
        except Exception as e:
            logger.error(f"Failed to create Spanner Instance: {e}")
            return
    else:
        logger.info(f"Spanner Instance '{instance_id}' already exists.")

    # 2. Parse DDL statements from schema.sql
    script_dir = os.path.dirname(os.path.abspath(__file__))
    schema_path = os.path.join(script_dir, "..", "schema.sql")
    if not os.path.exists(schema_path):
        logger.error(f"schema.sql file not found at: {schema_path}")
        return

    logger.info(f"Reading schema from: {schema_path}")
    with open(schema_path, "r") as f:
        schema_content = f.read()

    # Parse and clean DDL lines
    clean_lines = []
    for line in schema_content.splitlines():
        # Strip SQL comments
        clean_line = line.split("--", 1)[0].strip()
        if clean_line:
            clean_lines.append(clean_line)
            
    clean_sql = " ".join(clean_lines)
    ddl_statements = [stmt.strip() for stmt in clean_sql.split(";") if stmt.strip()]

    # 3. Create Spanner Database with schema DDLs
    database = instance.database(database_id, ddl_statements=ddl_statements)
    
    logger.info(f"Checking if Spanner Database '{database_id}' exists...")
    if not database.exists():
        logger.info(f"Creating Spanner Database '{database_id}' and applying DDL tables...")
        try:
            operation = database.create()
            operation.result(timeout=300)
            logger.info("Spanner Database created and schema applied successfully.")
        except Exception as e:
            logger.error(f"Failed to create Spanner Database: {e}")
    else:
        logger.info(f"Spanner Database '{database_id}' already exists.")

if __name__ == "__main__":
    main()
