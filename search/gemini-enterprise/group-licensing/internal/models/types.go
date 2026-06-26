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

import "time"

// Member represents a single entry returned by the Cloud Identity
// members.list API. Only members whose Type is MemberTypeUser are
// eligible to receive a license; GROUP-typed entries are containers
// that the adapter resolves by passing includeDerivedMembership=true.
type Member struct {
	Email string
	Type  MemberType
}

// UserLicense represents a single record returned by the Discovery
// Engine listUserLicenses API. LastLoginTime is zero when the API
// returns no last-login value (the user has never logged in or the
// field was omitted). AssignmentTime reflects when the license record
// was first created (the proto create_time field); it is used as a
// fallback reference for staleness checks when LastLoginTime is zero,
// so that a recently provisioned user who has not yet signed in is not
// immediately revoked.
type UserLicense struct {
	UserEmail         string
	LicenseConfigPath string // full resource path: projects/{p}/locations/{l}/licenseConfigs/{id}
	State             LicenseState
	LastLoginTime     time.Time
	AssignmentTime    time.Time // zero when the API omits create_time
}

// LicenseUpdate is the unit of work passed to BatchUpdateUserLicenses.
// Each value represents one grant or revoke operation for a single user.
//   - For grants: set SKU and Location; the adapter resolves the licenseConfig path.
//   - For revokes: set LicenseConfigPath from the UserLicense returned by ListUserLicenses.
//
// Callers must not construct slices longer than MaxBatchSize; the adapter
// enforces this limit but the service layer is expected to chunk proactively.
type LicenseUpdate struct {
	UserEmail         string
	SKU               SKU
	Location          Location
	LicenseConfigPath string // revokes only: resource path from UserLicense
	Action            LicenseAction
}

// LicenseConfigKey identifies a license configuration by its SKU, project
// number, and location. It is used as the key in a LicenseConfigIndex.
// ProjectNumber is the numeric GCP project number (e.g. "415104041262"), not
// the human-readable project ID — the Discovery Engine API uses numbers in
// licenseConfig resource paths.
type LicenseConfigKey struct {
	SKU           SKU
	ProjectNumber string
	Location      Location
}

// LicenseConfigEntry holds the full licenseConfig resource path and the number
// of licenses allocated to it from the billing account subscription.
// AllocatedCount is the value from BillingAccountLicenseConfig.LicenseConfigDistributions
// and represents the seat cap for this project/SKU/location combination.
type LicenseConfigEntry struct {
	Path           string
	AllocatedCount int64
}

// LicenseConfigIndex maps (SKU, ProjectNumber, Location) to the resolved
// LicenseConfigEntry. It is built once at startup from the
// billingAccountLicenseConfigs API and used by the service layer to resolve
// grant operations and look up available seat capacity.
type LicenseConfigIndex map[LicenseConfigKey]LicenseConfigEntry
