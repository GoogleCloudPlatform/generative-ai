# Copyright 2025 Google. This software is provided as-is, without warranty or
# representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Search for stores in the Cymbal Retail dataset."""

# pylint: disable=line-too-long,duplicate-code

import logging
from typing import Callable, Optional

from concierge import schemas as concierge_schemas
from concierge.tools import schemas
from google.cloud import bigquery
from google.genai import types as genai_types
from thefuzz import fuzz

MAX_STORE_RESULTS = 10
STORE_NAME_SIMILARITY_THRESHOLD = 90

logger = logging.getLogger(__name__)

find_stores_fd = genai_types.FunctionDeclaration(
    response=None,
    description="Search for stores nearby, by name, or offering certain products.",
    name="find_stores",
    parameters=genai_types.Schema(
        properties={
            "max_results": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                default=3,
                description="The max number of results to be returned.",
            ),
            "store_name": genai_types.Schema(
                type=genai_types.Type.STRING,
                nullable=True,
                default=None,
                description="The name (or part of a name) of a store to search for. Will try to find stores that fuzzy match this name.",
            ),
            "product_ids": genai_types.Schema(
                type=genai_types.Type.ARRAY,
                items=genai_types.Schema(type=genai_types.Type.STRING),
                nullable=True,
                default=None,
                description="List of product IDs that must exist at the given store. Leave empty if there is no product ID filtering.",
            ),
            "radius_km": genai_types.Schema(
                type=genai_types.Type.INTEGER,
                nullable=True,
                default=None,
                description="Radius in kilometers to restrict the nearby search around the user location. The user location doesn't have to be provided in the conversation context. This function can retrieve the user location from a backend database.",
            ),
        },
        required=[],
        type=genai_types.Type.OBJECT,
    ),
)


def generate_find_stores_handler(
    project: str,
    cymbal_dataset_location: str,
    cymbal_stores_table_uri: str,
    cymbal_inventory_table_uri: str,
    user_coordinate: Optional[concierge_schemas.Coordinate] = None,
) -> Callable[
    [list[str] | None, int, int | None, str | None], schemas.StoreSearchResult
]:
    """Generates a handler function for finding stores based on various criteria.

    This function creates a closure that encapsulates user location information (latitude and longitude)
    and returns a function that can search for stores. The returned function can filter stores based on
    product IDs, proximity (radius), store name, and maximum number of results.

    Args:
        project (str): The Google Cloud project ID.
        cymbal_dataset_location (str): The location of the BigQuery dataset.
        cymbal_stores_table_uri (str): The URI of the BigQuery table containing store information.
        cymbal_inventory_table_uri (str): The URI of the BigQuery table containing product inventory.
        user_latitude (Optional[float]): The user's latitude for location-based searches.
        user_longitude (Optional[float]): The user's longitude for location-based searches.

    Returns:
        Callable: A function that takes product IDs, max results, radius, and store name as input and returns a StoreSearchResult.
    """

    def find_stores(
        product_ids: list[str] | None = None,
        max_results: int = 3,
        # Note: google-genai doesn't properly handle floats, so we just set this as an integer
        radius_km: int | None = None,
        store_name: str | None = None,
    ) -> schemas.StoreSearchResult:
        """Search for stores nearby, by name, or offering certain products.

        Args:
            max_results (int): The max number of results to be returned. Largest allowed value is 10.
            radius_km (Optional[int]): Radius in kilometers to restrict the nearby search around the user location. The user location doesn't have to be provided in the conversation context. This function can retrieve the user location from a backend database.
            store_name (Optional[str]): The name (or part of a name) of a store to search for. Will try to find stores that fuzzy match this name.
            product_ids (list[str]): List of product IDs that must exist at the given store. Leave empty if there is no product ID filtering.

        Returns:
            StoreSearchResult: The return value. Object including top matched stores and/or an error message.
        """

        nonlocal project, cymbal_dataset_location, cymbal_stores_table_uri, cymbal_inventory_table_uri, user_coordinate

        product_ids = product_ids or []

        query_parameters = list[
            bigquery.ScalarQueryParameter | bigquery.ArrayQueryParameter
        ]()

        if max_results >= MAX_STORE_RESULTS:
            logger.warning(
                f"Top k is too large ({max_results}). Setting to {MAX_STORE_RESULTS}..."
            )
            max_results = MAX_STORE_RESULTS

        radius_selector = None
        if radius_km:
            if user_coordinate is None:
                raise ValueError("User location is not known")

            radius_selector = "ST_DISTANCE(ST_GEOGPOINT(@longitude, @latitude), ST_GEOGPOINT(longitude, latitude)) <= @radius_meters"

            query_parameters.extend(
                [
                    bigquery.ScalarQueryParameter(
                        name="latitude",
                        type_=bigquery.SqlParameterScalarTypes.FLOAT,
                        value=user_coordinate.latitude,
                    ),
                    bigquery.ScalarQueryParameter(
                        name="longitude",
                        type_=bigquery.SqlParameterScalarTypes.FLOAT,
                        value=user_coordinate.longitude,
                    ),
                    bigquery.ScalarQueryParameter(
                        name="radius_meters",
                        type_=bigquery.SqlParameterScalarTypes.FLOAT,
                        value=radius_km * 1_000.0,
                    ),
                ]
            )

        where_clause = ""
        if radius_selector:
            where_clause = f"WHERE {radius_selector}"

        select_stores_query = f"SELECT * FROM {cymbal_stores_table_uri}"
        if len(product_ids) > 0:
            select_stores_query = f"""
    SELECT
        store.*
    FROM
        {cymbal_stores_table_uri} AS store,
        (SELECT DISTINCT
            store_id
        FROM
            {cymbal_inventory_table_uri}
        WHERE
            uniq_id IN UNNEST(@product_ids)
        ) AS inventory
    WHERE
        store.store_id = inventory.store_id
    """.strip()

            query_parameters.append(
                bigquery.ArrayQueryParameter(
                    name="product_ids",
                    array_type=bigquery.SqlParameterScalarTypes.STRING,
                    values=product_ids,
                )
            )

        query = f"""
    SELECT
        CAST(store.store_id AS STRING) AS id,
        store.name,
        store.url,
        store.street_address,
        store.city,
        store.state,
        store.zip_code,
        store.country,
        store.phone_number_1 as phone_number,
        store.latitude,
        store.longitude,
    FROM
        ({select_stores_query}) AS store
    {where_clause}
    """.strip()

        query_job_config = bigquery.QueryJobConfig()
        query_job_config.query_parameters = query_parameters

        bq_client = bigquery.Client(project=project, location=cymbal_dataset_location)
        query_job = bq_client.query(
            query=query,
            job_config=query_job_config,
        )

        query_df = query_job.to_dataframe()

        stores = [
            schemas.Store.model_validate(row.to_dict())
            for idx, row in query_df.iterrows()
            # Filter by store names fuzzy matching the user input
            if (
                store_name is None
                or fuzz.WRatio(row["name"], store_name)
                >= STORE_NAME_SIMILARITY_THRESHOLD
            )
        ][
            :max_results
        ]  # filter max results

        return schemas.StoreSearchResult(stores=stores, query=query)

    return find_stores
