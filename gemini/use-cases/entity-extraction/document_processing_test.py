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

import document_processing

FORM_10_Q_URI = "gs://cloud-samples-data/gen-app-builder/search/alphabet-investor-pdfs/2021Q1_alphabet_earnings_release.pdf"
FORM_10_K_URI = "gs://cloud-samples-data/gen-app-builder/search/alphabet-investor-pdfs/2021_alphabet_annual_report.pdf"


def test_extract_from_document_10_q() -> None:
    extract_config_id = "form_10_q"
    document_uri = FORM_10_Q_URI
    expected_response = """\
        {
            "year": "2021",
            "quarter": "Q1",
            "company_name": "Alphabet Inc.",
            "ceo": "Sundar Pichai",
            "net_income_millions": "17930"
        }
    """

    response = document_processing.extract_from_document(
        extract_config_id=extract_config_id, document_uri=document_uri
    )
    print(response)
    assert json.loads(response) == json.loads(expected_response)


def test_extract_from_document_10_k() -> None:
    extract_config_id = "form_10_k"
    document_uri = FORM_10_K_URI
    expected_response = """\
        {
            "year": "2021",
            "company_name": "Alphabet Inc.",
            "ceo": "Sundar Pichai",
            "net_income_millions": "76033"
        }
    """

    response = document_processing.extract_from_document(
        extract_config_id=extract_config_id, document_uri=document_uri
    )
    print(response)
    assert json.loads(response) == json.loads(expected_response)

def test_classify_document() -> None:
    document_uri = FORM_10_Q_URI
    expected_response = """\
        {
            "class": "form_10_q"
        }
    """

    response = document_processing.classify_document(document_uri=document_uri)
    print(response)
    assert json.loads(response) == json.loads(expected_response)

def test_classify_and_extract_document() -> None:
    document_uri = FORM_10_Q_URI
    expected_response = """\
        {
            "year": "2021",
            "quarter": "Q1",
            "company_name": "Alphabet Inc.",
            "ceo": "Sundar Pichai",
            "net_income_millions": "17930"
        }
    """

    response = (
        document_processing.classify_and_extract_document(document_uri=document_uri)
    )
    print(response)
    assert json.loads(response) == json.loads(expected_response)

if __name__ == "__main__":
    test_extract_from_document_10_q()
    test_extract_from_document_10_k()
    test_classify_document()
    test_classify_and_extract_document()
    print("All tests passed!")
