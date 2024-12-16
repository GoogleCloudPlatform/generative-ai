from scripts.big_query_setup import create_dataset, create_table
from src.service.agent_config import AGENT_CONFIG_TABLE
from src.model.agent_config import AgentConfig

BIG_QUERY_DATASET=""

print("Setting up BigQuery... \n")

create_dataset(BIG_QUERY_DATASET)
create_table(BIG_QUERY_DATASET, AGENT_CONFIG_TABLE, AgentConfig.__schema__())

print("\nSuccess!\n")