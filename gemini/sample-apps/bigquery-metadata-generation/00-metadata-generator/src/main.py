import inquirer
from configparser import ConfigParser

from google.cloud import aiplatform

from data import EXAMPLE_TABLE
from agents import MetadataAgent
from dependencies.bigquery import BQClient
from utils import zip_all_files
config = ConfigParser()
config.read("src/config.ini")

aiplatform.init(location=config["GENERIC"]["REGION"])


if __name__ == "__main__":

    project_id = input("\nEnter the project_id (or press Enter to use test default): ")

    #project_id=config["GENERIC"]["DEFAULT_BQ_PROJECT"]

    #1
    BQ = BQClient(project_id=project_id if project_id else config["GENERIC"]["DEFAULT_BQ_PROJECT"])

    dataset = inquirer.prompt(
        [
            inquirer.List(
                "dataset",
                message="Choose a dataset",
                choices=[
                    dataset.dataset_id for dataset in list(BQ.client.list_datasets())
                ],
            ),
        ]
    )["dataset"]

    #2
    table_list = [a.table_id for a in BQ.client.list_tables(dataset=dataset)]

    print(table_list)

    if inquirer.prompt(
        [
            inquirer.Confirm(
                "proceed",
                message="Proceed with metadata generation for all the tables?",
                default=True,
            )
        ]
    )["proceed"]:


        #3
        df = [
            BQ.get_table_schema(
                dataset=dataset,
                table=table,
            )
            for table in table_list
        ]

        #4 # TODO: put project_id instead config["GENERIC"]["PROJECT_ID"]
        list(map(lambda x: MetadataAgent() \
        .generate_metadata(metadata_example=EXAMPLE_TABLE, table_data=x[1]) \
        .write_to_json(f"src/_out/{project_id}.{dataset}.{x[0]}"), zip(table_list, df)))

        zip_all_files(dataset, "src/_out/")