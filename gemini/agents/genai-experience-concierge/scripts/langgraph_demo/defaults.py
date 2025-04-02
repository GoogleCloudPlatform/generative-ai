# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Constants and sane defaults for the langgraph demo deployment."""

import pathlib

PROJECT_ROOT_DIR = (pathlib.Path(__file__).parent.parent.parent).resolve()

REGION = "us-central1"

CLOUD_RUN_DEMO_DIR = PROJECT_ROOT_DIR / "langgraph-demo"

BACKEND_DIR = CLOUD_RUN_DEMO_DIR / "backend"
FRONTEND_DIR = CLOUD_RUN_DEMO_DIR / "frontend"
TERRAFORM_DIR = CLOUD_RUN_DEMO_DIR / "terraform"
DATASETS_DIR = CLOUD_RUN_DEMO_DIR / "datasets"

PRODUCT_DATASET_PATH = DATASETS_DIR / "cymbal_product.parquet"
STORE_DATASET_PATH = DATASETS_DIR / "cymbal_store.parquet"
INVENTORY_DATASET_PATH = DATASETS_DIR / "cymbal_inventory.parquet"

SERVICE_YAML_TEMPLATE_PATH = BACKEND_DIR / "service.yaml.template"
APP_YAML_TEMPLATE_PATH = FRONTEND_DIR / "app.yaml.template"

PRODUCT_TABLE_NAME = "cymbal_product"
STORE_TABLE_NAME = "cymbal_store"
INVENTORY_TABLE_NAME = "cymbal_inventory"
EMBEDDING_MODEL_NAME = "text_embedding"
