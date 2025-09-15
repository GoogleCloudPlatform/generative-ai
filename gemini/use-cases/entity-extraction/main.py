# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Main file for web server."""

import os
import json

from flask import Flask, request, jsonify

import entity_extraction


app = Flask(__name__)

@app.route("/extract", methods=["POST"])
def handle_extraction():
    """HTTP endpoint to handle entity extraction requests."""
    data = request.get_json()
    print(f"received data request: {data}")

    if not data or "extract_config_id" not in data or "document_uri" not in data:
        print("Invalid request data")
        return (
            jsonify(
                {"error": "Request must include 'extract_config_id' and 'document_uri'"}
            ),
            400
        )

    try:
        result_text = (
            entity_extraction.extract_from_document(
                extract_config_id=data["extract_config_id"],
                document_uri=data["document_uri"],
            )
        )
        print(f"Entity extraction result: {result_text}")
        return jsonify(json.loads(result_text)), 200

    except Exception as e:
        print(f"An error occurred: {e}")
        return jsonify({"error": "An internal error occurred."}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
