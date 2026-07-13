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
	"fmt"
	"strconv"
	"strings"
	"sync"
	"time"

	discoveryenginesdk "cloud.google.com/go/discoveryengine/apiv1"
	"cloud.google.com/go/discoveryengine/apiv1/discoveryenginepb"
	discoveryengineapi "google.golang.org/api/discoveryengine/v1alpha"
	"google.golang.org/api/iterator"
	"google.golang.org/api/option"
	"google.golang.org/grpc/codes"
	"google.golang.org/grpc/status"
	"google.golang.org/protobuf/types/known/fieldmaskpb"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
	"github.com/cloud-gtm/gemini-box-office/internal/ports"
)

var _ ports.GeminiClient = (*Adapter)(nil)

// licenseListPageSize is the number of user licenses requested per page from
// the Discovery Engine API. iterator.NewPager requires a strictly positive
// value; the server may return fewer items on the final page.
const licenseListPageSize = 1000

// userLicenseIterator is the internal interface that the adapter requires from
// a Discovery Engine list iterator. *discoveryenginesdk.UserLicenseIterator
// satisfies this interface naturally. Tests provide a fakeIterator.
type userLicenseIterator interface {
	PageInfo() *iterator.PageInfo
}

// userLicenseClient is the internal interface that wraps only the Discovery
// Engine client methods called by Adapter. Tests provide a fakeUserLicenseClient.
// The BatchUpdateUserLicenses method blocks until the long-running operation
// completes; the real implementation calls op.Wait internally.
type userLicenseClient interface {
	ListUserLicenses(ctx context.Context, req *discoveryenginepb.ListUserLicensesRequest) userLicenseIterator
	BatchUpdateUserLicenses(ctx context.Context, req *discoveryenginepb.BatchUpdateUserLicensesRequest) error
}

// realClient wraps *discoveryenginesdk.UserLicenseClient to satisfy userLicenseClient.
type realClient struct {
	c *discoveryenginesdk.UserLicenseClient
}

func (r *realClient) ListUserLicenses(ctx context.Context, req *discoveryenginepb.ListUserLicensesRequest) userLicenseIterator {
	return r.c.ListUserLicenses(ctx, req)
}

func (r *realClient) BatchUpdateUserLicenses(ctx context.Context, req *discoveryenginepb.BatchUpdateUserLicensesRequest) error {
	op, err := r.c.BatchUpdateUserLicenses(ctx, req)
	if err != nil {
		return err
	}
	_, err = op.Wait(ctx)
	return err
}

// Endpoint hostname constants for location-prefixed Discovery Engine backends.
// The helpers below compose these into the full gRPC and REST endpoint strings.
const (
	usHost = "us-discoveryengine.googleapis.com"
	euHost = "eu-discoveryengine.googleapis.com"
)

// grpcEndpointForLocation returns the gRPC endpoint host:port for the given
// location. For non-global locations (us, eu) it returns the location-prefixed
// endpoint. For global it returns an empty string, meaning the SDK default
// (discoveryengine.googleapis.com:443) is used.
func grpcEndpointForLocation(loc models.Location) string {
	switch loc {
	case models.LocationUS:
		return usHost + ":443"
	case models.LocationEU:
		return euHost + ":443"
	default:
		return ""
	}
}

// restEndpointForLocation returns the REST base URL for the given location.
// For non-global locations (us, eu) it returns the location-prefixed URL.
// For global it returns an empty string, meaning the SDK default is used.
func restEndpointForLocation(loc models.Location) string {
	switch loc {
	case models.LocationUS:
		return "https://" + usHost + "/"
	case models.LocationEU:
		return "https://" + euHost + "/"
	default:
		return ""
	}
}

// Adapter implements ports.GeminiClient using the Discovery Engine API.
// It lazily creates and caches one gRPC client per location.
type Adapter struct {
	factory func(ctx context.Context, loc models.Location) (userLicenseClient, error)
	mu      sync.Mutex
	clients map[models.Location]userLicenseClient
}

// New constructs an Adapter whose gRPC clients are created on demand, one per
// location, using Application Default Credentials. For non-global locations the
// correct location-prefixed endpoint is selected automatically.
func New() *Adapter {
	a := &Adapter{
		clients: make(map[models.Location]userLicenseClient),
	}
	a.factory = func(ctx context.Context, loc models.Location) (userLicenseClient, error) {
		opts := []option.ClientOption{}
		if ep := grpcEndpointForLocation(loc); ep != "" {
			opts = append(opts, option.WithEndpoint(ep))
		}
		c, err := discoveryenginesdk.NewUserLicenseClient(ctx, opts...)
		if err != nil {
			return nil, err
		}
		return &realClient{c: c}, nil
	}
	return a
}

// newWithClient is used by tests to inject a single fake userLicenseClient that
// is returned for every location.
func newWithClient(c userLicenseClient) *Adapter {
	a := &Adapter{
		clients: make(map[models.Location]userLicenseClient),
	}
	a.factory = func(_ context.Context, _ models.Location) (userLicenseClient, error) {
		return c, nil
	}
	return a
}

// newWithFactory is used by tests to inject a custom factory function, enabling
// verification of per-location client creation and caching behaviour.
func newWithFactory(factory func(ctx context.Context, loc models.Location) (userLicenseClient, error)) *Adapter {
	return &Adapter{
		factory: factory,
		clients: make(map[models.Location]userLicenseClient),
	}
}

// clientFor returns the cached client for the given location, creating it via
// the factory if it has not been initialised yet. It uses double-checked locking
// so that the (potentially blocking) factory dial does not hold the mutex.
// It is safe for concurrent use.
func (a *Adapter) clientFor(ctx context.Context, location models.Location) (userLicenseClient, error) {
	a.mu.Lock()
	if c, ok := a.clients[location]; ok {
		a.mu.Unlock()
		return c, nil
	}
	a.mu.Unlock()

	c, err := a.factory(ctx, location)
	if err != nil {
		return nil, fmt.Errorf("creating discovery engine client for location %s: %w", location, err)
	}

	a.mu.Lock()
	if existing, ok := a.clients[location]; ok {
		// Another goroutine populated the cache while we were dialling; discard ours.
		a.mu.Unlock()
		return existing, nil
	}
	a.clients[location] = c
	a.mu.Unlock()
	return c, nil
}

// FetchLicenseConfigIndex retrieves all billing account license configurations
// and returns an index mapping (SKU, ProjectID, Location) to the full
// per-project licenseConfig resource path. The service layer calls this once
// at the start of each run and resolves paths before issuing grant operations.
// This endpoint is always global; no location-specific override is applied.
func (a *Adapter) FetchLicenseConfigIndex(ctx context.Context, billingAccountID string) (models.LicenseConfigIndex, error) {
	svc, err := discoveryengineapi.NewService(ctx)
	if err != nil {
		return nil, fmt.Errorf("creating discoveryengine REST client: %w", err)
	}

	parent := "billingAccounts/" + billingAccountID
	index := make(models.LicenseConfigIndex)

	err = svc.BillingAccounts.BillingAccountLicenseConfigs.List(parent).Context(ctx).Pages(ctx,
		func(resp *discoveryengineapi.GoogleCloudDiscoveryengineV1alphaListBillingAccountLicenseConfigsResponse) error {
			accumulateLicenseConfigs(index, resp.BillingAccountLicenseConfigs)
			return nil
		},
	)
	if err != nil {
		return nil, fmt.Errorf("fetching billing account license configs: %w", err)
	}

	return index, nil
}

// accumulateLicenseConfigs appends active, valid billing account license config
// entries into index. It is extracted from the pagination callback so that the
// index-building logic can be tested without a live REST client.
func accumulateLicenseConfigs(index models.LicenseConfigIndex, configs []*discoveryengineapi.GoogleCloudDiscoveryengineV1alphaBillingAccountLicenseConfig) {
	for _, c := range configs {
		if c.State != "ACTIVE" {
			continue
		}
		if c.SubscriptionTier == "" || c.SubscriptionTier == "SUBSCRIPTION_TIER_UNSPECIFIED" {
			continue
		}
		for licenseConfigPath, allocatedStr := range c.LicenseConfigDistributions {
			// Path format: projects/{project}/locations/{location}/licenseConfigs/{id}
			parts := strings.Split(licenseConfigPath, "/")
			if len(parts) != 6 {
				continue
			}
			allocated, err := strconv.ParseInt(allocatedStr, 10, 64)
			if err != nil {
				continue
			}
			key := models.LicenseConfigKey{
				SKU:           models.SKU(c.SubscriptionTier),
				ProjectNumber: parts[1],
				Location:      models.Location(parts[3]),
			}
			index[key] = append(index[key], models.LicenseConfigEntry{
				Path:           licenseConfigPath,
				AllocatedCount: allocated,
			})
		}
	}
}

// ListUserLicenses returns one page of user licenses for the given projectID at
// the given location. Pass an empty pageToken to start from the beginning. It
// uses iterator.NewPager to correctly honour the caller-supplied pageToken,
// fixing the pagination bug that existed when InternalFetch was called directly.
func (a *Adapter) ListUserLicenses(ctx context.Context, projectID string, location models.Location, pageToken string) ([]models.UserLicense, string, error) {
	client, err := a.clientFor(ctx, location)
	if err != nil {
		return nil, "", fmt.Errorf("%w: %w", models.ErrLicenseListFailed, err)
	}

	parent := fmt.Sprintf("projects/%s/locations/%s/userStores/default_user_store", projectID, location)

	req := &discoveryenginepb.ListUserLicensesRequest{
		Parent:    parent,
		PageToken: pageToken,
	}

	it := client.ListUserLicenses(ctx, req)

	pager := iterator.NewPager(it, licenseListPageSize, pageToken)

	var protos []*discoveryenginepb.UserLicense
	nextPageToken, err := pager.NextPage(&protos)
	if err != nil {
		if errors.Is(err, iterator.Done) {
			return nil, "", nil
		}
		return nil, "", fmt.Errorf("%w: %w", models.ErrLicenseListFailed, mapGRPCError(err))
	}

	licenses := make([]models.UserLicense, 0, len(protos))
	for _, p := range protos {
		license, err := protoToUserLicense(p)
		if err != nil {
			return nil, "", fmt.Errorf("%w: %w", models.ErrLicenseListFailed, err)
		}
		licenses = append(licenses, license)
	}

	return licenses, nextPageToken, nil
}

// BatchUpdateUserLicenses applies up to models.MaxBatchSize grant or revoke
// operations in a single API call. Batches must be homogeneous (all grants or
// all revokes). For grants, LicenseConfigPath must be set on every update; for
// revokes it is not sent to the API — only license_assignment_state is masked —
// to avoid the "subscription reaches the limit" error that occurs when the API
// processes a license_config field alongside a NO_LICENSE state.
func (a *Adapter) BatchUpdateUserLicenses(ctx context.Context, projectID string, location models.Location, updates []models.LicenseUpdate) error {
	if len(updates) > models.MaxBatchSize {
		return fmt.Errorf("%w: batch size %d exceeds maximum %d", models.ErrBatchUpdateFailed, len(updates), models.MaxBatchSize)
	}

	client, err := a.clientFor(ctx, location)
	if err != nil {
		return fmt.Errorf("%w: %w", models.ErrBatchUpdateFailed, err)
	}

	parent := fmt.Sprintf("projects/%s/locations/%s/userStores/default_user_store", projectID, location)

	isRevoke := len(updates) > 0 && updates[0].Action == models.LicenseActionRevoke

	protoLicenses := make([]*discoveryenginepb.UserLicense, 0, len(updates))
	for _, u := range updates {
		protoLicenses = append(protoLicenses, licenseUpdateToProto(u))
	}

	maskPaths := []string{"license_assignment_state", "license_config"}
	if isRevoke {
		maskPaths = []string{"license_assignment_state"}
	}

	req := &discoveryenginepb.BatchUpdateUserLicensesRequest{
		Parent: parent,
		Source: &discoveryenginepb.BatchUpdateUserLicensesRequest_InlineSource_{
			InlineSource: &discoveryenginepb.BatchUpdateUserLicensesRequest_InlineSource{
				UserLicenses: protoLicenses,
				UpdateMask: &fieldmaskpb.FieldMask{
					Paths: maskPaths,
				},
			},
		},
	}

	if err := client.BatchUpdateUserLicenses(ctx, req); err != nil {
		return fmt.Errorf("%w: %w", models.ErrBatchUpdateFailed, mapGRPCError(err))
	}

	return nil
}

// protoToUserLicense converts a discoveryenginepb.UserLicense to the domain model.
// The LicenseConfig field from the API is a resource path
// (projects/{p}/locations/{l}/licenseConfigs/{id}), stored as-is in LicenseConfigPath.
func protoToUserLicense(p *discoveryenginepb.UserLicense) (models.UserLicense, error) {
	state, err := assignmentStateToLicenseState(p.LicenseAssignmentState)
	if err != nil {
		return models.UserLicense{}, err
	}

	var lastLogin time.Time
	if p.LastLoginTime != nil {
		lastLogin = p.LastLoginTime.AsTime()
	}

	var assignmentTime time.Time
	if p.CreateTime != nil {
		assignmentTime = p.CreateTime.AsTime()
	}

	return models.UserLicense{
		UserEmail:         p.UserPrincipal,
		LicenseConfigPath: p.LicenseConfig,
		State:             state,
		LastLoginTime:     lastLogin,
		AssignmentTime:    assignmentTime,
	}, nil
}

// assignmentStateToLicenseState converts a proto LicenseAssignmentState to
// the domain LicenseState.
func assignmentStateToLicenseState(s discoveryenginepb.UserLicense_LicenseAssignmentState) (models.LicenseState, error) {
	switch s {
	case discoveryenginepb.UserLicense_ASSIGNED:
		return models.LicenseStateAssigned, nil
	case discoveryenginepb.UserLicense_NO_LICENSE,
		discoveryenginepb.UserLicense_UNASSIGNED,
		discoveryenginepb.UserLicense_NO_LICENSE_ATTEMPTED_LOGIN,
		discoveryenginepb.UserLicense_LICENSE_ASSIGNMENT_STATE_UNSPECIFIED:
		return models.LicenseStateRevoked, nil
	default:
		return "", fmt.Errorf("%w: %d", models.ErrUnknownLicenseState, s)
	}
}

// licenseUpdateToProto converts a domain LicenseUpdate to a proto UserLicense.
// For grants, LicenseConfig is set to the resolved resource path. For revokes,
// LicenseConfig is left empty — the API must not receive it alongside NO_LICENSE
// or it triggers a subscription-limit error.
func licenseUpdateToProto(u models.LicenseUpdate) *discoveryenginepb.UserLicense {
	if u.Action == models.LicenseActionGrant {
		return &discoveryenginepb.UserLicense{
			UserPrincipal:          u.UserEmail,
			LicenseConfig:          u.LicenseConfigPath,
			LicenseAssignmentState: discoveryenginepb.UserLicense_ASSIGNED,
		}
	}
	return &discoveryenginepb.UserLicense{
		UserPrincipal:          u.UserEmail,
		LicenseAssignmentState: discoveryenginepb.UserLicense_NO_LICENSE,
	}
}

// FetchLicenseUsageStats returns a map of licenseConfig resource path to the
// number of licenses currently assigned (usedLicenseCount) for all licenseConfigs
// under the given project's default user store. The projectID must be the numeric
// project number that appears in licenseConfig resource paths.
// For non-global locations the location-prefixed REST endpoint is used so that
// the request reaches the correct regional backend.
func (a *Adapter) FetchLicenseUsageStats(ctx context.Context, projectID string, location models.Location) (map[string]int64, error) {
	opts := []option.ClientOption{}
	if ep := restEndpointForLocation(location); ep != "" {
		opts = append(opts, option.WithEndpoint(ep))
	}

	svc, err := discoveryengineapi.NewService(ctx, opts...)
	if err != nil {
		return nil, fmt.Errorf("creating discoveryengine REST client: %w", err)
	}

	parent := fmt.Sprintf("projects/%s/locations/%s/userStores/default_user_store", projectID, location)

	resp, err := svc.Projects.Locations.UserStores.LicenseConfigsUsageStats.List(parent).Context(ctx).Do()
	if err != nil {
		return nil, fmt.Errorf("fetching license usage stats: %w", err)
	}

	stats := make(map[string]int64, len(resp.LicenseConfigUsageStats))
	for _, s := range resp.LicenseConfigUsageStats {
		stats[s.LicenseConfig] = s.UsedLicenseCount
	}
	return stats, nil
}

// mapGRPCError converts a gRPC status error into a domain transport sentinel error.
// License pool exhaustion (codes.InvalidArgument with a message containing
// "subscription" and "limit") is mapped to ErrLicensesExhausted so callers can
// distinguish it from a transient rate limit (codes.ResourceExhausted).
// The Discovery Engine API returns the message:
//
//	"Subscription reaches the limit of N licenses for license config {path}"
func mapGRPCError(err error) error {
	st, ok := status.FromError(err)
	if !ok {
		return err
	}

	switch st.Code() {
	case codes.InvalidArgument:
		msg := strings.ToLower(st.Message())
		if strings.Contains(msg, "subscription") && strings.Contains(msg, "limit") {
			return fmt.Errorf("%w: %w", models.ErrLicensesExhausted, err)
		}
		return err
	case codes.ResourceExhausted:
		return fmt.Errorf("%w: %w", models.ErrAPIRateLimited, err)
	case codes.NotFound:
		return fmt.Errorf("%w: %w", models.ErrAPINotFound, err)
	case codes.Unauthenticated, codes.PermissionDenied:
		return fmt.Errorf("%w: %w", models.ErrAPIUnauthorized, err)
	case codes.Unavailable, codes.Internal:
		return fmt.Errorf("%w: %w", models.ErrAPIUnavailable, err)
	default:
		return err
	}
}
