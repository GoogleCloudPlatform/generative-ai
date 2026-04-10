# **Technical Design Document: Gemini Enterprise License Management Utility**

## **1. Overview**

This document outlines the technical design for a standalone utility that provides robust, policy-driven license management for Gemini Enterprise. The solution addresses the need for granular, group-based license assignment, which is a critical requirement for large enterprise customers. It is designed to be deployed and managed by the customer within the customer's own Google Cloud project.

The core of the utility is a **Cloud Run Job** that executes scheduled reconciliation and garbage-collection tasks based on a provided JSON configuration.

## **2. Core Application Design & Hosting**

### **2.1. Artifact**

The utility will be delivered as a **Cloud Run Job** container image. This encapsulates all application logic, ensuring consistency and simplifying deployment.

### **2.2. Hosting**

The utility is designed for deployment on **Cloud Run Jobs**. This provides a fully managed, serverless environment that runs to completion and exits — there is no persistent HTTP server. The job scales to zero between executions, minimizing operational overhead and cost.

### **2.3. Performance & Execution**

The utility operates on an eventually consistent model — there is no requirement for "always-on" operation or sub-second response times. Jobs are triggered by Cloud Scheduler on a periodic basis and run to completion.

Cloud Run Jobs support a task timeout of up to **168 hours**, which accommodates organizations with very large user populations. Native task-level parallelism is available via `CLOUD_RUN_TASK_INDEX` and `CLOUD_RUN_TASK_COUNT` environment variables (injected automatically by Cloud Run), allowing the configured project list to be sharded across multiple concurrent task instances.

## **3. Data Storage & Configuration**

The utility uses a JSON-based configuration model which is persisted to GCP Secret Manager.

### **3.1. Entitlement Configuration (Secret Manager)**

Configuration is supplied by administrators as a JSON object stored in **Google Cloud Secret Manager**. This secret is mapped as a **volume mount** to the Cloud Run Job, allowing the utility to read the configuration from a local file path (e.g., `/run/secrets/entitlements.json`) at runtime. This approach ensures that group mappings are managed securely and can be updated independently of the function code.

**Example Configuration Structure:**

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
          "group-sales@example.com",
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

**Top-level fields:**

| Field | Type | Required | Description |
| ----- | ----- | ----- | ----- |
| `billing_account_id` | string | Yes | The GCP billing account ID associated with the managed projects. |
| `projects` | object | Yes | Map of GCP project ID → list of entitlement entries. |
| `settings.staleness_threshold_days` | integer | No | Users inactive beyond this many days are revoked. `0` (default) disables the staleness check. |

**Per-project entry fields:**

Each project maps to an ordered array of entitlement entries. A project may have multiple entries — one per SKU/location combination.

| Field | Type | Required | Description |
| ----- | ----- | ----- | ----- |
| `subscription_tier` | string | Yes | The Gemini SKU to assign. Must be a valid `SubscriptionTier` enum value (see section 5.3). |
| `location` | string | Yes | Geographic region for license management. Must be one of: `global`, `us`, `eu`. |
| `groups` | array of strings | Yes | List of Google Group email addresses whose members are entitled to this SKU. |
```

## **4. Job Definitions & Triggers**

The utility is packaged as a single container image and deployed as **two Cloud Run Job definitions**, each configured with a different `JOB_TYPE` environment variable. Both jobs are triggered by Cloud Scheduler via the Cloud Run Jobs API on independent schedules.

| Job Definition | `JOB_TYPE` | Schedule | Description |
| ----- | ----- | ----- | ----- |
| `gemini-box-office-joiner` | `joiner` | Daily (24hr) | Finds and grants licenses to members of entitled groups. |
| `gemini-box-office-gc` | `gc` | Every 6 hours | Finds and revokes licenses from stale or unentitled users. |

### **4.1. Environment Variables**

| Variable | Source | Description | Default |
| ----- | ----- | ----- | ----- |
| `JOB_TYPE` | Job definition | Selects the workflow to execute (`joiner` or `gc`). Required. | — |
| `DRY_RUN` | Job definition / per-execution override | When `true`, evaluation runs in full but no write API calls are made. Can be overridden per execution via the Cloud Scheduler request body. | `false` |
| `CLOUD_RUN_TASK_INDEX` | Injected by Cloud Run | 0-based index of this task instance. Used to shard the project list. | `0` |
| `CLOUD_RUN_TASK_COUNT` | Injected by Cloud Run | Total number of concurrent task instances. | `1` |

### **4.2. Project-Level Sharding**

When `CLOUD_RUN_TASK_COUNT` is greater than `1`, each task instance processes only the projects assigned to it: projects where `projectIndex % CLOUD_RUN_TASK_COUNT == CLOUD_RUN_TASK_INDEX`. This allows all configured projects to be processed in parallel with no shared state between tasks.

## **5. Detailed Workflows & External API Integrations**

The utility's logic is divided into two primary reconciliation workflows.

### **5.1. Workflow 1: Bulk "Joiner" Job (Scheduled: 24hr)**

* **Trigger:** Cloud Scheduler via the Cloud Run Jobs API (`JOB_TYPE=joiner`).
* **External APIs:**
  1. **Cloud Identity Admin API:** [`members.list`](https://developers.google.com/workspace/admin/directory/reference/rest/v1/members/list) — Go client: [`google.golang.org/api/admin/directory/v1`](https://pkg.go.dev/google.golang.org/api/admin/directory/v1)
  2. **Discovery Engine API:** [`batchUpdateUserLicenses`](https://cloud.google.com/go/discoveryengine/apiv1), [`licenseConfigsUsageStats.list`](https://cloud.google.com/go/discoveryengine/apiv1)
* **Flow:**
  1. For each group in the configuration, it calls the **Cloud Identity Admin API's** `members.list` method (with `includeDerivedMembership=true`).
  2. The job handles cursor-based pagination to traverse all members, including those in nested groups.
  3. For each member that is a `User`, it calls the **Discovery Engine API** (`batchUpdateUserLicenses`) to assign the license. This operation is idempotent.

* **License Pool Exhaustion Handling:**
  If a `batchUpdateUserLicenses` call fails because the license pool for a SKU is exhausted, the job does **not** treat this as a fatal error. Instead it:
  1. Calls `licenseConfigsUsageStats.list` for the affected project to retrieve the current `usedLicenseCount` for the relevant `licenseConfig`.
  2. Computes `available = allocatedCount - usedLicenseCount` (the allocated count is derived from the billing account `licenseConfigDistributions` map fetched at startup).
  3. Retries the batch trimmed to `available` items, granting as many licenses as possible.
  4. Soft-fails the remaining users: logs a `WARN` entry with the count of users who could not be assigned a license, then continues to the next batch or project. The job exits `0`.
  The `licenses_soft_failed` count is included in the final summary log and in the `SyncAddResponse`.

### **5.2. Workflow 2: Bulk "Garbage Collection" Job (Scheduled: 6hr)**

* **Trigger:** Cloud Scheduler via the Cloud Run Jobs API (`JOB_TYPE=gc`).
* **External APIs:**  
  1. **Discovery Engine API:** [`listUserLicenses`](https://cloud.google.com/go/discoveryengine/apiv1) and [`batchUpdateUserLicenses`](https://cloud.google.com/go/discoveryengine/apiv1).  
  2. **Cloud Identity Admin API:** [`members.hasMember`](https://developers.google.com/workspace/admin/directory/reference/rest/v1/members/hasMember) — Go client: [`google.golang.org/api/admin/directory/v1`](https://pkg.go.dev/google.golang.org/api/admin/directory/v1)
* **Flow:**  
  1. Iterates through all licensed users via the **Discovery Engine API** (`listUserLicenses`).  
  2. For each user, the job evaluates two deprovisioning conditions:
      - **Staleness**: If `staleness_threshold_days` is greater than `0`, checks whether the user's staleness reference date is more than `X` days ago. The reference date is chosen as follows: if `lastLoginTime` is set, it is used; if `lastLoginTime` is absent (the user has never logged in), `createTime` (the license assignment timestamp) is used instead, so that a recently provisioned account is not immediately revoked before the user has had a chance to sign in. If both timestamps are absent, the user is treated as immediately stale. Both timestamps are retrieved from the `UserLicense` object provided by the **Discovery Engine API**. Setting `staleness_threshold_days` to `0` (or omitting it) disables this check entirely — only entitlement is evaluated.
      - **Entitlement**: Calls the **Cloud Identity Admin API's** `members.hasMember` method to confirm if the user is still a member of any entitled group.
  3. If **either** condition is met (the user is stale OR no longer entitled), the utility calls the **Discovery Engine API** (`batchUpdateUserLicenses`) to revoke the license.

### **5.3. License Precedence Logic**

In scenarios where a user belongs to multiple groups mapped to different SKUs, the utility applies a hardcoded precedence ranking to ensure the highest entitlement is granted.

**Precedence Ranking (Highest to Lowest):**
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

If a user is eligible for multiple SKUs, the "Joiner" job will only attempt to assign the highest-ranked SKU. The "Garbage Collection" job will not revoke a higher-tier license if the user is still entitled to it, even if they are removed from a lower-tier group.

## **6. Authentication & Authorization** {#6.-authentication-&-authorization}

Two distinct layers of security must be implemented:

1. **Service-Level Authorization:** The utility's Cloud Run Job must run with a dedicated **Google Cloud Service Account**. This account requires the following IAM roles and OAuth scopes:

    **IAM Roles:**
    *   `roles/discoveryengine.admin`: Required to list and update user licenses.
    *   `roles/cloudidentity.groups.viewer`: Required to list group members and verify membership.
    *   `roles/secretmanager.secretAccessor`: Required to read the entitlement configuration mounted from Secret Manager.

    **OAuth Scopes:**
    *   `https://www.googleapis.com/auth/cloud-platform`
    *   `https://www.googleapis.com/auth/cloud-identity.groups.readonly`

    *Note: Domain-Wide Delegation is not required as the Cloud Identity API honors IAM-based permissions at the Organization/Folder level.*

2. **Trigger Authorization:** Access to the Cloud Run Jobs must be restricted to authorized callers. The Cloud Scheduler service account must be granted `roles/run.invoker` on each job resource. No HTTP endpoint is exposed.

## **7. Non-Functional Requirements** {#7.-non-functional-requirements}

* **API Rate Limiting & Concurrency:**
    *   **Request Batching:** The utility MUST utilize the `batchUpdateUserLicenses` endpoint to consolidate up to 100 license modifications (assignments or revocations) per API request, minimizing round-trip latency and quota consumption.
    *   **Backoff:** Exponential backoff will be applied to all 429 and 5xx errors using a standard retry library.
    *   **License Pool Exhaustion:** License pool exhaustion (`ErrLicensesExhausted`) is treated as a soft failure distinct from rate limiting (`ErrAPIRateLimited`). Exhaustion triggers a `licenseConfigsUsageStats.list` lookup, a trimmed retry for remaining available seats, and a structured warning log — it does not abort the job.
* **Structured Logging:**
    *   **Format:** All logs MUST be emitted in JSON format to stdout for automatic ingestion by Cloud Logging.
    *   **Library:** Use Go's standard `log/slog` library.
    *   **Fields:** Every log entry MUST include `severity`, `workflow` (`joiner` | `garbage_collection`), and `message`.
    *   **Contextual Fields:** Include `group_id`, `sku_id`, and `duration_ms` where applicable.
    *   **PII Protection:** `user_email` and other personally identifiable information MUST NOT be logged. `group_id` is the primary identifier for reconciliation context.
* **Multi-Project Deployment:** A single job definition handles all configured projects. For customers with very large project portfolios, `CLOUD_RUN_TASK_COUNT` can be increased to shard the project list across parallel task instances (see section 4.2).
* **Automation:** All components should be deployable with example gCloud commands provided in this repository.
