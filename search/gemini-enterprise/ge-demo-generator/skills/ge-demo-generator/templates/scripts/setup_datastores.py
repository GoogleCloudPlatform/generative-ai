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

# Deployed as a runtime template into the user's Cloud Shell (not imported by
# repo tooling); validated by py_compile and end-to-end demo deployments.
# Repo-level strict lint/typing is intentionally skipped for this generated-
# origin runtime code; incremental typing is planned as follow-up.
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# ruff: noqa


import sys
import json
import urllib.request
import urllib.error
import subprocess
import time

if len(sys.argv) < 6:
    print("Usage: setup_datastores.py <endpoint_loc> <project_id> <location> <app_id> <token> <service_name> [gcs_bucket] [bq_dataset] [enable_gcs] [enable_bq]")
    sys.exit(1)

endpoint_loc = sys.argv[1]
project_id = sys.argv[2]
location = sys.argv[3]
app_id = sys.argv[4]
token = sys.argv[5]
service_name = sys.argv[6]
gcs_bucket = sys.argv[7] if len(sys.argv) > 7 else ""
bq_dataset = sys.argv[8] if len(sys.argv) > 8 else ""
enable_gcs = (sys.argv[9].lower() == "true") if len(sys.argv) > 9 else bool(gcs_bucket)
enable_bq = (sys.argv[10].lower() == "true") if len(sys.argv) > 10 else bool(bq_dataset)

endpoint = "discoveryengine.googleapis.com" if endpoint_loc == "global" else f"{endpoint_loc}-discoveryengine.googleapis.com"
base_url = f"https://{endpoint}/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": project_id,
}

def api_call(method, url, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:500]}
    except Exception as e:
        return 0, {"error": str(e)[:500]}

def wait_for_op(op_name, max_wait_sec=60):
    start = time.time()
    while time.time() - start < max_wait_sec:
        code, resp = api_call("GET", f"https://{endpoint}/v1alpha/{op_name}")
        if code == 200 and resp.get("done"):
            return resp
        time.sleep(3)
    return None

created_datastores = []

# 1. Provision GCS Unstructured DataStore
if enable_gcs and gcs_bucket:
    ds_id = f"ds-{service_name}-gcs"
    print(f"📦 Provisioning GCS DataStore: {ds_id} from gs://{gcs_bucket}...")
    
    # Check if exists
    code, resp = api_call("GET", f"{base_url}/dataStores/{ds_id}")
    if code != 200:
        ds_payload = {
            "displayName": f"Demo GCS Documents ({service_name})",
            "industryVertical": "GENERIC",
            "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
            "contentConfig": "CONTENT_REQUIRED",
            "documentProcessingConfig": {
                "defaultParsingConfig": {
                    "digitalParsingConfig": {}
                }
            }
        }
        create_code, create_resp = api_call("POST", f"{base_url}/dataStores?dataStoreId={ds_id}", ds_payload)
        if create_code not in (200, 201):
            print(f"⚠️ Failed to create GCS DataStore ({create_code}): {create_resp.get('error', '')}")
        else:
            print(f"✅ GCS DataStore created: {ds_id}")
    else:
        print(f"ℹ️ GCS DataStore {ds_id} already exists.")

    # Import documents from GCS with dataSchema: "content"
    import_payload = {
        "gcsSource": {
            "inputUris": [f"gs://{gcs_bucket}/*"],
            "dataSchema": "content"
        },
        "reconciliationMode": "FULL"
    }
    imp_code, imp_resp = api_call("POST", f"{base_url}/dataStores/{ds_id}/branches/0/documents:import", import_payload)
    if imp_code in (200, 201, 202):
        print(f"✅ Started GCS document ingestion from gs://{gcs_bucket}/*")
    else:
        print(f"⚠️ Document import returned code {imp_code}: {imp_resp.get('error', '')}")

    created_datastores.append(ds_id)

# 2. Provision BigQuery Structured DataStore & Import Tables
if enable_bq and bq_dataset:
    ds_id = f"ds-{service_name}-bq"
    print(f"📊 Provisioning BigQuery DataStore: {ds_id} from dataset {bq_dataset}...")
    
    code, resp = api_call("GET", f"{base_url}/dataStores/{ds_id}")
    if code != 200:
        ds_payload = {
            "displayName": f"Demo BigQuery Data ({service_name})",
            "industryVertical": "GENERIC",
            "solutionTypes": ["SOLUTION_TYPE_SEARCH"],
            "contentConfig": "NO_CONTENT"
        }
        create_code, create_resp = api_call("POST", f"{base_url}/dataStores?dataStoreId={ds_id}", ds_payload)
        if create_code not in (200, 201):
            print(f"⚠️ Failed to create BigQuery DataStore ({create_code}): {create_resp.get('error', '')}")
        else:
            print(f"✅ BigQuery DataStore created: {ds_id}")
    else:
        print(f"ℹ️ BigQuery DataStore {ds_id} already exists.")

    # Discover BigQuery tables in dataset
    bq_tables = []
    try:
        bq_res = subprocess.run(
            ["bq", "ls", "--format=json", f"{project_id}:{bq_dataset}"],
            capture_output=True,
            text=True
        )
        if bq_res.returncode == 0 and bq_res.stdout.strip():
            items = json.loads(bq_res.stdout.strip())
            for it in items:
                t_ref = it.get("tableReference", {})
                t_id = t_ref.get("tableId", "")
                if t_id:
                    bq_tables.append(t_id)
    except Exception as e:
        print(f"⚠️ Could not list BQ tables via CLI: {e}")

    # Fallback to BigQuery REST API if CLI failed
    if not bq_tables:
        bq_api_url = f"https://bigquery.googleapis.com/bigquery/v2/projects/{project_id}/datasets/{bq_dataset}/tables"
        bq_code, bq_resp = api_call("GET", bq_api_url)
        if bq_code == 200:
            for t_item in bq_resp.get("tables", []):
                t_id = t_item.get("tableReference", {}).get("tableId", "")
                if t_id:
                    bq_tables.append(t_id)

    print(f"  📋 Found {len(bq_tables)} BigQuery tables to ingest: {', '.join(bq_tables) if bq_tables else 'none'}")
    
    # Ingest tables sequentially waiting for branch operations to complete
    for t_id in bq_tables:
        # Ensure BigQuery table has _id column for Discovery Engine document ID
        try:
            table_info_res = subprocess.run(
                ["bq", "show", "--schema", "--format=json", f"{project_id}:{bq_dataset}.{t_id}"],
                capture_output=True, text=True
            )
            if table_info_res.returncode == 0 and table_info_res.stdout.strip():
                schema_json = json.loads(table_info_res.stdout)
                has_id = any(c.get("name") == "_id" for c in schema_json)
                if not has_id and schema_json:
                    pk_col = schema_json[0].get("name", "id")
                    for c in schema_json:
                        if c.get("name", "").endswith("_id") or c.get("name") == "id":
                            pk_col = c.get("name")
                            break
                    print(f"  🔧 Ensuring _id column on BigQuery table {t_id} (mapped to {pk_col})...")
                    alter_query = f"ALTER TABLE `{project_id}.{bq_dataset}.{t_id}` ADD COLUMN IF NOT EXISTS _id STRING; UPDATE `{project_id}.{bq_dataset}.{t_id}` SET _id = CAST({pk_col} AS STRING) WHERE _id IS NULL;"
                    subprocess.run(
                        ["bq", "query", "--use_legacy_sql=false", f"--project_id={project_id}", alter_query],
                        capture_output=True, text=True
                    )
        except Exception as _e:
            print(f"  ⚠️ Could not ensure _id column on table {t_id}: {_e}")

        import_payload = {
            "bigquerySource": {
                "projectId": project_id,
                "datasetId": bq_dataset,
                "tableId": t_id,
                "dataSchema": "custom"
            },
            "reconciliationMode": "INCREMENTAL"
        }
        imp_code, imp_resp = api_call("POST", f"{base_url}/dataStores/{ds_id}/branches/0/documents:import", import_payload)
        if imp_code in (200, 201, 202):
            print(f"  ✅ Started ingestion for table: {t_id}")
            op_name = imp_resp.get("name", "")
            if op_name:
                wait_for_op(op_name, max_wait_sec=30)
        else:
            print(f"  ⚠️ Table {t_id} import returned code {imp_code}: {imp_resp.get('error', '')}")

    created_datastores.append(ds_id)


# 3. Attach created DataStores to Gemini Enterprise Engine (App) via PATCH dataStoreIds
if app_id and created_datastores:
    print(f"🔗 Attaching DataStores to Gemini Enterprise Engine: {app_id}...")
    eng_code, eng_resp = api_call("GET", f"{base_url}/engines/{app_id}")
    if eng_code == 200:
        current_ds_ids = eng_resp.get("dataStoreIds", [])
        updated_ds_ids = list(current_ds_ids)
        for ds in created_datastores:
            if ds not in updated_ds_ids:
                updated_ds_ids.append(ds)
        
        if len(updated_ds_ids) > len(current_ds_ids):
            patch_payload = {"dataStoreIds": updated_ds_ids}
            patch_code, patch_resp = api_call("PATCH", f"{base_url}/engines/{app_id}?updateMask=dataStoreIds", patch_payload)
            if patch_code == 200:
                print(f"   ✅ Successfully attached {len(created_datastores)} DataStores to Engine {app_id}")
            else:
                print(f"   ⚠️ Engine PATCH returned code {patch_code}: {patch_resp.get('error', '')}")
        else:
            print(f"   ℹ️ DataStores already attached to Engine {app_id}")
    else:
        print(f"   ⚠️ Could not fetch Engine {app_id} details (code {eng_code}): {eng_resp.get('error', '')}")

# 4. Save metadata
output_data = {
    "datastores": created_datastores,
    "app_id": app_id,
    "location": location,
    "endpoint": endpoint
}
with open(".datastores.json", "w") as f:
    json.dump(output_data, f, indent=2)

print("DATASTORE_IDS:" + ",".join(created_datastores))
print("✅ Discovery Engine DataStores setup completed successfully.")
