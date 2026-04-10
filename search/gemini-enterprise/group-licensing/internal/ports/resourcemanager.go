package ports

import "context"

// ResourceManagerClient is the port through which the service layer resolves
// GCP project metadata. Concrete adapter implementations live in
// internal/adapters/resourcemanager and must satisfy this interface.
type ResourceManagerClient interface {
	// ResolveProjectNumber returns the numeric project number for the given
	// project ID (e.g. "my-project" → "415104041262"). The number is required
	// to match resource paths returned by the Discovery Engine API, which uses
	// project numbers rather than project IDs in licenseConfig resource names.
	ResolveProjectNumber(ctx context.Context, projectID string) (string, error)
}
