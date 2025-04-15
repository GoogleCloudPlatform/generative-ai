from configparser import ConfigParser
import re

from dependencies.bigquery import BQClient
from dependencies.metadata.data_catalog import DataCatalog
from dependencies.utils import remove_null_fields

config = ConfigParser()
config.read("src/config.ini")

bq_client = BQClient(project_id=config["GENERIC"]["PROJECT_ID"])
catalog_client = DataCatalog(
    project_id=config["GENERIC"]["PROJECT_ID"],
    catalog_name=config["CATALOG"]["CATALOG_NAME"],
    catalog_location=config["CATALOG"]["CATALOG_LOCATION"],
    taxonomy_location=config["CATALOG"]["TAXONOMY_LOCATION"],
)


def uniform_to_google(fields: dict):
    fields = remove_null_fields(fields)
    for field in fields:
        if "fields" in field:
            if field["fields"]:
                field["fields"] = uniform_to_google(field["fields"])
        else:
            field["policyTags"] = catalog_client.create_new_policy_tag(
                field.pop("policyTag", "")
            )
    print()

    # print(fields)
    return fields


def update_descriptions(table_id: str, show_json: dict):
    """Utility function to insert almost any* useful metadata for a table.
    * Now only descriptions.

    Args:
        table_id (str): Table identifier <project_id>.<dataset>.<table_name>.
        show_json (dict): Very similar to the json object that is returned when running the command 'bq show <project>:<dataset>.<table_name>'.
            Main differences:
                - Simplified association of a policyTag. In this json you only need to enter the policyTag key and the Tag name as the value.
                It is not necessary to enter the expected resource ID in the native dictionary. The translation will be performed by Airflow.
                - Added overview key useful for entering a description in html format that allows links or other more usefull information.
                    (This is not displayed on BigQuery but on Dataplex)
    """

    show_json["schema"]["fields"] = uniform_to_google(
        fields=show_json["schema"]["fields"]
    )

    print(show_json)

    prj, dataset, table_name = table_id.split(".")

    is_sharded = show_json.get("type", "").upper() == "SHARDED_TABLE"
    if is_sharded:
        tables = filter(
            lambda x: re.fullmatch(f"{table_name}\d{{8}}", x.table_id),
            bq_client.client.list_tables(dataset=dataset),
        )
        table_id = f"{prj}.{dataset}.{max([table.table_id for table in tables])}"

    table = bq_client.client.get_table(table_id)
    table.description = show_json.get("description", "")[:1024]
    table.schema = show_json["schema"]["fields"]
    table.labels = show_json.get("labels", {})

    # Update Table Overview
    if overview := show_json.get("overview", ""):
        catalog_client.create_table_overview(
            overview, prj, dataset, table_name, is_sharded
        )  # dataset di data catalog

    # Update Table Tags
    if tags := show_json.get("tags", ""):
        catalog_client.create_table_tags(prj, dataset, table_name, tags, is_sharded)

    # Update Table Metadata
    table = bq_client.client.update_table(table, ["schema", "description", "labels"])
    print("Descriptions updated correctly!")
