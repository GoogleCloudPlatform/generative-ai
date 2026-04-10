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

import (
	"context"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
)

// IdpClient is the port through which the service layer interacts
// with the Google Cloud Identity Admin API. Concrete adapter implementations
// live in internal/adapters/cloudidentity and must satisfy this interface.
//
// Adapter satisfaction tests belong in internal/adapters/cloudidentity, not here.
type IdpClient interface {
	// ListMembers returns one page of members for groupEmail. Pass an empty
	// pageToken to start from the beginning. The adapter calls members.list
	// with includeDerivedMembership=true so nested groups are flattened.
	// A non-empty nextPageToken in the response means more pages are available.
	ListMembers(ctx context.Context, groupEmail, pageToken string) (members []models.Member, nextPageToken string, err error)

	// HasMember reports whether userEmail is a direct or indirect member of
	// groupEmail. It wraps the members.hasMember API call.
	HasMember(ctx context.Context, groupEmail, userEmail string) (bool, error)
}
