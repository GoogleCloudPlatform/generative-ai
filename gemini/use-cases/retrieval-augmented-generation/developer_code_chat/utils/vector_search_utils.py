# Copyright 2023 Google LLC. This software is provided as-is, without warranty
# or representation for any use or purpose. Your use of it is subject to your
# agreement with Google.
"""Vector Search Utils"""

from datetime import datetime
import logging
import time

# from google.cloud import aiplatform
from google.cloud import aiplatform_v1 as aipv1
from google.protobuf import struct_pb2
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()


class VectorSearchUtils:
    """Matching Engine Utils"""

    def __init__(self, project_id: str, region: str, index_name: str):
        self.project_id = project_id
        self.region = region
        self.index_name = index_name
        self.index_endpoint_name = f"{self.index_name}-endpoint"
        self.parent = f"projects/{self.project_id}/locations/{self.region}"

        endpoint = f"{self.region}-aiplatform.googleapis.com"
        # set index client
        self.index_client = aipv1.IndexServiceClient(
            client_options={"api_endpoint": endpoint}
        )
        # set index endpoint client
        self.index_endpoint_client = aipv1.IndexEndpointServiceClient(
            client_options={"api_endpoint": endpoint}
        )

    def get_index(self):
        """Get index ID if exists, using index name"""
        # Check if index exists
        request = aipv1.ListIndexesRequest(parent=self.parent)
        page_result = self.index_client.list_indexes(request=request)
        indexes = [
            response.name
            for response in page_result
            if response.display_name == self.index_name
        ]

        if len(indexes) == 0:
            return None
        else:
            index_id = indexes[0]
            request = aipv1.GetIndexRequest(name=index_id)
            index = self.index_client.get_index(request=request)
            return index

    def get_index_endpoint(self):
        # Check if index endpoint exists
        request = aipv1.ListIndexEndpointsRequest(parent=self.parent)
        page_result = self.index_endpoint_client.list_index_endpoints(request=request)
        index_endpoints = [
            response.name
            for response in page_result
            if response.display_name == self.index_endpoint_name
        ]

        if len(index_endpoints) == 0:
            return None
        else:
            index_endpoint_id = index_endpoints[0]
            request = aipv1.GetIndexEndpointRequest(name=index_endpoint_id)
            index_endpoint = self.index_endpoint_client.get_index_endpoint(
                request=request
            )
            return index_endpoint

    def create_index(
        self,
        embedding_gcs_uri: str,
        dimensions: int,
        index_update_method: str = "streaming",
        index_algorithm: str = "tree-ah",
    ):
        """Create New index"""
        # Get index
        index = self.get_index()
        # Create index if does not exists
        if index:
            logger.info(
                "Index %s already exists with id %s", self.index_name, index.name
            )
        else:
            logger.info("Index %s does not exists. Creating index ...", self.index_name)

            if index_update_method == "streaming":
                index_update_method = aipv1.Index.IndexUpdateMethod.STREAM_UPDATE
            else:
                index_update_method = aipv1.Index.IndexUpdateMethod.BATCH_UPDATE

            tree_ah_config = struct_pb2.Struct(
                fields={
                    "leafNodeEmbeddingCount": struct_pb2.Value(number_value=1000),
                    "leafNodesToSearchPercent": struct_pb2.Value(number_value=100),
                }
            )
            if index_algorithm == "treeah":
                algorithm_config = struct_pb2.Struct(
                    fields={
                        "treeAhConfig": struct_pb2.Value(struct_value=tree_ah_config)
                    }
                )
            else:
                algorithm_config = struct_pb2.Struct(
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
                        string_value="DOT_PRODUCT_DISTANCE"
                    ),
                    "algorithmConfig": struct_pb2.Value(struct_value=algorithm_config),
                    "shardSize": struct_pb2.Value(string_value="SHARD_SIZE_SMALL"),
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

            index_request = {
                "display_name": self.index_name,
                "description": "Index for LangChain demo",
                "metadata": struct_pb2.Value(struct_value=metadata),
                "index_update_method": index_update_method,
            }

            r = self.index_client.create_index(parent=self.parent, index=index_request)

            # Poll the operation until it's done successfullly.
            logging.info("Poll the operation to create index ...")
            while True:
                if r.done():
                    break
                time.sleep(60)
                print(".", end="")

            index = r.result()
            logger.info(
                "Index %s created with resource name as %s", self.index_name, index.name
            )

        return index

    def deploy_index(
        self,
        machine_type: str = "e2-standard-2",
        min_replica_count: int = 2,
        max_replica_count: int = 10,
        network: str = "",
    ):
        """Deploy New Index to Endpoint"""
        try:
            # Get index if exists
            index = self.get_index()
            if not index:
                raise Exception(
                    f"Index {self.index_name} does not exists. \
                                Please create index before deploying."
                )  # pylint: disable=W0719

            # Get index endpoint if exists
            index_endpoint = self.get_index_endpoint()
            # Create Index Endpoint if does not exists
            if index_endpoint:
                logger.info(
                    "Index endpoint %s already exists with resource \
                  name as %s and endpoint domain name as %s",
                    self.index_endpoint_name,
                    index_endpoint.name,
                    index_endpoint.public_endpoint_domain_name,
                )
            else:
                logger.info("Index endpoint %s doesn't exists.\
                  Creating new index endpoint...", self.index_endpoint_name)
                index_endpoint_request = Dict[str, Union[str, bool]]
                index_endpoint_request = {"display_name": \
                  self.index_endpoint_name}
                
                if network:
                    index_endpoint_request["network"] = network
                else:
                    index_endpoint_request["public_endpoint_enabled"] = True

                r = self.index_endpoint_client.create_index_endpoint(
                    parent=self.parent, index_endpoint=index_endpoint_request
                )

                logger.info("Poll the operation to create index endpoint ...")
                while True:
                    if r.done():
                        break
                    time.sleep(60)
                    print(".", end="")

                index_endpoint = r.result()
                logger.info(
                    "Index endpoint %s \
                  created with resource name as %s and \
                    endpoint domain name as %s",
                    self.index_endpoint_name,
                    index_endpoint.name,
                    index_endpoint.public_endpoint_domain_name,
                )
        except Exception as e:  # pylint:disable=C0103
            logger.error(
                "Failed to create index endpoint %s\n %s", self.index_endpoint_name, e
            )
            raise e

        # Deploy Index to endpoint
        try:
            # Check if index is already deployed to the endpoint
            for d_index in index_endpoint.deployed_indexes:
                if d_index.index == index.name:
                    logger.info(
                        "Skipping deploying Index. \
                      Index %s already deployed with id %s \
                        to the index endpoint %s",
                        self.index_name,
                        index.name,
                        self.index_endpoint_name,
                    )
                    return index_endpoint

            timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
            deployed_index_id = f"{self.index_name.replace('-', '_')}_{timestamp}"
            deploy_index = {
                "id": deployed_index_id,
                "display_name": deployed_index_id,
                "index": index.name,
                "dedicated_resources": {
                    "machine_spec": {
                        "machine_type": machine_type,
                    },
                    "min_replica_count": min_replica_count,
                    "max_replica_count": max_replica_count,
                },
            }
            logger.info("Deploying index with request = %s", deploy_index)
            r = self.index_endpoint_client.deploy_index(
                index_endpoint=index_endpoint.name, deployed_index=deploy_index
            )

            # Poll the operation until it's done successfullly.
            logger.info("Poll the operation to deploy index ...")
            while True:
                if r.done():
                    break
                time.sleep(60)
                print(".", end="")

            logger.info(
                "Deployed index %s to endpoint %s",
                self.index_name,
                self.index_endpoint_name,
            )

        except Exception as e:  # pylint:disable=C0103
            logger.error(
                "Failed to deploy index %s to the index endpoint %s",
                self.index_name,
                self.index_endpoint_name,
            )
            raise e

        return index_endpoint

    def get_index_and_endpoint(self):
        """Get index id if exists"""
        index = self.get_index()
        index_id = index.name if index else ""

        # Get index endpoint id if exists
        index_endpoint = self.get_index_endpoint()
        index_endpoint_id = index_endpoint.name if index_endpoint else ""

        return index_id, index_endpoint_id

    def delete_index(self):
        """Delete Index if exists"""
        # Check if index exists
        index = self.get_index()

        # create index if does not exists
        if index:
            # Delete index
            index_id = index.name
            logger.info("Deleting Index %s with id %s", self.index_name, index_id)
            self.index_client.delete_index(name=index_id)
        else:
            raise Exception(
                "Index {index_name} does not exists."
            )  # pylint: disable=W0719

    def delete_index_endpoint(self):
        """Delete Index Endpoint if exists"""
        # Check if index endpoint exists
        index_endpoint = self.get_index_endpoint()

        # Create Index Endpoint if does not exists
        if index_endpoint:
            logger.info(
                "Index endpoint %s exists \
              with resource name as %s and endpoint domain name as %s",
                self.index_endpoint_name,
                index_endpoint.name,
                index_endpoint.public_endpoint_domain_name,
            )

            index_endpoint_id = index_endpoint.name
            index_endpoint = self.index_endpoint_client.get_index_endpoint(
                name=index_endpoint_id
            )
            # Undeploy existing indexes
            for d_index in index_endpoint.deployed_indexes:
                logger.info(
                    "Undeploying index %s from Index endpoint %s",
                    d_index.id,
                    self.index_endpoint_name,
                )
                request = aipv1.UndeployIndexRequest(
                    index_endpoint=index_endpoint_id, deployed_index_id=d_index.id
                )
                r = self.index_endpoint_client.undeploy_index(request=request)
                response = r.result()
                logger.info(response)

            # Delete index endpoint
            logger.info("Deleting Index endpoint : %s", index_endpoint_id)
            self.index_endpoint_client.delete_index_endpoint(name=index_endpoint_id)
        else:
            raise Exception(
                f"Index endpoint {self.index_endpoint_name}\
               does not exists."
            )


def deploy_index_endpoint(logger, project_id, me_region, me_index_name):
    """Deploy Index to Endpoint"""
    start_time = time.time()
    mengine = VectorSearchUtils(project_id, me_region, me_index_name)
    list_endpoints = aipv1.MatchingEngineIndexEndpoint.list(
        filter=f"display_name={me_index_name}-endpoint"
    )
    if list_endpoints:
        logger.info("Found Endpoint from previous run")
    else:
        logger.info("Creating new endpoint as none existed from previous run.")
        index_endpoint = mengine.deploy_index()
        if index_endpoint:
            logger.info("Index endpoint resource name: %s", index_endpoint.name)
            logger.info(
                "Index endpoint public domain name: %s",
                index_endpoint.public_endpoint_domain_name,
            )
            logger.info("Deployed indexes on the index endpoint:")
            for d in index_endpoint.deployed_indexes:
                print(f"    {d.id}")
    end_time = time.time()
    time_to_deploy = np.round((end_time - start_time) / 60, 2)
    logger.info("Time(min) to deploy index endpoint: %s", time_to_deploy)


def delete_endppoint(project_id, me_region, me_index_name):
    """Delete index endpoint"""
    mengine = VectorSearchUtils(project_id, me_region, me_index_name)
    _, me_index_endpoint_id = mengine.get_index_and_endpoint()

    print(f"Undeploying index endpoint: {me_index_endpoint_id}")
    mengine.delete_index_endpoint()


def undeply_index(project_id, me_region, me_index_name):
    """Undeploy index"""

    mengine = VectorSearchUtils(project_id, me_region, me_index_name)
    me_index_id, _ = mengine.get_index_and_endpoint()

    print(f"Deleting the index: {me_index_id}")
    mengine.delete_index()
