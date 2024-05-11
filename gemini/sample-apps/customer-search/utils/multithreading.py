from concurrent.futures import ThreadPoolExecutor
from typing import Dict

from google.cloud import bigquery

client: bigquery.Client = bigquery.Client()


def run(name: str, statement: str) -> tuple[str, bigquery.table.RowIterator]:
    """
    Runs a BigQuery query and returns the name of the query and the result iterator.

    Args:
        name (str): The name of the query.
        statement (str): The BigQuery query statement.
        client (bigquery.Client): The BigQuery client.

    Returns:
        A tuple containing the name of the query and the result iterator.
    """

    return name, client.query(statement).result()  # blocks the thread


def run_all(statements: Dict[str, str]) -> Dict[str, bigquery.table.RowIterator]:
    """
    Runs multiple BigQuery queries in parallel and returns a dictionary of the results.

    Args:
        statements (Dict[str, str]): A dictionary of query names and statements.

    Returns:
        A dictionary of query names and result iterators.
    """

    with ThreadPoolExecutor() as executor:
        jobs = []
        for name, statement in statements.items():
            jobs.append(executor.submit(run, name, statement))
        result = dict([job.result() for job in jobs])
    return result