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

"""Flask Web Server"""

import os
import re

from consts import (
    CUSTOM_UI_DATASTORE_IDS,
    LOCATION,
    PROJECT_ID,
    VALID_LANGUAGES,
    WIDGET_CONFIGS,
    PERSONALIZE_DATASTORE_IDs,
)
from ekg_utils import search_public_kg
from flask import Flask, render_template, request
from genappbuilder_utils import (
    list_documents,
    recommend_personalize,
    search_enterprise_search,
)
from google.api_core.exceptions import ResourceExhausted
from werkzeug.exceptions import HTTPException

app = Flask(__name__)

FORM_OPTIONS = {
    "language_list": VALID_LANGUAGES,
    "default_language": VALID_LANGUAGES[0],
}

NAV_LINKS = [
    {"link": "/", "name": "Gen App Builder - Widgets", "icon": "widgets"},
    {
        "link": "/search",
        "name": "Enterprise Search - Custom UI",
        "icon": "build",
    },
    {
        "link": "/recommend",
        "name": "Personalize - Custom UI",
        "icon": "recommend",
    },
    {"link": "/ekg", "name": "Enterprise Knowledge Graph", "icon": "scatter_plot"},
]

PERSONALIZE_DOCUMENTS = list_documents(
    project_id=PROJECT_ID,
    location=LOCATION,
    datastore_id=PERSONALIZE_DATASTORE_IDs[0]["datastore_id"],
)


@app.route("/", methods=["GET"])
@app.route("/finance", methods=["GET"])
def index() -> str:
    """
    Web Server, Homepage for Widgets
    """

    return render_template(
        "index.html",
        nav_links=NAV_LINKS,
        search_engine_options=WIDGET_CONFIGS,
    )


@app.route("/search", methods=["GET"])
def search() -> str:
    """
    Web Server, Homepage for Search - Custom UI
    """
    return render_template(
        "search.html",
        nav_links=NAV_LINKS,
    )


@app.route("/search_genappbuilder", methods=["POST"])
def search_genappbuilder() -> str:
    """
    Handle Search Gen App Builder Request
    """
    search_query = request.form.get("search_query", "")

    # Check if POST Request includes search query
    if not search_query:
        return render_template(
            "search.html",
            nav_links=NAV_LINKS,
            message_error="No query provided",
        )

    results, request_url, raw_request, raw_response = search_enterprise_search(
        project_id=PROJECT_ID,
        location=LOCATION,
        search_engine_id=CUSTOM_UI_DATASTORE_IDS[0]["datastore_id"],
        search_query=search_query,
    )

    return render_template(
        "search.html",
        nav_links=NAV_LINKS,
        message_success=search_query,
        results=results,
        request_url=request_url,
        raw_request=raw_request,
        raw_response=raw_response,
    )


@app.route("/recommend", methods=["GET"])
def recommend() -> str:
    """
    Web Server, Homepage for Personalize - Custom UI
    """
    return render_template(
        "recommend.html",
        nav_links=NAV_LINKS,
        documents=PERSONALIZE_DOCUMENTS,
        attribution_token="",
    )


@app.route("/recommend_genappbuilder", methods=["POST"])
def recommend_genappbuilder() -> str:
    """
    Handle Recommend Gen App Builder Request
    """
    document_id = request.form.get("document_id", "")
    attribution_token = request.form.get("attribution_token", "")

    # Check if POST Request includes document id
    if not document_id:
        return render_template(
            "recommend.html",
            nav_links=NAV_LINKS,
            documents=PERSONALIZE_DOCUMENTS,
            attribution_token=attribution_token,
            message_error="No document provided",
        )

    (
        results,
        attribution_token,
        request_url,
        raw_request,
        raw_response,
    ) = recommend_personalize(
        project_id=PROJECT_ID,
        location=LOCATION,
        datastore_id=PERSONALIZE_DATASTORE_IDs[0]["datastore_id"],
        serving_config_id=PERSONALIZE_DATASTORE_IDs[0]["engine_id"],
        document_id=document_id,
        attribution_token=attribution_token,
    )

    return render_template(
        "recommend.html",
        nav_links=NAV_LINKS,
        documents=PERSONALIZE_DOCUMENTS,
        message_success=document_id,
        results=results,
        attribution_token=attribution_token,
        request_url=request_url,
        raw_request=raw_request,
        raw_response=raw_response,
    )


@app.route("/ekg", methods=["GET"])
def ekg() -> str:
    """
    Web Server, Homepage for EKG
    """

    return render_template("ekg.html", nav_links=NAV_LINKS, form_options=FORM_OPTIONS)


@app.route("/search_ekg", methods=["POST"])
def search_ekg() -> str:
    """
    Handle Search EKG Request
    """
    search_query = request.form.get("search_query", "")

    # Check if POST Request includes search query
    if not search_query:
        return render_template(
            "ekg.html",
            nav_links=NAV_LINKS,
            form_options=FORM_OPTIONS,
            message_error="No query provided",
        )

    languages = request.form.getlist("languages")
    form_types = request.form.get("types", "")

    types = re.split(r"[\s,]", form_types) if form_types else []

    entities, request_url, raw_request, raw_response = search_public_kg(
        project_id=PROJECT_ID,
        location=LOCATION,
        search_query=search_query,
        languages=languages,
        types=types,
    )

    return render_template(
        "ekg.html",
        nav_links=NAV_LINKS,
        form_options=FORM_OPTIONS,
        message_success=search_query,
        entities=entities,
        request_url=request_url,
        raw_request=raw_request,
        raw_response=raw_response,
    )


@app.errorhandler(Exception)
def handle_exception(ex: Exception):
    """
    Handle Application Exceptions
    """
    message_error = "An Unknown Error Occured"

    # Pass through HTTP errors
    if isinstance(ex, HTTPException):
        message_error = ex.get_description()
    elif isinstance(ex, ResourceExhausted):
        message_error = ex.message
    else:
        message_error = str(ex)

    return render_template(
        "search.html",
        form_options=FORM_OPTIONS,
        nav_links=NAV_LINKS,
        message_error=message_error,
    )


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))
