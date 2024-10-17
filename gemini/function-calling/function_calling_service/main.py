# Copyright 2024 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""A Flask app that uses Vertex AI and Nominatim to get address coordinates.

This app takes an address as input and uses the Vertex AI Gemini model to
extract relevant location information. It then uses the Nominatim API to
retrieve the coordinates for the address.
"""

import json
import logging
import os

from flask import Flask, render_template, request
import requests
import vertexai
from vertexai.generative_models import (
    FunctionDeclaration,
    GenerationConfig,
    GenerativeModel,
    Tool,
)

logger = logging.getLogger(__name__)

get_location = FunctionDeclaration(
    name="get_location",
    description="Get latitude and longitude for a given location",
    parameters={
        "type": "object",
        "properties": {
            "poi": {"type": "string", "description": "Point of interest"},
            "street": {"type": "string", "description": "Street name"},
            "city": {"type": "string", "description": "City name"},
            "county": {"type": "string", "description": "County name"},
            "state": {"type": "string", "description": "State name"},
            "country": {"type": "string", "description": "Country name"},
            "postal_code": {"type": "string", "description": "Postal code"},
        },
    },
)

location_tool = Tool(
    function_declarations=[get_location],
)

model = GenerativeModel(
    "gemini-1.5-flash",
    generation_config=GenerationConfig(temperature=0),
    tools=[location_tool],
)

app = Flask(__name__)

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT")
LOCATION = "us-central1"
vertexai.init(project=PROJECT_ID, location=LOCATION)


@app.route("/", methods=["GET", "POST"])
def get_coordinates() -> str:
    """
    Retrieves coordinates for an address using Vertex AI and Nominatim APIs.

    This function handles both GET and POST requests.
    For POST requests, it retrieves the address from the request form and uses
    it to construct a prompt for the Vertex AI model. It then extracts the
    arguments from the function call response and constructs a URL for the
    Nominatim API. Finally, it retrieves the coordinates from the Nominatim API
    and returns them as a JSON object. For GET requests, it simply renders the
    index.html template.
    """
    if request.method == "GET":
        return render_template("index.html")
    address = request.form["address"]
    prompt = f"""
    I want to get the coordinates for the following address:
    {address}
    """
    response = model.generate_content(prompt)

    x = response.candidates[0].function_calls[0].args
    if x is None:
        content = ""
    else:
        url = "https://nominatim.openstreetmap.org/search?"
        for i in x:
            url += f'{i}="{x[i]}&'
        url += "format=json"

        headers = {
            "User-Agent": "Mozilla/5.0 (compatible; Googlebot/2.1; +http://www.google.com/bot.html)"
        }
        x = requests.get(url, headers=headers)
        raw_content = x.json()
        content = json.dumps(raw_content, indent=4)
    return render_template("index.html", content=content)


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
