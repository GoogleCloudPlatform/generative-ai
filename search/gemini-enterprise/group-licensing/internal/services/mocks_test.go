package services

import (
	"context"

	"github.com/stretchr/testify/mock"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
)

// MockResourceManagerClient is a testify/mock implementation of ports.ResourceManagerClient.
type MockResourceManagerClient struct {
	mock.Mock
}

// ResolveProjectNumber satisfies ports.ResourceManagerClient.
func (m *MockResourceManagerClient) ResolveProjectNumber(ctx context.Context, projectID string) (string, error) {
	args := m.Called(ctx, projectID)
	return args.String(0), args.Error(1)
}

// MockIdpClient is a testify/mock implementation of ports.IdpClient.
// It is shared across all service test files in this package.
type MockIdpClient struct {
	mock.Mock
}

// ListMembers satisfies ports.IdpClient.
func (m *MockIdpClient) ListMembers(ctx context.Context, groupEmail, pageToken string) ([]models.Member, string, error) {
	args := m.Called(ctx, groupEmail, pageToken)
	members, _ := args.Get(0).([]models.Member)
	return members, args.String(1), args.Error(2)
}

// HasMember satisfies ports.IdpClient.
func (m *MockIdpClient) HasMember(ctx context.Context, groupEmail, userEmail string) (bool, error) {
	args := m.Called(ctx, groupEmail, userEmail)
	return args.Bool(0), args.Error(1)
}

// MockGeminiClient is a testify/mock implementation of ports.GeminiClient.
// It is shared across all service test files in this package.
type MockGeminiClient struct {
	mock.Mock
}

// FetchLicenseConfigIndex satisfies ports.GeminiClient.
func (m *MockGeminiClient) FetchLicenseConfigIndex(ctx context.Context, billingAccountID string) (models.LicenseConfigIndex, error) {
	args := m.Called(ctx, billingAccountID)
	index, _ := args.Get(0).(models.LicenseConfigIndex)
	return index, args.Error(1)
}

// ListUserLicenses satisfies ports.GeminiClient.
func (m *MockGeminiClient) ListUserLicenses(ctx context.Context, projectID, pageToken string) ([]models.UserLicense, string, error) {
	args := m.Called(ctx, projectID, pageToken)
	licenses, _ := args.Get(0).([]models.UserLicense)
	return licenses, args.String(1), args.Error(2)
}

// BatchUpdateUserLicenses satisfies ports.GeminiClient.
func (m *MockGeminiClient) BatchUpdateUserLicenses(ctx context.Context, projectID string, updates []models.LicenseUpdate) error {
	args := m.Called(ctx, projectID, updates)
	return args.Error(0)
}

// FetchLicenseUsageStats satisfies ports.GeminiClient.
func (m *MockGeminiClient) FetchLicenseUsageStats(ctx context.Context, projectID string) (map[string]int64, error) {
	args := m.Called(ctx, projectID)
	stats, _ := args.Get(0).(map[string]int64)
	return stats, args.Error(1)
}
