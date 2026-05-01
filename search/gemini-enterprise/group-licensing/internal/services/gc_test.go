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
	"time"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"

	"github.com/cloud-gtm/gemini-box-office/internal/config"
	"github.com/cloud-gtm/gemini-box-office/internal/models"
	"github.com/cloud-gtm/gemini-box-office/internal/models/dto"
)

// newGCConfig is a helper that returns an EntitlementConfig ready for GC tests.
// thresholdDays is used directly: 0 means the staleness check is disabled.
func newGCConfig(thresholdDays int, projects map[string]config.ProjectConfig) *config.EntitlementConfig {
	return &config.EntitlementConfig{
		BillingAccountID: "ABCDE-12345-FGHIJ",
		Projects:         projects,
		Settings: config.Settings{
			StalenessThresholdDays: thresholdDays,
		},
	}
}

func TestGCService_Run_StaleUser_LicenseRevoked(t *testing.T) {
	// A user whose last login is older than the staleness threshold must be revoked.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-stale"
		group     = "grp@example.com"
		userEmail = "stale-user@example.com"
	)

	staleLogin := time.Now().AddDate(0, 0, -60) // 60 days ago — beyond 30-day threshold.

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:     userEmail,
				State:         models.LicenseStateAssigned,
				LastLoginTime: staleLogin,
			},
		}, "", nil)

	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 1 &&
			updates[0].UserEmail == userEmail &&
			updates[0].Action == models.LicenseActionRevoke
	})).Return(nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 1, resp.LicensesRevoked)
	assert.Equal(t, 1, resp.UsersEvaluated)

	gemini.AssertExpectations(t)
	// Stale check short-circuits; HasMember must NOT be called.
	idp.AssertNotCalled(t, "HasMember")
}

func TestGCService_Run_NeverLoggedIn_RecentAssignment_LicenseKept(t *testing.T) {
	// A user who has never logged in but was assigned a license recently (within
	// the staleness threshold) must NOT be revoked. AssignmentTime is used as the
	// staleness reference when LastLoginTime is zero.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-never-recent"
		group     = "grp@example.com"
		userEmail = "new-user@example.com"
	)

	recentAssignment := time.Now().AddDate(0, 0, -5) // assigned 5 days ago — within 30-day threshold

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:      userEmail,
				State:          models.LicenseStateAssigned,
				LastLoginTime:  time.Time{},      // never logged in
				AssignmentTime: recentAssignment, // but recently provisioned
			},
		}, "", nil)

	// Still entitled — must be checked because staleness does not short-circuit.
	idp.On("HasMember", mock.Anything, group, userEmail).Return(true, nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 0, resp.LicensesRevoked)
	assert.Equal(t, 1, resp.UsersEvaluated)

	idp.AssertExpectations(t)
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestGCService_Run_NeverLoggedIn_StaleAssignment_LicenseRevoked(t *testing.T) {
	// A user who has never logged in and whose assignment date is beyond the
	// staleness threshold must have their license revoked. AssignmentTime is
	// used as the staleness reference when LastLoginTime is zero.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-never-stale"
		group     = "grp@example.com"
		userEmail = "ghost@example.com"
	)

	staleAssignment := time.Now().AddDate(0, 0, -60) // assigned 60 days ago — beyond 30-day threshold

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:      userEmail,
				State:          models.LicenseStateAssigned,
				LastLoginTime:  time.Time{},     // never logged in
				AssignmentTime: staleAssignment, // and assigned long ago
			},
		}, "", nil)

	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 1 &&
			updates[0].UserEmail == userEmail &&
			updates[0].Action == models.LicenseActionRevoke
	})).Return(nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 1, resp.LicensesRevoked)
	assert.Equal(t, 1, resp.UsersEvaluated)

	gemini.AssertExpectations(t)
	// Staleness short-circuits via AssignmentTime; HasMember must NOT be called.
	idp.AssertNotCalled(t, "HasMember")
}

func TestGCService_Run_NeverLoggedIn_NoAssignmentTime_LicenseRevoked(t *testing.T) {
	// When both LastLoginTime and AssignmentTime are zero (pathological case),
	// the user is treated as immediately stale and the license is revoked.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-never-no-assign"
		group     = "grp@example.com"
		userEmail = "no-timestamps@example.com"
	)

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:      userEmail,
				State:          models.LicenseStateAssigned,
				LastLoginTime:  time.Time{}, // never logged in
				AssignmentTime: time.Time{}, // no assignment time available
			},
		}, "", nil)

	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 1 &&
			updates[0].UserEmail == userEmail &&
			updates[0].Action == models.LicenseActionRevoke
	})).Return(nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 1, resp.LicensesRevoked)
	assert.Equal(t, 1, resp.UsersEvaluated)

	gemini.AssertExpectations(t)
	idp.AssertNotCalled(t, "HasMember")
}

func TestGCService_Run_EntitledActiveUser_NotRevoked(t *testing.T) {
	// A user with a recent login who is still a member of a configured group
	// must NOT be revoked.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-ok"
		group     = "grp@example.com"
		userEmail = "active@example.com"
	)

	recentLogin := time.Now().AddDate(0, 0, -5) // 5 days ago — within threshold.

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:     userEmail,
				State:         models.LicenseStateAssigned,
				LastLoginTime: recentLogin,
			},
		}, "", nil)

	// The user is still a member of the configured group.
	idp.On("HasMember", mock.Anything, group, userEmail).Return(true, nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 0, resp.LicensesRevoked)
	assert.Equal(t, 1, resp.UsersEvaluated)

	idp.AssertExpectations(t)
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestGCService_Run_UnentitledUser_LicenseRevoked(t *testing.T) {
	// A user with a recent login who is NOT a member of any configured group
	// must have their license revoked.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-unentitled"
		group     = "grp@example.com"
		userEmail = "removed@example.com"
	)

	recentLogin := time.Now().AddDate(0, 0, -5)

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:     userEmail,
				State:         models.LicenseStateAssigned,
				LastLoginTime: recentLogin,
			},
		}, "", nil)

	// The user is no longer in the group.
	idp.On("HasMember", mock.Anything, group, userEmail).Return(false, nil)

	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.MatchedBy(func(updates []models.LicenseUpdate) bool {
		return len(updates) == 1 &&
			updates[0].UserEmail == userEmail &&
			updates[0].Action == models.LicenseActionRevoke
	})).Return(nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 1, resp.LicensesRevoked)
	assert.Equal(t, 1, resp.UsersEvaluated)

	idp.AssertExpectations(t)
	gemini.AssertExpectations(t)
}

func TestGCService_Run_DryRun_NoAPIWrite(t *testing.T) {
	// In dry-run mode, evaluation runs in full but BatchUpdateUserLicenses is
	// never called, even when users qualify for revocation.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-dry-gc"
		group     = "grp@example.com"
		userEmail = "stale@example.com"
	)

	staleLogin := time.Now().AddDate(0, 0, -90)

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:     userEmail,
				State:         models.LicenseStateAssigned,
				LastLoginTime: staleLogin,
			},
		}, "", nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{DryRun: boolPtr(true)})

	require.NoError(t, err)
	assert.True(t, resp.DryRun)
	assert.Equal(t, 1, resp.LicensesRevoked)
	assert.Equal(t, 1, resp.UsersEvaluated)

	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestGCService_Run_ListUserLicensesError_ReturnsError(t *testing.T) {
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const projectID = "proj-list-err"

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return(nil, "", models.ErrLicenseListFailed)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{"grp@example.com"}},
		},
	})

	svc := NewGCService(idp, gemini)
	_, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrLicenseListFailed))

	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestGCService_Run_MultiPagePagination_AllUsersEvaluated(t *testing.T) {
	// Licensed users are spread across two pages; both must be evaluated.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-gc-pages"
		group     = "grp@example.com"
		tokenP1   = "gc-page-token-1"
	)

	recentLogin := time.Now().AddDate(0, 0, -1)

	// Page 1.
	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:     "user-a@example.com",
				State:         models.LicenseStateAssigned,
				LastLoginTime: recentLogin,
			},
		}, tokenP1, nil)

	// Page 2.
	gemini.On("ListUserLicenses", mock.Anything, projectID, tokenP1).
		Return([]models.UserLicense{
			{
				UserEmail:     "user-b@example.com",
				State:         models.LicenseStateAssigned,
				LastLoginTime: recentLogin,
			},
		}, "", nil)

	// Both users are still entitled.
	idp.On("HasMember", mock.Anything, group, "user-a@example.com").Return(true, nil)
	idp.On("HasMember", mock.Anything, group, "user-b@example.com").Return(true, nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 2, resp.UsersEvaluated)
	assert.Equal(t, 0, resp.LicensesRevoked)

	idp.AssertExpectations(t)
	gemini.AssertExpectations(t)
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestGCService_Run_HasMemberError_ReturnsError(t *testing.T) {
	// If HasMember returns an error, Run must propagate it.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-hm-err"
		group     = "grp@example.com"
		userEmail = "user@example.com"
	)

	recentLogin := time.Now().AddDate(0, 0, -1)

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:     userEmail,
				State:         models.LicenseStateAssigned,
				LastLoginTime: recentLogin,
			},
		}, "", nil)

	idp.On("HasMember", mock.Anything, group, userEmail).
		Return(false, models.ErrMembershipCheckFailed)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	_, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrMembershipCheckFailed))

	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestGCService_Run_AlreadyRevokedLicense_Skipped(t *testing.T) {
	// A license whose State is already LicenseStateRevoked must be skipped
	// entirely — no membership check, no revocation, not counted in UsersEvaluated.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const projectID = "proj-already-revoked"

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail: "revoked@example.com",
				State:     models.LicenseStateRevoked,
			},
		}, "", nil)

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{"grp@example.com"}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 0, resp.UsersEvaluated)
	assert.Equal(t, 0, resp.LicensesRevoked)

	idp.AssertNotCalled(t, "HasMember")
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestGCService_Run_ContextCancelled_ReturnsError(t *testing.T) {
	// A cancelled context must cause Run to return an error immediately without
	// ever calling ListUserLicenses.
	ctx, cancel := context.WithCancel(context.Background())
	cancel() // cancel before Run is invoked

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const projectID = "proj-ctx-gc"

	cfg := newGCConfig(30, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{"grp@example.com"}},
		},
	})

	svc := NewGCService(idp, gemini)
	_, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.Error(t, err)
	gemini.AssertNotCalled(t, "ListUserLicenses")
}

func TestGCService_Run_StalenessDisabled_NeverLoggedInUserNotRevoked(t *testing.T) {
	// When StalenessThresholdDays is 0 the staleness check is disabled. A user
	// who has never logged in (zero LastLoginTime) but IS a member of the
	// configured group must NOT be revoked — only the entitlement check runs.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const (
		projectID = "proj-staleness-disabled"
		group     = "grp@example.com"
		userEmail = "new-user@example.com"
	)

	gemini.On("ListUserLicenses", mock.Anything, projectID, "").
		Return([]models.UserLicense{
			{
				UserEmail:     userEmail,
				State:         models.LicenseStateAssigned,
				LastLoginTime: time.Time{}, // never logged in
			},
		}, "", nil)

	// The user is still a member of the configured group.
	idp.On("HasMember", mock.Anything, group, userEmail).Return(true, nil)

	cfg := newGCConfig(0, map[string]config.ProjectConfig{
		projectID: {
			{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{group}},
		},
	})

	svc := NewGCService(idp, gemini)
	resp, err := svc.Run(ctx, cfg, dto.SyncRemoveRequest{})

	require.NoError(t, err)
	assert.Equal(t, 0, resp.LicensesRevoked)
	assert.Equal(t, 1, resp.UsersEvaluated)

	// Entitlement check must still run even when staleness is disabled.
	idp.AssertExpectations(t)
	gemini.AssertNotCalled(t, "BatchUpdateUserLicenses")
}

func TestGCService_processProject_PageLimitReached(t *testing.T) {
	// ListUserLicenses always returns one stale licensed user and a non-empty
	// next-page token, simulating an endless paginator. processProject must
	// stop after models.MaxPagesPerGroup calls and return nil error.
	ctx := context.Background()

	idp := new(MockIdpClient)
	gemini := new(MockGeminiClient)

	const projectID = "proj-gc-page-limit"

	staleLogin := time.Now().AddDate(0, 0, -60) // beyond 30-day threshold

	// The mock returns a stale user and a non-empty next-page token on every
	// call regardless of the token supplied.
	gemini.On("ListUserLicenses", mock.Anything, projectID, mock.Anything).
		Return([]models.UserLicense{
			{
				UserEmail:     "stale@example.com",
				State:         models.LicenseStateAssigned,
				LastLoginTime: staleLogin,
			},
		}, "next-token", nil)

	// Each page produces one stale user who triggers a revocation batch.
	gemini.On("BatchUpdateUserLicenses", mock.Anything, projectID, mock.Anything).
		Return(nil)

	projectCfg := config.ProjectConfig{
		{SubscriptionTier: models.SKUAgentspaceBusiness, Location: models.LocationGlobal, Groups: []string{"grp@example.com"}},
	}

	svc := NewGCService(idp, gemini)
	_, _, err := svc.processProject(ctx, projectID, projectCfg, 30, false)

	require.NoError(t, err)
	gemini.AssertNumberOfCalls(t, "ListUserLicenses", models.MaxPagesPerGroup)
}
