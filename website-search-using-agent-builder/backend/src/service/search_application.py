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
        for row in results:
            search_application = SearchApplication.__from_row__(row)

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
        self.repository.insert_row(
            SEARCH_APPLICATION_TABLE, search_application.to_insert_string()
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
