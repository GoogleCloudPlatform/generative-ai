# Utility functions to create Index and deploy the index to an Endpoint
from datetime import datetime
import time
import logging

from google.cloud import aiplatform_v1 as aipv1
from google.protobuf import struct_pb2

logging.basicConfig(level = logging.INFO)
logger = logging.getLogger()

class MatchingEngineUtils:
    def __init__(self,
                 project_id: str,
                 region: str,
                 index_name: str):
        self.project_id = project_id
        self.region = region
        self.index_name = index_name
        self.index_endpoint_name = f"{self.index_name}-endpoint"
        self.PARENT = f"projects/{self.project_id}/locations/{self.region}"

        ENDPOINT = f"{self.region}-aiplatform.googleapis.com"
        # set index client
        self.index_client = aipv1.IndexServiceClient(
            client_options=dict(api_endpoint=ENDPOINT)
        )
        # set index endpoint client
        self.index_endpoint_client = aipv1.IndexEndpointServiceClient(
            client_options=dict(api_endpoint=ENDPOINT)
        )

    def get_index(self):
        # Check if index exists
        request = aipv1.ListIndexesRequest(parent=self.PARENT)
        page_result = self.index_client.list_indexes(request=request)
        indexes = [response.name for response in page_result
                   if response.display_name == self.index_name]

        if len(indexes) == 0:
            return None
        else:
            index_id = indexes[0]
            request = aipv1.GetIndexRequest(name=index_id)
            index = self.index_client.get_index(request=request)
            return index

    def get_index_endpoint(self):
        # Check if index endpoint exists
        request = aipv1.ListIndexEndpointsRequest(parent=self.PARENT)
        page_result = self.index_endpoint_client.list_index_endpoints(request=request)
        index_endpoints = [response.name for response in page_result
                           if response.display_name == self.index_endpoint_name]

        if len(index_endpoints) == 0:
            return None
        else:
            index_endpoint_id = index_endpoints[0]
            request = aipv1.GetIndexEndpointRequest(name=index_endpoint_id)
            index_endpoint = self.index_endpoint_client.get_index_endpoint(request=request)
            return index_endpoint

    def create_index(self,
                     embedding_gcs_uri: str,
                     dimensions: int,
                     index_update_method: str = "streaming",
                     index_algorithm:str = "tree-ah"
                     ):
        # Get index
        index = self.get_index()
        # Create index if does not exists
        if index:
            logger.info(f"Index {self.index_name} already exists with id {index.name}")
        else:
            logger.info(f"Index {self.index_name} does not exists. Creating index ...")

            if index_update_method == "streaming":
                index_update_method = aipv1.Index.IndexUpdateMethod.STREAM_UPDATE 
            else:
                index_update_method = aipv1.Index.IndexUpdateMethod.BATCH_UPDATE 
            
            treeAhConfig = struct_pb2.Struct(
                fields={
                    "leafNodeEmbeddingCount": struct_pb2.Value(number_value=500),
                    "leafNodesToSearchPercent": struct_pb2.Value(number_value=7),
                }
            )
            if index_algorithm == "treeah":
                algorithmConfig = struct_pb2.Struct(
                    fields={"treeAhConfig": struct_pb2.Value(struct_value=treeAhConfig)}
                )
            else:
                algorithmConfig = struct_pb2.Struct(
                    fields={"bruteForceConfig": struct_pb2.Value(struct_value=struct_pb2.Struct())}
                )
            config = struct_pb2.Struct(
                fields={
                    "dimensions": struct_pb2.Value(number_value=dimensions),
                    "approximateNeighborsCount": struct_pb2.Value(number_value=150),
                    "distanceMeasureType": struct_pb2.Value(string_value="DOT_PRODUCT_DISTANCE"),
                    "algorithmConfig": struct_pb2.Value(struct_value=algorithmConfig),
                    "shardSize": struct_pb2.Value(string_value="SHARD_SIZE_SMALL"),
                }
            )
            metadata = struct_pb2.Struct(
                fields={
                    "config": struct_pb2.Value(struct_value=config),
                    "contentsDeltaUri": struct_pb2.Value(string_value=embedding_gcs_uri),
                }
            )

            index_request = {
                "display_name": self.index_name,
                "description": "Index for LangChain demo",
                "metadata": struct_pb2.Value(struct_value=metadata),
                "index_update_method": index_update_method,
            }

            r = self.index_client.create_index(parent=self.PARENT,
                                               index=index_request)
            logger.info(f'Creating index with long running operation {r._operation.name}')

            # Poll the operation until it's done successfullly.
            logging.info("Poll the operation to create index ...")
            while True:
                if r.done():
                    break
                time.sleep(60)
                print('.', end='')

            index = r.result()
            logger.info(f"Index {self.index_name} created with resource name as {index.name}")

        return index

    def deploy_index(self,
                     machine_type: str = "e2-standard-2",
                     min_replica_count: int = 2,
                     max_replica_count: int = 10,
                     network: str = None):
        try:
            # Get index if exists
            index = self.get_index()
            if not index:
                raise Exception(f"Index {self.index_name} does not exists. Please create index before deploying.")

            # Get index endpoint if exists
            index_endpoint = self.get_index_endpoint()
            # Create Index Endpoint if does not exists
            if index_endpoint:
                logger.info(f"Index endpoint {self.index_endpoint_name} already exists with resource " +
                            f"name as {index_endpoint.name} and endpoint domain name as " +
                            f"{index_endpoint.public_endpoint_domain_name}")
            else:
                logger.info(f"Index endpoint {self.index_endpoint_name} does not exists. Creating index endpoint...")
                index_endpoint_request = {"display_name": self.index_endpoint_name}

                if network:
                    index_endpoint_request["network"] = network
                else:
                    index_endpoint_request["public_endpoint_enabled"] = True

                r = self.index_endpoint_client.create_index_endpoint(
                    parent=self.PARENT,
                    index_endpoint=index_endpoint_request)
                logger.info(f'Deploying index to endpoint with long running operation {r._operation.name}')

                logger.info("Poll the operation to create index endpoint ...")
                while True:
                    if r.done():
                        break
                    time.sleep(60)
                    print('.', end='')

                index_endpoint = r.result()
                logger.info(f"Index endpoint {self.index_endpoint_name} created with resource " +
                            f"name as {index_endpoint.name} and endpoint domain name as " +
                            f"{index_endpoint.public_endpoint_domain_name}")
        except Exception as e:
            logger.error(f"Failed to create index endpoint {self.index_endpoint_name}")
            raise e

        # Deploy Index to endpoint
        try:
            # Check if index is already deployed to the endpoint
            for d_index in index_endpoint.deployed_indexes:
                if d_index.index == index.name:
                    logger.info(f"Skipping deploying Index. Index {self.index_name}" +
                                f"already deployed with id {index.name} to the index endpoint {self.index_endpoint_name}")
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
                    "max_replica_count": max_replica_count
                    }
            }
            logger.info(f"Deploying index with request = {deploy_index}")
            r = self.index_endpoint_client.deploy_index(
                index_endpoint=index_endpoint.name,
                deployed_index=deploy_index
            )

            # Poll the operation until it's done successfullly.
            logger.info("Poll the operation to deploy index ...")
            while True:
                if r.done():
                    break
                time.sleep(60)
                print('.', end='')

            logger.info(f"Deployed index {self.index_name} to endpoint {self.index_endpoint_name}")

        except Exception as e:
            logger.error(f"Failed to deploy index {self.index_name} to the index endpoint {self.index_endpoint_name}")
            raise e

        return index_endpoint

    def get_index_and_endpoint(self):
        # Get index id if exists
        index = self.get_index()
        index_id = index.name if index else ''

        # Get index endpoint id if exists
        index_endpoint = self.get_index_endpoint()
        index_endpoint_id = index_endpoint.name if index_endpoint else ''

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
            logger.info(f"Index endpoint {self.index_endpoint_name}  exists with resource " +
                        f"name as {index_endpoint.name} and endpoint domain name as " +
                        f"{index_endpoint.public_endpoint_domain_name}")

            index_endpoint_id = index_endpoint.name
            index_endpoint = self.index_endpoint_client.get_index_endpoint(name=index_endpoint_id)
            # Undeploy existing indexes
            for d_index in index_endpoint.deployed_indexes:
                logger.info(f"Undeploying index with id {d_index.id} from Index endpoint {self.index_endpoint_name}")
                request = aipv1.UndeployIndexRequest(
                    index_endpoint=index_endpoint_id,
                    deployed_index_id=d_index.id)
                r = self.index_endpoint_client.undeploy_index(request=request)
                response = r.result()
                logger.info(response)

            # Delete index endpoint
            logger.info(f"Deleting Index endpoint {self.index_endpoint_name} with id {index_endpoint_id}")
            self.index_endpoint_client.delete_index_endpoint(name=index_endpoint_id)
        else:
            raise Exception(f"Index endpoint {self.index_endpoint_name} does not exists.")