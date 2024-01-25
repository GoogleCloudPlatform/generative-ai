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
from vertexai.preview.generative_models import GenerativeModel, Part


@functions_framework.http
def list_url(request) -> str | tuple[str, int]:
    print(request)
    try:
        request_json = request.get_json()
        calls = request_json["calls"]
        for call in calls:
            image_url = str(call[0])
            print(image_url)
        return image_url
    except Exception as e:
        return json.dumps({"errorMessage": str(e)}), 400


def analyze_image(image_file) -> str | None:
    gemini_pro_vision_model = GenerativeModel("gemini-pro-vision")
    print(gemini_pro_vision_model)
    image = Part.from_uri(image_file, mime_type="image/jpeg")
    print(image)
    context = """Describe and summarize this image.
      Use no more than 5 sentences to do so"""
    prompt = [context, image]
    print(prompt)
    response = gemini_pro_vision_model.generate_content(prompt, stream=False)
    print(response)
    output = " ".join(response.text.strip().split("\n"))
    print(output)
    return output


def run_it(request) -> str | tuple[str, int]:
    try:
        project_id = os.environ.get("PROJECT_ID")
        region = os.environ.get("REGION")
        vertexai.init(project=project_id, location=region)
        file_to_analyze = list_url(request)
        image_description = analyze_image(file_to_analyze)
        result = image_description or "Unable to generate description"
        return json.dumps({"replies": [result]})
    except Exception as e:
        return json.dumps({"errorMessage": str(e)}), 400
