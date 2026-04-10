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
