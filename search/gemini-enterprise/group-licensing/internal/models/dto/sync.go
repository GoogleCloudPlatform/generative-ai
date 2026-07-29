/*
Copyright © 2026 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

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
