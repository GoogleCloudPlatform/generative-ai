# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.

import json
import subprocess
from typing import Callable, TypedDict, TypeVar

from google.api_core import exceptions, retry
from google.cloud import bigquery
from scripts.langgraph_demo import defaults

connection_permission_retry_config = retry.Retry(
    predicate=lambda exc: isinstance(exc, subprocess.CalledProcessError),
    initial=1,
    maximum=60,
    multiplier=2,
    timeout=120,
    on_error=lambda exc: print(f"API Error: {str(exc)}"),
)

embedding_model_retry_config = retry.Retry(
    predicate=lambda exc: isinstance(exc, exceptions.BadRequest),
    initial=1,
    maximum=60,
    multiplier=2,
    timeout=120,
    on_error=lambda exc: print(f"API Error: {str(exc)}"),
)

_T = TypeVar("_T")

TEXT_EMBEDDING_MODEL = "text-embedding-004"

CREATE_EMBEDDING_MODEL_QUERY = """
CREATE OR REPLACE MODEL `{embedding_model_uri}`
REMOTE WITH CONNECTION `{connection_uri}`
OPTIONS (ENDPOINT = '{endpoint}');
""".strip()

COPY_TABLE_QUERY = """
CREATE OR REPLACE TABLE `{dest_table}`
AS (SELECT * FROM `{source_table}`)
""".strip()

CREATE_PRODUCTS_WITH_EMBEDDINGS_QUERY = """
CREATE OR REPLACE TABLE `{product_with_embedding_table_uri}` AS
SELECT * FROM ML.GENERATE_TEXT_EMBEDDING(
  MODEL `{embedding_model_uri}`,
  (
    SELECT *, CONCAT(product_name, " ", product_description) AS content
    FROM `{product_table_uri}`
  )
)
WHERE ARRAY_LENGTH(text_embedding) > 0;
""".strip()


class GeneratedDataset(TypedDict):
    """Represents the generated dataset with URIs for tables and models."""

    dataset_id: str
    products_table_uri: str
    stores_table_uri: str
    inventory_table_uri: str
    embedding_model_uri: str
    connection_uri: str


def create(
    project: str,
    location: str = "US",
    dataset_id: str = "cymbal_retail",
    connection_id: str = "cymbal_connection",
    product_path: str = str(defaults.PRODUCT_DATASET_PATH),
    store_path: str = str(defaults.STORE_DATASET_PATH),
    inventory_path: str = str(defaults.INVENTORY_DATASET_PATH),
):
    """
    Create the required Cymbal dataset models and tables.

    Only the project is required to exist before calling this function.

    This function sets up the BigQuery resources required for the Cymbal retail
    application. It creates an embedding model, loads product, store, and
    inventory data from Parquet files into BigQuery tables, and generates a
    product table with embeddings.

    Args:
        project (str): Project of the Cymbal dataset and connection.
        location (str): Location for the Cymbal dataset and connection.
        dataset_id (str): Dataset name for the generated Cymbal retail tables.
        connection_id (str): Connection ID to use for creating a BQ resource connection and embedding model.
        product_path (str): Path to a Parquet file containing product data.
        store_path (str): Path to a Parquet file containing store data.
        inventory_path (str): Path to a Parquet file containing inventory data.

    Returns:
        GeneratedDataset: A dictionary containing URIs for the created tables and model.

    Raises:
        Exception: If any BigQuery operation fails.
    """

    dataset_uri = f"{project}.{dataset_id}"

    bq_client = bigquery.Client(project=project, location=location)

    dataset = bigquery.Dataset(dataset_uri)
    dataset.location = location

    with_check(
        "Creating dataset (if not exists)...",
        lambda: bq_client.create_dataset(dataset, exists_ok=True),
    )

    connection_service_account: str | None = None
    try:
        connection_service_account = get_connection_service_account(
            project=project,
            location=location,
            connection_id=connection_id,
        )
    except subprocess.CalledProcessError:
        with_check(
            "Connection not found, attempting to create connection",
            lambda: subprocess.run(
                [
                    "bq",
                    "mk",
                    "--connection",
                    "--location",
                    location,
                    "--project_id",
                    project,
                    "--connection_type",
                    "CLOUD_RESOURCE",
                    connection_id,
                ],
                check=True,
            ),
        )

        # try to get service account again...
        connection_service_account = get_connection_service_account(
            project=project,
            location=location,
            connection_id=connection_id,
        )

    assert connection_service_account is not None, "Connection service account not set."

    connection_permission_retry_config(
        lambda: with_check(
            "Granting BQ connection the Vertex AI User role",
            lambda: subprocess.run(
                [
                    "gcloud",
                    "projects",
                    "add-iam-policy-binding",
                    project,
                    "--member",
                    f"serviceAccount:{connection_service_account}",
                    "--role",
                    "roles/aiplatform.user",
                ],
                check=True,
            ),
        )
    )()

    embedding_endpoint = TEXT_EMBEDDING_MODEL
    embedding_model_uri = f"{dataset_uri}.{defaults.EMBEDDING_MODEL_NAME}"
    connection_uri = (
        f"projects/{project}/locations/{location}/connections/{connection_id}"
    )
    embedding_query = CREATE_EMBEDDING_MODEL_QUERY.format(
        embedding_model_uri=embedding_model_uri,
        connection_uri=connection_uri,
        endpoint=embedding_endpoint,
    )

    try:
        embedding_model_retry_config(
            lambda: with_check(
                f"Creating embedding model: `{embedding_model_uri}`",
                lambda: bq_client.query_and_wait(embedding_query),
            )
        )()
    except exceptions.RetryError as e:
        e.add_note(
            "Please wait and try again if the error is permission-related. It is safe to re-run this command with the same inputs."
        )
        raise

    product_table_uri = f"{dataset_uri}.cymbal_product_only"
    store_table_uri = f"{dataset_uri}.{defaults.STORE_TABLE_NAME}"
    inventory_table_uri = f"{dataset_uri}.{defaults.INVENTORY_TABLE_NAME}"

    source_to_table_mapping = {
        product_table_uri: product_path,
        store_table_uri: store_path,
        inventory_table_uri: inventory_path,
    }
    for table_uri, source_path in source_to_table_mapping.items():
        job_config = bigquery.LoadJobConfig()
        job_config.write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
        job_config.source_format = bigquery.SourceFormat.PARQUET

        with open(source_path, "rb") as f:
            with_check(
                f"Creating table: `{table_uri}`",
                lambda: bq_client.load_table_from_file(
                    f,
                    destination=table_uri,
                    job_config=job_config,
                ).result(),
            )

    product_with_embedding_uri = f"{dataset_uri}.{defaults.PRODUCT_TABLE_NAME}"
    product_with_embedding_query = CREATE_PRODUCTS_WITH_EMBEDDINGS_QUERY.format(
        product_with_embedding_table_uri=product_with_embedding_uri,
        embedding_model_uri=embedding_model_uri,
        product_table_uri=product_table_uri,
    )

    with_check(
        f"Creating table: `{product_with_embedding_uri}`",
        lambda: bq_client.query_and_wait(product_with_embedding_query),
    )

    generated_dataset = GeneratedDataset(
        dataset_id=dataset_id,
        products_table_uri=product_with_embedding_uri,
        stores_table_uri=store_table_uri,
        inventory_table_uri=inventory_table_uri,
        embedding_model_uri=embedding_model_uri,
        connection_uri=connection_uri,
    )

    return generated_dataset


def with_check(start_message: str, fn: Callable[[], _T]) -> _T:
    """
    Executes a function and prints a success or failure message.

    Args:
        start_message (str): The message to print before executing the function.
        fn (Callable[[], _T]): The function to execute.

    Returns:
        _T: The result of the executed function.

    Raises:
        Exception: If the function execution fails.
    """

    print(f"{start_message}... ", end="")

    try:
        res = fn()
        print("SUCCESS")

        return res
    except Exception:
        print("FAILURE")
        raise


def get_connection_service_account(project: str, location: str, connection_id: str):
    completed_process = subprocess.run(
        [
            "bq",
            "show",
            "--format",
            "json",
            "--connection",
            f"{project}.{location}.{connection_id}",
        ],
        check=True,
        capture_output=True,
    )
    connection_details = json.loads(completed_process.stdout)
    connection_service_account = str(
        connection_details["cloudResource"]["serviceAccountId"]
    )

    return connection_service_account
