# Copyright 2022 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Vertex AI Search Demo Constant Definitions"""

PROJECT_ID = "YOUR_PROJECT_ID"
LOCATION = "global"

WIDGET_CONFIGS = [
    {
        "name": "Contracts (Unstructured)",
        "config_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "placeholder": "What is the SLA?",
    },
    {
        "name": "Alphabet Earnings Reports (Unstructured)",
        "config_id": "xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx",
        "placeholder": "What was Google's revenue in 2021?",
    },
]

CUSTOM_UI_DATASTORE_IDS = [
    {
        "name": "Google Cloud Website",
        "datastore_id": "google-cloud-site-search_xxxxxxxx",
    },
    {
        "name": "Google Merchandise Store (Advanced Indexing)",
        "datastore_id": "google-merch-store_xxxxxxxx",
    },
]


IMAGE_SEARCH_DATASTORE_IDs = [
    {
        "name": "Google Merchandise Store",
        "datastore_id": "google-merch-store_xxxxxxx",
    }
]

RECOMMENDATIONS_DATASTORE_IDs = [
    {
        "name": "ArXiv Natural Language Papers",
        "datastore_id": "arxiv_xxxxxxxxxx",
        "engine_id": "arxiv-personalize_xxxxxxxx",
    }
]

# iso639-1 code
# First Index will be default selection
VALID_LANGUAGES = [
    {"code": "en", "name": "English"},
    {"code": "sq", "name": "Albanian"},
    {"code": "ar", "name": "Arabic"},
    {"code": "hy", "name": "Armenian"},
    {"code": "eu", "name": "Basque"},
    {"code": "bn", "name": "Bengali"},
    {"code": "bg", "name": "Bulgarian"},
    {"code": "ca", "name": "Catalan"},
    {"code": "km", "name": "Central Khmer"},
    {"code": "zh", "name": "Chinese"},
    {"code": "hr", "name": "Croatian"},
    {"code": "cs", "name": "Czech"},
    {"code": "da", "name": "Danish"},
    {"code": "nl", "name": "Dutch"},
    {"code": "fil", "name": "Filipino"},
    {"code": "fi", "name": "Finnish"},
    {"code": "fr", "name": "French"},
    {"code": "gl", "name": "Galician"},
    {"code": "de", "name": "German"},
    {"code": "iw", "name": "Hebrew"},
    {"code": "hi", "name": "Hindi"},
    {"code": "hu", "name": "Hungarian"},
    {"code": "is", "name": "Icelandic"},
    {"code": "id", "name": "Indonesian"},
    {"code": "ga", "name": "Irish"},
    {"code": "it", "name": "Italian"},
    {"code": "ja", "name": "Japanese"},
    {"code": "ko", "name": "Korean"},
    {"code": "lo", "name": "Lao"},
    {"code": "lv", "name": "Latvian"},
    {"code": "lt", "name": "Lithuanian"},
    {"code": "el", "name": "Modern Greek"},
    {"code": "no", "name": "Norwegian"},
    {"code": "fa", "name": "Persian"},
    {"code": "pl", "name": "Polish"},
    {"code": "pt", "name": "Portuguese"},
    {"code": "ro", "name": "Romanian"},
    {"code": "ru", "name": "Russian"},
    {"code": "sr", "name": "Serbian"},
    {"code": "sk", "name": "Slovak"},
    {"code": "sl", "name": "Slovenian"},
    {"code": "es", "name": "Spanish"},
    {"code": "sv", "name": "Swedish"},
    {"code": "th", "name": "Thai"},
    {"code": "tr", "name": "Turkish"},
    {"code": "uk", "name": "Ukrainian"},
    {"code": "vi", "name": "Vietnamese"},
]

SUMMARY_MODELS = ["stable", "preview"]
