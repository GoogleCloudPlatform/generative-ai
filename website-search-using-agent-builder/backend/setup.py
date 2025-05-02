from scripts.big_query_setup import create_dataset, create_table
from src.service.search_application import SEARCH_APPLICATION_TABLE
from src.model.search import SearchApplication

BIG_QUERY_DATASET = ""

print("Setting up BigQuery... \n")

create_dataset(BIG_QUERY_DATASET)
create_table(
    BIG_QUERY_DATASET, SEARCH_APPLICATION_TABLE, SearchApplication.__schema__()
)

print("\nSuccess!\n")
