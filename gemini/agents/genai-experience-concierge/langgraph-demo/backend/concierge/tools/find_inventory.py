# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Search for product-store inventory in the Cymbal Retail dataset."""

# pylint: disable=duplicate-code

from typing import Callable

from concierge.tools import schemas
from google.cloud import bigquery
from google.genai import types as genai_types

find_inventory_fd = genai_types.FunctionDeclaration(
    response=None,
    description="""
Look up the inventory query for a given product at a certain store.
The product ID and store ID must be known before calling this function.
If either are not known, use the other tools to first find the right store and product IDs.
""".strip(),
    name="find_inventory",
    parameters=genai_types.Schema(
        properties={
            "store_id": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                description="Unique identifier of the store.",
            ),
            "product_id": genai_types.Schema(
                type=genai_types.Type.STRING,
                description="Unique identifier of the product.",
            ),
        },
        required=["store_id", "product_id"],
        type=genai_types.Type.OBJECT,
    ),
)


def generate_find_inventory_handler(
    project: str,
    cymbal_inventory_table_uri: str,
    cymbal_dataset_location: str,
) -> Callable[[int, str], schemas.InventorySearchResult]:
    """Generates a handler function for finding inventory information.

    This function creates a callable that queries BigQuery to find inventory
    details for a specific product at a given store.

    Args:
        project (str): The Google Cloud project ID.
        cymbal_inventory_table_uri (str): The URI of the BigQuery table containing
            inventory information.
        cymbal_dataset_location (str): The location of the BigQuery dataset.

    Returns:
        Callable: A function that takes store ID and product ID as input and returns
            an InventorySearchResult.
    """

    def find_inventory(
        store_id: int,
        product_id: str,
    ) -> schemas.InventorySearchResult:
        """Look up the inventory query for a given product at a certain store.
        The product ID and store ID must be known before calling this function.
        If either are not known, use the other tools to first find the right store and product IDs.

        Args:
            store_id (int): Unique identifier of the store.
            product_id (str): Unique identifier of the product.

        Returns:
            InventorySearchResult: The return value.
                Object including the current inventory and/or an error message.
        """
        nonlocal project, cymbal_inventory_table_uri

        query = f"""
    SELECT
        CAST(store_id AS STRING) AS store_id,
        uniq_id AS product_id,
        inventory AS value,
    FROM
        {cymbal_inventory_table_uri}
    WHERE
        store_id = @store_id
        AND uniq_id = @product_id
    """.strip()

        query_job_config = bigquery.QueryJobConfig()
        query_job_config.query_parameters = [
            bigquery.ScalarQueryParameter(
                name="store_id",
                type_=bigquery.SqlParameterScalarTypes.INTEGER,
                value=store_id,
            ),
            bigquery.ScalarQueryParameter(
                name="product_id",
                type_=bigquery.SqlParameterScalarTypes.STRING,
                value=product_id,
            ),
        ]

        bq_client = bigquery.Client(project=project, location=cymbal_dataset_location)
        query_job = bq_client.query(
            query=query,
            job_config=query_job_config,
        )

        query_df = query_job.to_dataframe()

        if len(query_df) > 1:
            return schemas.InventorySearchResult(
                error="Multiple store/product combinations found."
            )

        if len(query_df) == 0:
            return schemas.InventorySearchResult(
                error="No store/product combinations found."
            )

        inventory = schemas.Inventory.model_validate(query_df.iloc[0].to_dict())

        return schemas.InventorySearchResult(inventory=inventory, query=query)

    return find_inventory
