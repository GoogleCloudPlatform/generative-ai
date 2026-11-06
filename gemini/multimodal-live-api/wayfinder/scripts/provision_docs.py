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

"""Provision a Agent Search engine over uploaded documents (PDFs, etc.).

Use this when you want to ground Wayfinder in a curated set of files instead of
a crawled website — e.g. a handful of product PDFs for a demo.
Unlike the website path, this needs **no Search Console domain verification**.

What this does:
    1. Creates an UNSTRUCTURED data store (content_config = CONTENT_REQUIRED).
    2. (Optional) Uploads a local folder of files to your GCS prefix first.
    3. Imports the documents from GCS into the data store (data_schema="content").
    4. Creates a SEARCH_TIER_ENTERPRISE engine with SEARCH_ADD_ON_LLM
       (so search returns extractive answers + an LLM summary with citations).
    5. Prints a `VERTEX_SEARCH_ENGINES` entry to drop into `.env`.

No backend code changes are needed: Wayfinder's WebsiteSearchPipeline calls the
same `{engine}/servingConfigs/default_search:search` endpoint for any engine type.

Usage:
    # Import PDFs already in GCS:
    python scripts/provision_docs.py \\
        --project my-project \\
        --tenant acme-cloud-docs \\
        --origin acme-cloud \\
        --gcs-uri gs://my-demo-docs/acme-cloud/

    # Upload a local folder of PDFs first, then import:
    python scripts/provision_docs.py \\
        --project my-project \\
        --tenant acme-cloud-docs \\
        --origin acme-cloud \\
        --gcs-uri gs://my-demo-docs/acme-cloud/ \\
        --local-dir ./pdfs

Notes:
    - --gcs-uri is the import source. If it ends with "/", a "*" wildcard is
      appended (all files under the prefix). You may also pass an explicit
      wildcard (e.g. ".../acme-cloud/*.pdf") or a single file.
    - --local-dir uploads only files matching --include (default "*.pdf"),
      so source files that sit next to the PDFs (such as the demo's .html)
      aren't indexed twice. Pass e.g. --include "*.pdf,*.docx" for more types.
    - --origin is the grounding key this engine serves: the widget's
      data-tenant (e.g. `acme-cloud` for the /cloud demo) or the page hostname.
    - Import is asynchronous and can take several minutes; the script waits by
      default. Pass --no-wait to return immediately after kicking it off.

Idempotency:
    Data store / engine ids derive from --tenant (`wf-{tenant}`). Re-running
    with the same tenant reuses existing resources. Pass --reuse to skip the
    create calls entirely and just (optionally) import + print paths.
"""

# Google Cloud client libraries are imported inside functions so `--help` and
# the unit tests work without them. The two provisioning scripts are
# intentionally standalone, so some setup code is repeated.
# pylint: disable=import-outside-toplevel,duplicate-code

from __future__ import annotations

import argparse
import fnmatch
import json
import os
import sys
from collections.abc import Iterable

DEFAULT_INCLUDE = "*.pdf"


def matches_include(filename: str, patterns: Iterable[str]) -> bool:
    """True if filename (case-insensitive) matches any glob pattern, and isn't hidden."""
    if filename.startswith("."):
        return False
    name = filename.lower()
    return any(fnmatch.fnmatch(name, p.strip().lower()) for p in patterns if p.strip())


def _client_or_die(need_storage: bool) -> None:
    """Exits with install instructions if a required client library is missing."""
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
    if need_storage:
        try:
            from google.cloud import storage  # noqa: F401  # pylint: disable=unused-import
        except ImportError:
            print(
                "--local-dir needs google-cloud-storage. Install with:\n"
                "    pip install google-cloud-storage",
                file=sys.stderr,
            )
            sys.exit(2)


def _parse_gcs_uri(gcs_uri: str) -> tuple[str, str]:
    """Return (bucket, prefix) from a gs://bucket/prefix URI."""
    if not gcs_uri.startswith("gs://"):
        print(f"--gcs-uri must start with gs:// (got {gcs_uri!r})", file=sys.stderr)
        sys.exit(2)
    rest = gcs_uri.removeprefix("gs://")
    bucket, _, prefix = rest.partition("/")
    return bucket, prefix


def upload_local_dir(  # pylint: disable=too-many-locals
    local_dir: str, gcs_uri: str, include: Iterable[str] = (DEFAULT_INCLUDE,)
) -> None:
    """Upload files in local_dir that match `include` to the gs://bucket/prefix location."""
    from google.cloud import storage

    if not os.path.isdir(local_dir):
        print(f"--local-dir not found: {local_dir}", file=sys.stderr)
        sys.exit(2)

    patterns = list(include)
    bucket_name, prefix = _parse_gcs_uri(gcs_uri)
    # Treat a trailing-slash prefix as a folder; strip the wildcard if present.
    prefix = prefix.split("*", 1)[0]
    if prefix and not prefix.endswith("/"):
        prefix += "/"

    client = storage.Client()
    bucket = client.bucket(bucket_name)

    uploaded = skipped = 0
    for root, _dirs, files in os.walk(local_dir):
        for fname in files:
            if fname.startswith("."):
                continue
            if not matches_include(fname, patterns):
                skipped += 1
                continue
            local_path = os.path.join(root, fname)
            rel = os.path.relpath(local_path, local_dir).replace(os.sep, "/")
            blob = bucket.blob(prefix + rel)
            blob.upload_from_filename(local_path)
            print(f"  ↑ gs://{bucket_name}/{prefix}{rel}")
            uploaded += 1
    print(
        f"Uploaded {uploaded} file(s) to gs://{bucket_name}/{prefix}"
        + (f" (skipped {skipped} not matching {','.join(patterns)})" if skipped else "")
    )
    if not uploaded:
        print(f"No files in {local_dir} match {','.join(patterns)}.", file=sys.stderr)
        sys.exit(2)


def create_docs_data_store(
    project: str, tenant: str, display_name: str, reuse: bool
) -> str:
    """Creates (or reuses) an unstructured data store; returns its resource path."""
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
        data_store=de.DataStore(
            display_name=display_name,
            industry_vertical=de.IndustryVertical.GENERIC,
            solution_types=[de.SolutionType.SOLUTION_TYPE_SEARCH],
            content_config=de.DataStore.ContentConfig.CONTENT_REQUIRED,
        ),
    )
    try:
        op = client.create_data_store(request=req)
        print(
            f"Creating unstructured data store {data_store_id} (LRO {op.operation.name})..."
        )
        op.result(timeout=600)
        print(f"  done: {full_path}")
    except gax_exc.AlreadyExists:
        print(f"  exists, reusing: {full_path}")
    return full_path


def import_documents(
    project: str, data_store_id: str, input_uris: Iterable[str], wait: bool
) -> None:
    """Imports documents from GCS into the data store, optionally waiting."""
    from google.cloud import discoveryengine_v1 as de

    client = de.DocumentServiceClient()
    parent = (
        f"projects/{project}/locations/global/collections/default_collection"
        f"/dataStores/{data_store_id}/branches/default_branch"
    )
    uris = list(input_uris)
    req = de.ImportDocumentsRequest(
        parent=parent,
        gcs_source=de.GcsSource(input_uris=uris, data_schema="content"),
        reconciliation_mode=de.ImportDocumentsRequest.ReconciliationMode.INCREMENTAL,
    )
    op = client.import_documents(request=req)
    print(f"Importing documents from {uris} (LRO {op.operation.name})...")
    if not wait:
        print(
            "  --no-wait: import running in the background. Check status in the console."
        )
        return
    try:
        resp = op.result(timeout=1800)
        failed = len(getattr(resp, "error_samples", []) or [])
        print(
            f"  import finished (error samples: {failed}). Indexing may continue for a few minutes."
        )
    except Exception as e:  # noqa: BLE001  # pylint: disable=broad-exception-caught  # report, don't abort
        print(f"  import still running or errored: {e}")
        print("  You can re-run with --reuse once it completes, or check the console.")


def create_engine(
    project: str, tenant: str, display_name: str, data_store_path: str, reuse: bool
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
    """Parses arguments and provisions the documents engine."""
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument("--project", required=True, help="Google Cloud project id")
    parser.add_argument(
        "--tenant", required=True, help="Tenant slug (lowercase, used as id suffix)"
    )
    parser.add_argument(
        "--origin",
        required=True,
        help="Grounding key: the widget data-tenant (e.g. acme-cloud) or page hostname",
    )
    parser.add_argument(
        "--gcs-uri",
        required=True,
        help="GCS import source. gs://bucket/prefix/ (a '*' is appended), "
        "an explicit wildcard, or a single file.",
    )
    parser.add_argument(
        "--local-dir",
        help="Optional local folder to upload to --gcs-uri before importing",
    )
    parser.add_argument(
        "--include",
        default=DEFAULT_INCLUDE,
        help="Comma-separated glob patterns of files to upload from --local-dir "
        f"(default: {DEFAULT_INCLUDE})",
    )
    parser.add_argument("--display-name", help="Display name for the data store/engine")
    parser.add_argument(
        "--no-wait",
        action="store_true",
        help="Don't block waiting for the document import LRO",
    )
    parser.add_argument(
        "--reuse",
        action="store_true",
        help="Skip data store / engine creation; just import + print paths",
    )
    args = parser.parse_args()

    _client_or_die(need_storage=bool(args.local_dir))

    display_name = args.display_name or f"Wayfinder docs · {args.tenant}"

    print(
        f"Provisioning Wayfinder docs tenant '{args.tenant}' in project '{args.project}'..."
    )

    if args.local_dir:
        print(f"Uploading local files from {args.local_dir}:")
        upload_local_dir(args.local_dir, args.gcs_uri, args.include.split(","))

    data_store_path = create_docs_data_store(
        args.project, args.tenant, display_name, args.reuse
    )
    data_store_id = data_store_path.rsplit("/", 1)[-1]

    # Build the import URI: append a wildcard if a folder prefix (trailing /) was given.
    import_uri = args.gcs_uri
    if "*" not in import_uri and import_uri.endswith("/"):
        import_uri = import_uri + "*"
    print("Importing documents:")
    import_documents(args.project, data_store_id, [import_uri], wait=not args.no_wait)

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
    print("No domain verification is required for uploaded documents.")
    print(
        "Initial indexing can take a few minutes after import completes; then restart"
    )
    print(
        "the server and ask Wayfinder a 'how do I...' question to see grounded answers."
    )


if __name__ == "__main__":
    main()
