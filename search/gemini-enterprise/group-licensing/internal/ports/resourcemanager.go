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
