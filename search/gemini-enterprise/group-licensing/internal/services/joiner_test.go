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

package services

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"

	"github.com/cloud-gtm/gemini-box-office/internal/config"
	"github.com/cloud-gtm/gemini-box-office/internal/models"
	"github.com/cloud-gtm/gemini-box-office/internal/models/dto"
)

// boolPtr is a helper that returns a pointer to the given bool value.
func boolPtr(b bool) *bool { return &b }

// newJoinerConfig builds a minimal EntitlementConfig for joiner tests.
func newJoinerConfig(projects map[string]config.ProjectConfig) *config.EntitlementConfig {
	return &config.EntitlementConfig{
		BillingAccountID: "ABCDE-12345-FGHIJ",
		Projects:         projects,
		Settings: config.Settings{
			StalenessThresholdDays: 30,
		},
	}
}

// projectNumber is the fake numeric project number used in joiner tests.
// licenseIndexForProject keys use this number (as the API would return),
// while the config uses human-readable project IDs.
const projectNumber = "123456789"

// licenseIndexForProject returns a LicenseConfigIndex keyed by project number
// (as the Discovery Engine API returns) for the SKU/location combinations used
// across joiner tests.
func licenseIndexForProject(number string) models.LicenseConfigIndex {
	return models.LicenseConfigIndex{
		{SKU: models.SKUAgentspaceBusiness, ProjectNumber: number, Location: models.LocationGlobal}: {Path: "projects/" + number + "/locations/global/licenseConfigs/biz-config", AllocatedCount: 100},
		{SKU: models.SKUEnterprise, ProjectNumber: number, Location: models.LocationGlobal}:         {Path: "projects/" + number + "/locations/global/licenseConfigs/ent-config", AllocatedCount: 50},
	}
}

func TestJoinerService_Run_HappyPath_SKUPrecedence(t *testing.T) {
	// A user who is a member of both a GEMINI_BUSINESS group and a
	// GEMINI_ENTERPRISE group should receive only GEMINI_ENTERPRISE (higher
	// precedence). A user in only GEMINI_BUSINESS gets that SKU.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID   = "proj-1"
		groupBiz    = "biz@example.com"
		groupEnt    = "ent@example.com"
		userBizOnly = "biz-only@example.com"
		userBoth    = "both@example.com"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	// GEMINI_BUSINESS group: biz-only and both users.
	idp.On("ListMembers", mock.Anything, groupBiz, "").
		Return([]models.Member{
			{Email: userBizOnly, Type: models.MemberTypeUser},
			{Email: userBoth, Type: models.MemberTypeUser},
		}, "", nil)

	// GEMINI_ENTERPRISE group: only the "both" user.
	idp.On("ListMembers", mock.Anything, groupEnt, "").
		Return([]models.Member{
			{Email: userBoth, Type: models.MemberTypeUser},
		}, "", nil)

	// Updates are now grouped by licenseConfigPath, so we expect two separate
	// BatchUpdateUserLicenses calls: one for ent-config (bothUser) and one for
	// biz-config (bizOnlyUser). The calls may arrive in either order.
	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 1 &&
			updates[0].UserEmail == userBoth &&
			updates[0].LicenseConfigPath == "projects/"+projectNumber+"/locations/global/licenseConfigs/ent-config" &&
			updates[0].Action == models.LicenseActionGrant
	})).Return(nil)
	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 1 &&
			updates[0].UserEmail == userBizOnly &&
			updates[0].LicenseConfigPath == "projects/"+projectNumber+"/locations/global/licenseConfigs/biz-config" &&
			updates[0].Action == models.LicenseActionGrant
	})).Return(nil)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{groupBiz}},
			{SubscriptionTier: models.SKUEnterprise, Location: models.LocationGlobal, Groups: []string{groupEnt}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	resp, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.NoError(t, err)
	assert.Equal(t, 2, resp.LicensesGranted)
	assert.Equal(t, 2, resp.GroupsProcessed)
	assert.False(t, resp.DryRun)

	idp.AssertExpectations(t)
	gemini.AssertExpectations(t)
	rm.AssertExpectations(t)
}

func TestJoinerService_Run_DryRun_NoAPIWrite(t *testing.T) {
	// In dry-run mode, ListMembers is still called but BatchUpdateUserLicenses
	// must never be invoked.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID = "proj-dry"
		group     = "grp@example.com"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{
			{Email: "user@example.com", Type: models.MemberTypeUser},
		}, "", nil)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	resp, err := svc.Run(ctx, cfg, dto.SyncAddRequest{DryRun: boolPtr(true)})

	require.NoError(t, err)
	assert.True(t, resp.DryRun)
	assert.Equal(t, 1, resp.LicensesGranted)
	assert.Equal(t, 1, resp.GroupsProcessed)

	idp.AssertExpectations(t)
	rm.AssertExpectations(t)
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestJoinerService_Run_FetchLicenseConfigIndexError_ReturnsError(t *testing.T) {
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(models.LicenseConfigIndex(nil), errors.New("billing api unavailable"))

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		"proj-x": {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{"grp@example.com"}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	_, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.Error(t, err)
	rm.AssertNotCalled(t, "ResolveProjectNumber")
	idp.AssertNotCalled(t, "ListMembers")
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestJoinerService_Run_ResolveProjectNumberError_ReturnsError(t *testing.T) {
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, "proj-x").
		Return("", errors.New("project not found"))

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		"proj-x": {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{"grp@example.com"}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	_, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.Error(t, err)
	idp.AssertNotCalled(t, "ListMembers")
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestJoinerService_Run_ListMembersError_ReturnsWrappedError(t *testing.T) {
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID = "proj-err"
		group     = "grp@example.com"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return(nil, "", models.ErrMemberListFailed)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	_, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrMemberListFailed))

	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestJoinerService_Run_BatchUpdateError_ReturnsError(t *testing.T) {
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID = "proj-batch-err"
		group     = "grp@example.com"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{
			{Email: "user@example.com", Type: models.MemberTypeUser},
		}, "", nil)

	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.Anything).
		Return(models.ErrBatchUpdateFailed)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	_, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrBatchUpdateFailed))

	idp.AssertExpectations(t)
	gemini.AssertExpectations(t)
	rm.AssertExpectations(t)
}

func TestJoinerService_Run_MultiPagePagination_AllMembersCollected(t *testing.T) {
	// Members are spread across two pages. All must be collected and granted.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID = "proj-pages"
		group     = "grp@example.com"
		tokenP1   = "page-token-1"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{
			{Email: "user-a@example.com", Type: models.MemberTypeUser},
		}, tokenP1, nil)

	idp.On("ListMembers", mock.Anything, group, tokenP1).
		Return([]models.Member{
			{Email: "user-b@example.com", Type: models.MemberTypeUser},
		}, "", nil)

	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 2
	})).Return(nil)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	resp, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.NoError(t, err)
	assert.Equal(t, 2, resp.LicensesGranted)

	idp.AssertExpectations(t)
	gemini.AssertExpectations(t)
	rm.AssertExpectations(t)
}

func TestJoinerService_Run_EmptyGroup_NoBatchCall(t *testing.T) {
	// A group that returns zero members must not trigger any batch call.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID = "proj-empty"
		group     = "empty@example.com"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(models.LicenseConfigIndex{}, nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{}, "", nil)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	resp, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.NoError(t, err)
	assert.Equal(t, 0, resp.LicensesGranted)

	idp.AssertExpectations(t)
	rm.AssertExpectations(t)
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestJoinerService_Run_ContextCancelled_ReturnsError(t *testing.T) {
	// A cancelled context must cause Run to return an error immediately without
	// calling FetchLicenseConfigIndex, ResolveProjectNumber, or ListMembers.
	ctx, cancel := context.WithCancel(context.Background())
	cancel()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		"proj-ctx-joiner": {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{"grp@example.com"}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	_, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.Error(t, err)
	gemini.AssertNotCalled(t, "FetchLicenseConfigIndex")
	rm.AssertNotCalled(t, "ResolveProjectNumber")
	idp.AssertNotCalled(t, "ListMembers")
}

func TestJoinerService_Run_GroupTypeMembersIgnored(t *testing.T) {
	// Members whose Type is GROUP (not USER) must not receive a license.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID = "proj-group-type"
		group     = "parent@example.com"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{
			{Email: "nested-group@example.com", Type: models.MemberTypeGroup},
			{Email: "user@example.com", Type: models.MemberTypeUser},
		}, "", nil)

	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 1 && updates[0].UserEmail == "user@example.com"
	})).Return(nil)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	resp, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.NoError(t, err)
	assert.Equal(t, 1, resp.LicensesGranted)

	idp.AssertExpectations(t)
	gemini.AssertExpectations(t)
	rm.AssertExpectations(t)
}

func TestJoinerService_Run_LicensePoolExhausted_TrimsAndSoftFails(t *testing.T) {
	// BatchUpdateUserLicenses returns ErrLicensesExhausted on the first call.
	// FetchLicenseUsageStats reports 48 used out of 50 allocated → 2 available.
	// The service must retry with 2 users, soft-fail the remaining 3, and exit 0.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID    = "proj-exhaust"
		group        = "grp@example.com"
		configPath   = "projects/" + projectNumber + "/locations/global/licenseConfigs/ent-config"
		allocatedStr = "50"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	// 5 users in the group — all entitled to ENTERPRISE.
	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{
			{Email: "user-1@example.com", Type: models.MemberTypeUser},
			{Email: "user-2@example.com", Type: models.MemberTypeUser},
			{Email: "user-3@example.com", Type: models.MemberTypeUser},
			{Email: "user-4@example.com", Type: models.MemberTypeUser},
			{Email: "user-5@example.com", Type: models.MemberTypeUser},
		}, "", nil)

	// First call (all 5) → exhaustion.
	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 5
	})).Return(models.ErrLicensesExhausted).Once()

	// Usage stats: 48 used, allocated 50 → 2 available.
	gemini.On("FetchLicenseUsageStats", mock.Anything, projectNumber).
		Return(map[string]int64{configPath: 48}, nil)

	// Trimmed retry with exactly 2 users.
	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 2
	})).Return(nil).Once()

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUEnterprise, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	resp, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.NoError(t, err)
	assert.Equal(t, 2, resp.LicensesGranted)
	assert.Equal(t, 3, resp.LicensesSoftFailed)
	assert.False(t, resp.DryRun)

	idp.AssertExpectations(t)
	gemini.AssertExpectations(t)
	rm.AssertExpectations(t)
}

func TestJoinerService_Run_LicensePoolFullyExhausted_AllSoftFailed(t *testing.T) {
	// Pool is completely full (allocated == used). All users must be soft-failed;
	// no trimmed retry should be issued and the job must still exit 0.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID  = "proj-full"
		group      = "grp@example.com"
		configPath = "projects/" + projectNumber + "/locations/global/licenseConfigs/ent-config"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{
			{Email: "user-1@example.com", Type: models.MemberTypeUser},
			{Email: "user-2@example.com", Type: models.MemberTypeUser},
		}, "", nil)

	// First call → exhaustion.
	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 2
	})).Return(models.ErrLicensesExhausted).Once()

	// AllocatedCount for ent-config is 50; report 50 used → 0 available.
	gemini.On("FetchLicenseUsageStats", mock.Anything, projectNumber).
		Return(map[string]int64{configPath: 50}, nil)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUEnterprise, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	resp, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.NoError(t, err)
	assert.Equal(t, 0, resp.LicensesGranted)
	assert.Equal(t, 2, resp.LicensesSoftFailed)

	// No trimmed retry should have been issued.
	gemini.AssertNumberOfCalls(t, "BatchUpdateUserLicenses", 1)
	gemini.AssertExpectations(t)
	rm.AssertExpectations(t)
}

func TestJoinerService_Run_LicensePoolExhausted_UsageStatsFails_ReturnsError(t *testing.T) {
	// When BatchUpdateUserLicenses returns ErrLicensesExhausted and the
	// FetchLicenseUsageStats call also fails, the error must propagate as a
	// hard failure.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID = "proj-stats-err"
		group     = "grp@example.com"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{
			{Email: "user@example.com", Type: models.MemberTypeUser},
		}, "", nil)

	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.Anything).
		Return(models.ErrLicensesExhausted)

	gemini.On("FetchLicenseUsageStats", mock.Anything, projectNumber).
		Return(nil, errors.New("usage stats api unavailable"))

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUEnterprise, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	_, err := svc.Run(ctx, cfg, dto.SyncAddRequest{})

	require.Error(t, err)

	idp.AssertExpectations(t)
	gemini.AssertExpectations(t)
	rm.AssertExpectations(t)
}

func TestJoinerService_Run_LicensePoolExhausted_DryRun_NoFetchOrRetry(t *testing.T) {
	// In dry-run mode, exhaustion can never be triggered because no API writes
	// are made. All users should be counted as granted without any
	// BatchUpdateUserLicenses or FetchLicenseUsageStats calls.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)
	rm := new(MockResourceManagerClient)

	const (
		projectID = "proj-dry-exhaust"
		group     = "grp@example.com"
	)

	gemini.On("FetchLicenseConfigIndex", mock.Anything, "ABCDE-12345-FGHIJ").
		Return(licenseIndexForProject(projectNumber), nil)
	rm.On("ResolveProjectNumber", mock.Anything, projectID).Return(projectNumber, nil)

	idp.On("ListMembers", mock.Anything, group, "").
		Return([]models.Member{
			{Email: "user-1@example.com", Type: models.MemberTypeUser},
			{Email: "user-2@example.com", Type: models.MemberTypeUser},
		}, "", nil)

	cfg := newJoinerConfig(map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUEnterprise, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewJoinerService(idp, gemini, rm)
	resp, err := svc.Run(ctx, cfg, dto.SyncAddRequest{DryRun: boolPtr(true)})

	require.NoError(t, err)
	assert.Equal(t, 2, resp.LicensesGranted)
	assert.Equal(t, 0, resp.LicensesSoftFailed)
	assert.True(t, resp.DryRun)

	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
	gemini.AssertNotCalled(t, "FetchLicenseUsageStats")
}

func TestJoinerService_collectGroupMembers_PageLimitReached(t *testing.T) {
	// ListMembers always returns one member and a non-empty next-page token,
	// simulating an endless paginator. collectGroupMembers must stop after
	// models.MaxPagesPerGroup calls and return nil (no error).
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		groupEmail = "endless@example.com"
		userEmail  = "user@example.com"
	)

	// The mock returns a non-empty next-page token on every call regardless
	// of the token supplied, so we use mock.Anything for the token argument.
	idp.On("ListMembers", mock.Anything, groupEmail, mock.Anything).
		Return([]models.Member{
			{Email: userEmail, Type: models.MemberTypeUser},
		}, "next-token", nil)

	svc := NewJoinerService(idp, gemini, new(MockResourceManagerClient))
	userBestEntitlement := make(map[string]userEntitlement)

	err := svc.collectGroupMembers(ctx, groupEmail, models.SKUAgentspaceBusiness, models.LocationGlobal, userBestEntitlement)

	require.NoError(t, err)
	idp.AssertNumberOfCalls(t, "ListMembers", models.MaxPagesPerGroup)
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}
