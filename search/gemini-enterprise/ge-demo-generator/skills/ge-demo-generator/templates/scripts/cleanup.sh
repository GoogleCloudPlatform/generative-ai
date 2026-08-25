#!/bin/bash
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

# =============================================================================
# High-Speed Parallel Cleanup / Teardown Script for GE Demo Environment
# Deletes Cloud Run services, Agent Engine Sandbox, BigQuery datasets, Firestore,
# Discovery Engine Agent registration, DataStores, Pub/Sub topics, and GCS in parallel.
# =============================================================================

set -e

# Load environment variables.
# set -a exports every assignment below (and everything sourced from .env), so
# the inline `python3 - << EOF` heredocs further down can read them via
# os.environ. Without it they are shell-local, every os.environ.get() returns
# the default, and the Agent Engine / Firestore / Discovery Engine teardowns
# no-op while still printing a success line.
set -a

# Same quote-tolerant load as setup_and_deploy.sh, and it matters more here: a
# teardown that dies on line 1 of .env leaves the whole demo billing. See the
# comment there for why an unquoted `COMPANY_NAME=Northwind Cold Chain` is not
# a value but a command.
load_env() {
  # shellcheck source=/dev/null
  source <(awk '
    /^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=/ {
      sub(/\r$/, "")
      eq  = index($0, "=")
      key = substr($0, 1, eq)
      val = substr($0, eq + 1)
      if (val == "" || val ~ /^"/ || val ~ /^'"'"'/ || val ~ /"/) { print; next }
      sub(/[[:space:]]+#.*$/, "", val)
      sub(/[[:space:]]+$/, "", val)
      print key "\"" val "\""
      next
    }
    { print }
  ' "$1")
}

if [ -f .env ]; then
  load_env .env
fi

PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
# Pin every gcloud and bq call to the project `.env` names, exactly as
# setup_and_deploy.sh does - and here it is the difference between a teardown and
# an accident. `gcloud run services delete <name>` with no --project deletes that
# name in whatever project `gcloud config` points at, which is not necessarily
# the demo's.
export CLOUDSDK_CORE_PROJECT="$PROJECT_ID"
REGION=${REGION:-${CLOUD_RUN_REGION:-"asia-northeast1"}}
SERVICE_NAME=${SERVICE_NAME:-""}
BIGQUERY_DATASET=${BIGQUERY_DATASET:-""}
AGENT_ENGINE_NAME=${AGENT_ENGINE_NAME:-""}
# Both buckets are derived exactly as setup_and_deploy.sh derives them, and that
# is the point: defaulting them to "" made every teardown whose .env predated the
# key skip the bucket silently, because the guards below are `[ -n "$BUCKET" ]`.
# The derivation needs DOMAIN_SLUG and SUFFIX, which .env carries. Without them
# there is no safe guess - a wildcard sweep over the project's buckets could take
# a neighbouring demo's - so the run says so out loud rather than skipping quietly.
DOMAIN_SLUG=${DOMAIN_SLUG:-""}
SUFFIX=${SUFFIX:-""}
if [ -n "$DOMAIN_SLUG" ] && [ -n "$SUFFIX" ]; then
  GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-"${PROJECT_ID}-${DOMAIN_SLUG}-${SUFFIX}-docs"}
  DASH_BUCKET=${DASH_BUCKET:-"${PROJECT_ID}-${DOMAIN_SLUG}-${SUFFIX}-dash"}
else
  GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-""}
  DASH_BUCKET=${DASH_BUCKET:-""}
fi
FIRESTORE_COLLECTION=${FIRESTORE_COLLECTION:-""}
# The Discovery Engine authorization setup_and_deploy.sh creates for the
# Workspace paths. Derived the same way it derives it there, so a teardown does
# not depend on .env having gained a key it never had.
AUTH_ID=${AUTH_ID:-"${SERVICE_NAME}-auth"}
# DEMO_ID, not SERVICE_NAME, is what the runtime names its Pub/Sub topics,
# scheduler jobs and task collections after. They differ whenever .env sets one
# without the other, and keying teardown off the wrong one leaves live
# schedulers firing at a deleted service.
DEMO_ID=${DEMO_ID:-"$SERVICE_NAME"}
WORKER_QUEUE=${WORKER_QUEUE:-"${SERVICE_NAME}-worker"}
WORKER_QUEUE_LOCATION=${WORKER_QUEUE_LOCATION:-"us-central1"}

echo "========================================================"
echo "⚡ Starting High-Speed Parallel Teardown of GE Demo"
echo "Project:        $PROJECT_ID"
echo "Region:         $REGION"
echo "Service:        $SERVICE_NAME"
echo "Dataset:        $BIGQUERY_DATASET"
echo "Agent Engine:   $AGENT_ENGINE_NAME"
echo "========================================================"

if [ "$1" != "-y" ] && [ "$1" != "--force" ]; then
  read -r -p "Are you sure you want to delete all provisioned demo resources in parallel? (y/N) " confirm
  if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
    echo "Cleanup cancelled."
    exit 0
  fi
fi

PIDS=()
TOKEN=$(gcloud auth print-access-token 2>/dev/null || echo "")

set +a

# 1. Delete Cloud Run Main Service (Parallel)
if [ -n "$SERVICE_NAME" ]; then
  (
    echo "🗑️  [Parallel] Deleting Cloud Run main service: $SERVICE_NAME..."
    gcloud run services delete "$SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --quiet 2>/dev/null && echo "   ✅ Cloud Run main service deleted." || echo "   ⚠️  Main service not found or already deleted."
  ) &
  PIDS+=($!)
fi

# 2. Delete Data Viewer Cloud Run Service (Parallel)
VIEWER_SERVICE_NAME="ge-viewer-${SERVICE_NAME}"
if [ -n "$SERVICE_NAME" ]; then
  (
    echo "🗑️  [Parallel] Deleting Data Viewer Cloud Run service: $VIEWER_SERVICE_NAME..."
    gcloud run services delete "$VIEWER_SERVICE_NAME" --project="$PROJECT_ID" --region="$REGION" --quiet 2>/dev/null && echo "   ✅ Data Viewer service deleted." || echo "   ⚠️  Data Viewer service not found or already deleted."
  ) &
  PIDS+=($!)
fi

# 3. Delete Agent Engine & Sandboxes (Parallel)
# Pure REST (curl + jq): a bare `python3` here has no vertexai installed - the
# runtime deps live in the container, not on the deployer's machine - so the
# previous SDK heredoc died with ModuleNotFoundError, which `|| true` swallowed
# while the script went on to print "completed successfully". `uv run --with`
# would fix the import; matching setup_and_deploy.sh's own teardown is better
# still, because listing by display name also catches engines a re-run orphaned
# and works when AGENT_ENGINE_NAME never made it into .env.
if [ -n "$AGENT_ENGINE_NAME" ] || [ -n "$SERVICE_NAME" ]; then
  (
    echo "🧪 [Parallel] Deleting Agent Engine & Sandboxes..."
    if ! command -v jq >/dev/null 2>&1; then
      echo "   ⚠️  jq not found - the display-name scan is skipped, so only AGENT_ENGINE_NAME from .env is deleted. Orphaned engines from earlier re-runs will survive."
    fi
    AE_API="https://us-central1-aiplatform.googleapis.com/v1beta1"
    AE_PARENT="projects/${PROJECT_ID}/locations/us-central1"
    AE_DISPLAY="${SERVICE_NAME}-sandbox"
    AE_LIST=""
    AE_PAGE=""
    while :; do
      AE_URL="${AE_API}/${AE_PARENT}/reasoningEngines?pageSize=100"
      if [ -n "$AE_PAGE" ]; then AE_URL="${AE_URL}&pageToken=${AE_PAGE}"; fi
      AE_JSON=$(curl -s -H "Authorization: Bearer ${TOKEN}" "$AE_URL" 2>/dev/null || true)
      AE_LIST="$AE_LIST $(echo "$AE_JSON" | jq -r --arg dn "$AE_DISPLAY" '.reasoningEngines[]? | select(.displayName == $dn) | .name' 2>/dev/null || true)"
      AE_PAGE=$(echo "$AE_JSON" | jq -r '.nextPageToken // empty' 2>/dev/null || true)
      if [ -z "$AE_PAGE" ]; then break; fi
    done
    # The name from .env is a fallback, not the primary source: it is right when
    # the display-name scan is right and it is the only lead when the scan found
    # nothing (a renamed service, a listing permission gap).
    if [ -n "$AGENT_ENGINE_NAME" ]; then AE_LIST="$AE_LIST $AGENT_ENGINE_NAME"; fi
    AE_LIST=$(echo "$AE_LIST" | xargs -n1 2>/dev/null | sort -u || true)
    if [ -z "$AE_LIST" ]; then
      echo "   ⚠️  No Agent Engine named '${AE_DISPLAY}' found (already deleted?)."
    else
      for AE in $AE_LIST; do
        AE_CODE=""
        for AE_TRY in 1 2 3; do
          AE_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "Authorization: Bearer ${TOKEN}" "${AE_API}/${AE}?force=true" 2>/dev/null || true)
          if [ "$AE_CODE" = "429" ]; then sleep $((AE_TRY * 10)); else break; fi
        done
        if [ "$AE_CODE" = "200" ] || [ "$AE_CODE" = "404" ]; then
          echo "   ✅ Agent Engine delete requested: ${AE} (HTTP ${AE_CODE})"
        else
          echo "   ⚠️  Failed to delete ${AE} (HTTP ${AE_CODE}). Delete it manually from the console."
        fi
      done
    fi
  ) &
  PIDS+=($!)
fi

# 3b. Delete the Managed Autonomous Agent (Parallel)
# Separate resource, separate API, separate location: the managed agent lives at
# aiplatform .../locations/global/agents/<id>, not under reasoningEngines, so
# deleting the sandbox above leaves it running. Its id is derived the same way
# create_managed_agent.py derives it.
if [ -n "$SERVICE_NAME" ] && [ -n "$TOKEN" ]; then
  (
    MA_ID="${MANAGED_AGENT_ID:-$(printf '%s' "${SERVICE_NAME}-auto" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9-' '-' | cut -c1-63 | sed 's/-*$//')}"
    echo "🤖 [Parallel] Deleting Managed Autonomous Agent: ${MA_ID}..."
    MA_CODE=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE \
      -H "Authorization: Bearer ${TOKEN}" \
      "https://aiplatform.googleapis.com/v1beta1/projects/${PROJECT_ID}/locations/global/agents/${MA_ID}" 2>/dev/null || true)
    if [ "$MA_CODE" = "200" ]; then
      echo "   ✅ Managed Agent delete requested (long-running; its sandbox environments also expire after 7 idle days)."
    else
      echo "   ⚠️  Managed Agent not found or delete failed (HTTP ${MA_CODE})."
    fi
  ) &
  PIDS+=($!)
fi

# 4. Delete BigQuery Dataset (Parallel)
if [ -n "$BIGQUERY_DATASET" ]; then
  (
    echo "📊 [Parallel] Deleting BigQuery dataset: ${PROJECT_ID}:${BIGQUERY_DATASET}..."
    bq rm -r -f -d "${PROJECT_ID}:${BIGQUERY_DATASET}" 2>/dev/null && echo "   ✅ BigQuery dataset deleted." || echo "   ⚠️  BigQuery dataset not found or already deleted."
  ) &
  PIDS+=($!)
fi

# 5. Delete Pub/Sub Background Topics & Subscriptions (Parallel)
if [ -n "$DEMO_ID" ]; then
  (
    SCHED_TOPIC="${DEMO_ID}-sched-tasks"
    RESULT_TOPIC="${DEMO_ID}-task-results"
    echo "📨 [Parallel] Deleting Pub/Sub topics & subscriptions: ${SCHED_TOPIC}, ${RESULT_TOPIC}..."
    gcloud pubsub subscriptions delete "${SCHED_TOPIC}-push" --project="$PROJECT_ID" --quiet 2>/dev/null || true
    gcloud pubsub subscriptions delete "${RESULT_TOPIC}-push" --project="$PROJECT_ID" --quiet 2>/dev/null || true
    gcloud pubsub topics delete "$SCHED_TOPIC" --project="$PROJECT_ID" --quiet 2>/dev/null || true
    gcloud pubsub topics delete "$RESULT_TOPIC" --project="$PROJECT_ID" --quiet 2>/dev/null || true
    echo "   ✅ Pub/Sub topics and subscriptions deleted."
  ) &
  PIDS+=($!)
fi

# 6. Unregister from Discovery Engine & Delete DataStores (Parallel)
if [ -n "$SERVICE_NAME" ] && [ -n "$TOKEN" ]; then
  (
    echo "📢 [Parallel] Unregistering Gemini Enterprise Agent & DataStores..."
    python3 - <<'__DE_DELETE_EOF__' || true
import os, time, urllib.request, json
project_id = os.environ.get('PROJECT_ID', '')
service_name = os.environ.get('SERVICE_NAME', '')
token = os.environ.get('TOKEN', '')
# Counters, so the summary line reports what actually happened. A silent
# "cleaned up" here is how a demo agent stays registered in someone's Gemini
# Enterprise app long after the Cloud Run service behind it is gone.
deleted_agents = []
deleted_stores = []
failures = []
if project_id and service_name and token:
    headers = {'Authorization': f'Bearer {token}', 'Content-Type': 'application/json', 'X-Goog-User-Project': project_id}
    target_prefixes = [f"ds-{service_name}", service_name]

    def detach_datastores(base_url):
        """Remove this demo's dataStores from every engine that still lists them.

        Not read-your-writes consistent, and a concurrent write on the engine can
        drop the update, so this is called again before every delete retry rather
        than trusted once.
        """
        try:
            req = urllib.request.Request(f"{base_url}/engines", headers=headers)
            with urllib.request.urlopen(req) as resp:
                engines = json.loads(resp.read().decode('utf-8')).get('engines', [])
        except Exception:
            return
        for e in engines:
            app_id = e['name'].split('/')[-1]
            current_ds = e.get('dataStoreIds', [])
            remaining_ds = [ds for ds in current_ds if not any(ds.startswith(p) for p in target_prefixes)]
            if len(remaining_ds) == len(current_ds):
                continue
            try:
                patch_req = urllib.request.Request(f"{base_url}/engines/{app_id}?updateMask=dataStoreIds", data=json.dumps({'dataStoreIds': remaining_ds}).encode('utf-8'), headers=headers, method='PATCH')
                urllib.request.urlopen(patch_req)
            except Exception as err:
                failures.append("detach from engine %s: %s" % (app_id, str(err)[:120]))

    for loc in ['global', 'us', 'eu']:
        ep = 'discoveryengine.googleapis.com' if loc == 'global' else f'{loc}-discoveryengine.googleapis.com'
        base_url = f'https://{ep}/v1alpha/projects/{project_id}/locations/{loc}/collections/default_collection'
        
        # 1. Unregister agents
        try:
            req = urllib.request.Request(f"{base_url}/engines", headers=headers)
            with urllib.request.urlopen(req) as resp:
                engines = json.loads(resp.read().decode('utf-8')).get('engines', [])
                for e in engines:
                    app_id = e['name'].split('/')[-1]
                    
                    # Unregister matching agents
                    ag_url = f"{base_url}/engines/{app_id}/assistants/default_assistant/agents"
                    try:
                        ag_req = urllib.request.Request(ag_url, headers=headers)
                        with urllib.request.urlopen(ag_req) as ag_resp:
                            agents = json.loads(ag_resp.read().decode('utf-8')).get('agents', [])
                            for a in agents:
                                if service_name in a.get('displayName', '') or service_name in a.get('name', ''):
                                    del_req = urllib.request.Request(f"https://{ep}/v1alpha/{a['name']}", headers=headers, method='DELETE')
                                    try:
                                        urllib.request.urlopen(del_req)
                                        deleted_agents.append(a['name'].split('/')[-1])
                                    except Exception as err:
                                        failures.append("agent %s: %s" % (a['name'].split('/')[-1], str(err)[:120]))
                    except Exception:
                        pass
        except Exception:
            pass

        # 2. Detach and delete matching demo DataStores. A dataStore that is
        # still attached to an engine refuses to delete, so retry the pair.
        try:
            ds_req = urllib.request.Request(f"{base_url}/dataStores", headers=headers)
            with urllib.request.urlopen(ds_req) as ds_resp:
                all_ds = json.loads(ds_resp.read().decode('utf-8')).get('dataStores', [])
            pending = [
                ds['name'].split('/')[-1] for ds in all_ds
                if any(ds['name'].split('/')[-1].startswith(p) for p in target_prefixes)]
        except Exception:
            pending = []
        for attempt in range(4):
            if not pending:
                break
            if attempt:
                time.sleep(10)
            detach_datastores(base_url)
            still_pending, last_err = [], None
            for ds_id in pending:
                del_ds_req = urllib.request.Request(f"{base_url}/dataStores/{ds_id}", headers=headers, method='DELETE')
                try:
                    urllib.request.urlopen(del_ds_req)
                    deleted_stores.append(ds_id)
                except Exception as err:
                    still_pending.append(ds_id)
                    last_err = str(err)[:120]
            pending = still_pending
        for ds_id in pending:
            failures.append("dataStore %s could not be deleted after 4 attempts (%s). "
                            "Detach it from the Gemini Enterprise app in the console, "
                            "then delete it there." % (ds_id, last_err))
else:
    failures.append("PROJECT_ID / SERVICE_NAME / access token missing - nothing was attempted")

print("   OK - Gemini Enterprise teardown: %d agent(s), %d dataStore(s) deleted."
      % (len(deleted_agents), len(deleted_stores)))
for f in failures:
    print("   WARNING - " + f)
if not deleted_agents and not failures:
    print("   NOTE - no agent matched '%s'. If one is still listed in the Gemini "
          "Enterprise console, remove it by hand." % service_name)
__DE_DELETE_EOF__

    # 6b. Delete the Workspace OAuth authorization resource.
    # In the same subshell as the agent teardown above, deliberately: an
    # authorization that is still referenced by a registered agent refuses to
    # delete, so this has to run after the unregistration, not beside it.
    # Only the Workspace paths ever create one, hence the existence probe.
    if [ -n "$AUTH_ID" ]; then
      AUTH_URL="https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/authorizations/${AUTH_ID}"
      AUTH_EXISTS=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer ${TOKEN}" -H "X-Goog-User-Project: ${PROJECT_ID}" "$AUTH_URL" 2>/dev/null || true)
      if [ "$AUTH_EXISTS" = "200" ]; then
        AUTH_DEL=$(curl -s -o /dev/null -w "%{http_code}" -X DELETE -H "Authorization: Bearer ${TOKEN}" -H "X-Goog-User-Project: ${PROJECT_ID}" "$AUTH_URL" 2>/dev/null || true)
        if [ "$AUTH_DEL" = "200" ] || [ "$AUTH_DEL" = "204" ]; then
          echo "   OK - Gemini Enterprise authorization ${AUTH_ID} deleted."
        else
          echo "   WARNING - authorization ${AUTH_ID} could not be deleted (HTTP ${AUTH_DEL}). Delete it in the console."
        fi
      fi
    fi
  ) &
  PIDS+=($!)
fi

# 7. Delete Firestore Collection Documents (Parallel)
if [ -n "$FIRESTORE_COLLECTION" ] || [ -n "$DEMO_ID" ]; then
  (
    echo "🔥 [Parallel] Clearing Firestore collections for ${FIRESTORE_COLLECTION:-$DEMO_ID}..."
    # google-cloud-firestore is a container dependency, not something the
    # deployer's interpreter has: a bare `python3` here raised ImportError, and
    # `|| true` turned that into a silent no-op under a "completed successfully"
    # banner. setup_and_deploy.sh already installs uv, so borrow its runner.
    if command -v uv >/dev/null 2>&1; then
      FS_PY=(uv run --no-project --with "google-cloud-firestore>=2.16.0,<3.0.0"
        --with "google-api-core>=2.20.0,<2.35.0" python3)
    else
      FS_PY=(python3)
      echo "   ⚠️  uv not found - falling back to the system python3; if google-cloud-firestore is not installed there, clear the collections by hand."
    fi
    GOOGLE_API_USE_CLIENT_CERTIFICATE=false "${FS_PY[@]}" - <<'__FS_DELETE_EOF__' || true
import os
from google.cloud import firestore
fs_coll = os.environ.get('FIRESTORE_COLLECTION', '')
demo_id = os.environ.get('DEMO_ID', '')
project_id = os.environ.get('PROJECT_ID', '')
# The domain collection is only part of the footprint. Everything the runtime
# writes for itself - the scheduled-task definitions, their execution records,
# the A2A push configs, the managed agent's state, the A2UI action-replay guard
# and the ADK session store - is named "<DEMO_ID>_<something>". Left behind, a
# redeploy of the same demo id reopens on the previous run's task queue, and a
# stale _action_idempotency makes the first press of a re-created A2UI button
# return the previous run's cached result instead of acting.
targets = [c for c in [fs_coll] if c]
if demo_id:
    targets += [demo_id + s for s in (
        "_task_definitions", "_task_executions", "_task_push_configs",
        "_managed_agent_state", "_browser_sessions", "_activity_log",
        "_adk_sessions", "_action_idempotency",
    )]
try:
    db = firestore.Client(project=project_id) if project_id else firestore.Client()
    total = 0
    for coll in targets:
        docs = list(db.collection(coll).stream())
        for doc in docs:
            doc.reference.delete()
        total += len(docs)
    print("   OK - Firestore cleared (%d document(s) across %d collection(s))."
          % (total, len(targets)))
except Exception as err:
    print("   WARNING - Firestore clear failed, documents may remain: " + str(err)[:200])
__FS_DELETE_EOF__
  ) &
  PIDS+=($!)
fi

# 8. Delete GCS Artifact Bucket (Parallel)
if [ -z "$GCS_BUCKET_NAME" ] && [ -z "$DASH_BUCKET" ]; then
  echo "⚠️  Neither GCS_BUCKET_NAME nor DASH_BUCKET is set and DOMAIN_SLUG/SUFFIX are missing,"
  echo "    so the two buckets cannot be named. Delete them by hand - they look like"
  echo "    gs://${PROJECT_ID}-<domain>-<suffix>-docs and -dash, and their objects keep billing."
fi
if [ -n "$GCS_BUCKET_NAME" ]; then
  (
    echo "🪣 [Parallel] Deleting GCS Artifact Bucket: gs://${GCS_BUCKET_NAME}..."
    if gcloud storage rm -r "gs://${GCS_BUCKET_NAME}" --quiet 2>/dev/null; then
      echo "   ✅ GCS Artifact Bucket deleted."
    elif ! gcloud storage buckets describe "gs://${GCS_BUCKET_NAME}" >/dev/null 2>&1; then
      echo "   ⚠️  GCS Artifact Bucket not found or already deleted."
    else
      echo "   ❌ GCS Artifact Bucket gs://${GCS_BUCKET_NAME} still exists - delete it by hand."
    fi
  ) &
  PIDS+=($!)
fi

# 8b. Delete the dashboards bucket (Parallel)
# A second bucket, separate from the artifact bucket above: setup_and_deploy.sh
# creates "<PROJECT>-<DOMAIN_SLUG>-<SUFFIX>-dash" to hold the generated
# dashboards and the multi-agent skill payloads. Its name embeds the run's
# SUFFIX, which is why setup persists DASH_BUCKET to .env; the header re-derives
# it from DOMAIN_SLUG + SUFFIX when the key is absent, and every object in it
# keeps billing until one of the two names resolves.
if [ -n "$DASH_BUCKET" ]; then
  (
    echo "🪣 [Parallel] Deleting dashboards bucket: gs://${DASH_BUCKET}..."
    if gcloud storage rm -r "gs://${DASH_BUCKET}" --quiet 2>/dev/null; then
      echo "   ✅ Dashboards bucket deleted."
    elif ! gcloud storage buckets describe "gs://${DASH_BUCKET}" >/dev/null 2>&1; then
      echo "   ⚠️  Dashboards bucket not found or already deleted."
    else
      echo "   ❌ Dashboards bucket gs://${DASH_BUCKET} still exists - delete it by hand."
    fi
  ) &
  PIDS+=($!)
fi

# 9. Delete Cloud Scheduler jobs & the Cloud Tasks worker queue (Parallel)
# Scheduler jobs are created by the agent at runtime, one per scheduled task
# ("<DEMO_ID>-sched-<task_id>"), so there is no fixed list to delete - they have
# to be discovered. Skipping this is the one leak that keeps costing after
# teardown: the jobs keep firing at a Cloud Run URL that no longer resolves.
if [ -n "$DEMO_ID" ]; then
  (
    echo "⏰ [Parallel] Deleting Cloud Scheduler jobs: ${DEMO_ID}-sched-*..."
    # The job lives in REGION (schedule_autonomous_task builds its parent from
    # the runtime's own region), but older demos put it in us-central1, so both
    # are swept unless they are the same place.
    SCHED_LOCS="$REGION"
    if [ "$REGION" != "us-central1" ]; then
      SCHED_LOCS="$REGION us-central1"
    fi
    _found=0
    for _loc in $SCHED_LOCS; do
      SCHED_JOBS=$(gcloud scheduler jobs list --location="$_loc" --project="$PROJECT_ID" \
        --format="value(name)" 2>/dev/null | grep "${DEMO_ID}-sched-" || true)
      for JOB in $SCHED_JOBS; do
        _found=1
        gcloud scheduler jobs delete "$JOB" --location="$_loc" \
          --project="$PROJECT_ID" --quiet 2>/dev/null &&
          echo "   ✅ Scheduler job deleted: $JOB" ||
          echo "   ⚠️  Failed to delete scheduler job: $JOB"
      done
    done
    if [ "$_found" = "0" ]; then
      echo "   ✅ No scheduler jobs found."
    fi
  ) &
  PIDS+=($!)
fi

if [ -n "$WORKER_QUEUE" ]; then
  (
    echo "📥 [Parallel] Deleting Cloud Tasks queue: ${WORKER_QUEUE}..."
    gcloud tasks queues delete "$WORKER_QUEUE" --location="$WORKER_QUEUE_LOCATION" \
      --project="$PROJECT_ID" --quiet 2>/dev/null &&
      echo "   ✅ Cloud Tasks queue deleted." ||
      echo "   ⚠️  Cloud Tasks queue not found or already deleted."
  ) &
  PIDS+=($!)
fi

# 10. Delete the Maps API key and the demo's Secret Manager secrets (Parallel)
# Both are created by setup_and_deploy.sh. The secret filter is anchored on
# SERVICE_NAME on purpose: the OAuth client secrets (ge-demo-oauth-client-*) are
# shared project-wide across demos and must survive this teardown.
if [ -n "$SERVICE_NAME" ]; then
  (
    echo "🔑 [Parallel] Deleting Maps API key and demo secrets..."
    KEY_NAMES=$(gcloud alpha services api-keys list \
      --filter="displayName:mcp-demo-key-${SERVICE_NAME}" \
      --project="$PROJECT_ID" --format="value(name)" 2>/dev/null || true)
    for KN in $KEY_NAMES; do
      gcloud alpha services api-keys delete "$KN" --project="$PROJECT_ID" --quiet 2>/dev/null &&
        echo "   ✅ API key deleted: $KN" ||
        echo "   ⚠️  Failed to delete API key: $KN"
    done
    DEMO_SECRETS=$(gcloud secrets list --project="$PROJECT_ID" \
      --format="value(name)" 2>/dev/null | grep "$SERVICE_NAME" || true)
    for SEC in $DEMO_SECRETS; do
      gcloud secrets delete "$SEC" --project="$PROJECT_ID" --quiet 2>/dev/null &&
        echo "   ✅ Secret deleted: $SEC" ||
        echo "   ⚠️  Failed to delete secret: $SEC"
    done
    echo "   ✅ Key and secret teardown finished."
  ) &
  PIDS+=($!)
fi

# Wait for all parallel background jobs to complete
echo ""
echo "⏳ Waiting for all parallel cleanup tasks to finish..."
for pid in "${PIDS[@]}"; do
  wait "$pid" 2>/dev/null || true
done

echo ""
echo "========================================================"
# Deliberately not "completed successfully". Every job above is wrapped in
# `|| true` so one failure cannot strand the others, which means this line is
# reached whatever happened - and the old wording turned three silent no-ops
# into a green teardown. The per-resource ✅/⚠️/❌ lines are the actual result.
echo "⚡ Parallel Cleanup finished - review the lines above."
echo "   ✅ = deleted   ⚠️  = already gone or skipped   ❌ = still there, delete by hand"
echo "========================================================"
