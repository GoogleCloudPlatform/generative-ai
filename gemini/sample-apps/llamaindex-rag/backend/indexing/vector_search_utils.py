"""Module for vector search utils."""

from google.cloud import aiplatform


def create_index(vector_index_name: str, approximate_neighbors_count: int):
    """Creates a vector search index."""
    index_names = [
        index.resource_name
        for index in aiplatform.MatchingEngineIndex.list(
            filter=f"display_name={vector_index_name}"
        )
    ]
    print(f"Creating Vector Search index {vector_index_name} ...")
    vs_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
        display_name=vector_index_name,
        dimensions=768,
        distance_measure_type="DOT_PRODUCT_DISTANCE",
        shard_size="SHARD_SIZE_SMALL",
        index_update_method="STREAM_UPDATE",
        approximate_neighbors_count=approximate_neighbors_count,
    )
    print(
        f"Vector Search index {vs_index.display_name} "
        f"created with resource name {vs_index.resource_name}"
    )
    vs_index = aiplatform.MatchingEngineIndex(index_name=index_names[0])
    print(
        f"Vector Search index {vs_index.display_name} "
        f"exists with resource name {vs_index.resource_name}"
    )
    return vs_index


def create_endpoint(index_endpoint_name: str):
    """Creates an index endpoint."""
    endpoint_names = [
        endpoint.resource_name
        for endpoint in aiplatform.MatchingEngineIndexEndpoint.list(
            filter=f"display_name={index_endpoint_name}"
        )
    ]
    print(f"Creating Vector Search index endpoint {index_endpoint_name} ...")
    vs_endpoint = aiplatform.MatchingEngineIndexEndpoint.create(
        display_name=index_endpoint_name, public_endpoint_enabled=True
    )
    print(
        f"Vector Search index endpoint {vs_endpoint.display_name} "
        f"created with resource name {vs_endpoint.resource_name}"
    )
    vs_endpoint = aiplatform.MatchingEngineIndexEndpoint(
        index_endpoint_name=endpoint_names[0]
    )
    print(
        f"Vector Search index endpoint {vs_endpoint.display_name} "
        f"exists with resource name {vs_endpoint.resource_name}"
    )
    return vs_endpoint


def deploy_index(
    vs_index: aiplatform.MatchingEngineIndex,
    vs_endpoint: aiplatform.MatchingEngineIndexEndpoint,
    vector_index_name: str,
):
    """Deploys the index to the endpoint."""
    index_endpoints = [
        (deployed_index.index_endpoint, deployed_index.deployed_index_id)
        for deployed_index in vs_index.deployed_indexes
    ]

    if len(index_endpoints) == 0:
        print(
            f"Deploying Vector Search index {vs_index.display_name} "
            f"at endpoint {vs_endpoint.display_name} ..."
        )
        vs_deployed_index = vs_endpoint.deploy_index(
            index=vs_index,
            deployed_index_id=vector_index_name,
            display_name=vector_index_name,
            machine_type="e2-standard-16",
            min_replica_count=1,
            max_replica_count=1,
        )
        print(
            f"Vector Search index {vs_index.display_name} "
            f"is deployed at endpoint {vs_deployed_index.display_name}"
        )
        return vs_deployed_index
    vs_deployed_index = aiplatform.MatchingEngineIndexEndpoint(
        index_endpoint_name=index_endpoints[0][0]
    )
    print(
        f"Vector Search index {vs_index.display_name} "
        f"is already deployed at endpoint {vs_deployed_index.display_name}"
    )
    return vs_deployed_index


def get_existing_index_and_endpoint(vector_index_name: str, index_endpoint_name: str):
    """Gets existing index and endpoint."""
    # Check for existing index
    index = None
    index_list = aiplatform.MatchingEngineIndex.list(
        filter=f"display_name={vector_index_name}"
    )
    if index_list:
        index = index_list[0]
        print(f"Found existing index: {index.display_name}")

    # Check for existing endpoint
    endpoint = None
    endpoint_list = aiplatform.MatchingEngineIndexEndpoint.list(
        filter=f"display_name={index_endpoint_name}"
    )
    if endpoint_list:
        endpoint = endpoint_list[0]
        print(f"Found existing endpoint: {endpoint.display_name}")

    return index, endpoint


def is_index_deployed(vs_index: aiplatform.MatchingEngineIndex):
    """Checks if index is deployed."""
    return (
        len(vs_index.deployed_indexes) > 0
        and vs_index.deployed_indexes[0].display_name == vs_index.display_name
    )


def get_or_create_existing_index(
    vector_index_name: str, index_endpoint_name: str, approximate_neighbors_count: int
):
    """Gets or creates existing index."""
    # Creating Vector Search Index
    vs_index, vs_endpoint = get_existing_index_and_endpoint(
        vector_index_name, index_endpoint_name
    )

    if vs_index and vs_endpoint:
        # Check if the existing index is deployed
        if is_index_deployed(vs_index):
            print("Using existing deployed index and endpoint")
            return vs_index, vs_endpoint
        else:
            print("Existing index found, but it is not deployed.")

    print("Creating new index and/or endpoint")
    if not vs_index:
        vs_index = create_index(vector_index_name, approximate_neighbors_count)
    if not vs_endpoint:
        vs_endpoint = create_endpoint(index_endpoint_name)
    deploy_index(vs_index, vs_endpoint, vector_index_name)

    return vs_index, vs_endpoint
