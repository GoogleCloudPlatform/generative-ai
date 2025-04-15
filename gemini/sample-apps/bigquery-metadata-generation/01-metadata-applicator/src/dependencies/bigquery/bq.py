from google.cloud import bigquery


class BQClient:
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
            f"""SELECT * FROM `{self.project_id}.{dataset}.{table}` LIMIT 10"""
        ).to_dataframe()
