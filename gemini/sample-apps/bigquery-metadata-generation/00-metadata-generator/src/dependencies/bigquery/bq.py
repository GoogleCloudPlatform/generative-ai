from google.cloud import bigquery

class BQClient():
    def __init__(self, project_id):
        self.project_id = project_id
        self._client = bigquery.Client(project=project_id)

    @property
    def client(self):
        """Return the BigQuery client object."""
        return self._client

    def get_table_data(self, dataset: str, table: str):
        """Fetch data from a BigQuery table and return it as a DataFrame."""
        return self.client.query_and_wait(
            f"""SELECT * FROM `{self.project_id}.{dataset}.{table}` LIMIT 50"""
        ).to_dataframe()

    def get_table_schema(self, dataset: str, table: str):
        """Fetch schema from a BigQuery table and return it."""
        table_ref = self.client.dataset(dataset).table(table)
        return self.client.get_table(table_ref).schema
