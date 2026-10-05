#!/usr/bin/env bash
# Copyright 2026 Google LLC
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

# Deploy Gemini Live Studio to Cloud Run.
#
# Settings resolve in this order: command-line flag > environment variable >
# .env file > profile default. Run with --dry-run to see the resolved
# configuration and the gcloud commands without deploying anything.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: scripts/deploy.sh [options]

Options:
  --project ID          Google Cloud project (env GOOGLE_CLOUD_PROJECT; falls back to `gcloud config get project`)
  --region REGION       Cloud Run region and Live API location (env GOOGLE_CLOUD_LOCATION; default us-central1)
  --service NAME        Cloud Run service name (env SERVICE_NAME; default gemini-live-studio)
  --profile NAME        default, or a profile file in $PROFILE_DIR (default: a profile whose
                        PROFILE_PROJECT matches the project, otherwise default)
  --live-model ID       env GEMINI_LIVE_MODEL
  --image-model ID      env GEMINI_IMAGE_MODEL
  --image-location LOC  env GEMINI_IMAGE_LOCATION
  --base-url URL        env GEMINI_BASE_URL; pass '' to use the Production endpoint
  --allowed-origins LST env ALLOWED_ORIGINS (comma-separated origin allowlist; empty = same-origin)
  --iap | --no-iap      Put the service behind IAP, or deploy it publicly (env USE_IAP=true|false).
                        If neither is given and the service already uses IAP, IAP is kept.
  --iap-group LIST      Google group(s) to grant IAP access, comma-separated (env IAP_GROUP)
  --iap-users LIST      User email(s) to grant IAP access, comma-separated (env IAP_USERS).
                        IAP grants are only ever added; existing access is never removed.
                        --iap-group/--iap-users imply --iap. --iap with no group or
                        users keeps the current access list.
  --dry-run             Print the resolved config and commands, then exit
  -y, --yes             Deploy without asking for confirmation
  -h, --help            Show this help

Profiles:
  default      Production endpoint, gemini-3.8-live, gemini-nano-banana-2.1 on
               global, public service (no IAP).
  <name>       $PROFILE_DIR/<name>.env (default scripts/profiles): shell assignments
               that set defaults for any variable above, e.g. SERVICE_NAME=...,
               USE_IAP=true, IAP_GROUP=team@example.com, IAP_USERS=a@example.com.
               PROFILE_PROJECT=<id>
               selects the profile automatically for that project.
EOF
}

die() { echo "Error: $*" >&2; exit 1; }

VARS=(GOOGLE_CLOUD_PROJECT GOOGLE_CLOUD_LOCATION SERVICE_NAME GEMINI_LIVE_MODEL
  GEMINI_IMAGE_MODEL GEMINI_IMAGE_LOCATION GEMINI_BASE_URL ALLOWED_ORIGINS USE_IAP IAP_GROUP IAP_USERS)

# 1. Remember which variables were set in the caller's environment, so .env
#    cannot override them (Bash 3.2 compatible — avoids declare -A).
for v in "${VARS[@]}"; do
  if [[ -n "${!v+x}" ]]; then
    printf -v "HAS_ENV_${v}" '%s' "1"
    printf -v "FROM_ENV_${v}" '%s' "${!v}"
  fi
done

# 2. Parse flags.
PROFILE=""
DRY_RUN=false
ASSUME_YES=false
need_arg() { [[ $# -ge 2 ]] || die "$1 requires a value"; }
set_flag() {
  printf -v "HAS_FLAG_${1}" '%s' "1"
  printf -v "FROM_FLAG_${1}" '%s' "${2}"
}
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project)         need_arg "$@"; set_flag GOOGLE_CLOUD_PROJECT "$2"; shift 2 ;;
    --region)          need_arg "$@"; set_flag GOOGLE_CLOUD_LOCATION "$2"; shift 2 ;;
    --service)         need_arg "$@"; set_flag SERVICE_NAME "$2"; shift 2 ;;
    --profile)         need_arg "$@"; PROFILE="$2"; shift 2 ;;
    --live-model)      need_arg "$@"; set_flag GEMINI_LIVE_MODEL "$2"; shift 2 ;;
    --image-model)     need_arg "$@"; set_flag GEMINI_IMAGE_MODEL "$2"; shift 2 ;;
    --image-location)  need_arg "$@"; set_flag GEMINI_IMAGE_LOCATION "$2"; shift 2 ;;
    --base-url)        need_arg "$@"; set_flag GEMINI_BASE_URL "$2"; shift 2 ;;
    --allowed-origins) need_arg "$@"; set_flag ALLOWED_ORIGINS "$2"; shift 2 ;;
    --iap)             set_flag USE_IAP true; shift ;;
    --no-iap)          set_flag USE_IAP false; shift ;;
    --iap-group)       need_arg "$@"; set_flag IAP_GROUP "$2"; shift 2 ;;
    --iap-users)       need_arg "$@"; set_flag IAP_USERS "$2"; shift 2 ;;
    --dry-run)         DRY_RUN=true; shift ;;
    -y|--yes)          ASSUME_YES=true; shift ;;
    -h|--help)         usage; exit 0 ;;
    *)                 usage >&2; die "unknown option: $1" ;;
  esac
done

# 3. Load .env, then re-apply the caller's environment and flags on top.
if [[ -f .env ]]; then
  set -a
  # shellcheck disable=SC1091
  . ./.env
  set +a
fi
for v in "${VARS[@]}"; do
  has_env_var="HAS_ENV_${v}"
  from_env_var="FROM_ENV_${v}"
  if [[ -n "${!has_env_var:-}" ]]; then
    printf -v "$v" '%s' "${!from_env_var}"
  fi
  has_flag_var="HAS_FLAG_${v}"
  from_flag_var="FROM_FLAG_${v}"
  if [[ -n "${!has_flag_var:-}" ]]; then
    printf -v "$v" '%s' "${!from_flag_var}"
  fi
done

# 4. Resolve the project and profile.
if [[ -z "${GOOGLE_CLOUD_PROJECT:-}" ]]; then
  GOOGLE_CLOUD_PROJECT="$(gcloud config get project 2>/dev/null || true)"
fi
[[ -n "$GOOGLE_CLOUD_PROJECT" ]] || die "no project: pass --project, set GOOGLE_CLOUD_PROJECT, or run 'gcloud config set project ID'"

PROFILE_DIR="${PROFILE_DIR:-scripts/profiles}"
if [[ -z "$PROFILE" ]]; then
  PROFILE=default
  for f in "$PROFILE_DIR"/*.env; do
    [[ -f "$f" ]] || continue
    if grep -qx "PROFILE_PROJECT=${GOOGLE_CLOUD_PROJECT}" "$f"; then
      PROFILE="$(basename "$f" .env)"
      break
    fi
  done
fi

# 5. Fill anything still unset from the profile defaults. A profile file only
#    fills variables that are still unset, so flags, env and .env still win.
#    GEMINI_BASE_URL uses an is-set check because empty means Production.
if [[ "$PROFILE" != default ]]; then
  PROFILE_FILE="$PROFILE_DIR/$PROFILE.env"
  [[ -f "$PROFILE_FILE" ]] || die "unknown profile '$PROFILE' (no $PROFILE_FILE)"
  while IFS='=' read -r key value; do
    [[ -z "$key" || "$key" == \#* || "$key" == PROFILE_PROJECT ]] && continue
    [[ -n "${!key+x}" ]] || printf -v "$key" '%s' "$value"
  done < "$PROFILE_FILE"
fi
: "${GOOGLE_CLOUD_LOCATION:=us-central1}"
: "${SERVICE_NAME:=gemini-live-studio}"
: "${GEMINI_LIVE_MODEL:=gemini-3.8-live}"
: "${ALLOWED_ORIGINS:=}"
: "${GEMINI_IMAGE_MODEL:=gemini-nano-banana-2.1}"
: "${GEMINI_IMAGE_LOCATION:=global}"
[[ -n "${GEMINI_BASE_URL+x}" ]] || GEMINI_BASE_URL=""
: "${IAP_GROUP:=}"
: "${IAP_USERS:=}"

# IAP: an explicit choice (flag, env, .env or profile) wins. Otherwise keep IAP
# on a service that already uses it, so a plain redeploy never makes it public.
IAP_NOTE=""
if [[ -z "${USE_IAP+x}" && -n "${IAP_GROUP}${IAP_USERS}" ]]; then
  USE_IAP=true # granting IAP access implies IAP
fi
if [[ -z "${USE_IAP+x}" ]]; then
  existing_iap="$(gcloud run services describe "$SERVICE_NAME" --project "$GOOGLE_CLOUD_PROJECT" \
    --region "$GOOGLE_CLOUD_LOCATION" --format='value(metadata.annotations."run.googleapis.com/iap-enabled")' 2>/dev/null || true)"
  if [[ "$existing_iap" == true ]]; then
    USE_IAP=true
    IAP_NOTE=" (kept: the service already uses IAP; pass --no-iap to make it public)"
  else
    USE_IAP=false
  fi
fi
case "$USE_IAP" in
  true|false) ;;
  *) die "USE_IAP must be true or false, got '$USE_IAP'" ;;
esac

# IAP members to add: groups and users, comma-separated. A member that already
# has a type prefix (user:, group:, serviceAccount:, domain:) is kept as-is.
IAP_MEMBERS=()
add_members() {
  local kind="$1" list="$2" m items=()
  [[ -n "$list" ]] || return 0
  IFS=',' read -r -a items <<< "$list"
  for m in "${items[@]}"; do
    m="${m//[[:space:]]/}"
    [[ -z "$m" ]] && continue
    [[ "$m" == *:* ]] || m="${kind}:${m}"
    IAP_MEMBERS+=("$m")
  done
}
add_members group "$IAP_GROUP"
add_members user "$IAP_USERS"
if [[ "$USE_IAP" == false && ${#IAP_MEMBERS[@]} -gt 0 ]]; then
  die "--iap-group/--iap-users given together with --no-iap"
fi

# 6. Build the commands. Use ^;^ delimiter when ALLOWED_ORIGINS may contain commas.
ENV_VARS="^;^GOOGLE_CLOUD_PROJECT=${GOOGLE_CLOUD_PROJECT};GOOGLE_CLOUD_LOCATION=${GOOGLE_CLOUD_LOCATION}"
ENV_VARS+=";GEMINI_LIVE_MODEL=${GEMINI_LIVE_MODEL};GEMINI_IMAGE_MODEL=${GEMINI_IMAGE_MODEL}"
ENV_VARS+=";GEMINI_IMAGE_LOCATION=${GEMINI_IMAGE_LOCATION}"
if [[ -n "$GEMINI_BASE_URL" ]]; then
  ENV_VARS+=";GEMINI_BASE_URL=${GEMINI_BASE_URL}"
fi
if [[ -n "$ALLOWED_ORIGINS" ]]; then
  ENV_VARS+=";ALLOWED_ORIGINS=${ALLOWED_ORIGINS}"
fi

if [[ "$USE_IAP" == true ]]; then
  ACCESS_FLAGS=(--iap --no-allow-unauthenticated)
  if [[ ${#IAP_MEMBERS[@]} -gt 0 ]]; then
    ACCESS_DESC="IAP${IAP_NOTE}; adding: ${IAP_MEMBERS[*]}"
  else
    ACCESS_DESC="IAP${IAP_NOTE}; existing access unchanged"
  fi
else
  ACCESS_FLAGS=(--allow-unauthenticated)
  ACCESS_DESC="PUBLIC - anyone with the URL can use it and spend this project's quota"
fi

DEPLOY_CMD=(gcloud run deploy "$SERVICE_NAME"
  --source .
  --region "$GOOGLE_CLOUD_LOCATION"
  --project "$GOOGLE_CLOUD_PROJECT"
  --clear-base-image
  "${ACCESS_FLAGS[@]}"
  --cpu 2 --memory 2G
  --no-cpu-throttling
  --set-env-vars "$ENV_VARS")

IAP_ARGS=(--role="roles/iap.httpsResourceAccessor"
  --resource-type="cloud-run"
  --region="$GOOGLE_CLOUD_LOCATION"
  --service="$SERVICE_NAME"
  --project="$GOOGLE_CLOUD_PROJECT")

# Current IAP members (empty for a new service or one without IAP).
CURRENT_IAP="$(gcloud iap web get-iam-policy "${IAP_ARGS[@]:1}" \
  --flatten='bindings[].members' --filter='bindings.role=roles/iap.httpsResourceAccessor' \
  --format='value(bindings.members)' 2>/dev/null | paste -sd' ' - || true)"

cat <<EOF
Deployment plan
  Profile         : ${PROFILE}
  Project         : ${GOOGLE_CLOUD_PROJECT}
  Region          : ${GOOGLE_CLOUD_LOCATION}
  Service         : ${SERVICE_NAME}
  Live model      : ${GEMINI_LIVE_MODEL} (${GOOGLE_CLOUD_LOCATION})
  Image model     : ${GEMINI_IMAGE_MODEL} (${GEMINI_IMAGE_LOCATION})
  Vertex endpoint : ${GEMINI_BASE_URL:-Production (default)}
  Allowed origins : ${ALLOWED_ORIGINS:-same-origin (default)}
  Access          : ${ACCESS_DESC}
EOF
if [[ -n "$CURRENT_IAP" ]]; then
  echo "  Current IAP     : ${CURRENT_IAP}"
fi

print_cmd() { printf '  '; printf '%q ' "$@"; printf '\n'; }

if [[ "$DRY_RUN" == true ]]; then
  echo
  echo "Dry run. These commands would run:"
  print_cmd "${DEPLOY_CMD[@]}"
  if [[ "$USE_IAP" == true && ${#IAP_MEMBERS[@]} -gt 0 ]]; then
    for m in "${IAP_MEMBERS[@]}"; do
      print_cmd gcloud iap web add-iam-policy-binding --member="$m" "${IAP_ARGS[@]}" --condition=None --quiet
    done
  fi
  exit 0
fi

if [[ "$ASSUME_YES" != true ]]; then
  [[ -t 0 ]] || die "not running interactively; pass --yes to deploy without confirmation"
  read -r -p "Deploy with this configuration? [y/N] " reply
  [[ "$reply" =~ ^[Yy]$ ]] || { echo "Aborted."; exit 1; }
fi

echo "Deploying to Cloud Run from source..."
"${DEPLOY_CMD[@]}"

if [[ "$USE_IAP" == true && ${#IAP_MEMBERS[@]} -gt 0 ]]; then
  for m in "${IAP_MEMBERS[@]}"; do
    echo "Granting IAP access to ${m}..."
    gcloud iap web add-iam-policy-binding --member="$m" "${IAP_ARGS[@]}" --condition=None --quiet >/dev/null
  done
fi

URL="$(gcloud run services describe "$SERVICE_NAME" --project "$GOOGLE_CLOUD_PROJECT" --region "$GOOGLE_CLOUD_LOCATION" --format='value(status.url)')"
echo "Deployment completed successfully. Your app is live at: ${URL}"
