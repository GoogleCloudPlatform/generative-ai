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
