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

package models

const (
	// ConfigFilePath is the filesystem path where the entitlement configuration
	// is mounted from GCP Secret Manager.
	ConfigFilePath = "/run/secrets/entitlements.json"

	// MaxBatchSize is the maximum number of license modifications that may be
	// included in a single batchUpdateUserLicenses API call.
	MaxBatchSize = 100

	// MembersListPageSize is the number of members fetched per page when
	// calling the Cloud Identity Admin API members.list method.
	MembersListPageSize = 200

	// MaxPagesPerGroup is the maximum number of pages fetched per group or
	// license listing in a single workflow run. If exceeded, the loop logs a
	// warning and stops processing further pages rather than failing the run —
	// partial results are preferable to a full job failure for a scheduled
	// reconciliation job.
	MaxPagesPerGroup = 500
)
