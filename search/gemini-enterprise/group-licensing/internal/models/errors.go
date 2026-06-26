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

import "errors"

// Config errors.
var (
	ErrConfigNotFound   = errors.New("entitlement config file not found")
	ErrConfigUnreadable = errors.New("entitlement config file could not be read")
	ErrConfigInvalid    = errors.New("entitlement config is invalid or malformed")
	ErrConfigNoProjects = errors.New("entitlement config contains no projects")
	ErrConfigNoGroups   = errors.New("entitlement config contains no groups for project")
)

// SKU errors.
var (
	ErrInvalidSKU = errors.New("unrecognized SKU value")
)

// Location errors.
var (
	ErrInvalidLocation = errors.New("invalid location value")
)

// License operation errors.
var (
	ErrLicenseListFailed   = errors.New("failed to list user licenses")
	ErrBatchUpdateFailed   = errors.New("batch update of user licenses failed")
	ErrLicensesExhausted   = errors.New("license pool exhausted for SKU")
	ErrUnknownLicenseState = errors.New("unknown license assignment state received from API")
)

// Membership check errors.
var (
	ErrMemberListFailed      = errors.New("failed to list group members")
	ErrMembershipCheckFailed = errors.New("failed to check group membership")
)

// API transport errors.
var (
	ErrAPIRateLimited  = errors.New("api request was rate limited (429)")
	ErrAPINotFound     = errors.New("api resource not found (404)")
	ErrAPIUnavailable  = errors.New("api service temporarily unavailable (5xx)")
	ErrAPIUnauthorized = errors.New("api request unauthorized (401/403)")
)
