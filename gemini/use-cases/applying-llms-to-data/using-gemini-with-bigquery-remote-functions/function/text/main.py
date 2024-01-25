# Copyright 2023 Google LLC

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import functions_framework
import json
import os
import vertexai
from vertexai.preview.generative_models import GenerativeModel


@functions_framework.http
def list_text_input(request) -> str | tuple[str, int]:
    print(request)
    try:
        request_json = request.get_json()
        calls = request_json["calls"]
        for call in calls:
            text_prompt = str(call[0])
            print(text_prompt)
        return text_prompt
    except Exception as e:
        return json.dumps({"errorMessage": str(e)}), 400


def generate_text_from_prompt(text_string) -> str | None:
    # this is the text-to-text model
    text_model = GenerativeModel("gemini-pro")
    responses = text_model.generate_content(text_string, stream=False)
    print(responses)
    output = " ".join(responses.text.strip().split("\n"))
    print(output)
    return output


def run_it(request) -> str | tuple[str, int]:
    try:
        project_id = os.environ.get("PROJECT_ID")
        region = os.environ.get("REGION")
        vertexai.init(project=project_id, location=region)
        text_to_analyze = list_text_input(request)
        text_output = generate_text_from_prompt(text_to_analyze)
        result = text_output or "Unable to generate description"
        return json.dumps({"replies": [result]})
    except Exception as e:
        return json.dumps({"errorMessage": str(e)}), 400
