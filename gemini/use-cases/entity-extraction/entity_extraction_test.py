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

"""Tests for entity extraction."""

import json

import entity_extraction


def test_extract_from_document() -> None:
    extract_config_id = "exhibit_2021q1"
    document_uri = "gs://cloud-samples-data/gen-app-builder/search/alphabet-investor-pdfs/2021Q1_alphabet_earnings_release.pdf"
    expected_response = """\
        {
            "google_ceo": "Sundar Pichai",
            "company_name": "Alphabet Inc."
        }
    """

    response = entity_extraction.extract_from_document(
        extract_config_id=extract_config_id, document_uri=document_uri
    )
    assert json.loads(response) == json.loads(expected_response)


if __name__ == "__main__":
    test_extract_from_document()
