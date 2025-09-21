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

import json
import logging
import os

import entity_extraction
from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/extract", methods=["POST"])
def handle_extraction():
    """HTTP endpoint to handle entity extraction requests."""
    data = request.get_json()
    logging.info(f"Received data request: {data}")

    if not data or "extract_config_id" not in data or "document_uri" not in data:
        logging.warning("Invalid request data received. Missing required fields.")
        return (
            jsonify(
                {"error": "Request must include 'extract_config_id' and 'document_uri'"}
            ),
            400,
        )

    try:
        result_text = entity_extraction.extract_from_document(
            extract_config_id=data["extract_config_id"],
            document_uri=data["document_uri"],
        )
        print(f"Entity extraction result: {result_text}")
        return jsonify(json.loads(result_text)), 200

    except KeyError:
        error_msg = f"Configuration with data '{data}' not found."
        logging.info(error_msg)
        return jsonify({"error": error_msg}), 404
    except json.JSONDecodeError:
        error_msg = f"Failed to decode JSON from model response: {result_text}"
        logging.info(error_msg)
        return jsonify(
            {"error": "Failed to parse response from the extraction model."}
        ), 500
    except Exception as e:
        logging.info(f"An unexpected error occurred: {e}")
        return jsonify({"error": "An internal error occurred."}), 500


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
