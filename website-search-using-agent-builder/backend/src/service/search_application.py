from src.model.http_status import BadRequest
from src.model.search import SearchApplication
from src.repository.big_query import BigQueryRepository

SEARCH_APPLICATION_TABLE = "search_applications"
SEARCH_APPLICATION_TABLE_ID_COLUMN = "engine_id"

class SearchApplicationService:

    def __init__(self):
        self.repository = BigQueryRepository()
    
    def get(self):
        search_application = None
        results = self.repository.get_all_rows(SEARCH_APPLICATION_TABLE)
        for row in results:
            search_application = SearchApplication.__from_row__(row)

        return search_application

    def create(self, search_application: SearchApplication) -> SearchApplication:
        if self.get():
            raise BadRequest(detail=f"Search Application for this project already exists")
        self.repository.insert_row(SEARCH_APPLICATION_TABLE, search_application.to_insert_string())
        return search_application
    
    def update(self, engine_id: str, search_application: SearchApplication):
        update_dict = {
            'engine_id': f'"{search_application.engine_id}"',
            'region': f'"{search_application.region}"',
        }
        self.repository.update_row_by_id(SEARCH_APPLICATION_TABLE, SEARCH_APPLICATION_TABLE_ID_COLUMN, engine_id, update_dict)