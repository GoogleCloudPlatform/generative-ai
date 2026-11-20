# Keyless CI/CD, IAM & Workload Identity Federation Guide (`cicd/`)

This directory contains the GitHub Actions promotion gate templates and the idempotent Google Cloud IAM + Workload Identity Federation (OIDC) CLI utility (`setup_wif.py`) for Stage 2 (`staging`) and Stage 3 (`prod`).

---

## 1. Automated One-Command Setup (`cicd/setup_wif.py`)

Run [`cicd/setup_wif.py`](./setup_wif.py) from your authenticated terminal (`gcloud auth login` and `gh auth login`):

```bash
export GITHUB_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)

# Stage 2: Provision Staging Google Cloud APIs, IAM roles, WIF Pool/Provider, and GitHub Variables
uv run python cicd/setup_wif.py \
  --env staging \
  --project "staging-project" \
  --region "us-west1" \
  --repo "$GITHUB_REPO"

# Stage 3: Provision Isolated Production Google Cloud Project, IAM, WIF, and GitHub Variables
uv run python cicd/setup_wif.py \
  --env prod \
  --project "prod-project" \
  --region "us-west1" \
  --repo "$GITHUB_REPO"
```

*Tip*: Pass `--dry-run` to preview every `gcloud` and `gh` command without executing it. If you only want to run Stage 2 commands manually from your laptop without GitHub Actions, omit `--repo` (`uv run python cicd/setup_wif.py --env staging --project "staging-project"`).

---

## 2. Why Keyless Workload Identity Federation (OIDC)?

Exporting long-lived Service Account JSON keys (`GOOGLE_APPLICATION_CREDENTIALS` stored in GitHub Secrets) is a major cloud credential leak vector. With Workload Identity Federation (OIDC):

1. GitHub Actions requests a short-lived cryptographic OIDC JWT from `https://token.actions.githubusercontent.com` (`id-token: write`).
2. Google Cloud Security Token Service (STS) verifies the token signature and enforces an IAM attribute condition (`assertion.repository == '<OWNER>/adk-gemma-agentops'`) so forks or unrelated repositories cannot impersonate your service account.
3. STS exchanges the GitHub JWT for a short-lived (1-hour) Google Cloud access token with zero stored secrets.

### GitHub Repository Variables Configured by `setup_wif.py`

| GitHub Variable | Environment | Consumed By | Example Value |
| :--- | :--- | :--- | :--- |
| `GCP_PROJECT_ID` | Staging | `agent-cd-staging.yml` | `staging-project` |
| `WIF_PROVIDER_STAGING` | Staging | `agent-cd-staging.yml` | `projects/123456789/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `WIF_SA_STAGING` | Staging | `agent-cd-staging.yml` | `github-actions-cd@staging-project.iam.gserviceaccount.com` |
| `GCP_PROD_PROJECT_ID` | Production | `agent-cd-prod.yml` | `prod-project` |
| `WIF_PROVIDER_PROD` | Production | `agent-cd-prod.yml` | `projects/987654321/locations/global/workloadIdentityPools/github-pool/providers/github-provider` |
| `WIF_SA_PROD` | Production | `agent-cd-prod.yml` | `github-actions-cd@prod-project.iam.gserviceaccount.com` |
| `GCP_REGION` | Both | All CD workflows | `us-west1` |

---

## 3. Least-Privilege IAM Role Matrix (Why Each Role Exists)

Deploying to private Cloud Run revisions from source (`gcloud run deploy --source . --no-allow-unauthenticated`) and executing authenticated dark-URL checks requires specific permissions across two identities:

### A. GitHub Actions CD Service Account (`github-actions-cd@<PROJECT>.iam.gserviceaccount.com`)

| Role | Scope | Why It Is Required |
| :--- | :--- | :--- |
| `roles/run.admin` | Project | Creates services, sets `--no-allow-unauthenticated` IAM policies (`roles/run.developer` cannot modify service IAM), shifts canary traffic tags, and invokes tagged revision URLs. |
| `roles/cloudbuild.builds.editor` | Project | Submits `gcloud run deploy --source .` container builds to Cloud Build. |
| `roles/artifactregistry.admin` | Project | Creates and pushes images to the `cloud-run-source-deploy` Docker repository. |
| `roles/storage.admin` | Project | Uploads source archives to the `run-sources-<PROJECT>-<REGION>` Cloud Storage bucket. |
| `roles/aiplatform.user` | Project | Calls `gemini-3.8-flash` Judge (`final_response_match_v2`, `hallucinations_v1`, safety rubric) and serverless Gemini Agent Platform Gemma 4 MaaS (`global`) during Gate 3A. |
| `roles/iam.serviceAccountUser` | Compute SA | Attaches the runtime Compute Engine service account to deployed Cloud Run revisions. |
| `roles/iam.serviceAccountTokenCreator` | Self + WIF Principal | Allows keyless WIF (`external_account`) runners to mint Cloud Run OIDC identity tokens (`gcloud auth print-identity-token --impersonate-service-account=... --include-email`) for Gate 3B and Gate 4 checks. |
| `roles/iam.workloadIdentityUser` | WIF Principal | Allows GitHub Actions OIDC tokens from your repository to impersonate the CD service account. |

### B. Cloud Run Runtime Service Account (`<PROJECT_NUMBER>-compute@developer.gserviceaccount.com`)

| Role | Scope | Why It Is Required |
| :--- | :--- | :--- |
| `roles/aiplatform.user` | Project | Allows `GemmaEndpointLlm` inside Cloud Run to call serverless Gemini Agent Platform Gemma 4 MaaS (`/endpoints/openapi/chat/completions`). |
| `roles/cloudtrace.agent` & `roles/logging.logWriter` | Project | Exports sanitized OpenTelemetry Gen AI traces and structured logs. |
| `roles/cloudbuild.builds.builder`, `roles/artifactregistry.writer`, `roles/storage.admin` | Project | Allows default Cloud Build source builds executing under the Compute SA to push container layers. |

---

## 4. Architectural Notes & Common Pitfalls

1. **Tagged Dark & Canary URLs Require the Canonical Service URL as OIDC Audience**:
   When Gate 3B or Gate 4 probes `https://sha-abc1234---gemma-agent-staging-xyz-uc.a.run.app`, Cloud Run validates the OIDC Bearer JWT `aud` claim against the canonical `status.url` (`https://gemma-agent-staging-xyz-uc.a.run.app`), not the tag-prefixed URL. Both `agent-cd-staging.yml` and `agent-cd-prod.yml` pass `SERVICE_URL` to `--audiences` while targeting the tagged revision URL.
2. **Session Affinity for Multi-Turn ADK Requests**:
   Both CD workflows pass `--session-affinity` and `tests/load/load_test_cloud_run.py` forwards session cookies returned by `POST /sessions` onto `POST /run` so in-memory ADK sessions never hit a different Cloud Run container during traffic splits.
3. **`--condition=None` on `gcloud` IAM Bindings**:
   Projects with existing conditional IAM policies fail in non-interactive shells unless `--condition=None` is passed explicitly.
4. **`--clear-base-image` When Deploying with a `Dockerfile`**:
   If a Cloud Run service was previously deployed via Google Cloud Buildpacks, switching to a `Dockerfile` source build requires `--clear-base-image` (idempotent on all subsequent deploys).

---

## 5. Manual `gcloud` Reference (Without Helper Script)

If your organization requires running raw `gcloud` commands manually instead of `cicd/setup_wif.py`:

```bash
export PROJECT_ID="staging-project"          # or prod-project
export GCP_REGION="us-west1"
export GITHUB_REPO=$(gh repo view --json nameWithOwner -q .nameWithOwner)
PROJECT_NUMBER=$(gcloud projects describe "$PROJECT_ID" --format="value(projectNumber)")
GHA_SA="github-actions-cd@${PROJECT_ID}.iam.gserviceaccount.com"
COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

gcloud services enable \
  run.googleapis.com aiplatform.googleapis.com cloudbuild.googleapis.com \
  artifactregistry.googleapis.com cloudtrace.googleapis.com iamcredentials.googleapis.com \
  --project="$PROJECT_ID"

gcloud artifacts repositories create cloud-run-source-deploy \
  --repository-format=docker --location="$GCP_REGION" \
  --project="$PROJECT_ID" 2>/dev/null || true

gcloud iam service-accounts create github-actions-cd \
  --display-name="GitHub Actions CD" --project="$PROJECT_ID" 2>/dev/null || true

for ROLE in roles/cloudbuild.builds.builder roles/artifactregistry.writer \
  roles/storage.admin roles/aiplatform.user roles/cloudtrace.agent \
  roles/logging.logWriter; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${COMPUTE_SA}" --role="$ROLE" --condition=None
done

for ROLE in roles/run.admin roles/cloudbuild.builds.editor roles/artifactregistry.admin \
  roles/storage.admin roles/iam.serviceAccountUser roles/aiplatform.user; do
  gcloud projects add-iam-policy-binding "$PROJECT_ID" \
    --member="serviceAccount:${GHA_SA}" --role="$ROLE" --condition=None
done

gcloud iam service-accounts add-iam-policy-binding "$COMPUTE_SA" \
  --member="serviceAccount:${GHA_SA}" --role="roles/iam.serviceAccountUser" \
  --project="$PROJECT_ID" --condition=None

gcloud iam service-accounts add-iam-policy-binding "$GHA_SA" \
  --member="serviceAccount:${GHA_SA}" --role="roles/iam.serviceAccountTokenCreator" \
  --project="$PROJECT_ID" --condition=None

gcloud iam workload-identity-pools create github-pool \
  --location="global" --display-name="GitHub Actions Pool" \
  --project="$PROJECT_ID" 2>/dev/null || true

gcloud iam workload-identity-pools providers create-oidc github-provider \
  --location="global" --workload-identity-pool="github-pool" \
  --display-name="GitHub Actions Provider" \
  --issuer-uri="https://token.actions.githubusercontent.com" \
  --attribute-mapping="google.subject=assertion.sub,attribute.actor=assertion.actor,attribute.repository=assertion.repository,attribute.repository_owner=assertion.repository_owner" \
  --attribute-condition="assertion.repository == '${GITHUB_REPO}'" \
  --project="$PROJECT_ID" 2>/dev/null || true

WIF_MEMBER="principalSet://iam.googleapis.com/projects/${PROJECT_NUMBER}/locations/global/workloadIdentityPools/github-pool/attribute.repository/${GITHUB_REPO}"
for ROLE in roles/iam.workloadIdentityUser roles/iam.serviceAccountTokenCreator; do
  gcloud iam service-accounts add-iam-policy-binding "$GHA_SA" \
    --project="$PROJECT_ID" --role="$ROLE" --member="$WIF_MEMBER" --condition=None
done
```
