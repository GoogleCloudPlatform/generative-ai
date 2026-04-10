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

package discoveryengine

import (
	"context"
	"errors"
	"testing"
	"time"

	"cloud.google.com/go/discoveryengine/apiv1/discoveryenginepb"
	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"
	"google.golang.org/api/iterator"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/types/known/timestamppb"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
)

// --- fakeIterator ---

// fakeIterator implements userLicenseIterator (and therefore iterator.Pageable)
// by constructing a *iterator.PageInfo whose fetch function serves controlled
// pages of UserLicense protos. This lets tests exercise the real
// iterator.NewPager code path without hitting the Discovery Engine API.
type fakeIterator struct {
	pageInfo *iterator.PageInfo
}

func (f *fakeIterator) PageInfo() *iterator.PageInfo {
	return f.pageInfo
}

// newFakeIterator builds a fakeIterator that delivers pages in order.
// Each element of pages is one page of results. After all pages are exhausted,
// subsequent fetches return an empty slice and an empty token, signalling the
// end of iteration. If fetchErr is non-nil it is returned on the first fetch.
func newFakeIterator(pages [][]*discoveryenginepb.UserLicense, fetchErr error) *fakeIterator {
	// buf holds the items appended by the most recent fetch call. The PageInfo
	// machinery reads from buf via bufLen and takes from it via takeBuf.
	var buf []*discoveryenginepb.UserLicense
	pageIdx := 0

	fetch := func(_ int, _ string) (string, error) {
		if fetchErr != nil {
			return "", fetchErr
		}
		if pageIdx >= len(pages) {
			// No more pages; signal end of iteration with empty token.
			buf = nil
			return "", nil
		}
		buf = pages[pageIdx]
		pageIdx++
		// Return a non-empty token when more pages follow so that
		// iterator.Pager continues iterating. The token value itself is
		// opaque to our tests because fakeIterator ignores it.
		nextToken := ""
		if pageIdx < len(pages) {
			nextToken = "page-token"
		}
		return nextToken, nil
	}

	bufLen := func() int { return len(buf) }

	takeBuf := func() interface{} {
		b := buf
		buf = nil
		return b
	}

	pi, _ := iterator.NewPageInfo(fetch, bufLen, takeBuf)
	return &fakeIterator{pageInfo: pi}
}

// --- fakeUserLicenseClient ---

// fakeUserLicenseClient implements userLicenseClient using testify/mock. The
// ListUserLicenses method returns a userLicenseIterator so that tests can
// supply a fakeIterator directly.
type fakeUserLicenseClient struct {
	mock.Mock
}

func (f *fakeUserLicenseClient) ListUserLicenses(ctx context.Context, req *discoveryenginepb.ListUserLicensesRequest) userLicenseIterator {
	args := f.Called(ctx, req)
	return args.Get(0).(userLicenseIterator)
}

func (f *fakeUserLicenseClient) BatchUpdateUserLicenses(ctx context.Context, req *discoveryenginepb.BatchUpdateUserLicensesRequest) error {
	args := f.Called(ctx, req)
	return args.Error(0)
}

// --- helpers ---

func makeGRPCError(code codes.Code) error {
	return status.Error(code, "test error")
}

// --- ListUserLicenses tests ---

func TestListUserLicenses_HappyPath(t *testing.T) {
	loginTime := time.Date(2025, 1, 15, 10, 0, 0, 0, time.UTC)
	assignTime := time.Date(2025, 1, 1, 8, 0, 0, 0, time.UTC)

	page := []*discoveryenginepb.UserLicense{
		{
			UserPrincipal:          "alice@example.com",
			LicenseConfig:          "SUBSCRIPTION_TIER_ENTERPRISE",
			LicenseAssignmentState: discoveryenginepb.UserLicense_ASSIGNED,
			LastLoginTime:          timestamppb.New(loginTime),
			CreateTime:             timestamppb.New(assignTime),
		},
	}
	fakeIt := newFakeIterator([][]*discoveryenginepb.UserLicense{page}, nil)

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	got, tok, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.NoError(t, err)
	assert.Equal(t, "", tok)
	require.Len(t, got, 1)

	lic := got[0]
	assert.Equal(t, "alice@example.com", lic.UserEmail)
	assert.Equal(t, "SUBSCRIPTION_TIER_ENTERPRISE", lic.LicenseConfigPath)
	assert.Equal(t, models.LicenseStateAssigned, lic.State)
	assert.True(t, lic.LastLoginTime.Equal(loginTime))
	assert.True(t, lic.AssignmentTime.Equal(assignTime))

	mockClient.AssertExpectations(t)
}

func TestListUserLicenses_NilLastLoginTime(t *testing.T) {
	// When both LastLoginTime and CreateTime are nil, both domain fields must
	// be zero so that the GC service's staleness fallback can handle them.
	page := []*discoveryenginepb.UserLicense{
		{
			UserPrincipal:          "bob@example.com",
			LicenseConfig:          "SUBSCRIPTION_TIER_AGENTSPACE_BUSINESS",
			LicenseAssignmentState: discoveryenginepb.UserLicense_ASSIGNED,
			LastLoginTime:          nil,
			CreateTime:             nil,
		},
	}
	fakeIt := newFakeIterator([][]*discoveryenginepb.UserLicense{page}, nil)

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	got, _, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.NoError(t, err)
	require.Len(t, got, 1)
	assert.True(t, got[0].LastLoginTime.IsZero())
	assert.True(t, got[0].AssignmentTime.IsZero())

	mockClient.AssertExpectations(t)
}

func TestListUserLicenses_CreateTimeMappedToAssignmentTime(t *testing.T) {
	// When LastLoginTime is nil but CreateTime is set, AssignmentTime must
	// be populated from CreateTime so the GC service can apply the
	// assignment-date staleness fallback.
	assignTime := time.Date(2026, 3, 1, 9, 0, 0, 0, time.UTC)

	page := []*discoveryenginepb.UserLicense{
		{
			UserPrincipal:          "new-user@example.com",
			LicenseConfig:          "SUBSCRIPTION_TIER_ENTERPRISE",
			LicenseAssignmentState: discoveryenginepb.UserLicense_ASSIGNED,
			LastLoginTime:          nil,
			CreateTime:             timestamppb.New(assignTime),
		},
	}
	fakeIt := newFakeIterator([][]*discoveryenginepb.UserLicense{page}, nil)

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	got, _, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.NoError(t, err)
	require.Len(t, got, 1)
	assert.True(t, got[0].LastLoginTime.IsZero(), "LastLoginTime must be zero when proto field is nil")
	assert.True(t, got[0].AssignmentTime.Equal(assignTime), "AssignmentTime must be populated from CreateTime")

	mockClient.AssertExpectations(t)
}

func TestListUserLicenses_EmptyPage(t *testing.T) {
	// An empty page set signals end of iteration immediately.
	fakeIt := newFakeIterator([][]*discoveryenginepb.UserLicense{}, nil)

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	got, tok, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.NoError(t, err)
	assert.Equal(t, "", tok)
	assert.Empty(t, got)

	mockClient.AssertExpectations(t)
}

// TestListUserLicenses_NextPageTokenPropagation verifies the contract that the
// service layer depends on: when the underlying iterator signals that more data
// is available, ListUserLicenses returns a non-empty nextPageToken; when it is
// the last page, nextPageToken is empty.
//
// iterator.NewPager accumulates items until it has filled licenseListPageSize
// items or the server signals end-of-results with an empty token. A non-empty
// nextPageToken is returned to the adapter caller only when a full page of
// licenseListPageSize items was fetched AND the server returned a cursor for
// more data. The fake simulates exactly that scenario.
func TestListUserLicenses_NextPageTokenPropagation(t *testing.T) {
	// Build a page of exactly licenseListPageSize items so that NewPager stops
	// after one fetch (buffer is full) and returns the server token as nextPageToken.
	fullPage := make([]*discoveryenginepb.UserLicense, licenseListPageSize)
	for i := range fullPage {
		fullPage[i] = &discoveryenginepb.UserLicense{
			UserPrincipal:          "user@example.com",
			LicenseConfig:          "SUBSCRIPTION_TIER_ENTERPRISE",
			LicenseAssignmentState: discoveryenginepb.UserLicense_ASSIGNED,
		}
	}

	// First adapter call: one full page followed by a second page (simulated by
	// having two pages in the fake). NewPager will fetch the first page, fill the
	// buffer to licenseListPageSize, and — because the token is non-empty — return
	// it as nextPageToken without fetching the second page.
	lastPage := []*discoveryenginepb.UserLicense{
		{UserPrincipal: "alice@example.com", LicenseConfig: "SUBSCRIPTION_TIER_ENTERPRISE", LicenseAssignmentState: discoveryenginepb.UserLicense_ASSIGNED},
	}
	fakeIt1 := newFakeIterator([][]*discoveryenginepb.UserLicense{fullPage, lastPage}, nil)

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt1).Once()

	adapter := newWithClient(mockClient)
	got1, nextTok, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.NoError(t, err)
	require.Len(t, got1, licenseListPageSize)
	assert.NotEmpty(t, nextTok, "expected a non-empty next page token when server has more data")

	// Second adapter call: only the last (partial) page remains. The server
	// returns an empty token, so nextPageToken must be empty.
	fakeIt2 := newFakeIterator([][]*discoveryenginepb.UserLicense{lastPage}, nil)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt2).Once()

	got2, finalTok, err := adapter.ListUserLicenses(context.Background(), "my-project", nextTok)

	require.NoError(t, err)
	require.Len(t, got2, 1)
	assert.Equal(t, "alice@example.com", got2[0].UserEmail)
	assert.Empty(t, finalTok, "expected an empty next page token on the last page")

	mockClient.AssertExpectations(t)
}

func TestListUserLicenses_ResourceExhausted(t *testing.T) {
	fakeIt := newFakeIterator(nil, makeGRPCError(codes.ResourceExhausted))

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	_, _, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrAPIRateLimited),
		"error chain missing ErrAPIRateLimited; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrLicenseListFailed),
		"error chain missing ErrLicenseListFailed; err = %v", err)

	mockClient.AssertExpectations(t)
}

func TestListUserLicenses_Unavailable(t *testing.T) {
	fakeIt := newFakeIterator(nil, makeGRPCError(codes.Unavailable))

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	_, _, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrAPIUnavailable),
		"error chain missing ErrAPIUnavailable; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrLicenseListFailed),
		"error chain missing ErrLicenseListFailed; err = %v", err)

	mockClient.AssertExpectations(t)
}

func TestListUserLicenses_Unauthorized(t *testing.T) {
	fakeIt := newFakeIterator(nil, makeGRPCError(codes.Unauthenticated))

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	_, _, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrLicenseListFailed),
		"error chain missing ErrLicenseListFailed; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrAPIUnauthorized),
		"error chain missing ErrAPIUnauthorized; err = %v", err)

	mockClient.AssertExpectations(t)
}

func TestListUserLicenses_RevokedState(t *testing.T) {
	page := []*discoveryenginepb.UserLicense{
		{
			UserPrincipal:          "carol@example.com",
			LicenseConfig:          "SUBSCRIPTION_TIER_ENTERPRISE",
			LicenseAssignmentState: discoveryenginepb.UserLicense_NO_LICENSE,
		},
	}
	fakeIt := newFakeIterator([][]*discoveryenginepb.UserLicense{page}, nil)

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	got, _, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.NoError(t, err)
	require.Len(t, got, 1)
	assert.Equal(t, models.LicenseStateRevoked, got[0].State)

	mockClient.AssertExpectations(t)
}

func TestListUserLicenses_UnknownState(t *testing.T) {
	// Use a raw integer value that does not correspond to any known
	// LicenseAssignmentState constant to simulate a future SDK addition.
	const unknownStateValue = discoveryenginepb.UserLicense_LicenseAssignmentState(99)

	page := []*discoveryenginepb.UserLicense{
		{
			UserPrincipal:          "dave@example.com",
			LicenseConfig:          "SUBSCRIPTION_TIER_ENTERPRISE",
			LicenseAssignmentState: unknownStateValue,
		},
	}
	fakeIt := newFakeIterator([][]*discoveryenginepb.UserLicense{page}, nil)

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("ListUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.ListUserLicensesRequest")).
		Return(fakeIt)

	adapter := newWithClient(mockClient)
	_, _, err := adapter.ListUserLicenses(context.Background(), "my-project", "")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrLicenseListFailed),
		"error chain missing ErrLicenseListFailed; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrUnknownLicenseState),
		"error chain missing ErrUnknownLicenseState; err = %v", err)

	mockClient.AssertExpectations(t)
}

// --- BatchUpdateUserLicenses tests ---

func TestBatchUpdateUserLicenses_ExceedsMaxBatchSize(t *testing.T) {
	updates := make([]models.LicenseUpdate, models.MaxBatchSize+1)
	for i := range updates {
		updates[i] = models.LicenseUpdate{
			UserEmail:         "user@example.com",
			LicenseConfigPath: "projects/my-project/locations/global/licenseConfigs/ent-uuid",
			Action:            models.LicenseActionGrant,
		}
	}

	// No expectations set — the API must not be called.
	mockClient := new(fakeUserLicenseClient)

	adapter := newWithClient(mockClient)
	err := adapter.BatchUpdateUserLicenses(context.Background(), "my-project", updates)

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrBatchUpdateFailed),
		"error chain missing ErrBatchUpdateFailed; err = %v", err)

	// AssertExpectations verifies no unexpected calls were made.
	mockClient.AssertExpectations(t)
}

func TestBatchUpdateUserLicenses_Grant_SetsLicenseConfigAndMask(t *testing.T) {
	configPath := "projects/123/locations/global/licenseConfigs/ent-uuid"
	updates := []models.LicenseUpdate{
		{UserEmail: "alice@example.com", LicenseConfigPath: configPath, Action: models.LicenseActionGrant},
	}

	var capturedReq *discoveryenginepb.BatchUpdateUserLicensesRequest
	mockClient := new(fakeUserLicenseClient)
	mockClient.On("BatchUpdateUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.BatchUpdateUserLicensesRequest")).
		Run(func(args mock.Arguments) {
			capturedReq = args.Get(1).(*discoveryenginepb.BatchUpdateUserLicensesRequest)
		}).
		Return(nil)

	adapter := newWithClient(mockClient)
	err := adapter.BatchUpdateUserLicenses(context.Background(), "my-project", updates)

	require.NoError(t, err)

	src := capturedReq.GetSource().(*discoveryenginepb.BatchUpdateUserLicensesRequest_InlineSource_).InlineSource
	assert.Equal(t, []string{"license_assignment_state", "license_config"}, src.UpdateMask.Paths)
	require.Len(t, src.UserLicenses, 1)
	assert.Equal(t, discoveryenginepb.UserLicense_ASSIGNED, src.UserLicenses[0].LicenseAssignmentState)
	assert.Equal(t, configPath, src.UserLicenses[0].LicenseConfig)

	mockClient.AssertExpectations(t)
}

func TestBatchUpdateUserLicenses_Revoke_OmitsLicenseConfigAndMask(t *testing.T) {
	updates := []models.LicenseUpdate{
		{UserEmail: "bob@example.com", LicenseConfigPath: "projects/123/locations/global/licenseConfigs/ent-uuid", Action: models.LicenseActionRevoke},
	}

	var capturedReq *discoveryenginepb.BatchUpdateUserLicensesRequest
	mockClient := new(fakeUserLicenseClient)
	mockClient.On("BatchUpdateUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.BatchUpdateUserLicensesRequest")).
		Run(func(args mock.Arguments) {
			capturedReq = args.Get(1).(*discoveryenginepb.BatchUpdateUserLicensesRequest)
		}).
		Return(nil)

	adapter := newWithClient(mockClient)
	err := adapter.BatchUpdateUserLicenses(context.Background(), "my-project", updates)

	require.NoError(t, err)

	src := capturedReq.GetSource().(*discoveryenginepb.BatchUpdateUserLicensesRequest_InlineSource_).InlineSource
	assert.Equal(t, []string{"license_assignment_state"}, src.UpdateMask.Paths)
	require.Len(t, src.UserLicenses, 1)
	assert.Equal(t, discoveryenginepb.UserLicense_NO_LICENSE, src.UserLicenses[0].LicenseAssignmentState)
	assert.Empty(t, src.UserLicenses[0].LicenseConfig)

	mockClient.AssertExpectations(t)
}

func TestBatchUpdateUserLicenses_APIError(t *testing.T) {
	updates := []models.LicenseUpdate{
		{UserEmail: "alice@example.com", LicenseConfigPath: "projects/my-project/locations/global/licenseConfigs/ent-uuid", Action: models.LicenseActionGrant},
	}

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("BatchUpdateUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.BatchUpdateUserLicensesRequest")).
		Return(makeGRPCError(codes.Unavailable))

	adapter := newWithClient(mockClient)
	err := adapter.BatchUpdateUserLicenses(context.Background(), "my-project", updates)

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrBatchUpdateFailed),
		"error chain missing ErrBatchUpdateFailed; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrAPIUnavailable),
		"error chain missing ErrAPIUnavailable; err = %v", err)

	mockClient.AssertExpectations(t)
}

func TestBatchUpdateUserLicenses_LicensesExhausted(t *testing.T) {
	// An InvalidArgument error whose message contains "subscription" and "limit"
	// must produce ErrLicensesExhausted in the error chain, not ErrAPIRateLimited
	// or ErrAPIUnavailable. This matches the Discovery Engine API response:
	// "Subscription reaches the limit of N licenses for license config {path}"
	updates := []models.LicenseUpdate{
		{UserEmail: "alice@example.com", LicenseConfigPath: "projects/my-project/locations/global/licenseConfigs/ent-uuid", Action: models.LicenseActionGrant},
	}

	exhaustionErr := status.Error(codes.InvalidArgument, "Subscription reaches the limit of 3 licenses for license config projects/123/locations/global/licenseConfigs/ent-uuid")

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("BatchUpdateUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.BatchUpdateUserLicensesRequest")).
		Return(exhaustionErr)

	adapter := newWithClient(mockClient)
	err := adapter.BatchUpdateUserLicenses(context.Background(), "my-project", updates)

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrBatchUpdateFailed),
		"error chain missing ErrBatchUpdateFailed; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrLicensesExhausted),
		"error chain missing ErrLicensesExhausted; err = %v", err)
	assert.False(t, errors.Is(err, models.ErrAPIRateLimited),
		"ErrAPIRateLimited must not be in chain for exhaustion errors; err = %v", err)

	mockClient.AssertExpectations(t)
}

func TestBatchUpdateUserLicenses_InvalidArgument_NonExhaustion_NotMapped(t *testing.T) {
	// An InvalidArgument error that does NOT contain both "subscription" and
	// "limit" must not be mapped to ErrLicensesExhausted — it passes through as-is.
	updates := []models.LicenseUpdate{
		{UserEmail: "alice@example.com", LicenseConfigPath: "projects/my-project/locations/global/licenseConfigs/ent-uuid", Action: models.LicenseActionGrant},
	}

	otherPrecondErr := status.Error(codes.InvalidArgument, "invalid field: user_principal")

	mockClient := new(fakeUserLicenseClient)
	mockClient.On("BatchUpdateUserLicenses", mock.Anything, mock.AnythingOfType("*discoveryenginepb.BatchUpdateUserLicensesRequest")).
		Return(otherPrecondErr)

	adapter := newWithClient(mockClient)
	err := adapter.BatchUpdateUserLicenses(context.Background(), "my-project", updates)

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrBatchUpdateFailed),
		"error chain missing ErrBatchUpdateFailed; err = %v", err)
	assert.False(t, errors.Is(err, models.ErrLicensesExhausted),
		"ErrLicensesExhausted must not appear for non-exhaustion FailedPrecondition; err = %v", err)

	mockClient.AssertExpectations(t)
}
