from scripts.big_query_setup import create_dataset, create_table

BIG_QUERY_DATASET=""

print("Setting up BigQuery... \n")

create_dataset(BIG_QUERY_DATASET)

print("\nSuccess!\n")