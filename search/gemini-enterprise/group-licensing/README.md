# Gemini Box Office

A Cloud Run Job that automates Gemini Enterprise license lifecycle management through scheduled batch reconciliation. It bridges the gap between Google Cloud Identity group membership and Discovery Engine license assignment, providing group-based SKU mapping, automatic provisioning, and stale-license cleanup.

**Authors: [Matt Williams](https://github.com/williamsmt), [Charles He](https://github.com/googlecharles)**

## How it works

Two Cloud Run Job definitions are deployed from a single container image, each triggered by Cloud Scheduler on its own schedule:

| Job | `JOB_TYPE` | Schedule | Description |
|---|---|---|---|
| `gemini-box-office-joiner` | `joiner` | Daily (24hr) | Pages through all configured group members and grants missing licenses. If a user belongs to multiple SKU-mapped groups, the highest-precedence SKU wins. |
| `gemini-box-office-gc` | `garbage_collection` | Every 6 hours | Pages through all licensed users and revokes licenses from users who are stale (no login within the configured threshold) or no longer a member of any entitled group. |

## Environment variables

| Variable | Description | Default |
|---|---|---|
| `JOB_TYPE` | Selects the workflow to run (`joiner` or `garbage_collection`). Required. | — |
| `DRY_RUN` | When `true`, the full evaluation runs but no write API calls are made. Can be overridden per execution via the Cloud Scheduler request body. | `false` |
| `CLOUD_RUN_TASK_INDEX` | Injected by Cloud Run. 0-based index of this task instance. | `0` |
| `CLOUD_RUN_TASK_COUNT` | Injected by Cloud Run. Total number of concurrent task instances. | `1` |

## SKU names and precedence

The current list of Gemini Enterprise subscription tier SKUs is [here](https://docs.cloud.google.com/gemini/enterprise/docs/reference/rest/v1beta/SubscriptionTier).

When a user qualifies for multiple SKUs, the highest-ranked one is assigned:

1. `SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT`
2. `SUBSCRIPTION_TIER_ENTERPRISE`
3. `SUBSCRIPTION_TIER_SEARCH`
4. `SUBSCRIPTION_TIER_NOTEBOOK_LM`
5. `SUBSCRIPTION_TIER_AGENTSPACE_BUSINESS`
6. `SUBSCRIPTION_TIER_AGENTSPACE_STARTER`
7. `SUBSCRIPTION_TIER_FRONTLINE_WORKER`
8. `SUBSCRIPTION_TIER_FRONTLINE_STARTER`
9. `SUBSCRIPTION_TIER_ENTERPRISE_EMERGING`
10. `SUBSCRIPTION_TIER_EDU_PRO`
11. `SUBSCRIPTION_TIER_EDU`
12. `SUBSCRIPTION_TIER_EDU_PRO_EMERGING`
13. `SUBSCRIPTION_TIER_EDU_EMERGING`

## Configuration

Configuration is stored in **GCP Secret Manager** and mounted as a file volume into the job at `/run/secrets/entitlements.json`.

```json
{
  "billing_account_id": "ABCDE-12345-FGHIJ",
  "projects": {
    "customer-project-alpha": [
      {
        "subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE",
        "location": "global",
        "groups": [
          "group-data-scientists@example.com",
          "group-senior-devs@example.com"
        ]
      },
      {
        "subscription_tier": "SUBSCRIPTION_TIER_AGENTSPACE_BUSINESS",
        "location": "global",
        "groups": [
          "group-marketing@example.com",
          "group-general-staff@example.com"
        ]
      }
    ]
  },
  "settings": {
    "staleness_threshold_days": 30
  }
}
```

| Field | Description |
|---|---|
| `billing_account_id` | The GCP billing account ID associated with the managed projects. Required. |
| `projects` | Map of GCP project ID → list of entitlement entries (one per SKU/location combination). |
| `projects[].subscription_tier` | The Gemini SKU for this entry. See **SKU precedence** below for all valid values. |
| `projects[].location` | Geographic region for license management. Must be one of: `global`, `us`, `eu`. |
| `projects[].groups` | List of Google Group email addresses whose members are entitled to this SKU. |
| `settings.staleness_threshold_days` | Users inactive beyond this many days are revoked. Set to `0` (or omit) to disable staleness checking — only entitlement is evaluated. |

Multiple projects can be managed from a single job by adding additional entries under `projects`. For very large project portfolios, set `--tasks N` on the job execution to shard the project list across N parallel task instances.

## IAM, OAuth, API requirements

The job's service account requires the following:

**IAM roles:**
- `roles/discoveryengine.admin` — list and update user licenses
- `roles/cloudidentity.groups.viewer` — list group members and verify membership
- `roles/secretmanager.secretAccessor` — read the mounted configuration secret
- `roles/billing.viewer` — read the purchased Gemini Enterprise subscription configurations

**OAuth scopes:**
- `https://www.googleapis.com/auth/cloud-platform`
- `https://www.googleapis.com/auth/admin.directory.group.member.readonly`

**API requirements:**
- Discovery Engine API (GCP)
- Resource Manager API (GCP)
- Admin SDK API (Cloud Identity / Workspace)

The job uses **Application Default Credentials**. No service account key files are required.

**Trigger authorization:** The Cloud Scheduler service account must be granted `roles/run.invoker` on each Cloud Run Job resource.

## Project structure

```
cmd/job/             # Job entry point
internal/
  adapters/
    cloudidentity/   # Cloud Identity Admin API adapter
    discoveryengine/ # Discovery Engine API adapter
  config/            # Config loading and validation (entitlement config + job settings)
  middleware/        # Structured logging middleware
  models/            # Domain types, DTOs, errors, constants, enums
  ports/             # Interface definitions (IdpClient, GeminiClient)
  services/          # Business logic (JoinerService, GCService)
docs/
  PRD.md             # Product requirements
  TDD.md             # Technical design document
Dockerfile           # Multi-stage build → distroless runtime image
```

## Building

```bash
docker build -t gemini-box-office:latest .
```

## Running tests

```bash
go test ./...
```

All tests are unit tests and require no external services or credentials.

## Deploying to Cloud Run as Job

An example command to deploy as a job on Cloud Run is below. For more information on creating Cloud Run jobs, reference documentation [here](https://docs.cloud.google.com/run/docs/create-jobs).
```bash
gcloud run jobs deploy [name_of_job] \
  --source . \
  --region [desired_cloud_run_region] \
  --update-secrets=/run/secrets/entitlements.json=[name_of_secret_in_secret_manager]:latest \
  --set-env-vars JOB_TYPE=[joiner_or_garbage_collection],DRY_RUN=false
```

## Job output

On completion the job exits `0` (success) or `1` (failure). Results are emitted as structured JSON log entries to stdout and ingested automatically by Cloud Logging:

```json
{"time":"...","level":"INFO","workflow":"joiner","task_index":0,"msg":"joiner workflow complete","duration_ms":4821,"licenses_granted":42,"licenses_soft_failed":0,"groups_processed":5,"dry_run":false}
```

If the license pool for a SKU is exhausted mid-run, a warning is emitted and the job continues:

```json
{"time":"...","level":"WARN","workflow":"joiner","task_index":0,"msg":"license pool exhausted, soft-failing remaining users","project_id":"customer-project-alpha","license_config_path":"projects/123/locations/global/licenseConfigs/ent-config","available":3,"soft_failed":17}
```

```json
{"time":"...","level":"INFO","workflow":"garbage_collection","task_index":0,"msg":"garbage collection workflow complete","duration_ms":9134,"licenses_revoked":12,"users_evaluated":500,"dry_run":false}
```

## Logging

All log output is structured JSON emitted to stdout for automatic ingestion by Cloud Logging. Every entry includes `workflow` and `task_index` fields. PII (user email addresses) is never logged.
