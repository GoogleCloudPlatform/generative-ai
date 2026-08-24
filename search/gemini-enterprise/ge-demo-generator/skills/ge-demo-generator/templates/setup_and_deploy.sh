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
# High-Speed Parallel Setup & Deployment Script for Synthesized GE Demo Environment
# Adheres to optimized Dependency DAG:
# Stage 1: Parallel Pre-requisites (Catalog, Sandbox, Viewer, BQ, Drive)
# Stage 2: Main Multi-Agent Cloud Run Deploy
# Stage 3: Parallel Post-Deployment Wire-up & Gemini Enterprise Registration
# =============================================================================

set -e

# Feature flags are spelled `true`/`false` in .env because a human writes that
# file, but the container compares them with a literal `== "1"` (tools.py,
# fast_api_app.py), so every other spelling reads as OFF at runtime. Normalise
# once here and pass the normalised value to Cloud Run. Handing the .env
# spelling straight through is worse than not passing it at all: agent.py
# accepts "true" and tools.py does not, so the Workspace toolsets would load
# with their auth injection switched off.
bool01() {
  case "$(printf '%s' "${1:-}" | tr '[:upper:]' '[:lower:]')" in
  true | 1 | yes | on) echo 1 ;;
  *) echo 0 ;;
  esac
}

# Load environment variables.
# set -a exports every assignment below (and everything sourced from .env), so
# the inline `python3 - << EOF` heredocs further down can read them via
# os.environ. Without it they are shell-local and every os.environ.get() in
# this script silently returns the default.
set -a

# `.env` is shell, but a human (or the skill) writes it, so its values are not
# reliably quoted - and an unquoted value with a space in it is not a value at
# all. `COMPANY_NAME=Northwind Cold Chain` runs `Chain` as a command with
# COMPANY_NAME=Northwind in its environment, so under `set -e` the whole deploy
# dies on the first line of the file with "Cold: command not found" and no hint
# of what it was trying to do. Multi-word company names are the norm, so quote
# every bare value on the way in. Double quotes rather than single, so a value
# that legitimately references another key still expands, and lines that are
# already quoted (or contain a quote anywhere) are passed through untouched.
load_env() {
  # shellcheck source=/dev/null
  source <(awk '
    /^[[:space:]]*(export[[:space:]]+)?[A-Za-z_][A-Za-z0-9_]*=/ {
      sub(/\r$/, "")
      eq  = index($0, "=")
      key = substr($0, 1, eq)
      val = substr($0, eq + 1)
      if (val == "" || val ~ /^"/ || val ~ /^'"'"'/ || val ~ /"/) { print; next }
      # An unquoted value ends at the first unquoted "#" for `source` too, so
      # dropping the trailing comment here preserves the behaviour rather than
      # changing it.
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

GCP_ACCOUNT=${GCP_ACCOUNT:-$(gcloud config get-value account 2>/dev/null || echo "Unknown")}
PROJECT_ID=${PROJECT_ID:-$(gcloud config get-value project 2>/dev/null)}
# PROJECT_ID comes from `.env` here, so it is free to disagree with whatever
# `gcloud config` happens to point at - and it did: a deploy that announced
# "Target Project: <the .env one>" built the agent into the *config* project,
# because the two `gcloud run deploy` calls below are the only ones in this script
# that never passed --project. Pin the whole process instead of chasing flags:
# every gcloud and bq call, in this shell and in the parallel subshells, now
# resolves to the project the banner names. The explicit --project on the deploys
# stays as well, so the divergence cannot come back one flag at a time.
export CLOUDSDK_CORE_PROJECT="$PROJECT_ID"
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)" 2>/dev/null || echo "")
REGION=${REGION:-${CLOUD_RUN_REGION:-"asia-northeast1"}}
DATASET_ID=${BIGQUERY_DATASET:-"demo_dataset"}
# Extra datasets the agent's scope gate may read beyond its own, for a demo
# that legitimately joins a shared reference dataset or a public table hosted
# outside `bigquery-public-data` (which is exempt already). Semicolon-
# separated, because a comma would end the value inside --set-env-vars.
BQ_ALLOWED_DATASETS=${BQ_ALLOWED_DATASETS:-""}
FIRESTORE_COLLECTION=${FIRESTORE_COLLECTION:-"demo_tasks"}
SERVICE_NAME=${SERVICE_NAME:-"ge-demo-agent"}
AUTH_ID="${SERVICE_NAME}-auth"
COMPANY_NAME=${COMPANY_NAME:-"Demo Enterprise"}
DOMAIN_SLUG=${DOMAIN_SLUG:-"demo"}
SUFFIX=${SUFFIX:-$(date +%s | tail -c 5)}

# DEMO_ID is the runtime's scoping key, not a display string: the background
# task documents, the scheduled-task definitions and the managed agent's
# `<DEMO_ID>_managed_agent_state` collection are all named from it, and the Data
# Viewer resolves the same collections. Agent and viewer MUST be given the same
# value or the dashboard renders an empty console next to a working agent.
DEMO_ID=${DEMO_ID:-"${DOMAIN_SLUG}-${SUFFIX}"}

# Feature flags, normalised to the 1/0 form the container expects.
# Managed Agent is the one default-ON capability: it is what the delegation
# prompts in the demo playbook exercise.
ENABLE_MANAGED_AGENT=$(bool01 "${ENABLE_MANAGED_AGENT:-true}")
# Workspace MCP stays OFF unless explicitly requested. The Workspace MCP servers
# are Developer Preview and the project has to be allowlisted first, so enabling
# it blindly produces an agent whose Workspace tools 403 on every call.
ENABLE_WORKSPACE_MCP=$(bool01 "${ENABLE_WORKSPACE_MCP:-false}")
# Workspace Auth is the commonly useful one (it needs no allowlist), but it is
# still OFF by default: plenty of organizations refuse to authorize an OAuth
# client they have not vetted, and in those the sign-in fails for every demo
# user. Turn it on when the target project's org is known to permit it.
ENABLE_WORKSPACE_AUTH=$(bool01 "${ENABLE_WORKSPACE_AUTH:-false}")
# Computer Use additionally needs the Playwright lines uncommented in BOTH
# requirements.txt and the Dockerfile; the pre-flight below refuses to deploy
# a half-configured build.
ENABLE_COMPUTER_USE=$(bool01 "${ENABLE_COMPUTER_USE:-false}")
# Data exploration mode: how the agent reads the demo's data.
#
#   mcp (default) - Knowledge Catalog + SQL only. No Discovery Engine index is
#     built, imported or scoped, and nothing is registered with the search app.
#     This is NOT the slow path it sounds like: the data-asset catalog is already
#     in the agent's system instruction, so a figure question is ONE execute_sql
#     call. The four-to-five round trips people associate with "no index" came
#     from the METADATA-FIRST rule sending the model on a catalog expedition
#     first, and agent.py's mcp routing block overrides exactly that.
#
#   rag - additionally builds the index and makes it the READ path:
#     search_datastore answers lookups and document questions in one sub-second
#     call, while computed figures and every write stay on MCP because the index
#     lags the tables. Worth the extra provisioning when the demo turns on
#     documents, manuals or reports rather than on numbers.
#
# One switch, not three. The former ENABLE_DATASTORE_BQ / ENABLE_DATASTORE_GCS
# were pure redundancy: a BigQuery connector is only meaningful when there is a
# dataset and a GCS connector only when there is a bucket, so the two resource
# names already carry the answer. setup_datastores.py infers each side from
# whether it was handed a name.
#
# ENABLE_DATASTORE_CONNECTORS is the pre-v11.73 boolean. It is still honoured
# when DATA_EXPLORATION_MODE is unset so an existing invocation keeps working,
# but note the default flipped with it: the boolean used to default to true.
DATA_EXPLORATION_MODE="$(printf '%s' "${DATA_EXPLORATION_MODE:-}" | tr '[:upper:]' '[:lower:]')"
if [ -z "$DATA_EXPLORATION_MODE" ]; then
  if [ -n "${ENABLE_DATASTORE_CONNECTORS:-}" ] && [ "$(bool01 "${ENABLE_DATASTORE_CONNECTORS}")" = "1" ]; then
    DATA_EXPLORATION_MODE="rag"
  else
    DATA_EXPLORATION_MODE="mcp"
  fi
fi
if [ "$DATA_EXPLORATION_MODE" != "rag" ] && [ "$DATA_EXPLORATION_MODE" != "mcp" ]; then
  echo "❌ DATA_EXPLORATION_MODE must be 'mcp' or 'rag' (got '${DATA_EXPLORATION_MODE}')." >&2
  exit 1
fi
# Kept as the single condition the rest of the script branches on, so adding a
# third mode later touches this line rather than every call site.
RAG_MODE=$([ "$DATA_EXPLORATION_MODE" = "rag" ] && echo 1 || echo 0)

# Optional data amplification. Unset (the default) loads exactly the CSVs that
# were generated. Set it to a row count and the hand-written hero rows are
# expanded to that volume before `bq load` runs - deterministically, with the
# hero rows kept verbatim at the top of each file so every id a demo prompt
# names still resolves. Per-table control lives in data/data_scale_spec.json,
# which overrides this number; the number alone applies to the fact tables
# (those with a foreign key) and leaves master data at hero size.
# See scripts/amplify_data.py for the spec format and what it will not do.
DATA_SCALE=${DATA_SCALE:-}

# The unstructured half of the index. Defaulted rather than left unset: with no
# bucket the connectors provision the BigQuery side only, and the demo loses
# exactly the documents-and-reports search the fast path is best at.
GCS_BUCKET_NAME=${GCS_BUCKET_NAME:-"${PROJECT_ID}-${DOMAIN_SLUG}-${SUFFIX}-docs"}

# Deliverables / dashboards bucket. `publish_dashboard` and the managed agent's
# skill mount both read it; unset, the runtime silently drops both features.
DASH_BUCKET=${DASH_BUCKET:-"${PROJECT_ID}-${DOMAIN_SLUG}-${SUFFIX}-dash"}

# Cloud Tasks is the durable transport for background runs. us-central1 is not
# a stray default: the queue only has to be reachable from the service, and
# pinning it decouples the queue from REGION so a demo in a region without
# Cloud Tasks still gets durable background work.
WORKER_QUEUE=${WORKER_QUEUE:-"${SERVICE_NAME}-worker"}
WORKER_QUEUE_LOCATION=${WORKER_QUEUE_LOCATION:-"us-central1"}

# Pub/Sub topic names are dictated by the runtime, which builds them from
# DEMO_ID. Keep these two in sync with tools.py / fast_api_app.py or the
# scheduled-task path breaks without an error anywhere.
SCHED_TOPIC="${DEMO_ID}-sched-tasks"
RESULT_TOPIC="${DEMO_ID}-task-results"
MANAGED_AGENT_ID=${MANAGED_AGENT_ID:-"$(printf '%s' "${SERVICE_NAME}-auto" | tr '[:upper:]' '[:lower:]' | tr -c 'a-z0-9-' '-' | cut -c1-63 | sed 's/-*$//')"}

set +a

echo "================================================================================"
echo "⚡ High-Speed Parallel Deployment of GE Demo Environment"
echo "--------------------------------------------------------------------------------"
echo "👤 Active User Account:  ${GCP_ACCOUNT}"
echo "🏢 Target Project:       ${PROJECT_ID} (${PROJECT_NUMBER})"
echo "🌐 Target Region:        ${REGION}"
echo "🤖 Service Account:      ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo "📊 BigQuery Dataset:     ${DATASET_ID}"
echo "🔥 Firestore Collection: ${FIRESTORE_COLLECTION}"
echo "🤖 Service Name:         ${SERVICE_NAME}"
echo "🆔 Demo ID:              ${DEMO_ID}"
echo "--------------------------------------------------------------------------------"
echo "🤖 Managed Agent:        ${ENABLE_MANAGED_AGENT}   🖥️  Computer Use:      ${ENABLE_COMPUTER_USE}"
echo "🔑 Workspace Auth:       ${ENABLE_WORKSPACE_AUTH}   🔑 Workspace MCP:     ${ENABLE_WORKSPACE_MCP}"
echo "🔎 Data Exploration:     ${DATA_EXPLORATION_MODE}"
echo "================================================================================"

# --- Step 0a: Gemini Enterprise pre-flight ------------------------------------
# This deploy is meant to run unattended and finish with something you can open
# and demo. Exactly one thing in it needs a human decision - starting a free
# trial subscription means accepting terms, and no script may accept those on
# someone's behalf - so that decision is taken HERE, before anything is built,
# instead of after twenty minutes of provisioning.
#
# Three outcomes:
#   an app already exists              nothing to decide. Continue.
#   no app, ACTIVE subscription        the app itself carries no terms, so
#                                      Stage 3 creates it unattended. Continue.
#   no app, no subscription            consent decides. Given (interactively or
#                                      GE_FREE_TRIAL_CONSENT=y), Stage 3 starts
#                                      the trial and creates the app. Refused,
#                                      STOP HERE.
# Stopping is the point. Registration into a Gemini Enterprise app is what makes
# the demo demoable; a run that provisions everything and then reports "there is
# nowhere to register this" costs twenty minutes to reach the same dead end a
# five-second refusal reaches now, and leaves billable resources behind.
echo "🔎 Checking Gemini Enterprise prerequisites..."
gcloud services enable discoveryengine.googleapis.com --project "$PROJECT_ID" >/dev/null 2>&1 || true
_GE_PF_TOKEN=$(gcloud auth print-access-token 2>/dev/null || echo "")
_GE_PF_FOUND=""
# "No app" and "could not tell" are different answers and only one of them may
# stop the run. A listing that comes back as an API error - Discovery Engine not
# enabled yet, or an account without permission to list engines - is not
# evidence that the project has no app, and aborting on it would refuse to
# deploy into a project that is already set up correctly.
_GE_PF_READABLE=""
if [ -n "$_GE_PF_TOKEN" ]; then
  for _PF_LOC in "global" "us" "eu"; do
    _PF_EP="discoveryengine.googleapis.com"
    if [ "$_PF_LOC" != "global" ]; then
      _PF_EP="${_PF_LOC}-discoveryengine.googleapis.com"
    fi
    _PF_JSON=$(curl -s -H "Authorization: Bearer $_GE_PF_TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" \
      "https://${_PF_EP}/v1alpha/projects/$PROJECT_ID/locations/${_PF_LOC}/collections/default_collection/engines" 2>/dev/null || echo "")
    if echo "$_PF_JSON" | grep -q '"error"'; then
      continue
    fi
    _GE_PF_READABLE="yes"
    if echo "$_PF_JSON" | grep -q '"name": "projects/[^"]*/engines/'; then
      _GE_PF_FOUND="$_PF_LOC"
      break
    fi
  done
fi

if [ -n "$_GE_PF_FOUND" ]; then
  echo "   ✅ Gemini Enterprise app found in '${_GE_PF_FOUND}'. The agent will be registered into it."
elif [ -z "$_GE_PF_TOKEN" ] || [ -z "$_GE_PF_READABLE" ]; then
  echo "   ⚠️  Could not check for a Gemini Enterprise app (no access token, or the"
  echo "      engines listing returned an error). This is not proof that none exists,"
  echo "      so the deploy continues; registration is retried after it."
else
  _GE_PF_LICENSE=$(curl -s -H "Authorization: Bearer $_GE_PF_TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" \
    "https://discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_ID/locations/global/licenseConfigs" |
    python3 -c '
import sys, json
try:
    configs = json.load(sys.stdin).get("licenseConfigs", [])
    active = any(c.get("state") == "ACTIVE" and c.get("subscriptionTier") == "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT" for c in configs)
    print("ACTIVE" if active else "INACTIVE")
except Exception:
    print("UNKNOWN")
' 2>/dev/null)

  if [ "$_GE_PF_LICENSE" = "ACTIVE" ]; then
    echo "   ℹ️  No Gemini Enterprise app yet, but this project has an active subscription."
    echo "      One will be created automatically after the deploy."
  else
    echo ""
    echo "⚠️  This project has no Gemini Enterprise app and no active Gemini Enterprise"
    echo "   subscription. The agent cannot be registered - and therefore cannot be"
    echo "   demoed - until one exists."
    echo ""
    echo "   A free trial subscription can be started automatically. Proceeding means"
    echo "   you accept:"
    echo "   - the Terms for data use (https://cloud.google.com/retail/data-use-terms)"
    echo "   - the Gemini Enterprise (Agentspace) quality-of-service terms"
    echo "   A paid subscription is never purchased: the request pins freeTrial=true and"
    echo "   the result is accepted only if the server confirms an ACTIVE free trial."
    _GE_PF_REPLY="${GE_FREE_TRIAL_CONSENT:-}"
    if [ -z "$_GE_PF_REPLY" ] && [ -t 0 ]; then
      read -p "   Start a free trial subscription automatically? (y/n) " -n 1 -r _GE_PF_REPLY
      echo
    fi
    if [[ "$_GE_PF_REPLY" =~ ^[Yy] ]]; then
      # Carry the answer to Stage 3 so the same question is not asked twice.
      export GE_FREE_TRIAL_CONSENT=y
      echo "   ✅ Consent recorded. The trial and the app will be created after the deploy."
    else
      echo ""
      echo "🛑 Stopping before anything is deployed. Nothing has been created and nothing"
      echo "   is being billed."
      echo ""
      echo "   To continue, do ONE of these and re-run: bash setup_and_deploy.sh"
      echo "   1. Create a Gemini Enterprise app in this project:"
      echo "      https://console.cloud.google.com/gemini-enterprise/products?project=$PROJECT_ID"
      echo "   2. Or allow the free trial: re-run and answer 'y', or set"
      echo "      GE_FREE_TRIAL_CONSENT=y in .env for an unattended run."
      echo ""
      exit 1
    fi
  fi
fi

# --- Step 0: Parallel Prerequisites (APIs & IAM Roles) ---
echo "📡 [0/4] Checking APIs & IAM Permissions (Parallel)..."
(
  gcloud services enable \
    run.googleapis.com \
    cloudbuild.googleapis.com \
    artifactregistry.googleapis.com \
    aiplatform.googleapis.com \
    cloudscheduler.googleapis.com \
    cloudtasks.googleapis.com \
    pubsub.googleapis.com \
    bigquery.googleapis.com \
    firestore.googleapis.com \
    dataplex.googleapis.com \
    secretmanager.googleapis.com \
    discoveryengine.googleapis.com \
    mapstools.googleapis.com \
    --project="$PROJECT_ID" 2>/dev/null || true
  # A second call, not more arguments: `gcloud services enable` takes at most 20
  # services and silently rejects the whole batch past that. apikeys is the one
  # that is load-bearing rather than merely tidy - the Maps key is minted with
  # `gcloud alpha services api-keys create` further down, which cannot run
  # without it. The rest are on by default in most projects but not in a bare
  # one, and each is something this script or the runtime actually calls.
  gcloud services enable \
    apikeys.googleapis.com \
    cloudresourcemanager.googleapis.com \
    serviceusage.googleapis.com \
    iam.googleapis.com \
    cloudbilling.googleapis.com \
    logging.googleapis.com \
    monitoring.googleapis.com \
    clouderrorreporting.googleapis.com \
    telemetry.googleapis.com \
    --project="$PROJECT_ID" 2>/dev/null || true
) &
PID_APIS=$!

# Enabling the API is not enough: the agent talks to Google's MANAGED MCP
# endpoints for these services, and each one is enabled separately. Without
# this the BigQuery, Firestore, Knowledge Catalog and Maps toolsets all fail
# to connect - the entire data path - so it runs before anything needs them.
(
  for _mcp_svc in bigquery.googleapis.com firestore.googleapis.com \
    dataplex.googleapis.com mapstools.googleapis.com; do
    gcloud beta services mcp enable "$_mcp_svc" --project="$PROJECT_ID" >/dev/null 2>&1 || true
  done
) &
PID_MCP_SVC=$!

# Workspace APIs, enabled only on the Workspace paths. The auth-only mode still
# needs the plain APIs: the Drive/Gmail calls run with the END USER's OAuth
# token, but the quota is billed to THIS project, so a disabled API fails the
# call with SERVICE_DISABLED no matter how good the token is. The *mcp variants
# are the managed Workspace MCP servers and are a developer-preview allowlist on
# top of that, which is why they are gated separately.
PID_WS_SVC=""
if [ "$ENABLE_WORKSPACE_AUTH" = "1" ] || [ "$ENABLE_WORKSPACE_MCP" = "1" ]; then
  (
    gcloud services enable \
      gmail.googleapis.com \
      drive.googleapis.com \
      calendar-json.googleapis.com \
      chat.googleapis.com \
      people.googleapis.com \
      --project="$PROJECT_ID" 2>/dev/null || true
    if [ "$ENABLE_WORKSPACE_MCP" = "1" ]; then
      gcloud services enable \
        gmailmcp.googleapis.com \
        drivemcp.googleapis.com \
        calendarmcp.googleapis.com \
        chatmcp.googleapis.com \
        --project="$PROJECT_ID" 2>/dev/null || true
    fi
  ) &
  PID_WS_SVC=$!
fi

COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
SCHED_SA="service-${PROJECT_NUMBER}@gcp-sa-cloudscheduler.iam.gserviceaccount.com"
DISCOVERY_ENGINE_SA="service-${PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com"

grant_roles_fast() {
  local project=$1
  local member_prefix=$2
  local member=$3
  shift 3
  local roles_to_grant=("$@")

  local existing_roles
  existing_roles=$(gcloud projects get-iam-policy "$project" \
    --flatten="bindings[].members" \
    --format="value(bindings.role)" \
    --filter="bindings.members:$member_prefix:$member" 2>/dev/null || echo "")

  for role in "${roles_to_grant[@]}"; do
    if ! echo "$existing_roles" | grep -q "$role"; then
      gcloud projects add-iam-policy-binding "$project" \
        --member="$member_prefix:$member" \
        --role="$role" --condition=None >/dev/null 2>&1 || true
    fi
  done
}

(
  grant_roles_fast "$PROJECT_ID" "serviceAccount" "$COMPUTE_SA" \
    "roles/mcp.toolUser" "roles/bigquery.jobUser" "roles/bigquery.dataEditor" \
    "roles/serviceusage.serviceUsageConsumer" "roles/aiplatform.user" "roles/logging.logWriter" \
    "roles/datastore.user" "roles/storage.objectViewer" "roles/artifactregistry.admin" "roles/run.invoker" \
    "roles/pubsub.publisher" "roles/cloudscheduler.admin" "roles/dataplex.catalogViewer" \
    "roles/storage.objectAdmin" "roles/cloudtasks.enqueuer" "roles/secretmanager.secretAccessor" \
    "roles/secretmanager.secretVersionAdder"
  grant_roles_fast "$PROJECT_ID" "serviceAccount" "$SCHED_SA" "roles/pubsub.publisher"
  grant_roles_fast "$PROJECT_ID" "serviceAccount" "$DISCOVERY_ENGINE_SA" "roles/run.invoker"
  # Signed download links are minted through the IAM signBlob API rather than a
  # key file, which needs the runtime SA to impersonate ITSELF. Project-level
  # roles cannot express that; it has to be a binding on the SA resource.
  gcloud iam service-accounts add-iam-policy-binding "$COMPUTE_SA" \
    --member="serviceAccount:$COMPUTE_SA" \
    --role="roles/iam.serviceAccountTokenCreator" \
    --project="$PROJECT_ID" --quiet >/dev/null 2>&1 || true
  if [ ! -z "$GCP_ACCOUNT" ] && [ "$GCP_ACCOUNT" != "Unknown" ]; then
    grant_roles_fast "$PROJECT_ID" "user" "$GCP_ACCOUNT" \
      "roles/mcp.toolUser" "roles/serviceusage.serviceUsageConsumer" "roles/storage.admin" \
      "roles/datastore.user" "roles/iam.serviceAccountUser" "roles/bigquery.jobUser" "roles/bigquery.dataEditor"
  fi
) &
PID_IAM=$!

wait $PID_APIS $PID_MCP_SVC $PID_IAM $PID_WS_SVC 2>/dev/null || true
echo "  ✅ APIs and IAM permissions configured."

_A2UI_PRUNE_LIST=""
if [ "$ENABLE_WORKSPACE_MCP" != "1" ]; then
  _A2UI_PRUNE_LIST="chat_compose calendar_event_compose email_compose drive_file_compose chat_conversation_list drive_file_list contact_list"
fi
# --- Prune few-shot examples for capabilities this demo does not have ---
# a2ui's CatalogConfig globs this directory, so EVERY file left in it is loaded
# into the system prompt whether or not the matching tools are registered. The
# seven Workspace surfaces are 21,793 characters - about 5.5k tokens of the
# ~100k the model prefills on every turn - teaching an agent to compose a Gmail
# draft it has no tool to send. Maps is not on this list: a Maps key is
# provisioned unconditionally, so maps_place_card always has a toolset behind it.
if [ -n "$_A2UI_PRUNE_LIST" ] && [ "$A2UI_KEEP_ALL_EXAMPLES" != "1" ]; then
  _A2UI_PRUNED=0
  for _A2UI_EX in $_A2UI_PRUNE_LIST; do
    if [ -f "adk_agent/app/examples/0.9/${_A2UI_EX}.json" ]; then
      rm -f "adk_agent/app/examples/0.9/${_A2UI_EX}.json"
      _A2UI_PRUNED=$((_A2UI_PRUNED + 1))
    fi
  done
  echo "  OK - pruned $_A2UI_PRUNED A2UI example(s) for disabled capabilities."
fi

# --- Substitute placeholders in the A2UI few-shot examples ---
# The example surfaces ship with a literal [CURRENCY] placeholder so the skill's
# templates stay currency-neutral. Cloud Run loads these files verbatim as few-shot
# examples, so an unsubstituted placeholder teaches the agent to render
# "[CURRENCY]50,000" in its cards. Substitute before the image is built.
CURRENCY_SYMBOL=${CURRENCY_SYMBOL:-'$'}
if [ -d adk_agent/app/examples/0.9 ]; then
  echo "💱 Applying currency symbol '${CURRENCY_SYMBOL}' to the A2UI examples..."
  python3 - "$CURRENCY_SYMBOL" <<'__CURRENCY_EOF__'
import glob
import sys

symbol = sys.argv[1]
changed = 0
for path in sorted(glob.glob("adk_agent/app/examples/0.9/*.json")):
    with open(path, encoding="utf-8") as fh:
        text = fh.read()
    if "[CURRENCY]" not in text:
        continue
    with open(path, "w", encoding="utf-8") as fh:
        fh.write(text.replace("[CURRENCY]", symbol))
    changed += 1
print("  OK - currency placeholder substituted in %d example file(s)." % changed)
__CURRENCY_EOF__
  # Check exactly what the substitution touched, which is exactly what the
  # runtime loads: a2ui's CatalogConfig globs `<examples_path>/*.json`, so the
  # directory's README - which documents the placeholder and must keep saying
  # "[CURRENCY]" - never reaches the model. A recursive grep here fails every
  # deploy on that README.
  if grep -l '\[CURRENCY\]' adk_agent/app/examples/0.9/*.json 2>/dev/null | grep -q .; then
    echo "❌ [CURRENCY] is still present in the A2UI examples. The agent would render it literally."
    exit 1
  fi
fi

# The autonomous agent's system instruction ships as a template with the same
# kind of placeholders. [BUSINESS_CONTEXT] is the skill's job - it is the demo's
# own domain knowledge and cannot be derived here - but the dataset and
# collection names are known at this point, and they matter: the instruction
# tells the sandbox agent, by name, which dataset and collection it must NOT try
# to reach. Left as literals it would name "[DATASET_ID]" and the guardrail
# stops matching anything the delegating assistant says.
if [ -f scripts/managed_agent_instruction.txt ]; then
  MA_INSTR_TMP="scripts/.managed_agent_instruction.tmp"
  sed -e "s|\[DATASET_ID\]|${DATASET_ID}|g" \
    -e "s|\[COLLECTION_ID\]|${FIRESTORE_COLLECTION}|g" \
    scripts/managed_agent_instruction.txt >"$MA_INSTR_TMP" &&
    mv "$MA_INSTR_TMP" scripts/managed_agent_instruction.txt
  if grep -q '\[BUSINESS_CONTEXT\]' scripts/managed_agent_instruction.txt 2>/dev/null; then
    echo "⚠️  scripts/managed_agent_instruction.txt still carries [BUSINESS_CONTEXT]."
    echo "   Delegated tasks will run without this demo's domain knowledge. Fill it in"
    echo "   with the same business context you wrote into agent.py and re-run."
  fi
fi

# --- Data amplification & data-asset catalog ---
# Both steps are local, CPU-only and deterministic, and both have to finish
# before the container image is built: the catalog is baked into the image, and
# it has to describe the CSVs in their final, amplified form. That is why
# amplification is here and not inside the parallel BigQuery job it used to live
# in - nothing waits for that job before the build, so a catalog written
# alongside it would have raced the very rows it claims to count.

# Grow the hand-written hero CSVs to demo-realistic volume. Deterministic and
# idempotent (the hero rows are stashed on the first run and every later run
# amplifies from that stash), so running it here is safe whether or not the
# data-generation phase already did.
if [ -f scripts/amplify_data.py ] && { [ -n "${DATA_SCALE:-}" ] || [ -f data/data_scale_spec.json ]; }; then
  echo "📈 Amplifying demo data to target volume..."
  if [ -f data/data_scale_spec.json ]; then
    python3 scripts/amplify_data.py --data-dir ./data --spec data/data_scale_spec.json \
      ${DATA_SCALE:+--scale "$DATA_SCALE"} 2>&1 | sed 's/^/  /' || true
  else
    python3 scripts/amplify_data.py --data-dir ./data --scale "$DATA_SCALE" 2>&1 | sed 's/^/  /' || true
  fi
  # Not data/*.csv: that glob also matches the *.hero.csv stashes, and
  # rewriting a stash would change what the next run amplifies from.
  for _amp_csv in data/*.csv; do
    case "$_amp_csv" in *.hero.csv) continue ;; esac
    [ -f "$_amp_csv" ] && python3 scripts/validate_csv.py "$_amp_csv" >/dev/null 2>&1 || true
  done
fi

# Write adk_agent/app/data_assets.md - every table, column, row count and date
# range, read straight off the CSVs. agent.py substitutes it into the
# [DATA_ASSET_CATALOG] placeholder at import time, and the instruction's
# "answer from the prompt" and "no rediscovery" rules are only honest because
# of it. Fail-soft: a missing catalog costs discovery round trips, not the demo.
if [ -f scripts/build_data_catalog.py ]; then
  python3 scripts/build_data_catalog.py --data-dir ./data \
    --out adk_agent/app/data_assets.md 2>&1 | sed 's/^/  /' || true
fi

# --- Local Pre-flight Verification ---
if [ -f "scripts/preflight_check.py" ]; then
  echo "🔍 Running Local Pre-flight Verification..."
  python3 scripts/preflight_check.py || {
    echo "❌ Pre-flight check failed! Fix local errors before attempting Cloud Run deployment."
    exit 1
  }
fi

# Computer Use needs a build change, not just a flag: the wheel and the Chromium
# layer live behind commented blocks. With the flag on and the build untouched,
# every browse fails at launch inside Cloud Run - eight minutes after the deploy,
# in front of the audience. Refuse here instead.
if [ "$ENABLE_COMPUTER_USE" = "1" ]; then
  if ! grep -qE '^[[:space:]]*RUN playwright install' Dockerfile 2>/dev/null ||
    ! grep -qE '^[[:space:]]*playwright==' requirements.txt 2>/dev/null; then
    echo "❌ ENABLE_COMPUTER_USE is on but the build is not configured for it."
    echo "   Uncomment the Computer Use block in BOTH requirements.txt (4 lines) and"
    echo "   Dockerfile (the 'RUN playwright install --with-deps chromium' layer), then re-run."
    exit 1
  fi
fi

# Deliverables bucket. Created unconditionally: `publish_dashboard` writes here
# on any turn that produces an HTML report, whether or not the autonomous agent
# exists, and a missing bucket turns every such turn into a 404 at the last step.
gcloud storage buckets create "gs://${DASH_BUCKET}" \
  --project="$PROJECT_ID" --location="$REGION" --uniform-bucket-level-access >/dev/null 2>&1 || true

# --- Stage 0.5: Managed Autonomous Agent, PHASE A (start provisioning) ---
# Creation takes ~8-10 min, so it is fired here and awaited in PHASE B after the
# Cloud Run deploy; the two overlap almost entirely. Everything the agent needs
# at CREATE time (its skill mount) has to exist first, hence the upload below.
MA_SKILLS_SOURCE=""
if [ "$ENABLE_MANAGED_AGENT" = "1" ]; then
  echo "🤖 [0.5/4] Starting Managed Autonomous Agent provisioning (runs in parallel)..."
  if [ -d demo_skills ] && [ -n "$(ls -A demo_skills 2>/dev/null)" ]; then
    if gcloud storage cp -r demo_skills/* "gs://${DASH_BUCKET}/skills/" >/dev/null 2>&1; then
      MA_SKILLS_SOURCE="gs://${DASH_BUCKET}/skills"
      echo "  ✅ Craft skill packs uploaded ($(find demo_skills -name 'SKILL.md' | wc -l | tr -d ' ') packs)."
    else
      echo "  ⚠️  Skill upload failed - the autonomous agent will run without mounted skills."
    fi
  fi

  # create_managed_agent.py reads its system instruction from a sibling file and
  # does not tolerate its absence. Phase 4 of the skill writes it; without it
  # there is nothing to provision, so skip rather than crash the whole deploy.
  if [ ! -f scripts/managed_agent_instruction.txt ]; then
    echo "  ⚠️  scripts/managed_agent_instruction.txt is missing - skipping the autonomous agent."
    echo "     (Write it during scaffolding, then re-run this script to add delegation.)"
    ENABLE_MANAGED_AGENT=0
    MANAGED_AGENT_ID=""
  else
    MA_TOKEN=$(gcloud auth print-access-token 2>/dev/null || echo "")
    MA_OUT="/tmp/ma_start_$$.txt"
    MA_OUT="$MA_OUT" PROJECT_ID="$PROJECT_ID" python3 scripts/create_managed_agent.py \
      start "$MANAGED_AGENT_ID" "$MA_TOKEN" "$MA_SKILLS_SOURCE" 2>&1 | sed 's/^/  /' || true
    MA_START_STATE=$(cat "$MA_OUT" 2>/dev/null || echo "")
    rm -f "$MA_OUT"
    if [ -n "$MA_START_STATE" ]; then
      echo "  ✅ Provisioning started (${MA_START_STATE}) - continuing setup in parallel."
    else
      echo "  ⚠️  Managed Agent could not be started - deploying WITHOUT autonomous delegation."
      ENABLE_MANAGED_AGENT=0
      MANAGED_AGENT_ID=""
    fi
  fi
fi

# --- Stage 1: Parallel Background Initialization Jobs ---
echo "⚡ [1/4] Launching Parallel Infrastructure & Data Pre-requisites..."

# Job 1.1: Fetch A2UI v0.9 Composite Catalog
(
  echo "  📦 [Parallel] Fetching A2UI v0.9 Composite Catalog..."
  mkdir -p adk_agent/app/catalogs
  curl -fsSL "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json" -o adk_agent/app/catalogs/gemini_enterprise_composite_catalog.json 2>/dev/null || true
  echo "  ✅ A2UI Composite Catalog downloaded."
) &
PID_CATALOG=$!

# Job 1.2: Provision Agent Engine Sandbox
(
  echo "  🧪 [Parallel] Provisioning Agent Engine Sandbox..."
  SANDBOX_TMPDIR=$(mktemp -d)
  pushd "$SANDBOX_TMPDIR" >/dev/null 2>&1
  uv run --with "google-cloud-aiplatform[agent_engines]" python3 - <<'__SANDBOX_PROV_EOF__' 2>/dev/null || true
import os, sys, vertexai
from vertexai import types

client = vertexai.Client(project=os.environ.get('PROJECT_ID', ''), location='us-central1')
display_name = os.environ.get('SERVICE_NAME', 'demo') + '-sandbox'

agent_engine = client.agent_engines.create(config={'display_name': display_name})
ae_name = agent_engine.api_resource.name

sandbox_op = client.agent_engines.sandboxes.create(
    name=ae_name,
    config=types.CreateAgentEngineSandboxConfig(display_name='code-sandbox'),
    spec={'code_execution_environment': {}}
)
sandbox_name = sandbox_op.response.name

with open('/tmp/sandbox_result.txt', 'w') as f:
    f.write(ae_name + '|' + sandbox_name)
__SANDBOX_PROV_EOF__
  popd >/dev/null 2>&1
  rm -rf "$SANDBOX_TMPDIR"
  if [ -s /tmp/sandbox_result.txt ]; then
    echo "  ✅ Agent Engine Sandbox provisioned."
  else
    echo "  ⚠️  Agent Engine Sandbox provisioning failed - the agent will fall back to no sandbox."
  fi
) &
PID_SANDBOX=$!

# Job 1.3: Deploy Data Viewer Dashboard (Cloud Run with --no-allow-unauthenticated + IAP)
(
  echo "  🌐 [Parallel] Deploying Data Viewer Cloud Run Dashboard with IAP..."
  VIEWER_LOG=$(mktemp /tmp/viewer-deploy-XXXXXX.log)
  if gcloud run deploy "ge-viewer-${SERVICE_NAME}" \
    --source viewer_app \
    --project "$PROJECT_ID" \
    --region "$REGION" \
    --platform managed \
    --ingress all \
    --no-allow-unauthenticated \
    --min-instances 0 \
    --set-env-vars="PROJECT_ID=${PROJECT_ID},FIRESTORE_COLLECTION=${FIRESTORE_COLLECTION},DEMO_ID=${DEMO_ID},DASHBOARD_TITLE=${DOMAIN_SLUG} Operations Console,SYSTEM_DESCRIPTION=Real-Time Operational Intelligence Dashboard" \
    --format="value(status.url)" >.viewer_url 2>"$VIEWER_LOG"; then

    echo "    🔐 Enabling IAP on the Data Viewer (no public access)..."
    gcloud beta services identity create --service=iap.googleapis.com --project="$PROJECT_ID" >/dev/null 2>&1 || true
    if [ -n "$PROJECT_NUMBER" ]; then
      IAP_SA="service-${PROJECT_NUMBER}@gcp-sa-iap.iam.gserviceaccount.com"
      gcloud run services add-iam-policy-binding "ge-viewer-${SERVICE_NAME}" --region="$REGION" --member="serviceAccount:$IAP_SA" --role="roles/run.invoker" --project="$PROJECT_ID" >/dev/null 2>&1 || true
    fi

    VIEWER_IAP_OK=false
    _IAP_ERR=""
    for _IAP_TRY in 1 2 3; do
      if _IAP_ERR=$(gcloud beta run services update "ge-viewer-${SERVICE_NAME}" --region="$REGION" --iap --project="$PROJECT_ID" 2>&1); then
        VIEWER_IAP_OK=true
        break
      fi
      sleep 10
    done

    DEPLOYER_EMAIL=$(gcloud config get-value account 2>/dev/null || echo "")
    if [ "$VIEWER_IAP_OK" = "true" ]; then
      if [ -n "$DEPLOYER_EMAIL" ]; then
        gcloud beta iap web add-iam-policy-binding --project="$PROJECT_ID" --resource-type=cloud-run --region="$REGION" --service="ge-viewer-${SERVICE_NAME}" --member="user:$DEPLOYER_EMAIL" --role="roles/iap.httpsResourceAccessor" >/dev/null 2>&1 || true
      fi
      echo "  ✅ Data Viewer deployed with IAP enabled. Access granted to: $DEPLOYER_EMAIL"
      echo "  ℹ️  Open the viewer once in your browser before the demo to complete sign-in."
      echo "  ℹ️  Grant more viewers with:"
      echo "      gcloud beta iap web add-iam-policy-binding --project=$PROJECT_ID --resource-type=cloud-run --region=$REGION --service=ge-viewer-${SERVICE_NAME} --member=user:EMAIL --role=roles/iap.httpsResourceAccessor"
    else
      echo "  ⚠️  WARNING: Could not enable IAP on the Data Viewer; disabling viewer."
      echo "  ℹ️  Last error was: $_IAP_ERR"
      rm -f .viewer_url
    fi
  else
    if grep -q "run.allowedIngress" "$VIEWER_LOG" 2>/dev/null; then
      echo "  🚧 Cause: org policy 'constraints/run.allowedIngress' does not allow public ingress."
      echo "     If you hold Org Policy Admin, run: gcloud resource-manager org-policies allow constraints/run.allowedIngress all --project=$PROJECT_ID"
    fi
    echo "  ⚠️  Data Viewer deploy skipped (optional component)."
    rm -f .viewer_url
  fi
  rm -f "$VIEWER_LOG"
) &
PID_VIEWER=$!

# Job 1.4: BigQuery Dataset Provisioning & Parallel Table Loading
(
  echo "  📊 [Parallel] Provisioning BigQuery Dataset & Tables..."
  # US, not $REGION, to match the Web UI. A dataset's location is fixed at
  # creation, and the two consumers that matter are location-sensitive in
  # opposite directions: the Discovery Engine BigQuery connector imports from a
  # global datastore, and the public sample datasets a demo may join against
  # (bigquery-public-data) live in US - a query cannot cross locations. A
  # single-region dataset also has to be recreated, not moved, to fix either.
  bq show "${PROJECT_ID}:${DATASET_ID}" >/dev/null 2>&1 || bq --location=US mk -d "${PROJECT_ID}:${DATASET_ID}" 2>/dev/null || true

  # The CSVs are amplified and catalogued synchronously before this job starts -
  # see "Data amplification & data-asset catalog" above - because the row counts
  # and date ranges the agent's prompt states have to be the ones that get loaded.

  BQ_LOAD_PIDS=()
  for csv_file in data/*.csv; do
    # Skip the amplifier's hero stashes for the same reason the loop above does,
    # with a worse failure mode here: `basename foo.hero.csv .csv` is "foo.hero",
    # and `bq load dataset.foo.hero` is not a table name, so every amplified run
    # would fire a load that can only fail - silently, since the error is
    # swallowed by `|| true`.
    case "$csv_file" in *.hero.csv) continue ;; esac
    if [ -f "$csv_file" ]; then
      (
        tbl=$(basename "$csv_file" .csv)
        bq load --source_format=CSV --autodetect --skip_leading_rows=1 --replace "${DATASET_ID}.${tbl}" "$csv_file" >/dev/null 2>&1 || true
        if [ -f "data/${tbl}_schema.json" ]; then
          bq update "${DATASET_ID}.${tbl}" "data/${tbl}_schema.json" >/dev/null 2>&1 || true
        fi
        # Table-level description. Column descriptions alone leave the entry
        # Knowledge Catalog harvests without a grain sentence ("what is one row
        # here?"), which is the first thing both a human browsing the Console and
        # `lookup_entry` want. build_data_catalog.py wrote this file, so what
        # Catalog reports and what the agent's prompt states are the same text,
        # down to the row count and the coverage window.
        if [ -f "data/${tbl}_bqdescription.txt" ]; then
          bq update --description "$(cat "data/${tbl}_bqdescription.txt")" "${DATASET_ID}.${tbl}" >/dev/null 2>&1 || true
        fi
      ) &
      BQ_LOAD_PIDS+=($!)
    fi
  done
  for bq_p in "${BQ_LOAD_PIDS[@]}"; do
    wait "$bq_p" 2>/dev/null || true
  done
  echo "  ✅ BigQuery tables and Knowledge Catalog schemas loaded."
) &
PID_BQ=$!

# Job 1.5: Generate External Files (PDF, Excel, Images) and upload to Google Drive
(
  if [ -f scripts/generate_and_upload_external_files.py ]; then
    echo "  📁 [Parallel] Generating External Files & Uploading to Google Drive..."
    # The generator always rewrites all four files, so it MUST be handed this
    # demo's spec. Without --spec-file it falls back to deliberately generic
    # placeholder content ("Counterparty A", "REF-0101") - and because this step
    # runs at deploy time, that placeholder version is what overwrites the
    # documents Phase 3 wrote, what gets staged to GCS, and what the datastore
    # indexes. The cross-source prompt then has nothing to cross-reference.
    EXT_SPEC_ARG=""
    [ -f data/external_files_spec.json ] && EXT_SPEC_ARG="--spec-file ./data/external_files_spec.json"
    EXT_LOG=$(mktemp /tmp/ge-extfiles-XXXXXX.log)
    uv run --with "openpyxl,reportlab,pillow" python3 scripts/generate_and_upload_external_files.py \
      --domain "$DOMAIN_SLUG" \
      --company "$COMPANY_NAME" \
      --suffix "$SUFFIX" \
      $EXT_SPEC_ARG \
      --outdir "./external_files" >"$EXT_LOG" 2>&1 || true
    # The folder is owned by whoever the gdrive CLI is signed in as - a CLI owns
    # whatever it creates - and the deploy target is added as Writer. When the
    # CLI is absent or unauthenticated the upload is skipped entirely, which is
    # not an error, but announcing "uploaded to Google Drive" either way sent
    # operators looking for a folder that was never created.
    if grep -q '"folder_url": "http' external_files/drive_upload_summary.json 2>/dev/null; then
      echo "  ✅ External sample files generated and uploaded to Google Drive."
    else
      echo "  ✅ External sample files generated in ./external_files (Drive upload skipped)."
      grep -A5 'Skipping the Google Drive upload' "$EXT_LOG" 2>/dev/null | sed 's/^/     /' || true
    fi
    rm -f "$EXT_LOG"
  fi
) &
PID_DRIVE=$!

# Job 1.6: Pre-create Pub/Sub topics
# The names are NOT free-form: the runtime derives them from DEMO_ID
# ("<DEMO_ID>-sched-tasks" in schedule_autonomous_task, "<DEMO_ID>-task-results"
# in the execute_task worker). DEMO_ID defaults to "<DOMAIN_SLUG>-<SUFFIX>",
# which is not SERVICE_NAME, so naming these after the service silently
# publishes into a topic nothing is listening on and every scheduled task
# vanishes.
(
  gcloud pubsub topics create "$SCHED_TOPIC" --project="$PROJECT_ID" 2>/dev/null || true
  gcloud pubsub topics create "$RESULT_TOPIC" --project="$PROJECT_ID" 2>/dev/null || true
) &

# Job 1.6b: Cloud Tasks queue for background work
# The runtime enqueues here instead of calling itself over localhost, so a
# background run survives the turn that started it, retries when the instance is
# recycled, and can wake a service that has scaled to zero. This service deploys
# with --min-instances 0, so without the queue every background task is stuck on
# the localhost fallback, which dies with the process and cannot wake a cold
# instance (see the transport note in tools.py). max-concurrent-dispatches
# matches the runtime's worker semaphore so work queues instead of piling up
# inside one container.
(
  gcloud tasks queues create "$WORKER_QUEUE" \
    --location="$WORKER_QUEUE_LOCATION" \
    --max-attempts=5 \
    --max-concurrent-dispatches=2 \
    --max-dispatches-per-second=5 \
    --min-backoff=15s \
    --max-backoff=300s \
    --project="$PROJECT_ID" >/dev/null 2>&1 ||
    gcloud tasks queues resume "$WORKER_QUEUE" \
      --location="$WORKER_QUEUE_LOCATION" --project="$PROJECT_ID" >/dev/null 2>&1 || true
) &

# Job 1.7: Initialize Firestore Collection with domain operational data
(
  echo "  🔥 [Parallel] Initializing Firestore Collection & Seeding Data..."
  # A project that has never used Firestore has no database, and nothing here
  # created one - the Web UI script does, this one did not. On a clean project
  # that meant: the seed failed into /dev/null, the line below still printed a
  # tick, the managed agent could not store its environment id, and the deployed
  # agent's task queue, background jobs and scheduled tasks all had nowhere to
  # write. Create it first, in the demo's own region.
  if ! gcloud firestore databases describe --database="(default)" \
    --project="$PROJECT_ID" >/dev/null 2>&1; then
    echo "    Creating the Firestore database in $REGION (first use in this project)..."
    _FS_ERR=$(gcloud firestore databases create --location="$REGION" \
      --project="$PROJECT_ID" 2>&1) || true
    if ! gcloud firestore databases describe --database="(default)" \
      --project="$PROJECT_ID" >/dev/null 2>&1; then
      # Not every Cloud Run region is a Firestore location. us-central1 always
      # is, and a demo with a working task queue in the wrong region beats a
      # demo with no task queue at all.
      echo "    ⚠️  Could not create it in $REGION; falling back to us-central1."
      echo "       Last error was: $(echo "$_FS_ERR" | tail -n 1)"
      gcloud firestore databases create --location="us-central1" \
        --project="$PROJECT_ID" >/dev/null 2>&1 || true
    fi
  fi

  if [ -f scripts/setup_fs.py ]; then
    # Report what happened. The seed silently failing is exactly the case that
    # has to be visible: every Firestore-backed feature of the demo depends on it.
    if _FS_SEED_OUT=$(uv run --with "google-cloud-firestore>=2.16.0,<3.0.0" \
      python3 scripts/setup_fs.py \
      --project "$PROJECT_ID" \
      --collection "$FIRESTORE_COLLECTION" 2>&1); then
      echo "  ✅ Firestore Collection seeded."
    else
      echo "  ⚠️  Firestore seeding FAILED - the task queue and background jobs will"
      echo "      have nothing to read. Last error was:"
      echo "      $(echo "$_FS_SEED_OUT" | tail -n 1)"
    fi
  fi
) &
PID_FIRESTORE=$!

# --- Wait for Main Cloud Run Build Dependencies ---
echo "⏳ Synchronizing build pre-requisites (Sandbox, Viewer, Catalog, Firestore)..."
wait $PID_CATALOG 2>/dev/null || true
wait $PID_SANDBOX 2>/dev/null || true
wait $PID_VIEWER 2>/dev/null || true
wait $PID_FIRESTORE 2>/dev/null || true

SANDBOX_RESULT=$(cat /tmp/sandbox_result.txt 2>/dev/null || echo "|")
rm -f /tmp/sandbox_result.txt
AGENT_ENGINE_NAME=$(echo "$SANDBOX_RESULT" | cut -d'|' -f1)
SANDBOX_RESOURCE_NAME=$(echo "$SANDBOX_RESULT" | cut -d'|' -f2)
VIEWER_URL=$(cat .viewer_url 2>/dev/null || echo "")

# Persist the provisioned Agent Engine to .env. scripts/cleanup.sh reads
# AGENT_ENGINE_NAME from there; without this the teardown silently skips the
# Agent Engine and leaves it billing.
if [ -n "$AGENT_ENGINE_NAME" ] && [ -f .env ] && ! grep -q '^AGENT_ENGINE_NAME=' .env; then
  {
    echo "AGENT_ENGINE_NAME=${AGENT_ENGINE_NAME}"
    echo "SANDBOX_RESOURCE_NAME=${SANDBOX_RESOURCE_NAME}"
  } >>.env
fi

# Same reason, for the names that are DERIVED here rather than supplied. DEMO_ID
# defaults to "<DOMAIN_SLUG>-<SUFFIX>" and SUFFIX defaults to a timestamp, so a
# teardown run later cannot recompute either one - it would guess a different
# suffix and walk past the scheduler jobs, topics and task collections entirely.
# DOMAIN_SLUG and GCS_BUCKET_NAME are here for the same reason as DASH_BUCKET:
# cleanup.sh guards each bucket on the name being non-empty, so an unpersisted
# name is a bucket that is skipped in silence and keeps billing.
if [ -f .env ]; then
  for _kv in "DEMO_ID=${DEMO_ID}" "SUFFIX=${SUFFIX}" "WORKER_QUEUE=${WORKER_QUEUE}" \
    "WORKER_QUEUE_LOCATION=${WORKER_QUEUE_LOCATION}" \
    "DASH_BUCKET=${DASH_BUCKET}" "DOMAIN_SLUG=${DOMAIN_SLUG}" \
    "GCS_BUCKET_NAME=${GCS_BUCKET_NAME}"; do
    if ! grep -q "^${_kv%%=*}=" .env; then
      echo "$_kv" >>.env
    fi
  done
  # Only when it exists: an empty value would still satisfy `grep -q` on a later
  # run and pin the key to blank, and cleanup.sh re-derives it anyway.
  if [ -n "$MANAGED_AGENT_ID" ] && ! grep -q '^MANAGED_AGENT_ID=' .env; then
    echo "MANAGED_AGENT_ID=${MANAGED_AGENT_ID}" >>.env
  fi
fi

# --- Stage 2: Deploy Main Multi-Agent Service (Cloud Run) ---
echo "🤖 [2/4] Deploying Main Multi-Agent Service to Cloud Run..."

# Every capability in this runtime is switched on by an environment variable, not
# by the code that was shipped: the templates read the flags at import time rather
# than being generated with the feature already compiled in. A variable that is
# not passed here is therefore not "left at its default", it is OFF, and the
# corresponding tool answers {"status": "unavailable"} for the life of the demo.
CR_ENV_VARS="PROJECT_ID=${PROJECT_ID}"
CR_ENV_VARS="${CR_ENV_VARS},GOOGLE_CLOUD_PROJECT=${PROJECT_ID}"
# The Interactions API that backs the managed agent is global-only; a regional
# value here makes every delegated task 404.
CR_ENV_VARS="${CR_ENV_VARS},GOOGLE_CLOUD_LOCATION=global"
CR_ENV_VARS="${CR_ENV_VARS},BIGQUERY_DATASET=${DATASET_ID}"
if [ -n "$BQ_ALLOWED_DATASETS" ]; then
  CR_ENV_VARS="${CR_ENV_VARS},BQ_ALLOWED_DATASETS=${BQ_ALLOWED_DATASETS}"
fi
CR_ENV_VARS="${CR_ENV_VARS},FIRESTORE_COLLECTION=${FIRESTORE_COLLECTION}"
CR_ENV_VARS="${CR_ENV_VARS},DEMO_ID=${DEMO_ID}"
CR_ENV_VARS="${CR_ENV_VARS},SANDBOX_RESOURCE_NAME=${SANDBOX_RESOURCE_NAME}"
CR_ENV_VARS="${CR_ENV_VARS},AGENT_ENGINE_NAME=${AGENT_ENGINE_NAME}"
CR_ENV_VARS="${CR_ENV_VARS},DATA_VIEWER_URL=${VIEWER_URL}"
CR_ENV_VARS="${CR_ENV_VARS},GEMINI_AUTHORIZATION_ID=${AUTH_ID}"
CR_ENV_VARS="${CR_ENV_VARS},DASHBOARDS_BUCKET=${DASH_BUCKET}"
# The demo's external sample documents are staged in this bucket in EVERY mode,
# and import_demo_files_to_my_drive reads it to copy them into the signed-in
# user's own Drive. Without the name that tool has nothing to list and answers
# "not configured" - which is how those documents reach a user's Drive whenever
# the deploy-time gdrive upload did not happen or could not be shared with them.
CR_ENV_VARS="${CR_ENV_VARS},GCS_BUCKET_NAME=${GCS_BUCKET_NAME}"
# When the deploy-time upload DID land, the agent gets the folder link: it can
# point the user at the documents they already have, and the unprompted import
# stands down instead of dropping a second copy in their My Drive.
DEPLOYED_DRIVE_FOLDER_URL=""
if [ -f external_files/drive_upload_summary.json ]; then
  DEPLOYED_DRIVE_FOLDER_URL=$(jq -r '.folder_url // empty' external_files/drive_upload_summary.json 2>/dev/null || echo "")
fi
if [ -n "$DEPLOYED_DRIVE_FOLDER_URL" ]; then
  CR_ENV_VARS="${CR_ENV_VARS},DRIVE_FOLDER_URL=${DEPLOYED_DRIVE_FOLDER_URL}"
fi
# publish_dashboard signs URLs by impersonating the runtime identity; without the
# address it cannot name the principal to sign as and returns unsigned links.
CR_ENV_VARS="${CR_ENV_VARS},RUNTIME_SA_EMAIL=${COMPUTE_SA}"
CR_ENV_VARS="${CR_ENV_VARS},WORKER_QUEUE=${WORKER_QUEUE}"
CR_ENV_VARS="${CR_ENV_VARS},WORKER_QUEUE_LOCATION=${WORKER_QUEUE_LOCATION}"
# One MCP server failing to start must degrade to "that toolset is missing",
# not to a dead agent; and ADK's JSON-schema conversion rejects the recursive
# schemas some MCP servers publish, which surfaces as a deterministic 500.
CR_ENV_VARS="${CR_ENV_VARS},ADK_ENABLE_MCP_GRACEFUL_ERROR_HANDLING=1"
CR_ENV_VARS="${CR_ENV_VARS},ADK_DISABLE_JSON_SCHEMA_FOR_FUNC_DECL=1"
CR_ENV_VARS="${CR_ENV_VARS},ENABLE_WORKSPACE_MCP=${ENABLE_WORKSPACE_MCP}"
CR_ENV_VARS="${CR_ENV_VARS},ENABLE_WORKSPACE_AUTH=${ENABLE_WORKSPACE_AUTH}"
CR_ENV_VARS="${CR_ENV_VARS},ENABLE_COMPUTER_USE=${ENABLE_COMPUTER_USE}"
CR_ENV_VARS="${CR_ENV_VARS},ENABLE_MANAGED_AGENT=${ENABLE_MANAGED_AGENT}"
# Picks agent.py's data-exploration routing block, and gates whether
# search_datastore is registered at all.
CR_ENV_VARS="${CR_ENV_VARS},DATA_EXPLORATION_MODE=${DATA_EXPLORATION_MODE}"
CR_ENV_VARS="${CR_ENV_VARS},AGENT_MODEL=${AGENT_MODEL:-gemini-3.7-flash}"
CR_ENV_VARS="${CR_ENV_VARS},AGENT_MODEL_LITE=${AGENT_MODEL_LITE:-gemini-3.7-flash}"
if [ "$ENABLE_MANAGED_AGENT" = "1" ]; then
  # MANAGED_AGENT_ID is the whole switch on the tool side: the delegation tools
  # check it before the flag and report "unavailable" when it is blank, so an
  # agent deployed with the flag on and the id missing looks broken rather than
  # disabled. PHASE A above clears both together when provisioning cannot start.
  CR_ENV_VARS="${CR_ENV_VARS},MANAGED_AGENT_ID=${MANAGED_AGENT_ID}"
  CR_ENV_VARS="${CR_ENV_VARS},MANAGED_AGENT_SKILLS_SOURCE=${MA_SKILLS_SOURCE:-}"
fi

# Maps. get_maps_mcp_toolset() returns None when MAPS_API_KEY is unset, which
# drops the geospatial tools silently - and the demo playbook mandates one
# prompt that needs them. The key goes through Secret Manager, not
# --set-env-vars, so it is not readable in the service description. Named after
# the demo so cleanup's suffix match removes it with everything else.
MAPS_SECRET="${SERVICE_NAME}-maps-key"
if ! gcloud secrets describe "$MAPS_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  echo "🔑 Provisioning the Maps API key..."
  MAPS_KEY=$(gcloud alpha services api-keys create \
    --display-name="mcp-demo-key-${SERVICE_NAME}" \
    --api-target=service=mapstools.googleapis.com \
    --project="$PROJECT_ID" --format="value(keyString)" 2>/dev/null || echo "")
  if [ -z "$MAPS_KEY" ]; then
    MAPS_KEY=$(gcloud alpha services api-keys list \
      --filter="displayName:mcp-demo-key-${SERVICE_NAME}" \
      --project="$PROJECT_ID" --format="value(keyString)" 2>/dev/null || echo "")
  fi
  if [ -n "$MAPS_KEY" ]; then
    printf '%s' "$MAPS_KEY" | gcloud secrets create "$MAPS_SECRET" \
      --data-file=- --replication-policy="automatic" --project="$PROJECT_ID" >/dev/null 2>&1 || true
  else
    echo "  ⚠️  Could not mint a Maps API key - the geospatial tools stay off."
  fi
fi

# Workspace credentials come from Secret Manager rather than --set-env-vars so
# the client secret is not readable in the service description. Bound only when
# a Workspace path is actually on, because a missing secret fails the deploy.
SECRETS_FLAG=""
if gcloud secrets describe "$MAPS_SECRET" --project="$PROJECT_ID" >/dev/null 2>&1; then
  SECRETS_FLAG="--update-secrets=MAPS_API_KEY=${MAPS_SECRET}:latest"
fi
if [ "$ENABLE_WORKSPACE_MCP" = "1" ] || [ "$ENABLE_WORKSPACE_AUTH" = "1" ]; then
  if gcloud secrets describe ge-demo-oauth-client-id --project="$PROJECT_ID" >/dev/null 2>&1 &&
    gcloud secrets describe ge-demo-oauth-client-secret --project="$PROJECT_ID" >/dev/null 2>&1; then
    if [ -n "$SECRETS_FLAG" ]; then
      SECRETS_FLAG="${SECRETS_FLAG},OAUTH_CLIENT_ID=ge-demo-oauth-client-id:latest,OAUTH_CLIENT_SECRET=ge-demo-oauth-client-secret:latest"
    else
      SECRETS_FLAG="--update-secrets=OAUTH_CLIENT_ID=ge-demo-oauth-client-id:latest,OAUTH_CLIENT_SECRET=ge-demo-oauth-client-secret:latest"
    fi
  else
    echo "  ⚠️  Workspace is enabled but the OAuth client secrets are not provisioned."
    echo "     Create ge-demo-oauth-client-id / ge-demo-oauth-client-secret, then re-run."
  fi
fi

# Scale-to-zero by default: an idle demo costs nothing between conversations.
# Three things make that safe -- background runs go through Cloud Tasks so they
# survive the turn that started them, ADK sessions are mirrored to Firestore and
# rehydrated on a cold start, and a worker heartbeat plus an abandoned-run sweep
# finalize anything that dies with a recycled instance. The cost is a cold start
# on the first message after an idle gap (measured ~+25s). Export MIN_INSTANCES=1
# before running this script to keep a warm instance for a live presentation.
MIN_INSTANCES="${MIN_INSTANCES:-0}"

# --no-cpu-throttling and --cpu-boost are what keep a turn responsive: without
# them the container loses CPU between streamed chunks and a cold start crawls.
# --max-instances 1 makes the process-local state the runtime relies on (per
# session locks, the regenerate cache, the worker semaphore) actually true; one
# instance serves up to 80 concurrent requests, so it is not a throughput ceiling
# at demo scale. 8Gi is sized for the sandbox and the data-generation paths.
# --no-allow-unauthenticated + --ingress internal is the posture the Web UI ships:
# Gemini Enterprise reaches the service over Google-internal traffic, so nothing
# needs to be exposed publicly.
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --project "$PROJECT_ID" \
  --region "$REGION" \
  --platform managed \
  --memory 8Gi \
  --cpu 2 \
  --no-cpu-throttling \
  --cpu-boost \
  --min-instances "$MIN_INSTANCES" \
  --max-instances 1 \
  --timeout 1800 \
  --no-allow-unauthenticated \
  --ingress internal \
  --labels "created-by=adk" \
  --set-env-vars="$CR_ENV_VARS" \
  --quiet \
  $SECRETS_FLAG

AGENT_URL=$(gcloud run services describe "$SERVICE_NAME" --region="$REGION" --format="value(status.url)" 2>/dev/null || echo "")
echo "  ✅ Agent Service URL: $AGENT_URL"

# --- Stage 3: Post-Deployment Registration & Wire-up ---
echo "⚡ [3/4] Running Post-Deployment Wire-up & Registration..."
TOKEN=$(gcloud auth print-access-token 2>/dev/null || echo "")

# Discover Gemini Enterprise App ID with valid Assistant support
SELECTED_APP_ID=""
SELECTED_LOC="global"
for LOC in "global" "us" "eu"; do
  ENDPOINT="discoveryengine.googleapis.com"
  if [ "$LOC" != "global" ]; then
    ENDPOINT="${LOC}-discoveryengine.googleapis.com"
  fi
  ENGINES_JSON=$(curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" "https://${ENDPOINT}/v1alpha/projects/$PROJECT_ID/locations/${LOC}/collections/default_collection/engines" 2>/dev/null || echo "{}")

  # Check engines in this location for assistants
  for E_NAME in $(echo "$ENGINES_JSON" | grep -o '"name": "projects/[^/]*/locations/[^/]*/collections/default_collection/engines/[^"]*"' | cut -d'"' -f4); do
    AST_JSON=$(curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" "https://${ENDPOINT}/v1alpha/${E_NAME}/assistants" 2>/dev/null || echo "{}")
    if echo "$AST_JSON" | grep -q "default_assistant"; then
      SELECTED_APP_ID=$(echo "$E_NAME" | awk -F'/' '{print $NF}')
      SELECTED_LOC="$LOC"
      break 2
    fi
  done
done

# If still not found by assistants check, fallback to subscription tier filter
if [ -z "$SELECTED_APP_ID" ]; then
  for LOC in "global" "us" "eu"; do
    ENDPOINT="discoveryengine.googleapis.com"
    if [ "$LOC" != "global" ]; then
      ENDPOINT="${LOC}-discoveryengine.googleapis.com"
    fi
    ENGINES_JSON=$(curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" "https://${ENDPOINT}/v1alpha/projects/$PROJECT_ID/locations/${LOC}/collections/default_collection/engines" 2>/dev/null || echo "{}")
    FOUND_APP=$(echo "$ENGINES_JSON" | grep -B2 -A10 "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT" | grep -o '"name": "projects/[^/]*/locations/[^/]*/collections/default_collection/engines/[^"]*"' | head -n 1 | cut -d'"' -f4)
    if [ ! -z "$FOUND_APP" ]; then
      SELECTED_APP_ID=$(echo "$FOUND_APP" | awk -F'/' '{print $NF}')
      SELECTED_LOC="$LOC"
      break
    fi
  done
fi

# No app anywhere: say so, then create one - the same recovery the Web UI script
# offers. Everything the deploy just built (agent, data, viewer) is fine; without
# an app there is only nothing to register it WITH, and on a clean project that
# is the normal case, not an error. Two-step recovery, both server-verified:
#   1. an ACTIVE Gemini Enterprise subscription (license config) must exist -
#      if not, a FREE TRIAL can be started, but ONLY with explicit consent to
#      the data-use and quality-of-service terms (interactive y/n, or
#      GE_FREE_TRIAL_CONSENT=y in .env for unattended runs). freeTrial is
#      pinned true and the result is accepted only if the server confirms an
#      ACTIVE free trial - a paid subscription is never purchased.
#   2. the app itself carries no terms, so with an active subscription it is
#      created without asking.
if [ -z "$SELECTED_APP_ID" ]; then
  echo ""
  echo "⚠️  No Gemini Enterprise app was found in this project ('global', 'us' or 'eu')."
  echo "   The agent needs one to be registered into. Creating one now..."
  GE_LICENSE_STATE=$(curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" \
    "https://discoveryengine.googleapis.com/v1alpha/projects/$PROJECT_ID/locations/global/licenseConfigs" |
    python3 -c '
import sys, json
try:
    configs = json.load(sys.stdin).get("licenseConfigs", [])
    active = any(c.get("state") == "ACTIVE" and c.get("subscriptionTier") == "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT" for c in configs)
    print("ACTIVE" if active else "INACTIVE")
except Exception:
    print("UNKNOWN")
' 2>/dev/null)

  if [ "$GE_LICENSE_STATE" != "ACTIVE" ]; then
    echo "ℹ️  No active Gemini Enterprise subscription was found in this project."
    echo "   A free trial subscription can be started automatically. Proceeding means"
    echo "   you accept:"
    echo "   - the Terms for data use (https://cloud.google.com/retail/data-use-terms)"
    echo "   - the Gemini Enterprise (Agentspace) quality-of-service terms"
    _GE_TRIAL_REPLY="${GE_FREE_TRIAL_CONSENT:-}"
    if [ -z "$_GE_TRIAL_REPLY" ] && [ -t 0 ]; then
      read -p "   Start a free trial subscription automatically? (y/n) " -n 1 -r _GE_TRIAL_REPLY
      echo
    fi
    if [[ "$_GE_TRIAL_REPLY" =~ ^[Yy] ]]; then
      TRIAL_OUT=$(
        python3 - "$PROJECT_ID" "$TOKEN" <<'PYEOF'
import sys, json, time, datetime, urllib.request, urllib.error
project_id, token = sys.argv[1], sys.argv[2]
headers = {
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "X-Goog-User-Project": project_id,
}
api = "https://discoveryengine.googleapis.com/v1alpha/"

# Step 1: provision the project for Discovery Engine / Gemini Enterprise.
# This creates the default user store required by license configs. Idempotent
# on already-provisioned projects. The user consented to the terms above.
prov_body = {
    "acceptDataUseTerms": True,
    "dataUseTermsVersion": "2022-11-23",
    "saasParams": {"acceptBizQos": True},
}
req = urllib.request.Request(
    api + "projects/" + project_id + ":provision",
    data=json.dumps(prov_body).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        op = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("TRIAL_FAIL: provisioning failed: HTTP " + str(e.code) + " " + e.read().decode("utf-8")[:300])
    sys.exit(1)
except Exception as e:
    print("TRIAL_FAIL: provisioning failed: " + str(e))
    sys.exit(1)
deadline = time.time() + 120
while not op.get("done") and op.get("name") and time.time() < deadline:
    time.sleep(5)
    try:
        with urllib.request.urlopen(urllib.request.Request(api + op["name"], headers=headers)) as resp:
            op = json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
if not op.get("done") or op.get("error"):
    print("TRIAL_FAIL: provisioning did not complete: " + json.dumps(op.get("error") or {})[:300])
    sys.exit(1)

# Step 2: create the free trial license config. freeTrial is pinned to True
# and the result is only accepted if the server confirms an ACTIVE free
# trial - a paid subscription is NEVER purchased automatically.
# The server validates startDate as "future" against Pacific time, so
# passing today's local date fails with 400 whenever local date == PT date.
# Always send tomorrow: the server still activates the trial immediately
# (state=ACTIVE) and normalizes the term to one month.
start = datetime.date.today() + datetime.timedelta(days=1)
end = start + datetime.timedelta(days=30)
body = {
    "subscriptionTier": "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT",
    "licenseCount": "50",
    "subscriptionTerm": "SUBSCRIPTION_TERM_CUSTOM",
    "startDate": {"year": start.year, "month": start.month, "day": start.day},
    "endDate": {"year": end.year, "month": end.month, "day": end.day},
    "freeTrial": True,
}
url = (
    api + "projects/" + project_id
    + "/locations/global/licenseConfigs?licenseConfigId=free_trial_agent_space")
req = urllib.request.Request(url, data=json.dumps(body).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        data = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("TRIAL_FAIL: HTTP " + str(e.code) + " " + e.read().decode("utf-8")[:300])
    sys.exit(1)
except Exception as e:
    print("TRIAL_FAIL: " + str(e))
    sys.exit(1)
if data.get("freeTrial") is True and data.get("state") == "ACTIVE":
    print("TRIAL_OK")
else:
    print("TRIAL_FAIL: the created config is not a confirmed active free trial"
          + " (state=" + str(data.get("state")) + ", freeTrial=" + str(data.get("freeTrial"))
          + "). Please check the Gemini Enterprise console.")
    sys.exit(1)
PYEOF
      ) || true
      if echo "$TRIAL_OUT" | grep -q "^TRIAL_OK"; then
        echo "   ✅ Free trial subscription activated."
        GE_LICENSE_STATE="ACTIVE"
      else
        echo "   ⚠️  Could not start a free trial automatically:"
        # shellcheck disable=SC2001  # per-line prefix, not a substring swap
        echo "$TRIAL_OUT" | sed 's/^/      /'
      fi
    else
      echo "   ⏭️  Skipping the free trial (no consent given). To allow it on an"
      echo "      unattended run, set GE_FREE_TRIAL_CONSENT=y in .env."
    fi
  fi

  if [ "$GE_LICENSE_STATE" = "ACTIVE" ]; then
    echo "   ⏳ Creating the Gemini Enterprise app (this can take a minute or two)..."
    CREATE_OUT=$(
      python3 - "$PROJECT_ID" "$TOKEN" <<'PYEOF'
import sys, json, time, urllib.request, urllib.error
project_id, token = sys.argv[1], sys.argv[2]
headers = {
    "Authorization": "Bearer " + token,
    "Content-Type": "application/json",
    "X-Goog-User-Project": project_id,
}
engine_id = "gemini-enterprise-" + str(int(time.time()))
base = ("https://discoveryengine.googleapis.com/v1alpha/projects/" + project_id
        + "/locations/global/collections/default_collection/engines")
body = {
    "displayName": "Gemini Enterprise",
    "solutionType": "SOLUTION_TYPE_SEARCH",
    "appType": "APP_TYPE_INTRANET",
    "industryVertical": "GENERIC",
    "searchEngineConfig": {
        "searchTier": "SEARCH_TIER_ENTERPRISE",
        "searchAddOns": ["SEARCH_ADD_ON_LLM"],
        "requiredSubscriptionTier": "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT",
    },
}
req = urllib.request.Request(
    base + "?engineId=" + engine_id,
    data=json.dumps(body).encode("utf-8"), headers=headers)
try:
    with urllib.request.urlopen(req) as resp:
        op = json.loads(resp.read().decode("utf-8"))
except urllib.error.HTTPError as e:
    print("CREATE_FAIL: HTTP " + str(e.code) + " " + e.read().decode("utf-8")[:300])
    sys.exit(1)
except Exception as e:
    print("CREATE_FAIL: " + str(e))
    sys.exit(1)
op_name = op.get("name", "")
deadline = time.time() + 180
while op_name and not op.get("done") and time.time() < deadline:
    time.sleep(5)
    try:
        poll = urllib.request.Request("https://discoveryengine.googleapis.com/v1alpha/" + op_name, headers=headers)
        with urllib.request.urlopen(poll) as resp:
            op = json.loads(resp.read().decode("utf-8"))
    except Exception:
        pass
if op.get("error"):
    print("CREATE_FAIL: " + json.dumps(op["error"])[:300])
    sys.exit(1)
# Wait until the new app is visible in the engines list (later steps re-list it).
while time.time() < deadline:
    try:
        lst = urllib.request.Request(base, headers=headers)
        with urllib.request.urlopen(lst) as resp:
            engines = json.loads(resp.read().decode("utf-8")).get("engines", [])
        if any(e.get("name", "").endswith("/" + engine_id) for e in engines):
            print("GE_APP_CREATED:" + engine_id)
            sys.exit(0)
    except Exception:
        pass
    time.sleep(5)
print("CREATE_FAIL: the app did not appear in the engines list within the timeout")
sys.exit(1)
PYEOF
    ) || true
    GE_APP_CREATED=$(echo "$CREATE_OUT" | grep "^GE_APP_CREATED:" | cut -d':' -f2)
    if [ ! -z "$GE_APP_CREATED" ]; then
      SELECTED_APP_ID="$GE_APP_CREATED"
      SELECTED_LOC="global"
      echo "   ✅ Created Gemini Enterprise app: $GE_APP_CREATED (location: global)"
    else
      echo "   ⚠️  Automatic app creation failed:"
      # shellcheck disable=SC2001  # per-line prefix, not a substring swap
      echo "$CREATE_OUT" | sed 's/^/      /'
    fi
  fi

  if [ -z "$SELECTED_APP_ID" ]; then
    echo ""
    echo "   ⚠️  Continuing WITHOUT Gemini Enterprise registration. The agent, its data"
    echo "      and the dashboards are all deployed and healthy; the DataStores and the"
    echo "      agent registration were skipped because there is no app to attach them to."
    echo "      Create one at:"
    echo "      https://console.cloud.google.com/gemini-enterprise/products?project=$PROJECT_ID"
    echo "      then re-run: bash setup_and_deploy.sh (it is idempotent), or just"
    echo "      python3 scripts/verify_and_heal.py after registering by hand."
    echo ""
  fi
fi

# Job 3.1: Pub/Sub push subscription
# Only the scheduler topic gets a push subscription. The result topic is for
# downstream consumers; pushing it back into /execute_task re-enters the same
# session and collides with the run that just published it.
(
  gcloud pubsub subscriptions create "${SCHED_TOPIC}-push" \
    --topic="$SCHED_TOPIC" \
    --push-endpoint="${AGENT_URL}/execute_task" \
    --push-auth-service-account="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
    --ack-deadline=600 \
    --project="$PROJECT_ID" 2>/dev/null || true
) &

# Job 3.2: Discovery Engine IAM Invoker Binding & DataStore SA Permissions
(
  DE_SA="serviceAccount:service-${PROJECT_NUMBER}@gcp-sa-discoveryengine.iam.gserviceaccount.com"
  gcloud run services add-iam-policy-binding "$SERVICE_NAME" \
    --region="$REGION" \
    --member="$DE_SA" \
    --role="roles/run.servicesInvoker" >/dev/null 2>&1 || true

  if [ "$RAG_MODE" = "1" ]; then
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="$DE_SA" --role="roles/storage.objectViewer" --condition=None >/dev/null 2>&1 || true
    gcloud projects add-iam-policy-binding "$PROJECT_ID" --member="$DE_SA" --role="roles/bigquery.dataViewer" --condition=None >/dev/null 2>&1 || true
  fi
) &

# The generator rewrites all four sample documents, so staging them before it
# has finished uploads whatever Phase 3 left behind - or half a file. Job 1.5
# started back in stage 1 and is normally long done; this only makes it certain.
# It cannot be waited on from inside the job below: `wait` reaches a shell's own
# children, and a subshell is not the parent of a sibling job.
wait $PID_DRIVE 2>/dev/null || true

# Job 3.2b: Stage the external sample files, provision DataStores (Optional)
(
  # The staging is NOT rag-only. In mcp mode nothing indexes these documents,
  # but import_demo_files_to_my_drive still reads this bucket to copy them into
  # the signed-in user's own Drive - and until v2.9.0 the copy sat inside the
  # rag branch, so every mcp-mode demo left that tool pointing at a bucket that
  # was never even created. cleanup.sh deletes the bucket by name in both modes,
  # so creating it here leaks nothing.
  if [ -n "${GCS_BUCKET_NAME:-}" ]; then
    gcloud storage buckets create "gs://${GCS_BUCKET_NAME}" --project="$PROJECT_ID" --location="$REGION" --uniform-bucket-level-access 2>/dev/null || true
    if [ -d "./external_files" ]; then
      gcloud storage cp -r external_files/* "gs://${GCS_BUCKET_NAME}/" 2>/dev/null || true
    fi
  fi
  if [ "$RAG_MODE" = "1" ] && [ -f scripts/setup_datastores.py ] && [ ! -z "$SELECTED_APP_ID" ]; then
    echo "  📦 Setting up Discovery Engine DataStores (GCS / BigQuery)..."
    # The trailing enable_gcs / enable_bq arguments are deliberately omitted:
    # setup_datastores.py then derives each side from whether the corresponding
    # resource name is non-empty, which is the same answer without the flags.
    python3 scripts/setup_datastores.py \
      "$SELECTED_LOC" \
      "$PROJECT_ID" \
      "$SELECTED_LOC" \
      "$SELECTED_APP_ID" \
      "$TOKEN" \
      "$SERVICE_NAME" \
      "${GCS_BUCKET_NAME:-}" \
      "${DATASET_ID:-}" >/dev/null 2>&1 || true
  fi
) &

# The Discovery Engine Authorization is what makes Gemini Enterprise attach the
# end user's OAuth token to each request. Both Workspace paths need it, not just
# the MCP one: with auth-only enabled and no authorization on the registration,
# no token ever arrives and the Drive handoff falls back to the service account.
#
# The RESOURCE has to exist before the registration names it. Discovery Engine
# resolves authorizationConfig.agentAuthorization at create time and answers
# 404 NOT_FOUND when it points at nothing, which fails the whole registration -
# so the demo came up with no agent, no direct chat link, and a deploy that
# still exited 0 (observed 2026-08-23). Binding the OAuth secrets into Cloud Run
# is NOT the same step: that is what the container reads, this is what Gemini
# Enterprise reads. Mirrors the Web UI's generated script (v11.35 / v11.38).
AUTH_ARG=""
if [ "$ENABLE_WORKSPACE_MCP" = "1" ] || [ "$ENABLE_WORKSPACE_AUTH" = "1" ]; then
  AUTH_CLIENT_ID=$(gcloud secrets versions access latest --secret=ge-demo-oauth-client-id --project="$PROJECT_ID" 2>/dev/null || echo "")
  AUTH_CLIENT_SECRET=$(gcloud secrets versions access latest --secret=ge-demo-oauth-client-secret --project="$PROJECT_ID" 2>/dev/null || echo "")
  if [ -z "$AUTH_CLIENT_ID" ] || [ -z "$AUTH_CLIENT_SECRET" ] || [ -z "$TOKEN" ]; then
    echo "  ⚠️  Workspace is enabled but the OAuth client credentials could not be read"
    echo "     from Secret Manager - skipping the Gemini Enterprise authorization."
    echo "     The agent is registered WITHOUT it, so Workspace tools run as the service"
    echo "     account. Create ge-demo-oauth-client-id / ge-demo-oauth-client-secret and"
    echo "     re-run this script to wire end-user OAuth in."
  else
    # Kept as a plain list so it stays diffable against the Web UI script and
    # against the scopes tools.py asks the MCP servers for; the wire format is
    # one percent-encoded, space-separated string.
    AUTH_SCOPES="https://www.googleapis.com/auth/gmail.readonly https://www.googleapis.com/auth/gmail.compose https://www.googleapis.com/auth/gmail.modify https://www.googleapis.com/auth/drive.readonly https://www.googleapis.com/auth/drive.file https://www.googleapis.com/auth/calendar.calendarlist.readonly https://www.googleapis.com/auth/calendar.events.freebusy https://www.googleapis.com/auth/calendar.events.readonly https://www.googleapis.com/auth/calendar.events https://www.googleapis.com/auth/chat.spaces.readonly https://www.googleapis.com/auth/chat.memberships.readonly https://www.googleapis.com/auth/chat.messages.readonly https://www.googleapis.com/auth/chat.messages.create https://www.googleapis.com/auth/chat.users.readstate.readonly https://www.googleapis.com/auth/directory.readonly https://www.googleapis.com/auth/userinfo.profile https://www.googleapis.com/auth/contacts.readonly"
    AUTH_SCOPES_ENC=$(printf '%s' "$AUTH_SCOPES" | sed -e 's|:|%3A|g' -e 's|/|%2F|g' -e 's| |%20|g')
    # Authorizations are ALWAYS global, whatever location the app is in.
    AUTH_API="https://discoveryengine.googleapis.com/v1alpha/projects/${PROJECT_ID}/locations/global/authorizations"
    AUTH_BODY=$(mktemp /tmp/ge-auth-body-XXXXXX.json)
    cat >"$AUTH_BODY" <<__AUTH_BODY_EOF__
{
  "name": "projects/${PROJECT_ID}/locations/global/authorizations/${AUTH_ID}",
  "serverSideOauth2": {
    "clientId": "${AUTH_CLIENT_ID}",
    "clientSecret": "${AUTH_CLIENT_SECRET}",
    "authorizationUri": "https://accounts.google.com/o/oauth2/v2/auth?access_type=offline&prompt=consent&response_type=code&scope=${AUTH_SCOPES_ENC}&client_id=${AUTH_CLIENT_ID}&redirect_uri=https%3A%2F%2Fvertexaisearch.cloud.google.com%2Foauth-redirect",
    "tokenUri": "https://oauth2.googleapis.com/token"
  }
}
__AUTH_BODY_EOF__
    echo "🔐 Creating/updating the Gemini Enterprise authorization resource (${AUTH_ID})..."
    AUTH_RESP=$(mktemp /tmp/ge-auth-resp-XXXXXX.json)
    AUTH_HTTP=$(curl -s -o "$AUTH_RESP" -w "%{http_code}" -X POST -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "X-Goog-User-Project: $PROJECT_ID" "${AUTH_API}?authorizationId=${AUTH_ID}" -d @"$AUTH_BODY" 2>/dev/null || echo "000")
    if [ "$AUTH_HTTP" = "409" ]; then
      # updateMask is MANDATORY on this endpoint: without it the PATCH is
      # accepted, answers 200 and changes nothing, so an overwrite deploy only
      # *claims* to have refreshed the scopes and the client secret (v11.38).
      AUTH_HTTP=$(curl -s -o "$AUTH_RESP" -w "%{http_code}" -X PATCH -H "Authorization: Bearer $TOKEN" -H "Content-Type: application/json" -H "X-Goog-User-Project: $PROJECT_ID" "${AUTH_API}/${AUTH_ID}?updateMask=serverSideOauth2" -d @"$AUTH_BODY" 2>/dev/null || echo "000")
      [ "$AUTH_HTTP" = "200" ] && echo "  ♻️  Authorization already existed - updated in place (scopes + secret refreshed)."
    elif [ "$AUTH_HTTP" = "200" ]; then
      echo "  ✅ Authorization resource created."
    fi
    # A 200 is not proof the resource is readable, and the registration below
    # only cares about that. Read it back and let the answer - not the write -
    # decide whether the agent is registered with an authorization at all.
    AUTH_GET=$(curl -s -o /dev/null -w "%{http_code}" -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" "${AUTH_API}/${AUTH_ID}" 2>/dev/null || echo "000")
    if [ "$AUTH_GET" = "200" ]; then
      AUTH_ARG="$AUTH_ID"
    else
      echo "  ⚠️  Authorization ${AUTH_ID} is not readable (write HTTP ${AUTH_HTTP}, read HTTP ${AUTH_GET}):"
      head -n 5 "$AUTH_RESP" 2>/dev/null | sed 's/^/     /' || true
      echo "     Registering the agent WITHOUT it - the agent and its direct chat link"
      echo "     still work; Workspace tools fall back to the service account until this"
      echo "     is fixed and the script is re-run."
    fi
    rm -f "$AUTH_BODY" "$AUTH_RESP"
  fi
fi

# Job 3.3: Register Agent to Gemini Enterprise & Resolve Direct URL
(
  if [ -f scripts/register_agent.py ] && [ ! -z "$SELECTED_APP_ID" ]; then
    echo "  🚀 Registering Agent to Gemini Enterprise (A2UI v0.9)..."
    # `|| true` on its own is what let a failed registration read as a clean
    # deploy: the summary just lost its direct chat link and said nothing about
    # why. Keep the script alive, but print what the API answered.
    register_agent_once() {
      python3 scripts/register_agent.py \
        "$SELECTED_LOC" \
        "$PROJECT_ID" \
        "$SELECTED_LOC" \
        "$SELECTED_APP_ID" \
        "$TOKEN" \
        "$SERVICE_NAME" \
        "$AGENT_URL" \
        "${DEMO_DISPLAY_NAME:-Demo Agent}" \
        "${DEMO_DESCRIPTION:-Operational AI Agent}" \
        "$1" 2>&1
    }
    REG_OUT=$(register_agent_once "$AUTH_ARG" || true)
    AGENT_ID=$(echo "$REG_OUT" | grep "AGENT_ID:" | head -n 1 | cut -d: -f2 | tr -d '\r\n ')

    # An authorization that exists can still be refused (wrong project number,
    # already bound to another agent). A registered agent with degraded
    # Workspace tools beats no agent at all, so fall back once and say so.
    if [ -z "$AGENT_ID" ] && [ -n "$AUTH_ARG" ]; then
      echo "  ⚠️  Registration with the authorization failed:"
      echo "$REG_OUT" | tail -n 5 | sed 's/^/     /'
      echo "     Retrying without it..."
      REG_OUT=$(register_agent_once "" || true)
      AGENT_ID=$(echo "$REG_OUT" | grep "AGENT_ID:" | head -n 1 | cut -d: -f2 | tr -d '\r\n ')
      [ -n "$AGENT_ID" ] && echo "  ⚠️  Registered WITHOUT end-user OAuth. Fix the authorization, then re-run."
    fi

    WC_ENDPOINT="discoveryengine.googleapis.com"
    if [ "$SELECTED_LOC" != "global" ]; then
      WC_ENDPOINT="${SELECTED_LOC}-discoveryengine.googleapis.com"
    fi
    CONFIG_ID=$(curl -s -H "Authorization: Bearer $TOKEN" -H "X-Goog-User-Project: $PROJECT_ID" \
      "https://${WC_ENDPOINT}/v1alpha/projects/$PROJECT_ID/locations/$SELECTED_LOC/collections/default_collection/engines/$SELECTED_APP_ID/widgetConfigs/default_search_widget_config" 2>/dev/null |
      python3 -c 'import sys, json; print(json.load(sys.stdin).get("configId", ""))' 2>/dev/null || echo "")

    if [ ! -z "$AGENT_ID" ] && [ ! -z "$CONFIG_ID" ]; then
      echo "https://vertexaisearch.cloud.google.com/home/cid/${CONFIG_ID}/r/agent/${AGENT_ID}/session/-" >.ge_direct_url
      echo "$AGENT_ID" >.agent_id
      echo "  ✅ Registered with Gemini Enterprise. Agent ID: ${AGENT_ID}"
    elif [ ! -z "$AGENT_ID" ]; then
      echo "$AGENT_ID" >.agent_id
      echo "  ✅ Registered with Gemini Enterprise. Agent ID: ${AGENT_ID}"
      echo "  ⚠️  The app's widget config has no configId, so no direct chat link could be built."
    else
      echo "  ❌ Agent registration FAILED - the demo has no agent in Gemini Enterprise:"
      echo "$REG_OUT" | tail -n 10 | sed 's/^/     /'
      echo "     Stage 3.5 below retries this; if it still fails, fix the cause and re-run"
      echo "     python3 scripts/verify_and_heal.py."
    fi
  fi
) &

# Wait for all background tasks to finish
wait $PID_BQ 2>/dev/null || true
wait $PID_DRIVE 2>/dev/null || true
wait

# --- Stage 3.4: Runtime wire-up of everything discovered after the deploy ---
# These values do not exist yet at deploy time: the service URL is assigned by
# Cloud Run, the Gemini Enterprise app is discovered in Stage 3, and the managed
# agent finishes provisioning here. They are applied in a single update so the
# service revisits its revision once instead of four times.
POST_ENV=""

# SELF_URL is how the runtime addresses itself when handing work to Cloud Tasks.
# Unset, _enqueue_worker_task refuses to enqueue and background runs fall back to
# an in-process localhost call that dies with the turn that started it.
if [ -n "$AGENT_URL" ]; then
  POST_ENV="SELF_URL=${AGENT_URL}"
fi

# search_datastore's engine-wide fallback path. DEFAULT_DATASTORE_ID is
# deliberately left unset: searching the engine covers every datastore attached
# to it, so one variable keeps working as connectors are added or removed.
#
# Gated on RAG_MODE as well as on discovery, and that gate is the fix for a real
# defect: agent.py decides whether search_datastore exists by looking at this
# variable, not at the mode. Setting it unconditionally meant an MCP-mode deploy
# still armed the search path - against an engine that, because the scoping
# block below DOES respect the mode, was left unscoped and therefore ranked
# across every other demo sharing the app.
if [ "$RAG_MODE" = "1" ] && [ -n "$SELECTED_APP_ID" ]; then
  POST_ENV="${POST_ENV:+$POST_ENV;}GEMINI_ENTERPRISE_APP_ID=${SELECTED_APP_ID};DATASTORE_LOCATION=${SELECTED_LOC}"
fi

# ...but a Gemini Enterprise app is routinely shared by several demos, and an
# unscoped engine search ranks across ALL of their datastores: a generic query
# ("gold tier customers") then answers out of a NEIGHBOURING demo's customer
# table and reads as this demo returning wrong data. DATASTORE_SCOPE_IDS confines
# the search to the datastores this deployment created. The names are derived the
# same way setup_datastores.py derives them - ds-<service>-gcs when a bucket was
# staged, ds-<service>-bq when a dataset was loaded - so the two stay in step
# without passing anything back out of the background job. Unset (no connectors)
# the runtime keeps the old engine-wide behaviour.
if [ "$RAG_MODE" = "1" ] && [ -n "$SELECTED_APP_ID" ]; then
  DS_SCOPE=""
  [ -n "${GCS_BUCKET_NAME:-}" ] && DS_SCOPE="ds-${SERVICE_NAME}-gcs"
  [ -n "${DATASET_ID:-}" ] && DS_SCOPE="${DS_SCOPE:+$DS_SCOPE,}ds-${SERVICE_NAME}-bq"
  if [ -n "$DS_SCOPE" ]; then
    POST_ENV="${POST_ENV:+$POST_ENV;}DATASTORE_SCOPE_IDS=${DS_SCOPE}"
  fi
fi

# --- Managed Autonomous Agent, PHASE B: await readiness + warm-up ---
# Creation started in Stage 0.5, so most of its ~8-10 min has already elapsed
# alongside the data load, the sandbox and the Cloud Run build.
if [ "$ENABLE_MANAGED_AGENT" = "1" ] && [ -n "$MANAGED_AGENT_ID" ]; then
  echo ""
  echo "🤖 Finalizing Managed Autonomous Agent (started earlier in parallel)..."
  MA_TOKEN=$(gcloud auth print-access-token 2>/dev/null || echo "")
  MA_OUT="/tmp/ma_ready_$$.txt"
  MA_OUT="$MA_OUT" PROJECT_ID="$PROJECT_ID" python3 scripts/create_managed_agent.py \
    wait "$MANAGED_AGENT_ID" "$MA_TOKEN" 2>&1 | sed 's/^/  /' || true
  MA_READY=$(cat "$MA_OUT" 2>/dev/null || echo "")
  rm -f "$MA_OUT"

  if [ -n "$MA_READY" ]; then
    echo "  ✅ Managed Agent ready: ${MANAGED_AGENT_ID} (location: global)"
    echo "  🔥 Warming up the autonomous sandbox (pre-provisioning the environment)..."
    # The warm-up writes the environment id to Firestore, which is where the
    # runtime looks first; MANAGED_AGENT_ENV_ID is only the fallback for a cold
    # instance that has not read the collection yet. Both are set so neither
    # path has to pay the several-minute provisioning cost mid-demo.
    MA_OUT="/tmp/ma_env_$$.txt"
    MA_OUT="$MA_OUT" PROJECT_ID="$PROJECT_ID" MA_STATE_COLL="${DEMO_ID}_managed_agent_state" \
      python3 scripts/warmup_managed_agent.py \
      "$MANAGED_AGENT_ID" "$MA_TOKEN" "$MA_SKILLS_SOURCE" 2>&1 | sed 's/^/  /' || true
    MANAGED_AGENT_ENV_ID=$(cat "$MA_OUT" 2>/dev/null || echo "")
    rm -f "$MA_OUT"
    if [ -n "$MANAGED_AGENT_ENV_ID" ]; then
      echo "  ✅ Sandbox environment pre-provisioned: ${MANAGED_AGENT_ENV_ID}"
      POST_ENV="${POST_ENV:+$POST_ENV;}MANAGED_AGENT_ENV_ID=${MANAGED_AGENT_ENV_ID}"
    else
      echo "  ⚠️  Warm-up returned no environment id (first delegation will provision on demand)."
    fi
  else
    # Leaving a stale id in place is worse than removing it: the delegation tools
    # would accept the task and then fail against an agent that does not exist,
    # whereas with the id gone they report "unavailable" and the root agent
    # answers the question itself.
    echo "  ⚠️  Managed Agent is not ready - disabling autonomous delegation on the deployed service."
    MANAGED_AGENT_ID=""
    gcloud run services update "$SERVICE_NAME" --region "$REGION" \
      --remove-env-vars MANAGED_AGENT_ID --quiet >/dev/null 2>&1 &&
      echo "  ✅ MANAGED_AGENT_ID removed (re-run this script later to retry)." ||
      echo "  ⚠️  Could not update the service - delegation may fail at runtime."
  fi
fi

if [ -n "$POST_ENV" ]; then
  echo "🔧 Applying post-deployment runtime configuration..."
  # ^;^ switches gcloud's pair separator from comma to semicolon. DATASTORE_SCOPE_IDS
  # is itself a comma-separated list, and with the default separator gcloud would
  # split inside it, see a bare token with no '=', and reject the whole update -
  # taking SELF_URL and the app id down with it.
  gcloud run services update "$SERVICE_NAME" --region "$REGION" \
    --update-env-vars="^;^$POST_ENV" --quiet >/dev/null 2>&1 &&
    echo "  ✅ Runtime wire-up applied." ||
    echo "  ⚠️  Post-deployment env update failed - background tasks and datastore search may be degraded."
fi

# --- Stage 3.5: Autonomous Verification & Real-Time Self-Healing ---
if [ -f scripts/verify_and_heal.py ]; then
  echo ""
  echo "🛡️  [4/4] Running Autonomous Verification & Real-Time Self-Healing Engine..."
  python3 scripts/verify_and_heal.py || {
    echo "⚠️ Autonomous verification noted warnings/issues. Review logs above."
  }
fi

GE_DIRECT_CHAT_URL=$(cat .ge_direct_url 2>/dev/null || echo "")
AGENT_ID=$(cat .agent_id 2>/dev/null || echo "")
rm -f .ge_direct_url .agent_id

if [ ! -z "$SELECTED_APP_ID" ]; then
  GE_CHAT_URL="https://console.cloud.google.com/gemini-enterprise/locations/${SELECTED_LOC}/engines/${SELECTED_APP_ID}/overview/dashboard?&project=${PROJECT_ID}"
else
  GE_CHAT_URL="https://console.cloud.google.com/gemini-enterprise/overview?&project=${PROJECT_ID}"
fi
BQ_CONSOLE_URL="https://console.cloud.google.com/bigquery?referrer=search&project=${PROJECT_ID}&ws=!1m4!1m3!3m2!1s${PROJECT_ID}!2s${DATASET_ID}"

# gs:// is not a URL anyone can click. storage.cloud.google.com serves the
# object itself to a signed-in browser, and the console URL opens the bucket
# listing - print both, so "where are the files" never ends at a path.
GCS_CONSOLE_URL=""
GCS_FILE_LINKS=""
if [ -n "${GCS_BUCKET_NAME:-}" ]; then
  GCS_CONSOLE_URL="https://console.cloud.google.com/storage/browser/${GCS_BUCKET_NAME}?project=${PROJECT_ID}"
  if [ -d external_files ]; then
    for _gf in external_files/*; do
      [ -f "$_gf" ] || continue
      # The summary and the .url.json artifacts are bookkeeping, not documents.
      case "$(basename "$_gf")" in drive_upload_summary.json | *.url.json) continue ;; esac
      GCS_FILE_LINKS="${GCS_FILE_LINKS}   📄 $(basename "$_gf"): https://storage.cloud.google.com/${GCS_BUCKET_NAME}/$(basename "$_gf")
"
    done
  fi
fi

DRIVE_FOLDER_URL=""
DRIVE_OWNER_ACCOUNT=""
DRIVE_FILES_SUMMARY=""
DRIVE_SKIP_REASON=""
DRIVE_SHARE_ERROR=""
DRIVE_SHARED_WITH=""
if [ -f external_files/drive_upload_summary.json ]; then
  DRIVE_FOLDER_URL=$(cat external_files/drive_upload_summary.json | jq -r '.folder_url // empty' 2>/dev/null || echo "")
  DRIVE_OWNER_ACCOUNT=$(cat external_files/drive_upload_summary.json | jq -r '.owner_account // empty' 2>/dev/null || echo "")
  DRIVE_SKIP_REASON=$(cat external_files/drive_upload_summary.json | jq -r '.upload_skipped_reason // empty' 2>/dev/null || echo "")
  DRIVE_FILES_SUMMARY=$(cat external_files/drive_upload_summary.json | jq -r '.uploaded_files[] | "   📄 \(.fileName): \(.url)"' 2>/dev/null || echo "")
  DRIVE_SHARE_ERROR=$(cat external_files/drive_upload_summary.json | jq -r '.share_error // empty' 2>/dev/null || echo "")
  DRIVE_SHARED_WITH=$(cat external_files/drive_upload_summary.json | jq -r '.shared_permissions | join(", ") // empty' 2>/dev/null || echo "")
fi
if [ -z "$DRIVE_OWNER_ACCOUNT" ]; then
  DRIVE_OWNER_ACCOUNT="$GCP_ACCOUNT"
fi

# --- Stage 4: Comprehensive Output Banner ---
echo ""
echo "================================================================================"
if [ ! -z "$SELECTED_APP_ID" ]; then
  echo "🎉 Gemini Enterprise Deployment & Registration Complete!"
else
  echo "⚠️ Gemini Enterprise Deployment Complete (Manual Registration Required)"
fi
echo "================================================================================"
echo ""
echo "👤 Deployment Identity & Environment"
echo "--------------------------------------------------------------------------------"
echo "👤 Deployed By Account : ${GCP_ACCOUNT}"
echo "🏢 Target Project      : ${PROJECT_ID} (Project Number: ${PROJECT_NUMBER})"
echo "🌐 Deployed Region     : ${REGION}"
echo "🤖 Service Account     : ${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"
echo ""
echo "🌟 Agent Profile"
echo "--------------------------------------------------------------------------------"
echo "🤖 Agent Name:        ${DEMO_DISPLAY_NAME:-Demo Agent} ($SERVICE_NAME)"
if [ ! -z "$AGENT_ID" ]; then
  echo "🆔 Agent ID:          ${AGENT_ID}"
fi
echo "📝 Description:       ${DEMO_DESCRIPTION:-Operational AI Agent}"
echo "🧠 Reasoning Model:   gemini-3.7-flash"
echo "🎨 Image Gen Model:   gemini-3.1-flash-image"
echo ""
echo "🗄️ Data Resources"
echo "--------------------------------------------------------------------------------"
echo "📊 BigQuery Dataset:  ${DATASET_ID}"
echo "🔥 Firestore:         ${FIRESTORE_COLLECTION}"
echo "🧪 Agent Engine:      ${AGENT_ENGINE_NAME}"
echo "📦 Sandbox Resource:  ${SANDBOX_RESOURCE_NAME}"
if [ ! -z "$DRIVE_FOLDER_URL" ]; then
  echo ""
  echo "📁 Google Drive External Sample Files"
  echo "--------------------------------------------------------------------------------"
  echo "👤 Drive Owner Account: ${DRIVE_OWNER_ACCOUNT}"
  echo "📂 Open the folder    : ${DRIVE_FOLDER_URL}"
  if [ ! -z "$DRIVE_SHARED_WITH" ]; then
    echo "🔑 Shared with        : ${DRIVE_SHARED_WITH}"
  fi
  if [ ! -z "$DRIVE_FILES_SUMMARY" ]; then
    echo "📄 Uploaded Files:"
    echo "$DRIVE_FILES_SUMMARY"
  fi
  if [ ! -z "$DRIVE_SHARE_ERROR" ]; then
    echo "❗ SHARING FAILED     : ${GCP_ACCOUNT} cannot open the folder yet."
    echo "   Reason: ${DRIVE_SHARE_ERROR}"
    echo "   Share it by hand from the Drive UI as [${DRIVE_OWNER_ACCOUNT}] - or, with"
    echo "   Workspace OAuth on, ask the agent to import the documents into that Drive."
  elif [ "${DRIVE_OWNER_ACCOUNT}" != "${GCP_ACCOUNT}" ]; then
    echo "⚠️ ACCESS INSTRUCTION:"
    echo "   [${DRIVE_OWNER_ACCOUNT}] OWNS this folder and [${GCP_ACCOUNT}] has Writer access,"
    echo "   so it appears under 'Shared with me' for the deploy account. Open the links"
    echo "   as either of those two accounts; any other account gets 403/404."
  else
    echo "⚠️ ACCESS INSTRUCTION:"
    echo "   Make sure your browser is currently switched to Google Account [${DRIVE_OWNER_ACCOUNT}]"
    echo "   when opening the Google Drive folder/file links above to avoid permission (403/404) errors."
  fi
elif [ ! -z "$DRIVE_SKIP_REASON" ]; then
  echo ""
  echo "📁 External Sample Files (local - no Google Drive upload)"
  echo "--------------------------------------------------------------------------------"
  echo "📂 Location: ./external_files/"
  echo "ℹ️ Drive upload skipped: ${DRIVE_SKIP_REASON}."
  if [ "$ENABLE_WORKSPACE_MCP" = "1" ] || [ "$ENABLE_WORKSPACE_AUTH" = "1" ]; then
    echo "✅ They still reach a Drive by themselves: on your first message to the agent"
    echo "   in Gemini Enterprise it copies them from the bucket with YOUR OAuth token,"
    echo "   so you own the result (the ledger arrives as a Google Sheet), and it replies"
    echo "   with the folder link. Once per account - a second conversation gets the same"
    echo "   folder, not a second copy. You can also just ask for them:"
    echo "   \"import the demo's sample documents into my Google Drive\"."
    echo "   Set AUTO_IMPORT_DEMO_FILES=0 on the Cloud Run service to require the ask."
  else
    echo "   Sign the gdrive CLI in and re-run to get a Drive folder, or open the files"
    echo "   from Cloud Storage with the links below."
    echo "   With Workspace OAuth enabled the agent could import them into your own Drive"
    echo "   on request instead - that option needs enableWorkspaceAuth (or the full MCP)."
  fi
fi
if [ ! -z "$GCS_CONSOLE_URL" ]; then
  echo ""
  echo "📦 External Sample Files in Cloud Storage"
  echo "--------------------------------------------------------------------------------"
  echo "🗂️ Browse the bucket  : ${GCS_CONSOLE_URL}"
  if [ ! -z "$GCS_FILE_LINKS" ]; then
    echo "📄 Open a file directly (signed-in browser):"
    printf '%s' "$GCS_FILE_LINKS"
  fi
  echo "📂 Also on this machine: ./external_files/"
fi
echo ""
echo "🔗 Quick Access Links"
echo "--------------------------------------------------------------------------------"
echo "⚠️  IMPORTANT - Account Notice:"
echo "   Open every link below in a browser signed in to Google Cloud / Workspace"
echo "   as the deploying account [${GCP_ACCOUNT}]."
echo "   Opening them as a different account returns 403 Forbidden or 'agent not found'."
echo ""
if [ ! -z "$GE_DIRECT_CHAT_URL" ]; then
  echo "💬 Start Chatting with Your Agent (Direct):"
  echo "   👉 ${GE_DIRECT_CHAT_URL}"
  echo ""
fi
echo "💻 Gemini Enterprise Console (Overview):"
echo "   👉 ${GE_CHAT_URL}"
if [ -z "$GE_DIRECT_CHAT_URL" ]; then
  echo "   💡 Click the 'Preview' button at the top to launch Gemini Enterprise, then select 'Agents' from the left menu to start chatting with your deployed agent."
fi
echo ""
if [ ! -z "$VIEWER_URL" ]; then
  echo "📊 Firestore Data Viewer Dashboard:"
  echo "   👉 ${VIEWER_URL}"
  echo ""
fi
echo "🔎 BigQuery Console:"
echo "   👉 ${BQ_CONSOLE_URL}"
echo ""
if [ ! -z "$DRIVE_FOLDER_URL" ]; then
  echo "📁 Google Drive Folder (external sample files, owned by ${DRIVE_OWNER_ACCOUNT}):"
  echo "   👉 ${DRIVE_FOLDER_URL}"
  echo ""
fi
if [ ! -z "$GCS_CONSOLE_URL" ]; then
  echo "📦 Cloud Storage Bucket (external sample files):"
  echo "   👉 ${GCS_CONSOLE_URL}"
  echo ""
fi
echo "================================================================================"
echo "💡 Next Steps:"
echo "• Open the Gemini Enterprise Chat URL above and try the 7 Demo Prompts!"
echo "• To clean up all provisioned resources in high-speed parallel mode, run:"
echo "  $ bash scripts/cleanup.sh"
echo "================================================================================"
