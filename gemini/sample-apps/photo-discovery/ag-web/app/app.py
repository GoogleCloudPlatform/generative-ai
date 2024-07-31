# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import json
import os
import re

import requests

#
# Reasoning Engine
#

PROJECT_ID = "<YOUR GOOGLE CLOUD PROJECT ID>"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://<YOUR GCS BUCKET>"
REASONING_ENGINE_ID = "<YOUR REASONING ENGINE ID>"

import vertexai

vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)
from vertexai.preview import reasoning_engines

remote_agent = reasoning_engines.ReasoningEngine(
    f"projects/{PROJECT_ID}/locations/{LOCATION}/reasoningEngines/{REASONING_ENGINE_ID}"
)

#
# Vertex AI Search
#

from google.api_core.client_options import ClientOptions
from google.cloud import discoveryengine_v1 as discoveryengine

SEARCH_ENGINE_ID = "<YOUR SEARCH ENGINE ID>"

search_client_options = ClientOptions(api_endpoint=f"us-discoveryengine.googleapis.com")
search_client = discoveryengine.SearchServiceClient(
    client_options=search_client_options
)
search_serving_config = f"projects/{PROJECT_ID}/locations/us/collections/default_collection/dataStores/{SEARCH_ENGINE_ID}/servingConfigs/default_search:search"

import json


def search_gms(search_query, rows):
    # build a search request
    request = discoveryengine.SearchRequest(
        serving_config=search_serving_config,
        query=search_query,
        page_size=rows,
        query_expansion_spec=discoveryengine.SearchRequest.QueryExpansionSpec(
            condition=discoveryengine.SearchRequest.QueryExpansionSpec.Condition.AUTO,
        ),
        spell_correction_spec=discoveryengine.SearchRequest.SpellCorrectionSpec(
            mode=discoveryengine.SearchRequest.SpellCorrectionSpec.Mode.AUTO
        ),
    )

    # search
    resp_pager = search_client.search(request)

    # parse the results
    response = discoveryengine.SearchResponse(
        results=resp_pager.results,
        facets=resp_pager.facets,
        total_size=resp_pager.total_size,
        attribution_token=resp_pager.attribution_token,
        next_page_token=resp_pager.next_page_token,
        corrected_query=resp_pager.corrected_query,
        summary=resp_pager.summary,
    )
    response_json = json.loads(
        discoveryengine.SearchResponse.to_json(
            response,
            including_default_value_fields=True,
            use_integers_for_enums=False,
        )
    )

    # extract ids
    resp_list = [doc for doc in response_json["results"]]
    return resp_list


#
# Flask app
#

from flask import Flask, request
from flask_cors import CORS

# init Flask app
app = Flask(__name__)
CORS(app)

PROF_ENABLED = False

MAX_RETRIES = 3


# Endpoint for the Flask app to call the Agent
@app.route("/ask_gemini", methods=["GET"])
def ask_gemini():
    query = request.args.get("query")
    print("[ask_gemini] query: " + query)
    retries = 0
    resp = None
    while retries < MAX_RETRIES:
        try:
            retries += 1
            resp = remote_agent.query(input=query)
            if len(resp["output"].strip()) == 0:
                raise ValueError("Empty response.")
            break
        except Exception as e:
            print("[ask_gemini] error: " + str(e))
    if resp == None:
        raise ValueError("Too many retries.")
    return resp["output"]


# Endpoint for the Agent to call Vertex AI Search
@app.route("/ask_gms", methods=["GET"])
def ask_gms():
    query = request.args.get("query")
    item = search_gms(query, 1)[0]["document"]["structData"]
    return json.dumps(item)


# run Flask app
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
