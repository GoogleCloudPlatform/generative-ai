# Gemini Enterprise Group Licensing — Agent Context

## Mandatory First Step: Read the Service TDD

> [!IMPORTANT]
> **Before making any code changes, architectural decisions, or refactoring in this codebase**, any skill, agent, or subagent **MUST first read the service Technical Design Document (TDD)** located at [docs/TDD.md](file:///usr/local/google/home/williamsmt/Projects/development/generative-ai/search/gemini-enterprise/group-licensing/docs/TDD.md) (in the `docs/` subdirectory). This document contains the definitive architectural requirements, data flows, and design rationale for the service.

## Project identity

- **Module:** `github.com/GoogleCloudPlatform/generative-ai/search/gemini-enterprise/group-licensing`
- **Language:** Go 1.25.4
- **Deployment:** Google Cloud Run Jobs (serverless batch — no HTTP server)
- **Purpose:** Automates Gemini Enterprise license lifecycle management by reconciling Google Cloud Identity group membership with Discovery Engine user license state. Runs two independent workflows from a single binary: `joiner` (grant) and `garbage_collection` (revoke).

## Quick reference

```bash
# Run all unit tests (no credentials required)
go test ./...

# Build the binary
CGO_ENABLED=0 go build -trimpath -ldflags="-s -w" -o /tmp/job ./cmd/job

# Build the container image
docker build -t gemini-box-office:latest .
```

No linter config is present; use `go vet ./...` for static checks.

## Architecture

Strict **Ports and Adapters (Hexagonal Architecture)**. The layers must not be mixed:

```
cmd/job/main.go          composition root — wires adapters into services, dispatches workflow
internal/ports/          Go interfaces (the ports) — the only API surface the service layer sees
internal/adapters/       Concrete Google SDK implementations of the ports
internal/services/       Pure business logic — imports ports only, never adapter or SDK packages
internal/models/         Domain types, enums, sentinel errors, constants — no external imports
internal/config/         Config loading and env-var parsing
internal/middleware/     slog logger retrieval from context
```

Every adapter declares a compile-time interface satisfaction check:
```go
var _ ports.SomeClient = (*Adapter)(nil)
```
Add this to any new adapter you write.

## Key files

| File | Role |
|---|---|
| `docs/TDD.md` | **Technical Design Document (MUST READ FIRST before any changes)** — definitive service architecture, data flows, and requirements |
| `docs/PRD.md` | Product Requirements Document — background and user stories |
| `cmd/job/main.go` | Entry point. 8-step startup: logger → config → settings → logger enrichment → project sharding → client init → workflow dispatch → exit |
| `internal/ports/gemini.go` | `GeminiClient` interface (Discovery Engine) |
| `internal/ports/idp.go` | `IdpClient` interface (Cloud Identity) |
| `internal/ports/resourcemanager.go` | `ResourceManagerClient` interface |
| `internal/services/joiner.go` | Joiner workflow business logic |
| `internal/services/gc.go` | GC workflow business logic + `chunkLicenseUpdates` (shared) |
| `internal/services/mocks_test.go` | `testify/mock` implementations of all three ports (package-internal) |
| `internal/models/types.go` | Domain data structures: `Member`, `UserLicense`, `LicenseUpdate`, `LicenseConfigKey`, `LicenseConfigEntry`, `LicenseConfigIndex` |
| `internal/models/enums.go` | All typed-string enums: `SKU`, `WorkflowType`, `LicenseState`, `LicenseAction`, `Location`, `MemberType` |
| `internal/models/errors.go` | All sentinel errors — use `errors.Is` against these |
| `internal/models/constants.go` | `MaxBatchSize=100`, `MembersListPageSize=200`, `MaxPagesPerGroup=500`, `ConfigFilePath` |
| `internal/models/dto/sync.go` | Request and response DTOs (`SyncAddRequest`/`Response`, `SyncRemoveRequest`/`Response`) |
| `internal/config/config.go` | JSON config parsing and validation rules for entitlement configuration |
| `internal/config/job_settings.go` | Parses and validates Cloud Run Job runtime environment variables (`JOB_TYPE`, `DRY_RUN`, etc.) |
| `internal/adapters/discoveryengine/adapter.go` | Most complex adapter — see Known Constraints below |
| `internal/adapters/cloudidentity/adapter.go` | Cloud Identity Admin SDK adapter implementation |
| `internal/adapters/resourcemanager/adapter.go` | Cloud Resource Manager API v3 adapter implementation |

## Ports (interfaces)

```go
// ports/gemini.go
type GeminiClient interface {
    FetchLicenseConfigIndex(ctx context.Context, billingAccountID string) (models.LicenseConfigIndex, error)
    ListUserLicenses(ctx context.Context, projectID string, location models.Location, pageToken string) ([]models.UserLicense, string, error)
    BatchUpdateUserLicenses(ctx context.Context, projectID string, location models.Location, updates []models.LicenseUpdate) error
    FetchLicenseUsageStats(ctx context.Context, projectID string, location models.Location) (map[string]int64, error)
}

// ports/idp.go
type IdpClient interface {
    ListMembers(ctx context.Context, groupEmail, pageToken string) ([]models.Member, string, error)
    HasMember(ctx context.Context, groupEmail, userEmail string) (bool, error)
}

// ports/resourcemanager.go
type ResourceManagerClient interface {
    ResolveProjectNumber(ctx context.Context, projectID string) (string, error)
}
```

## Workflows

### Joiner (`JOB_TYPE=joiner`)

1. `FetchLicenseConfigIndex` — builds a `LicenseConfigIndex`: `map[LicenseConfigKey][]LicenseConfigEntry`. Multiple active subscriptions for the same `(SKU, ProjectNumber, Location)` appear as distinct slice entries (multi-pool spill).
2. `ResolveProjectNumber` — project IDs → numeric project numbers (Discovery Engine paths use numbers).
3. Per project: page through all group members via `ListMembers` (with `includeDerivedMembership=true`), resolve the highest-precedence SKU per user via `SKU.HasHigherPrecedenceThan`.
4. Group grant updates by `LicenseConfigKey`, chunk to `MaxBatchSize=100`, call `BatchUpdateUserLicenses`.
5. On `ErrLicensesExhausted`: call `FetchLicenseUsageStats`, compute available seats, retry trimmed batch, carry remainder to next subscription pool in the slice. After all pools exhausted, soft-fail remaining users (`licenses_soft_failed` in summary log). Exit 0.

### Garbage Collection (`JOB_TYPE=garbage_collection`)

1. Deduplicate locations from project config; iterate each location separately.
2. Page through `ListUserLicenses`; skip `State=REVOKED` records.
3. Per active license, evaluate `shouldRevoke`:
   - **Staleness** (only when `staleness_threshold_days > 0`): reference time = `LastLoginTime` → fallback `AssignmentTime` → fallback zero (treat as stale). Short-circuits the membership check.
   - **Entitlement**: `HasMember` for every group in the project config. First `true` → keep. All false → revoke.
4. Collect revocation candidates per page, flush in `MaxBatchSize` chunks, then advance to the next page (bounds memory).

### SKU precedence (highest → lowest)

`SEARCH_AND_ASSISTANT` (13) → `ENTERPRISE` (12) → `SEARCH` (11) → `NOTEBOOK_LM` (10) → `AGENTSPACE_BUSINESS` (9) → `AGENTSPACE_STARTER` (8) → `FRONTLINE_WORKER` (7) → `FRONTLINE_STARTER` (6) → `ENTERPRISE_EMERGING` (5) → `EDU_PRO` (4) → `EDU` (3) → `EDU_PRO_EMERGING` (2) → `EDU_EMERGING` (1)

## Error handling model

| Error | Classification | Behavior |
|---|---|---|
| `ErrLicensesExhausted` | Soft failure (joiner only) | Fetch usage stats, trim retry, spill to next pool, `WARN` log, exit 0 |
| `ErrInvalidMemberKey` | Soft failure (GC only) | Skip user, `WARN` log with `problematic_username`, no revocation |
| `ErrAPIRateLimited` | Hard failure | Return error, job exits 1 |
| All other errors | Hard failure | Return error, job exits 1 |

Never promote a soft-failure error to a hard failure. Never demote a hard failure to a soft one without explicit justification.

## Configuration

Runtime config is read from `/run/secrets/entitlements.json` (mounted from Secret Manager):

```json
{
  "billing_account_id": "ABCDE-12345-FGHIJ",
  "projects": {
    "customer-project-alpha": [
      {
        "subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE",
        "location": "global",
        "groups": ["eng-team@example.com"]
      }
    ]
  },
  "settings": {
    "staleness_threshold_days": 30
  }
}
```

Validation rules enforced at startup (`internal/config/config.go`):
- `billing_account_id` must be non-empty
- Project IDs must match `^[a-z][a-z0-9\-]{4,28}[a-z0-9]$`
- Each project must have at least one entry with a valid SKU, a valid location (`global`/`us`/`eu`), and at least one group email
- `staleness_threshold_days` must be `>= 0` (0 = disabled)

Environment variables (`internal/config/job_settings.go`):

| Variable | Required | Default | Notes |
|---|---|---|---|
| `JOB_TYPE` | Yes | — | `joiner` or `garbage_collection` |
| `DRY_RUN` | No | `false` | Skips all write API calls when `true` |
| `CLOUD_RUN_TASK_INDEX` | No | `0` | Injected by Cloud Run |
| `CLOUD_RUN_TASK_COUNT` | No | `1` | Injected by Cloud Run |

## Testing conventions

- All tests are unit tests. `go test ./...` requires no credentials and no network.
- Use `testify/mock` for port mocks. The three mock implementations live in `internal/services/mocks_test.go` (package `services`, not exported). Add new mock methods there rather than creating separate mock files.
- Adapter tests inject testable interfaces via package-private `newWith*` constructors (e.g., `cloudidentity.newWithMembers`, `discoveryengine.newWithClient`). Follow this pattern for any new adapter.
- Service tests are white-box (same package, `package services`). Use table-driven tests with `t.Run` sub-tests.
- Config tests write fixture JSON to `t.TempDir()` — never write to the module root.
- Do not add integration tests or tests that require GCP credentials.

## Known constraints and non-obvious decisions

**Revoke field mask omits `license_config`:** `BatchUpdateUserLicenses` for `REVOKE` sends only `["license_assignment_state"]` in the update mask. Including `license_config` alongside `NO_LICENSE` state triggers a known API bug ("subscription reaches the limit"). Do not change this without re-testing against the live API.

**Discovery Engine gRPC client caching uses double-checked locking:** The `discoveryengine` adapter lazily creates one gRPC client per location using a `sync.Mutex`. The lock is released before the blocking dial, then re-acquired before writing the cache. A post-write check guards against concurrent winners. Do not simplify this without understanding the race.

**Project sharding is deterministic:** `main.go` sorts project map keys with `slices.SortedFunc` before applying modulo arithmetic. This ensures each project is processed by exactly one task instance. Any change to the sharding logic must preserve determinism across all concurrent task instances.

**`LicenseConfigIndex` maps to a slice, not a single entry:** A billing account can have multiple active subscriptions for the same `(SKU, ProjectNumber, Location)`. The slice preserves all pools in order; the joiner iterates them to spill ungranted users from an exhausted pool into the next one. Never collapse this to a single entry.

**`MaxPagesPerGroup=500` is a safety net, not a hard error:** When the limit is hit, a `WARN` is logged and processing continues with partial results. This applies to both `collectGroupMembers` (joiner) and the license listing loop (GC). Partial results are always preferred over a full job failure for a scheduled reconciliation job.

**DTOs carry vestigial HTTP tags:** `dto.SyncAddRequest` and `dto.SyncRemoveRequest` have `json` struct tags referencing `POST /sync/add` and `POST /sync/remove`. These are from an earlier HTTP server design. The structs are constructed directly in `main.go`; no HTTP deserialization occurs. Do not add an HTTP server without re-evaluating the entire auth model.

**PII policy:** User email addresses must not appear in log output at `INFO` level or higher. The sole exception is the `problematic_username` field in the GC `ErrInvalidMemberKey` warning — it is deliberate and logged to help operators diagnose malformed emails stored in Discovery Engine.

**`GROUP`-typed members are discarded in the joiner:** `ListMembers` is called with `includeDerivedMembership=true`, which causes the Admin SDK to return flattened leaf members. Any `Member` whose `Type != MemberTypeUser` is skipped. Do not attempt to recurse into nested groups manually.

## External API surface

The service is a client of three Google Cloud APIs. It exposes no server endpoints.

| API | SDK | Methods used |
|---|---|---|
| Cloud Identity Admin (`admin/directory/v1`) | REST via `google.golang.org/api` | `members.list` (paginated, `includeDerivedMembership=true`), `members.hasMember` |
| Discovery Engine gRPC SDK | `cloud.google.com/go/discoveryengine/apiv1` | `ListUserLicenses` (iterator), `BatchUpdateUserLicenses` (LRO, adapter waits) |
| Discovery Engine REST v1alpha | REST via `google.golang.org/api` | `billingAccounts.billingAccountLicenseConfigs.list`, `projects.locations.userStores.licenseConfigsUsageStats.list` |
| Cloud Resource Manager v3 | REST via `google.golang.org/api` | `projects.get` |

Non-global Discovery Engine gRPC calls use regional endpoints:
- `us` → `us-discoveryengine.googleapis.com:443`
- `eu` → `eu-discoveryengine.googleapis.com:443`
- `global` → default endpoint

## IAM requirements

The Cloud Run Job service account needs:
- `roles/discoveryengine.admin` — list and update user licenses
- `roles/cloudidentity.groups.viewer` — enumerate group members and check membership
- `roles/secretmanager.secretAccessor` — read the entitlement config volume mount
- `roles/billing.viewer` — read billing account license configs

OAuth scopes used:
- `https://www.googleapis.com/auth/cloud-platform`
- `https://www.googleapis.com/auth/admin.directory.group.member.readonly`

## Logging

All logs are structured JSON emitted to stdout via `log/slog` (`slog.NewJSONHandler`). Every log line automatically carries `workflow` and `task_index` (set once in `main.go` step 4). Retrieve the logger in service/adapter code via `middleware.LoggerFromContext(ctx)` — never call `slog.Default()` directly from library code.

Required fields on summary log lines: `duration_ms`, workflow-specific counts (`licenses_granted`, `licenses_revoked`, `licenses_soft_failed`, `groups_processed`, `users_evaluated`), `dry_run`.

## Available Subagents & Delegation

When working on complex tasks in this repository, you can delegate work to specialized subagents using `invoke_subagent`.

### Built-in Subagents

| Subagent | Capabilities | Best Used For |
|---|---|---|
| `research` | Read-only codebase exploration, file reading, and web search | Running broad codebase surveys, searching documentation, or investigating multi-package patterns without cluttering the primary conversation context. |
| `self` | Full inheritance of parent agent's configuration, read/write/execute tools, and model | Running independent implementation tasks, refactoring isolated adapters, or executing comprehensive test suites in a separate conversation context. |
| `owl` | Multi-agent orchestrator with deep strategic planning and verification | Solving complex architectural tasks, large-scale refactoring, or difficult bugs requiring multi-perspective analysis and rigorous verification. |

### Custom Subagents

You can also define custom subagents using `define_subagent` and invoke them with `invoke_subagent`. Subagent workspaces can be configured as:
- `inherit`: Uses the same workspace as the parent agent (default).
- `branch`: Creates an isolated workspace branched or cloned from the parent.
- `share`: Creates a new workspace sharing the underlying repository directory (similar to a git worktree) for independent branching without storage duplication.

### Delegation Guidelines for this Repository

- **Mandatory TDD Review:** When delegating any task that involves modifying code or architecture, explicitly instruct the invoked subagent or skill to read [docs/TDD.md](file:///usr/local/google/home/williamsmt/Projects/development/generative-ai/search/gemini-enterprise/group-licensing/docs/TDD.md) before making any changes.
- **Research & Exploration:** For tasks requiring exploration across multiple adapters (`discoveryengine`, `cloudidentity`, `resourcemanager`), delegate investigation to a `research` subagent.
- **Isolated Adapter Refactoring:** When modifying an individual adapter or adding a new port/adapter implementation, delegate to a `self` subagent in a `branch` or `share` workspace to keep changes isolated and test them cleanly before merging back.
- **Direct Implementation:** For focused, single-package edits (e.g., updating a sentinel error in `models/errors.go` or modifying a service test), perform the work directly in the main conversation.
