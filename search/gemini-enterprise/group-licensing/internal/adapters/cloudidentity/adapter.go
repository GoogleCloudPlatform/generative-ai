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
	"fmt"

	admin "google.golang.org/api/admin/directory/v1"
	"google.golang.org/api/googleapi"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
	"github.com/cloud-gtm/gemini-box-office/internal/ports"
)

var _ ports.IdpClient = (*Adapter)(nil)

// MembersListCall is the interface wrapping the fluent builder and execution of
// a members.list API call. The exported method names allow external test
// packages to implement this interface with fakes.
type MembersListCall interface {
	IncludeDerivedMembership(v bool) MembersListCall
	MaxResults(n int64) MembersListCall
	PageToken(tok string) MembersListCall
	Do() (*admin.Members, error)
}

// MemberHasMemberCall is the interface wrapping the execution of a
// members.hasMember API call.
type MemberHasMemberCall interface {
	Do() (*admin.MembersHasMember, error)
}

// MembersService is the interface wrapping only the Admin SDK methods called
// by Adapter. External test packages implement this with fakes.
type MembersService interface {
	List(groupEmail string) MembersListCall
	HasMember(groupEmail, userEmail string) MemberHasMemberCall
}

// adminMembersService wraps *admin.MembersService to satisfy MembersService.
type adminMembersService struct {
	svc *admin.MembersService
}

func (a *adminMembersService) List(groupEmail string) MembersListCall {
	return &adminMembersListCall{call: a.svc.List(groupEmail)}
}

func (a *adminMembersService) HasMember(groupEmail, userEmail string) MemberHasMemberCall {
	return &adminMemberHasMemberCall{call: a.svc.HasMember(groupEmail, userEmail)}
}

type adminMembersListCall struct {
	call *admin.MembersListCall
}

func (c *adminMembersListCall) IncludeDerivedMembership(v bool) MembersListCall {
	c.call = c.call.IncludeDerivedMembership(v)
	return c
}

func (c *adminMembersListCall) MaxResults(n int64) MembersListCall {
	c.call = c.call.MaxResults(n)
	return c
}

func (c *adminMembersListCall) PageToken(tok string) MembersListCall {
	c.call = c.call.PageToken(tok)
	return c
}

func (c *adminMembersListCall) Do() (*admin.Members, error) {
	return c.call.Do()
}

type adminMemberHasMemberCall struct {
	call *admin.MembersHasMemberCall
}

func (c *adminMemberHasMemberCall) Do() (*admin.MembersHasMember, error) {
	return c.call.Do()
}

// Adapter implements ports.IdpClient using the Google Cloud Identity Admin API.
type Adapter struct {
	members MembersService
}

// New constructs an Adapter from an already-authenticated *admin.Service. The
// caller is responsible for configuring Application Default Credentials before
// calling New.
func New(service *admin.Service) *Adapter {
	return &Adapter{members: &adminMembersService{svc: service.Members}}
}

// newWithMembers is used by tests to inject a mock MembersService.
func newWithMembers(svc MembersService) *Adapter {
	return &Adapter{members: svc}
}

// ListMembers returns one page of members for groupEmail. It includes derived
// (nested) membership so that users inside sub-groups are enumerated. Pass an
// empty pageToken to start from the beginning.
func (a *Adapter) ListMembers(ctx context.Context, groupEmail, pageToken string) ([]models.Member, string, error) {
	call := a.members.List(groupEmail).
		IncludeDerivedMembership(true).
		MaxResults(models.MembersListPageSize)

	if pageToken != "" {
		call = call.PageToken(pageToken)
	}

	resp, err := call.Do()
	if err != nil {
		transport := mapHTTPError(err)
		return nil, "", fmt.Errorf("%w: %w", models.ErrMemberListFailed, transport)
	}

	members := make([]models.Member, 0, len(resp.Members))
	for _, m := range resp.Members {
		members = append(members, models.Member{
			Email: m.Email,
			Type:  models.MemberType(m.Type),
		})
	}

	return members, resp.NextPageToken, nil
}

// HasMember reports whether userEmail is a direct or indirect member of
// groupEmail.
func (a *Adapter) HasMember(ctx context.Context, groupEmail, userEmail string) (bool, error) {
	resp, err := a.members.HasMember(groupEmail, userEmail).Do()
	if err != nil {
		transport := mapHTTPError(err)
		return false, fmt.Errorf("%w: %w", models.ErrMembershipCheckFailed, transport)
	}

	return resp.IsMember, nil
}

// mapHTTPError converts a *googleapi.Error into a domain transport sentinel
// error. Non-googleapi errors are returned unchanged.
func mapHTTPError(err error) error {
	var apiErr *googleapi.Error
	if !errors.As(err, &apiErr) {
		return err
	}

	switch {
	case apiErr.Code == 429:
		return fmt.Errorf("%w: %w", models.ErrAPIRateLimited, apiErr)
	case apiErr.Code == 404:
		return fmt.Errorf("%w: %w", models.ErrAPINotFound, apiErr)
	case apiErr.Code == 401 || apiErr.Code == 403:
		return fmt.Errorf("%w: %w", models.ErrAPIUnauthorized, apiErr)
	case apiErr.Code >= 500:
		return fmt.Errorf("%w: %w", models.ErrAPIUnavailable, apiErr)
	default:
		return apiErr
	}
}
