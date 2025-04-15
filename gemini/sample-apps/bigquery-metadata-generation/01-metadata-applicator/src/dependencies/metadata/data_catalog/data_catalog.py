from time import sleep
from google.cloud import datacatalog_v1beta1, datacatalog_v1, bigquery

class DataCatalog:
    def __init__(self, project_id, catalog_name, catalog_location, taxonomy_location):

        self.project_id = project_id
        self.catalog_name = catalog_name
        self.catalog_location = catalog_location
        self.taxonomy_location = taxonomy_location

        self._client_policy = datacatalog_v1beta1.PolicyTagManagerClient()
        self._client_catalog = datacatalog_v1.DataCatalogClient()

    def create_table_overview(self, overview: str, table_project_id: str, dataset: str, table: str, is_sharded: bool = False):
        """Create Table Overview from display name."""
        request = datacatalog_v1.ModifyEntryOverviewRequest(
            name=self._lookup_entry(table_project_id, dataset, table, is_sharded),
            entry_overview=datacatalog_v1.EntryOverview(
                overview=overview
            )
        )
        return self._client_catalog.modify_entry_overview(request=request)

    def create_table_tags(self, table_project_id: str, dataset: str, table: str, tags: str, is_sharded: bool = False):
        """Create Table Tags from given tags."""
        tag_template = f"projects/{self.project_id}/locations/{self.catalog_location}/tagTemplates/{self.catalog_name}"

        # Create TagField for table_tags template
        tag_field = datacatalog_v1.TagField()
        tag_field.string_value = tags

        # Create Tag instance
        tag = datacatalog_v1.Tag()
        tag.template = tag_template

        # Insert TagField in tag.field parameter
        tag.fields["tags"] = tag_field

        # Get entry URL from BigQuery table reference
        parent = self._lookup_entry(table_project_id, dataset, table, is_sharded)

        return self.submit_reconcile_tags(parent, tag_template, [tag], False, 0.5)

    def _lookup_entry(self, table_project_id: str, dataset: str, table_name: str, is_sharded: bool = False) -> datacatalog_v1.Entry:
        """Gets an entry (URL format) by its target resource name building its fully qualified name."""
        sharded = ""
        if is_sharded:
            sharded = "sharded:"
        request = datacatalog_v1.LookupEntryRequest(
            fully_qualified_name=f"bigquery:{sharded}{table_project_id}.{dataset}.{table_name}", # test proj
            project=table_project_id,
            location=self.catalog_location
        )
        return self._client_catalog.lookup_entry(request=request).name

    def submit_reconcile_tags(self, table_parent: str, tag_template_name: str, tags: list,
                               force_delete_missing: bool, sleep_time: float):
        """
        Creates or updates a list of tags on the entry (table_parent).
        If the force_delete_missing parameter is set, the operation deletes tags not included in the input tag list.
        """
        request = datacatalog_v1.ReconcileTagsRequest(
            parent=table_parent,
            tag_template=tag_template_name,
            force_delete_missing=force_delete_missing,
            tags=tags
        )

        operation = self._client_catalog.reconcile_tags(request=request)
        op_name = operation.operation.name
        print(f"Operation {op_name} submitted")
        while not operation.done():
            print(f"Operation {op_name} not completed yet")
            sleep(sleep_time)
        print(f"Operation {op_name} completed")
        return operation

    def create_new_policy_tag(self, display_name: str):
        """Create PolicyTagList from display name."""
        tags = []
        if display_name:
            tags.append(self.get_policy_tag_by_display_name(display_name))
        return bigquery.PolicyTagList(tags).to_api_repr()

    def get_policy_tag_by_display_name(self, display_name: str):
        taxonomies = self.get_all_taxonomies()
        tags = self.get_all_policy_tags(taxonomies)
        return tags[display_name]

    def get_all_policy_tags(self, taxonomies):
        tags = {}
        for tax in taxonomies:
            for tag in self._client_policy.list_policy_tags(parent=tax.name):
                tags.update({tag.display_name: tag.name})
        return tags

    def get_all_taxonomies(self):
        return self._client_policy.list_taxonomies(parent=f"projects/{self.project_id}/locations/{self.taxonomy_location}")
