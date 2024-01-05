# Utility functions to create Index and deploy the index to an Endpoint
from datetime import datetime
import logging
import time
from typing import Optional

from google.api_core.client_options import ClientOptions
from google.cloud import aiplatform_v1 as aipv1
from google.protobuf import struct_pb2

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class MatchingEngineUtils:
    def __init__(
        self,
        project_id: str,
        region: str,
        index_name: str,
        index_endpoint_name: Optional[str] = None,
    ):
        self.project_id = project_id
        self.region = region
        self.index_name = index_name
        self.index_endpoint_name = index_endpoint_name or f"{self.index_name}-endpoint"
        self.PARENT = f"projects/{self.project_id}/locations/{self.region}"

        ENDPOINT = f"{self.region}-aiplatform.googleapis.com"
        # set index client
        self.index_client = aipv1.IndexServiceClient(
            client_options=ClientOptions(api_endpoint=ENDPOINT)
        )
        # set index endpoint client
        self.index_endpoint_client = aipv1.IndexEndpointServiceClient(
            client_options=ClientOptions(api_endpoint=ENDPOINT)
        )

    def get_index(self):
        # Check if index exists
        page_result = self.index_client.list_indexes(
            request=aipv1.ListIndexesRequest(parent=self.PARENT)
        )
        indexes = [
            response.name
            for response in page_result
            if response.display_name == self.index_name
        ]

        if len(indexes) == 0:
            return None

        index_id = indexes[0]
        return self.index_client.get_index(request=aipv1.GetIndexRequest(name=index_id))

    def get_index_endpoint(self):
        # Check if index endpoint exists
        page_result = self.index_endpoint_client.list_index_endpoints(
            request=aipv1.ListIndexEndpointsRequest(parent=self.PARENT)
        )
        index_endpoints = [
            response.name
            for response in page_result
            if response.display_name == self.index_endpoint_name
        ]

        if len(index_endpoints) == 0:
            return None

        index_endpoint_id = index_endpoints[0]
        return self.index_endpoint_client.get_index_endpoint(
            request=aipv1.GetIndexEndpointRequest(name=index_endpoint_id)
        )

    def create_index(
        self,
        embedding_gcs_uri: str,
        dimensions: int,
        index_update_method: str = "streaming",
        index_algorithm: str = "tree-ah",
        shard_size: str = "SHARD_SIZE_SMALL",
        distance_measure_type: str = "DOT_PRODUCT_DISTANCE",
        description: str = "Index for LangChain demo",
    ):
        # Get index
        index = self.get_index()
        # Create index if does not exists
        if index:
            logger.info(f"Index {self.index_name} already exists with id {index.name}")
        else:
            logger.info(f"Index {self.index_name} does not exists. Creating index ...")

            index_update_method_enum = (
                aipv1.Index.IndexUpdateMethod.STREAM_UPDATE
                if index_update_method == "streaming"
                else aipv1.Index.IndexUpdateMethod.BATCH_UPDATE
            )

            if index_algorithm == "tree-ah":
                treeAhConfig = struct_pb2.Struct(
                    fields={
                        "leafNodeEmbeddingCount": struct_pb2.Value(number_value=500),
                        "leafNodesToSearchPercent": struct_pb2.Value(number_value=7),
                    }
                )
                algorithmConfig = struct_pb2.Struct(
                    fields={"treeAhConfig": struct_pb2.Value(struct_value=treeAhConfig)}
                )
            else:
                algorithmConfig = struct_pb2.Struct(
                    fields={
                        "bruteForceConfig": struct_pb2.Value(
                            struct_value=struct_pb2.Struct()
                        )
                    }
                )
            config = struct_pb2.Struct(
                fields={
                    "dimensions": struct_pb2.Value(number_value=dimensions),
                    "approximateNeighborsCount": struct_pb2.Value(number_value=150),
                    "distanceMeasureType": struct_pb2.Value(
                        string_value=distance_measure_type
                    ),
                    "algorithmConfig": struct_pb2.Value(struct_value=algorithmConfig),
                    "shardSize": struct_pb2.Value(string_value=shard_size),
                }
            )
            metadata = struct_pb2.Struct(
                fields={
                    "config": struct_pb2.Value(struct_value=config),
                    "contentsDeltaUri": struct_pb2.Value(
                        string_value=embedding_gcs_uri
                    ),
                }
            )

            index_request = aipv1.Index(
                display_name=self.index_name,
                description=description,
                metadata=struct_pb2.Value(struct_value=metadata),
                index_update_method=index_update_method_enum,
            )

            r = self.index_client.create_index(parent=self.PARENT, index=index_request)
            logger.info(
                f"Creating index with long running operation {r._operation.name}"
            )

            # Poll the operation until it's done successfullly.
            logging.info("Poll the operation to create index ...")
            while True:
                if r.done():
                    break
                time.sleep(60)
                print(".", end="")

            index = r.result()
            logger.info(
                f"Index {self.index_name} created with resource name as {index.name}"
            )

        return index

    def deploy_index(
        self,
        machine_type: str = "e2-standard-2",
        min_replica_count: int = 2,
        max_replica_count: int = 10,
        public_endpoint_enabled: bool = True,
        network: Optional[str] = None,
    ):
        try:
            # Get index if exists
            index = self.get_index()
            if not index:
                raise Exception(
                    f"Index {self.index_name} does not exists. Please create index before deploying."
                )

            # Get index endpoint if exists
            index_endpoint = self.get_index_endpoint()
            # Create Index Endpoint if does not exists
            if index_endpoint:
                logger.info(
                    f"Index endpoint {self.index_endpoint_name} already exists with resource "
                    + f"name as {index_endpoint.name} and endpoint domain name as "
                    + f"{index_endpoint.public_endpoint_domain_name}"
                )
            else:
                logger.info(
                    f"Index endpoint {self.index_endpoint_name} does not exists. Creating index endpoint..."
                )
                index_endpoint_request = aipv1.IndexEndpoint(
                    display_name=self.index_endpoint_name
                )

                if network:
                    index_endpoint_request.network = network
                else:
                    index_endpoint_request.public_endpoint_enabled = (
                        public_endpoint_enabled
                    )
                r = self.index_endpoint_client.create_index_endpoint(
                    parent=self.PARENT, index_endpoint=index_endpoint_request
                )
                logger.info(
                    f"Deploying index to endpoint with long running operation {r._operation.name}"
                )

                logger.info("Poll the operation to create index endpoint ...")
                while True:
                    if r.done():
                        break
                    time.sleep(60)
                    print(".", end="")

                index_endpoint = r.result()
                logger.info(
                    f"Index endpoint {self.index_endpoint_name} created with resource "
                    + f"name as {index_endpoint.name} and endpoint domain name as "
                    + f"{index_endpoint.public_endpoint_domain_name}"
                )
        except Exception as e:
            logger.error(f"Failed to create index endpoint {self.index_endpoint_name}")
            raise e

        # Deploy Index to endpoint
        try:
            # Check if index is already deployed to the endpoint
            for d_index in index_endpoint.deployed_indexes:
                if d_index.index == index.name:
                    logger.info(
                        f"Skipping deploying Index. Index {self.index_name}"
                        + f"already deployed with id {index.name} to the index endpoint {self.index_endpoint_name}"
                    )
                    return index_endpoint

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            deployed_index_id = f"{self.index_name.replace('-', '_')}_{timestamp}"
            deployed_index = aipv1.DeployedIndex(
                id=deployed_index_id,
                display_name=deployed_index_id,
                index=index.name,
                dedicated_resources=aipv1.DedicatedResources(
                    machine_spec=aipv1.MachineSpec(machine_type=machine_type),
                    min_replica_count=min_replica_count,
                    max_replica_count=max_replica_count,
                ),
            )

            logger.info(f"Deploying index with request = {deployed_index}")
            r = self.index_endpoint_client.deploy_index(
                index_endpoint=index_endpoint.name, deployed_index=deployed_index
            )

            # Poll the operation until it's done successfullly.
            logger.info("Poll the operation to deploy index ...")
            while True:
                if r.done():
                    break
                time.sleep(60)
                print(".", end="")

            logger.info(
                f"Deployed index {self.index_name} to endpoint {self.index_endpoint_name}"
            )

        except Exception as e:
            logger.error(
                f"Failed to deploy index {self.index_name} to the index endpoint {self.index_endpoint_name}"
            )
            raise e

        return index_endpoint

    def get_index_and_endpoint(self):
        # Get index id if exists
        index = self.get_index()
        index_id = index.name if index else ""

        # Get index endpoint id if exists
        index_endpoint = self.get_index_endpoint()
        index_endpoint_id = index_endpoint.name if index_endpoint else ""

        return index_id, index_endpoint_id

    def delete_index(self):
        # Check if index exists
        index = self.get_index()

        # create index if does not exists
        if index:
            # Delete index
            index_id = index.name
            logger.info(f"Deleting Index {self.index_name} with id {index_id}")
            self.index_client.delete_index(name=index_id)
        else:
            raise Exception("Index {index_name} does not exists.")

    def delete_index_endpoint(self):
        # Check if index endpoint exists
        index_endpoint = self.get_index_endpoint()

        # Create Index Endpoint if does not exists
        if index_endpoint:
            logger.info(
                f"Index endpoint {self.index_endpoint_name}  exists with resource "
                + f"name as {index_endpoint.name} and endpoint domain name as "
                + f"{index_endpoint.public_endpoint_domain_name}"
            )

            index_endpoint_id = index_endpoint.name
            index_endpoint = self.index_endpoint_client.get_index_endpoint(
                name=index_endpoint_id
            )
            # Undeploy existing indexes
            for d_index in index_endpoint.deployed_indexes:
                logger.info(
                    f"Undeploying index with id {d_index.id} from Index endpoint {self.index_endpoint_name}"
                )
                request = aipv1.UndeployIndexRequest(
                    index_endpoint=index_endpoint_id, deployed_index_id=d_index.id
                )
                r = self.index_endpoint_client.undeploy_index(request=request)
                response = r.result()
                logger.info(response)

            # Delete index endpoint
            logger.info(
                f"Deleting Index endpoint {self.index_endpoint_name} with id {index_endpoint_id}"
            )
            self.index_endpoint_client.delete_index_endpoint(name=index_endpoint_id)
        else:
            raise Exception(
                f"Index endpoint {self.index_endpoint_name} does not exists."
            )
