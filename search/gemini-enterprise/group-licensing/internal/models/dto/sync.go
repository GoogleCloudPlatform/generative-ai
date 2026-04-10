package dto

// SyncAddRequest is the HTTP request body for POST /sync/add.
// Cloud Scheduler may POST an empty body; all fields are optional overrides.
type SyncAddRequest struct {
	// DryRun overrides the config-level dry_run setting when present.
	// A nil pointer means "use the config value".
	DryRun *bool `json:"dry_run,omitempty"`
}

// Validate checks that SyncAddRequest contains only valid field values.
func (r *SyncAddRequest) Validate() error {
	// No required fields; nothing to validate beyond type safety.
	return nil
}

// SyncAddResponse is the HTTP response body for POST /sync/add.
type SyncAddResponse struct {
	RequestID          string `json:"request_id"`
	LicensesGranted    int    `json:"licenses_granted"`
	LicensesSoftFailed int    `json:"licenses_soft_failed"`
	GroupsProcessed    int    `json:"groups_processed"`
	DryRun             bool   `json:"dry_run"`
}

// SyncRemoveRequest is the HTTP request body for POST /sync/remove.
type SyncRemoveRequest struct {
	// DryRun overrides the config-level dry_run setting when present.
	DryRun *bool `json:"dry_run,omitempty"`
}

// Validate checks that SyncRemoveRequest contains only valid field values.
func (r *SyncRemoveRequest) Validate() error {
	return nil
}

// SyncRemoveResponse is the HTTP response body for POST /sync/remove.
type SyncRemoveResponse struct {
	RequestID       string `json:"request_id"`
	LicensesRevoked int    `json:"licenses_revoked"`
	UsersEvaluated  int    `json:"users_evaluated"`
	DryRun          bool   `json:"dry_run"`
}
