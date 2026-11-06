#!/usr/bin/env python3
# Copyright 2026 Google LLC
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

"""Provision a Vertex AI Search engine over a customer's documentation site.

What this does:
    1. Creates a PUBLIC_WEBSITE data store with advanced indexing enabled.
    2. Adds the supplied URL pattern(s) as INCLUDE target sites.
    3. Optionally registers a sitemap for the data store.
    4. Creates a SEARCH_TIER_ENTERPRISE engine with SEARCH_ADD_ON_LLM.
    5. Prints a `VERTEX_SEARCH_ENGINES` entry you can drop into `.env`.

What it does NOT do:
    - Domain verification. The customer must verify ownership of the
      target domain via Google Search Console (or accept an association
      request). The script prints a reminder at the end.
    - Wait for indexing to complete. Initial crawl takes hours; poll the
      console or list_target_sites to check status.

Usage:
    python scripts/provision_engine.py \\
        --project my-gcp-project \\
        --tenant acme \\
        --origin acme.com \\
        --uri-pattern "docs.acme.com/*" \\
        [--sitemap https://docs.acme.com/sitemap.xml]

Idempotency:
    The data store id is derived from `--tenant`, so re-running with the
    same tenant will fail if resources already exist. Pass `--reuse` to
    skip creates and just print the resulting paths.
"""

# Google Cloud client libraries are imported inside functions so `--help` works
# without them. The two provisioning scripts are intentionally standalone, so
# some setup code is repeated.
# pylint: disable=import-outside-toplevel,duplicate-code

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable


def _client_or_die() -> None:
    """Exits with install instructions if the client library is missing."""
    try:
        from google.api_core import exceptions as gax_exc  # noqa: F401  # pylint: disable=unused-import
        from google.cloud import discoveryengine_v1 as de  # noqa: F401  # pylint: disable=unused-import
    except ImportError:
        print(
            "Missing google-cloud-discoveryengine. Install with:\n"
            "    pip install google-cloud-discoveryengine",
            file=sys.stderr,
        )
        sys.exit(2)


def create_website_data_store(
    project: str,
    tenant: str,
    display_name: str,
    reuse: bool,
) -> str:
    """Creates (or reuses) a website data store; returns its resource path."""
    from google.api_core import exceptions as gax_exc
    from google.cloud import discoveryengine_v1 as de

    client = de.DataStoreServiceClient()
    parent = f"projects/{project}/locations/global/collections/default_collection"
    data_store_id = f"wf-{tenant}"
    full_path = f"{parent}/dataStores/{data_store_id}"

    if reuse:
        print(f"[reuse] data store: {full_path}")
        return full_path

    req = de.CreateDataStoreRequest(
        parent=parent,
        data_store_id=data_store_id,
        create_advanced_site_search=True,
        data_store=de.DataStore(
            display_name=display_name,
            industry_vertical=de.IndustryVertical.GENERIC,
            solution_types=[de.SolutionType.SOLUTION_TYPE_SEARCH],
            content_config=de.DataStore.ContentConfig.PUBLIC_WEBSITE,
        ),
    )
    try:
        op = client.create_data_store(request=req)
        print(f"Creating data store {data_store_id} (LRO {op.operation.name})...")
        op.result(timeout=600)
        print(f"  done: {full_path}")
    except gax_exc.AlreadyExists:
        print(f"  exists, reusing: {full_path}")
    return full_path


def add_target_sites(
    project: str,
    data_store_id: str,
    patterns: Iterable[str],
) -> list[str]:
    """Adds URL patterns as target sites; returns the patterns now present."""
    from google.api_core import exceptions as gax_exc
    from google.cloud import discoveryengine_v1 as de

    client = de.SiteSearchEngineServiceClient()
    parent = (
        f"projects/{project}/locations/global/collections/default_collection"
        f"/dataStores/{data_store_id}/siteSearchEngine"
    )
    created: list[str] = []
    for pattern in patterns:
        clean = pattern.strip().removeprefix("https://").removeprefix("http://")
        if not clean:
            continue
        req = de.CreateTargetSiteRequest(
            parent=parent,
            target_site=de.TargetSite(
                provided_uri_pattern=clean,
                type_=de.TargetSite.Type.INCLUDE,
                exact_match=False,
            ),
        )
        try:
            op = client.create_target_site(request=req)
            op.result(timeout=300)
            print(f"  + target site: {clean}")
            created.append(clean)
        except gax_exc.AlreadyExists:
            print(f"  - already present: {clean}")
            created.append(clean)
    return created


def add_sitemap(project: str, data_store_id: str, sitemap_uri: str) -> None:
    """Submits a sitemap so the data store can discover pages."""
    from google.api_core import exceptions as gax_exc
    from google.cloud import discoveryengine_v1 as de

    client = de.SiteSearchEngineServiceClient()
    parent = (
        f"projects/{project}/locations/global/collections/default_collection"
        f"/dataStores/{data_store_id}/siteSearchEngine"
    )
    req = de.CreateSitemapRequest(
        parent=parent,
        sitemap=de.Sitemap(uri=sitemap_uri),
    )
    try:
        op = client.create_sitemap(request=req)
        op.result(timeout=300)
        print(f"  + sitemap: {sitemap_uri}")
    except gax_exc.AlreadyExists:
        print(f"  - sitemap already present: {sitemap_uri}")
    except AttributeError:
        # SDK version doesn't expose CreateSitemapRequest yet — fall back
        # to printing the REST call the operator can run manually.
        print(
            "  ! SDK does not expose CreateSitemapRequest. Submit manually:\n"
            f"    POST .../dataStores/{data_store_id}/siteSearchEngine/sitemaps?sitemap.uri={sitemap_uri}"
        )


def create_engine(
    project: str,
    tenant: str,
    display_name: str,
    data_store_path: str,
    reuse: bool,
) -> str:
    """Creates (or reuses) a search engine over the data store; returns its path."""
    from google.api_core import exceptions as gax_exc
    from google.cloud import discoveryengine_v1 as de

    client = de.EngineServiceClient()
    parent = f"projects/{project}/locations/global/collections/default_collection"
    engine_id = f"wf-{tenant}"
    full_path = f"{parent}/engines/{engine_id}"

    if reuse:
        print(f"[reuse] engine: {full_path}")
        return full_path

    data_store_id = data_store_path.rsplit("/", 1)[-1]
    req = de.CreateEngineRequest(
        parent=parent,
        engine_id=engine_id,
        engine=de.Engine(
            display_name=display_name,
            data_store_ids=[data_store_id],
            solution_type=de.SolutionType.SOLUTION_TYPE_SEARCH,
            industry_vertical=de.IndustryVertical.GENERIC,
            search_engine_config=de.Engine.SearchEngineConfig(
                search_tier=de.SearchTier.SEARCH_TIER_ENTERPRISE,
                search_add_ons=[de.SearchAddOn.SEARCH_ADD_ON_LLM],
            ),
        ),
    )
    try:
        op = client.create_engine(request=req)
        print(f"Creating engine {engine_id} (LRO {op.operation.name})...")
        op.result(timeout=600)
        print(f"  done: {full_path}")
    except gax_exc.AlreadyExists:
        print(f"  exists, reusing: {full_path}")
    return full_path


def main() -> None:
    """Parses arguments and provisions the website engine."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--project", required=True, help="GCP project id")
    parser.add_argument(
        "--tenant", required=True, help="Tenant slug (lowercase, used as id suffix)"
    )
    parser.add_argument(
        "--origin",
        required=True,
        help="Origin the widget will be embedded on (e.g. acme.com)",
    )
    parser.add_argument(
        "--uri-pattern",
        required=True,
        action="append",
        help="URL pattern to include (repeatable). E.g. 'docs.acme.com/*'",
    )
    parser.add_argument("--sitemap", help="Optional sitemap URL to register")
    parser.add_argument("--display-name", help="Display name for the data store/engine")
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Skip creates; print the expected paths for an already-provisioned tenant",
    )
    args = parser.parse_args()

    _client_or_die()

    display_name = args.display_name or f"Wayfinder · {args.tenant}"

    print(
        f"Provisioning Wayfinder tenant '{args.tenant}' in project '{args.project}'..."
    )
    data_store_path = create_website_data_store(
        args.project, args.tenant, display_name, args.reuse
    )

    if not args.reuse:
        print("Adding target sites:")
        data_store_id = data_store_path.rsplit("/", 1)[-1]
        add_target_sites(args.project, data_store_id, args.uri_pattern)
        if args.sitemap:
            print("Registering sitemap:")
            add_sitemap(args.project, data_store_id, args.sitemap)

    engine_path = create_engine(
        args.project, args.tenant, display_name, data_store_path, args.reuse
    )

    print()
    print("=" * 70)
    print("Add this to VERTEX_SEARCH_ENGINES in your .env (merge with existing JSON):")
    print()
    snippet = {
        args.origin: {
            "website_engine": engine_path,
        }
    }
    print(json.dumps(snippet, indent=2))
    print()
    print("Reminder: verify domain ownership in Google Search Console for the")
    print("indexed hostnames, or grant the indexing account ownership via an")
    print("association request — Vertex AI Search will not crawl unverified sites.")
    print()
    print("Initial crawl typically takes a few hours. Check status in the console")
    print(
        f"or via list_target_sites against parent {data_store_path}/siteSearchEngine."
    )


if __name__ == "__main__":
    main()
