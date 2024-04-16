"""
Cloud function to generate embedding of given file.
"""

import json

import functions_framework
from google.cloud import aiplatform
from google.protobuf import json_format
from google.protobuf.json_format import MessageToDict
from google.protobuf.struct_pb2 import Value

PROJECT_ID = "<YOUR_PROJECT_ID>"
LOCATION = "<YOUR_LOCATION>"
MODEL_NAME = "textembedding-gecko@001"
API_ENDPOINT = f"{LOCATION}-aiplatform.googleapis.com"
ENDPOINT = (
    f"projects/{PROJECT_ID}/locations/{LOCATION}/publishers/google/models/{MODEL_NAME}"
)
client_options = {"api_endpoint": API_ENDPOINT}
client = aiplatform.gapic.PredictionServiceClient(client_options=client_options)


def get_embeddings(instances):
    """
    Sends prediction request to the model hosted on AI Platform Prediction service.

    Args:
        instances: List of instances to be predicted.

    Returns:
        Response from the prediction service.
    """
    parameters = {
        "temperature": 0,
        "topP": 0,
        "topK": 1,
    }
    parameters_client = json_format.ParseDict(parameters, Value())
    try:
        response = client.predict(
            endpoint=ENDPOINT, instances=instances, parameters=parameters_client
        )
        return response
    except Exception as e:
        print(e)
        return False


def generate_embeddings(pdf_data):
    """
    Generates embeddings for the given PDF data.

    Args:
        pdf_data: JSON string containing the PDF data.

    Returns:
        JSON response containing the embedding column.
    """
    pdf_data = json.loads(pdf_data)
    instances = []
    values = []

    batch_size = 10
    iterate = 0

    for content in pdf_data.values():
        instance_dict = {"content": content}
        instance = json_format.ParseDict(instance_dict, Value())
        instances.append(instance)
        iterate += 1

        if iterate % batch_size == 0 or iterate == len(pdf_data):
            embeddings = get_embeddings(instances)
            response_json = MessageToDict(embeddings._pb)

            for prediction in response_json["predictions"]:
                embeddings = prediction["embeddings"]
                values.append(embeddings["values"])

            instances = []

    response_json = json.dumps({"embedding_column": values})
    response = json.loads(response_json)
    return response


@functions_framework.http
def hello_http(request):
    """
    HTTP Cloud Function that generates embeddings for the given PDF data.

    Args:
        request (flask.Request): The request object.
        <https://flask.palletsprojects.com/en/1.1.x/api/#incoming-request-data>

    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`
        <https://flask.palletsprojects.com/en/1.1.x/api/#flask.make_response>.
    """
    request_json = request.get_json(silent=True)
    if not request_json or "pdf_data" not in request_json:
        return {"error": "Request body must contain 'pdf_data' field."}, 400
    pdf_data = request_json["pdf_data"]
    return generate_embeddings(pdf_data)
