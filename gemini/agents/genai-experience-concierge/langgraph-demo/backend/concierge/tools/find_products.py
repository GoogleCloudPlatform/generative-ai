# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Search for products in the Cymbal Retail dataset."""

# pylint: disable=line-too-long,duplicate-code

import logging
from typing import Callable, Optional

from concierge.tools import schemas
from google.cloud import bigquery
from google.genai import types as genai_types

MAX_PRODUCT_RESULTS = 10

logger = logging.getLogger(__name__)

find_products_fd = genai_types.FunctionDeclaration(
    response=None,
    description="Search for products with optional semantic search queries and filters.",
    name="find_products",
    parameters=genai_types.Schema(
        properties={
            "max_results": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                default=3,
                description="The max number of results to be returned.",
            ),
            "product_search_query": genai_types.Schema(
                type=genai_types.Type.STRING,
                nullable=True,
                default=None,
                description="Product text search for semantic similarity, can utilize name, description, brand or category.",
            ),
            "store_ids": genai_types.Schema(
                type=genai_types.Type.ARRAY,
                items=genai_types.Schema(type=genai_types.Type.INTEGER),
                nullable=True,
                default=None,
                description="List of store IDs that must carry the returned products. Only include if store IDs are already known, otherwise the store search tool may be more useful.",
            ),
            "min_price": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                nullable=True,
                default=None,
                description="Minimum price of products in dollars",
            ),
            "max_price": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                nullable=True,
                default=None,
                description="Maximum price of products in dollars",
            ),
        },
        required=[],
        type=genai_types.Type.OBJECT,
    ),
)


def generate_find_products_handler(
    project: str,
    cymbal_dataset_location: str,
    cymbal_products_table_uri: str,
    cymbal_inventory_table_uri: str,
    cymbal_embedding_model_uri: str,
) -> Callable[
    [int, str | None, list[int] | None, int | None, int | None],
    schemas.ProductSearchResult,
]:
    """
    Generates a function handler for finding products based on search queries and filters.

    This function allows searching for products using a semantic search query, filtering by store IDs,
    and applying price range constraints. It leverages BigQuery's vector search capabilities for
    semantic similarity and standard SQL queries for other filters.

    Args:
        project (str): The Google Cloud project ID.
        cymbal_dataset_location (str): The location of the BigQuery dataset.
        cymbal_products_table_uri (str): The URI of the products table in BigQuery.
        cymbal_inventory_table_uri (str): The URI of the inventory table in BigQuery.
        cymbal_embedding_model_uri (str): The URI of the embedding model in BigQuery for semantic search.

    Returns:
        Callable[[int, Optional[str], Optional[list[str]], Optional[int], Optional[int]], types.ProductSearchResult]:
            A function that accepts search parameters and returns a ProductSearchResult object.

            The returned function accepts the following arguments:
            - max_results (int): The maximum number of products to return.
            - product_search_query (Optional[str]): A text query for semantic product search.
            - store_ids (Optional[list[int]]): A list of store IDs to filter products by.
            - min_price (Optional[int]): The minimum price of the products.
            - max_price (Optional[int]): The maximum price of the products.
    """

    def find_products(
        max_results: int = 3,
        product_search_query: str | None = None,
        store_ids: list[int] | None = None,
        min_price: int | None = None,
        max_price: int | None = None,
    ) -> schemas.ProductSearchResult:
        """Search for products with optional semantic search queries and filters.

        Args:
            max_results (int): The max number of results to be returned.
            product_search_query (Optional[str]): Product text search for semantic similarity, can utilize name, description, brand or category.
            store_ids (Optional[list[int]]): List of store IDs that must carry the returned products. Only include if store IDs are already known, otherwise the store search tool may be more useful.
            min_price (Optional[int]): Minimum price of products in dollars.
            max_price (Optional[int]): Maximum price of products in dollars.

        Returns:
            ProductSearchResult: The return value. Object including top matched products and/or an error message.
        """

        nonlocal project, cymbal_dataset_location, cymbal_products_table_uri, cymbal_inventory_table_uri, cymbal_embedding_model_uri

        if max_results >= MAX_PRODUCT_RESULTS:
            logger.warning(
                f"Top k is too large ({max_results}). Setting to {MAX_PRODUCT_RESULTS}..."
            )
            max_results = MAX_PRODUCT_RESULTS

        if product_search_query:
            query, query_job_config = _build_query_with_vector_search(
                cymbal_products_table_uri=cymbal_products_table_uri,
                cymbal_inventory_table_uri=cymbal_inventory_table_uri,
                cymbal_embedding_model_uri=cymbal_embedding_model_uri,
                max_results=max_results,
                product_search_query=product_search_query,
                store_ids=store_ids,
                min_price=min_price,
                max_price=max_price,
            )
        else:
            query, query_job_config = _build_query_without_vector_search(
                cymbal_products_table_uri=cymbal_products_table_uri,
                cymbal_inventory_table_uri=cymbal_inventory_table_uri,
                max_results=max_results,
                store_ids=store_ids,
                min_price=min_price,
                max_price=max_price,
            )

        bq_client = bigquery.Client(project=project, location=cymbal_dataset_location)
        query_job = bq_client.query(
            query=query,
            job_config=query_job_config,
        )

        query_df = query_job.to_dataframe()

        products = [
            schemas.Product.model_validate(row.to_dict())
            for idx, row in query_df.iterrows()
        ]

        return schemas.ProductSearchResult(products=products, query=query)

    return find_products


# pylint: disable=too-many-arguments,too-many-positional-arguments
def _build_query_without_vector_search(
    cymbal_products_table_uri: str,
    cymbal_inventory_table_uri: str,
    max_results: int = 3,
    store_ids: Optional[list[int]] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
) -> tuple[str, bigquery.QueryJobConfig]:
    """
    Builds a BigQuery SQL query for product search without semantic vector search.

    This function constructs a SQL query that filters products based on store availability and price range,
    without using vector search for semantic similarity.

    Args:
        max_results: The maximum number of results to return.
        store_ids: Optional list of store IDs to filter products by availability.
        min_price: Optional minimum price to filter products.
        max_price: Optional maximum price to filter products.

    Returns:
        A tuple containing the SQL query string and the BigQuery query job configuration.
    """
    where_conditions = list[str]()
    query_parameters = list[
        bigquery.ScalarQueryParameter | bigquery.ArrayQueryParameter
    ]()

    if min_price is not None:
        min_price_selector = "@min_price <= IFNULL(sale_price, list_price)"
        where_conditions.append(min_price_selector)

        query_parameters.append(
            bigquery.ScalarQueryParameter(
                name="min_price",
                type_=bigquery.SqlParameterScalarTypes.FLOAT,
                value=min_price,
            )
        )

    if max_price is not None:
        max_price_selector = "IFNULL(sale_price, list_price) <= @max_price"
        where_conditions.append(max_price_selector)

        query_parameters.append(
            bigquery.ScalarQueryParameter(
                name="max_price",
                type_=bigquery.SqlParameterScalarTypes.FLOAT,
                value=max_price,
            )
        )

    select_products_query = f"SELECT * FROM `{cymbal_products_table_uri}`"
    filter_store_ids = store_ids is not None and len(store_ids) > 0
    if filter_store_ids:
        select_products_query = f"""
SELECT
    product.*
FROM
    `{cymbal_products_table_uri}` AS product,
    (SELECT DISTINCT
        uniq_id
    FROM
        `{cymbal_inventory_table_uri}`
    WHERE
        store_id IN UNNEST(@store_ids)
    ) AS inventory
WHERE
    product.uniq_id = inventory.uniq_id
""".strip()

        query_parameters.append(
            bigquery.ArrayQueryParameter(
                name="store_ids",
                array_type=bigquery.SqlParameterScalarTypes.INTEGER,
                values=store_ids,
            )
        )

    where_clause = ""
    if where_conditions:
        where_clause = f"WHERE {'AND '.join(f'({cond})' for cond in where_conditions)}"

    query_parameters.append(
        bigquery.ScalarQueryParameter(
            name="max_results",
            type_=bigquery.SqlParameterScalarTypes.INTEGER,
            value=max_results,
        )
    )

    query = f"""
SELECT
    product.uniq_id AS id,
    product.product_name AS name,
    product.product_url AS url,
    product.product_description AS description,
    product.brand,
    product.category,
    product.available,
    product.list_price,
    IF(product.sale_price <= product.list_price, product.sale_price, NULL) AS sale_price
FROM
    ({select_products_query}) AS product
{where_clause}
LIMIT @max_results
""".strip()

    query_job_config = bigquery.QueryJobConfig()
    query_job_config.query_parameters = query_parameters

    return query, query_job_config


# pylint: enable=too-many-arguments,too-many-positional-arguments


# pylint: disable=too-many-arguments,too-many-positional-arguments
def _build_query_with_vector_search(
    cymbal_products_table_uri: str,
    cymbal_inventory_table_uri: str,
    cymbal_embedding_model_uri: str,
    product_search_query: str,
    max_results: int = 3,
    store_ids: Optional[list[int]] = None,
    min_price: Optional[int] = None,
    max_price: Optional[int] = None,
) -> tuple[str, bigquery.QueryJobConfig]:
    """
    Builds a BigQuery SQL query for product search using semantic vector search.

    This function constructs a SQL query that uses BigQuery's vector search capabilities to find products
    based on semantic similarity to the provided search query. It also applies filters for store availability
    and price range.

    Args:
        product_search_query: The text query for semantic product search.
        max_results: The maximum number of results to return.
        store_ids: Optional list of store IDs to filter products by availability.
        min_price: Optional minimum price to filter products.
        max_price: Optional maximum price to filter products.

    Returns:
        A tuple containing the SQL query string and the BigQuery query job configuration.
    """

    where_conditions = list[str]()
    query_parameters = list[
        bigquery.ScalarQueryParameter | bigquery.ArrayQueryParameter
    ]()

    if min_price is not None:
        where_conditions.append(
            "@min_price <= IFNULL(base.sale_price, base.list_price)"
        )

        query_parameters.append(
            bigquery.ScalarQueryParameter(
                name="min_price",
                type_=bigquery.SqlParameterScalarTypes.FLOAT,
                value=min_price,
            )
        )

    if max_price is not None:
        where_conditions.append(
            "IFNULL(base.sale_price, base.list_price) <= @max_price"
        )

        query_parameters.append(
            bigquery.ScalarQueryParameter(
                name="max_price",
                type_=bigquery.SqlParameterScalarTypes.FLOAT,
                value=max_price,
            )
        )

    from_inventory_snippet = ""
    filter_store_ids = store_ids is not None and len(store_ids) > 0
    if filter_store_ids:
        where_conditions.append("base.uniq_id = inventory.uniq_id")
        from_inventory_snippet = f""",
(SELECT DISTINCT
    uniq_id
FROM
    `{cymbal_inventory_table_uri}`
WHERE
    store_id IN UNNEST(@store_ids)
) AS inventory""".strip()

        query_parameters.append(
            bigquery.ArrayQueryParameter(
                name="store_ids",
                array_type=bigquery.SqlParameterScalarTypes.INTEGER,
                values=store_ids,
            )
        )

    where_clause = ""
    if where_conditions:
        where_clause = f"WHERE {'AND '.join(f'({cond})' for cond in where_conditions)}"

    query_parameters.append(
        bigquery.ScalarQueryParameter(
            name="top_k",
            type_=bigquery.SqlParameterScalarTypes.INTEGER,
            value=max_results * 3,  # add some wiggle room for post-filtering
        )
    )

    query_parameters.append(
        bigquery.ScalarQueryParameter(
            name="max_results",
            type_=bigquery.SqlParameterScalarTypes.INTEGER,
            value=max_results,
        )
    )

    query = f"""
SELECT
    base.uniq_id AS id,
    base.product_name AS name,
    base.product_url AS url,
    base.product_description AS description,
    base.brand,
    base.category,
    base.available,
    base.list_price,
    IF(base.sale_price <= base.list_price, base.sale_price, NULL) AS sale_price
FROM
    VECTOR_SEARCH(
        TABLE `{cymbal_products_table_uri}`,
        'text_embedding',
        (SELECT
            text_embedding,
            content AS query
        FROM
            ML.GENERATE_TEXT_EMBEDDING(
                MODEL `{cymbal_embedding_model_uri}`,
                (
                    SELECT @semantic_search_query AS content
                )
            )
        ),
        top_k => @top_k
    ) as vector_search
    {from_inventory_snippet}
{where_clause}
LIMIT @max_results
""".strip()

    query_parameters.append(
        bigquery.ScalarQueryParameter(
            name="semantic_search_query",
            type_=bigquery.SqlParameterScalarTypes.STRING,
            value=product_search_query,
        )
    )

    query_job_config = bigquery.QueryJobConfig()
    query_job_config.query_parameters = query_parameters

    return query, query_job_config


# pylint: enable=too-many-arguments,too-many-positional-arguments,too-many-locals
