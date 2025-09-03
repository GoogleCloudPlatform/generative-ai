# Copyright 2025 Google LLC
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

"""Service for managing the Search Application configuration 
stored in BigQuery."""

from src.model.http_status import BadRequest
from src.model.search import SearchApplication
from src.repository.big_query import BigQueryRepository

SEARCH_APPLICATION_TABLE = "search_applications"
SEARCH_APPLICATION_TABLE_ID_COLUMN = "engine_id"


class SearchApplicationService:
    """Handles business logic for Search Application configuration."""

    def __init__(self):
        """Initializes the service with a BigQuery repository."""
        self.repository = BigQueryRepository()

    def get(self):
        """
        Retrieves the currently configured Search Application.

        Assumes that there is at most one Search Application configuration
        stored in the BigQuery table. If multiple rows exist, it returns
        the last one processed.

        Returns:
            A SearchApplication object if found, otherwise None.
        """
        search_application = None
        results = self.repository.get_all_rows(SEARCH_APPLICATION_TABLE)
        # Convert RowIterator to list to check if it's empty or get the last item
        rows = list(results)
        if rows:
            # Assuming we take the last row if multiple exist, or the only one
            search_application = SearchApplication.from_row(rows[-1])

        return search_application

    def create(
        self, search_application: SearchApplication
    ) -> SearchApplication:
        """
        Creates a new Search Application configuration in BigQuery.

        Ensures that no configuration already exists before creating a new one.

        Args:
            search_application: The SearchApplication object to create.

        Returns:
            The created SearchApplication object.

        Raises:
            BadRequest: If a Search Application configuration already exists
                        for the project.
        """
        if self.get():
            raise BadRequest(
                detail="Search Application for this project already exists"
            )
        schema_fields = SearchApplication.__schema__()
        column_names = [field.name for field in schema_fields]

        # Prepare values as a tuple, matching the order of schema_fields
        # Ensure the order here matches the order in SearchApplication.__schema__
        values_tuple = (search_application.engine_id, search_application.region)

        self.repository.insert_row(
            SEARCH_APPLICATION_TABLE,
            column_names,
            values_tuple,
        )
        return search_application

    def update(self, engine_id: str, search_application: SearchApplication):
        """
        Updates an existing Search Application configuration in BigQuery.

        Identifies the row to update using the provided engine_id.

        Args:
            engine_id: The engine_id of the Search Application configuration
                       to update.
            search_application: A SearchApplication object containing the
                                updated details (engine_id and region).

        Returns:
            The updated SearchApplication object.

        Raises:
            # Note: The underlying repository might raise exceptions on failure,
            # which are not explicitly handled here.
            # Consider adding error handling.
        """
        update_dict = {
            "engine_id": f'"{search_application.engine_id}"',
            "region": f'"{search_application.region}"',
        }
        self.repository.update_row_by_id(
            SEARCH_APPLICATION_TABLE,
            SEARCH_APPLICATION_TABLE_ID_COLUMN,
            engine_id,
            update_dict,
        )
