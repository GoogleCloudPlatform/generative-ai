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

package cloudidentity

import (
	"context"
	"errors"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/mock"
	"github.com/stretchr/testify/require"
	admin "google.golang.org/api/admin/directory/v1"
	"google.golang.org/api/googleapi"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
)

// --- mocks ---

// MockMembersListCall implements MembersListCall using testify/mock.
type MockMembersListCall struct {
	mock.Mock
}

func (m *MockMembersListCall) IncludeDerivedMembership(v bool) MembersListCall {
	args := m.Called(v)
	return args.Get(0).(MembersListCall)
}

func (m *MockMembersListCall) MaxResults(n int64) MembersListCall {
	args := m.Called(n)
	return args.Get(0).(MembersListCall)
}

func (m *MockMembersListCall) PageToken(tok string) MembersListCall {
	args := m.Called(tok)
	return args.Get(0).(MembersListCall)
}

func (m *MockMembersListCall) Do() (*admin.Members, error) {
	args := m.Called()
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*admin.Members), args.Error(1)
}

// MockMemberHasMemberCall implements MemberHasMemberCall using testify/mock.
type MockMemberHasMemberCall struct {
	mock.Mock
}

func (m *MockMemberHasMemberCall) Do() (*admin.MembersHasMember, error) {
	args := m.Called()
	if args.Get(0) == nil {
		return nil, args.Error(1)
	}
	return args.Get(0).(*admin.MembersHasMember), args.Error(1)
}

// MockMembersService implements MembersService using testify/mock.
type MockMembersService struct {
	mock.Mock
}

func (m *MockMembersService) List(groupEmail string) MembersListCall {
	args := m.Called(groupEmail)
	return args.Get(0).(MembersListCall)
}

func (m *MockMembersService) HasMember(groupEmail, userEmail string) MemberHasMemberCall {
	args := m.Called(groupEmail, userEmail)
	return args.Get(0).(MemberHasMemberCall)
}

// --- helpers ---

func makeAPIError(code int) *googleapi.Error {
	return &googleapi.Error{Code: code, Message: "test error"}
}

// --- tests ---

func TestListMembers_HappyPath(t *testing.T) {
	listCall := new(MockMembersListCall)
	listCall.On("IncludeDerivedMembership", true).Return(listCall)
	listCall.On("MaxResults", int64(models.MembersListPageSize)).Return(listCall)
	listCall.On("Do").Return(&admin.Members{
		Members: []*admin.Member{
			{Email: "alice@example.com", Type: "USER"},
			{Email: "nested-group@example.com", Type: "GROUP"},
		},
		NextPageToken: "",
	}, nil)

	mockSvc := new(MockMembersService)
	mockSvc.On("List", "group@example.com").Return(listCall)

	adapter := newWithMembers(mockSvc)
	got, tok, err := adapter.ListMembers(context.Background(), "group@example.com", "")

	require.NoError(t, err)
	assert.Equal(t, "", tok)
	require.Len(t, got, 2)
	assert.Equal(t, "alice@example.com", got[0].Email)
	assert.Equal(t, models.MemberTypeUser, got[0].Type)
	assert.Equal(t, "nested-group@example.com", got[1].Email)
	assert.Equal(t, models.MemberTypeGroup, got[1].Type)

	mockSvc.AssertExpectations(t)
	listCall.AssertExpectations(t)
}

func TestListMembers_Pagination(t *testing.T) {
	const wantToken = "next-page-token-abc"

	listCall := new(MockMembersListCall)
	listCall.On("IncludeDerivedMembership", true).Return(listCall)
	listCall.On("MaxResults", int64(models.MembersListPageSize)).Return(listCall)
	listCall.On("Do").Return(&admin.Members{
		Members: []*admin.Member{
			{Email: "bob@example.com", Type: "USER"},
		},
		NextPageToken: wantToken,
	}, nil)

	mockSvc := new(MockMembersService)
	mockSvc.On("List", "group@example.com").Return(listCall)

	adapter := newWithMembers(mockSvc)
	_, tok, err := adapter.ListMembers(context.Background(), "group@example.com", "")

	require.NoError(t, err)
	assert.Equal(t, wantToken, tok)

	mockSvc.AssertExpectations(t)
	listCall.AssertExpectations(t)
}

func TestListMembers_PageTokenPropagated(t *testing.T) {
	// When ListMembers is called with a non-empty pageToken, the adapter must
	// pass it to call.PageToken — exercising the conditional branch in adapter.go.
	const incomingToken = "resume-token-xyz"

	listCall := new(MockMembersListCall)
	listCall.On("IncludeDerivedMembership", true).Return(listCall)
	listCall.On("MaxResults", int64(models.MembersListPageSize)).Return(listCall)
	listCall.On("PageToken", incomingToken).Return(listCall)
	listCall.On("Do").Return(&admin.Members{
		Members:       []*admin.Member{{Email: "carol@example.com", Type: "USER"}},
		NextPageToken: "",
	}, nil)

	mockSvc := new(MockMembersService)
	mockSvc.On("List", "group@example.com").Return(listCall)

	adapter := newWithMembers(mockSvc)
	_, _, err := adapter.ListMembers(context.Background(), "group@example.com", incomingToken)

	require.NoError(t, err)

	mockSvc.AssertExpectations(t)
	listCall.AssertExpectations(t) // verifies PageToken(incomingToken) was called
}

func TestListMembers_RateLimited(t *testing.T) {
	listCall := new(MockMembersListCall)
	listCall.On("IncludeDerivedMembership", true).Return(listCall)
	listCall.On("MaxResults", int64(models.MembersListPageSize)).Return(listCall)
	listCall.On("Do").Return((*admin.Members)(nil), makeAPIError(429))

	mockSvc := new(MockMembersService)
	mockSvc.On("List", "group@example.com").Return(listCall)

	adapter := newWithMembers(mockSvc)
	_, _, err := adapter.ListMembers(context.Background(), "group@example.com", "")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrAPIRateLimited),
		"error chain missing ErrAPIRateLimited; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrMemberListFailed),
		"error chain missing ErrMemberListFailed; err = %v", err)

	mockSvc.AssertExpectations(t)
	listCall.AssertExpectations(t)
}

func TestHasMember_True(t *testing.T) {
	hasMemberCall := new(MockMemberHasMemberCall)
	hasMemberCall.On("Do").Return(&admin.MembersHasMember{IsMember: true}, nil)

	mockSvc := new(MockMembersService)
	mockSvc.On("HasMember", "group@example.com", "alice@example.com").Return(hasMemberCall)

	adapter := newWithMembers(mockSvc)
	got, err := adapter.HasMember(context.Background(), "group@example.com", "alice@example.com")

	require.NoError(t, err)
	assert.True(t, got)

	mockSvc.AssertExpectations(t)
	hasMemberCall.AssertExpectations(t)
}

func TestHasMember_False(t *testing.T) {
	hasMemberCall := new(MockMemberHasMemberCall)
	hasMemberCall.On("Do").Return(&admin.MembersHasMember{IsMember: false}, nil)

	mockSvc := new(MockMembersService)
	mockSvc.On("HasMember", "group@example.com", "unknown@example.com").Return(hasMemberCall)

	adapter := newWithMembers(mockSvc)
	got, err := adapter.HasMember(context.Background(), "group@example.com", "unknown@example.com")

	require.NoError(t, err)
	assert.False(t, got)

	mockSvc.AssertExpectations(t)
	hasMemberCall.AssertExpectations(t)
}

func TestHasMember_Forbidden(t *testing.T) {
	hasMemberCall := new(MockMemberHasMemberCall)
	hasMemberCall.On("Do").Return((*admin.MembersHasMember)(nil), makeAPIError(403))

	mockSvc := new(MockMembersService)
	mockSvc.On("HasMember", "group@example.com", "alice@example.com").Return(hasMemberCall)

	adapter := newWithMembers(mockSvc)
	_, err := adapter.HasMember(context.Background(), "group@example.com", "alice@example.com")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrAPIUnauthorized),
		"error chain missing ErrAPIUnauthorized; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrMembershipCheckFailed),
		"error chain missing ErrMembershipCheckFailed; err = %v", err)

	mockSvc.AssertExpectations(t)
	hasMemberCall.AssertExpectations(t)
}

func TestListMembers_ServerError(t *testing.T) {
	listCall := new(MockMembersListCall)
	listCall.On("IncludeDerivedMembership", true).Return(listCall)
	listCall.On("MaxResults", int64(models.MembersListPageSize)).Return(listCall)
	listCall.On("Do").Return((*admin.Members)(nil), makeAPIError(500))

	mockSvc := new(MockMembersService)
	mockSvc.On("List", "group@example.com").Return(listCall)

	adapter := newWithMembers(mockSvc)
	_, _, err := adapter.ListMembers(context.Background(), "group@example.com", "")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrMemberListFailed),
		"error chain missing ErrMemberListFailed; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrAPIUnavailable),
		"error chain missing ErrAPIUnavailable; err = %v", err)

	mockSvc.AssertExpectations(t)
	listCall.AssertExpectations(t)
}

func TestListMembers_Unauthorized(t *testing.T) {
	listCall := new(MockMembersListCall)
	listCall.On("IncludeDerivedMembership", true).Return(listCall)
	listCall.On("MaxResults", int64(models.MembersListPageSize)).Return(listCall)
	listCall.On("Do").Return((*admin.Members)(nil), makeAPIError(401))

	mockSvc := new(MockMembersService)
	mockSvc.On("List", "group@example.com").Return(listCall)

	adapter := newWithMembers(mockSvc)
	_, _, err := adapter.ListMembers(context.Background(), "group@example.com", "")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrMemberListFailed),
		"error chain missing ErrMemberListFailed; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrAPIUnauthorized),
		"error chain missing ErrAPIUnauthorized; err = %v", err)

	mockSvc.AssertExpectations(t)
	listCall.AssertExpectations(t)
}

func TestListMembers_EmptyGroup(t *testing.T) {
	listCall := new(MockMembersListCall)
	listCall.On("IncludeDerivedMembership", true).Return(listCall)
	listCall.On("MaxResults", int64(models.MembersListPageSize)).Return(listCall)
	listCall.On("Do").Return(&admin.Members{Members: nil, NextPageToken: ""}, nil)

	mockSvc := new(MockMembersService)
	mockSvc.On("List", "group@example.com").Return(listCall)

	adapter := newWithMembers(mockSvc)
	got, tok, err := adapter.ListMembers(context.Background(), "group@example.com", "")

	require.NoError(t, err)
	assert.Empty(t, got)
	assert.Equal(t, "", tok)

	mockSvc.AssertExpectations(t)
	listCall.AssertExpectations(t)
}

func TestHasMember_RateLimited(t *testing.T) {
	hasMemberCall := new(MockMemberHasMemberCall)
	hasMemberCall.On("Do").Return((*admin.MembersHasMember)(nil), makeAPIError(429))

	mockSvc := new(MockMembersService)
	mockSvc.On("HasMember", "group@example.com", "alice@example.com").Return(hasMemberCall)

	adapter := newWithMembers(mockSvc)
	_, err := adapter.HasMember(context.Background(), "group@example.com", "alice@example.com")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrMembershipCheckFailed),
		"error chain missing ErrMembershipCheckFailed; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrAPIRateLimited),
		"error chain missing ErrAPIRateLimited; err = %v", err)

	mockSvc.AssertExpectations(t)
	hasMemberCall.AssertExpectations(t)
}

func TestHasMember_ServerError(t *testing.T) {
	hasMemberCall := new(MockMemberHasMemberCall)
	hasMemberCall.On("Do").Return((*admin.MembersHasMember)(nil), makeAPIError(500))

	mockSvc := new(MockMembersService)
	mockSvc.On("HasMember", "group@example.com", "alice@example.com").Return(hasMemberCall)

	adapter := newWithMembers(mockSvc)
	_, err := adapter.HasMember(context.Background(), "group@example.com", "alice@example.com")

	require.Error(t, err)
	assert.True(t, errors.Is(err, models.ErrMembershipCheckFailed),
		"error chain missing ErrMembershipCheckFailed; err = %v", err)
	assert.True(t, errors.Is(err, models.ErrAPIUnavailable),
		"error chain missing ErrAPIUnavailable; err = %v", err)

	mockSvc.AssertExpectations(t)
	hasMemberCall.AssertExpectations(t)
}
