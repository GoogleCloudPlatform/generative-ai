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

// GeminiClient is the port through which the service layer interacts
// with the Google Gemini Enterprise API. Concrete adapter
// implementations live in internal/adapters/discoveryengine and must satisfy
// this interface.
//
// Adapter satisfaction tests belong in internal/adapters/discoveryengine, not here.
type GeminiClient interface {
	// FetchLicenseConfigIndex retrieves all license configurations for the given
	// billing account and returns an index mapping (SKU, ProjectID, Location) to
	// the full licenseConfig resource path. Call this once at startup and pass the
	// result to SetLicenseConfigIndex before issuing any grant operations.
	FetchLicenseConfigIndex(ctx context.Context, billingAccountID string) (models.LicenseConfigIndex, error)

	// ListUserLicenses returns one page of licensed users for projectID. Pass
	// an empty pageToken to start from the beginning. A non-empty nextPageToken
	// in the response means more pages are available.
	ListUserLicenses(ctx context.Context, projectID, pageToken string) (licenses []models.UserLicense, nextPageToken string, err error)

	// BatchUpdateUserLicenses applies up to models.MaxBatchSize grant or revoke
	// operations in a single API call. The adapter returns models.ErrBatchUpdateFailed
	// if the underlying API reports any per-item or request-level failure.
	// When the license pool for a SKU is exhausted, the error chain contains
	// models.ErrLicensesExhausted. Callers are responsible for splitting slices
	// longer than models.MaxBatchSize into multiple calls.
	BatchUpdateUserLicenses(ctx context.Context, projectID string, updates []models.LicenseUpdate) error

	// FetchLicenseUsageStats returns a map of licenseConfig resource path to
	// the number of licenses currently assigned (usedLicenseCount) for all
	// licenseConfigs under the given project's default user store. Callers use
	// this to compute available seats after a license pool exhaustion error.
	FetchLicenseUsageStats(ctx context.Context, projectID string) (map[string]int64, error)
}
