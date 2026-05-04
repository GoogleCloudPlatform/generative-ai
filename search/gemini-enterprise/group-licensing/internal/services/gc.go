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
	"fmt"
	"log/slog"
	"time"

	"github.com/cloud-gtm/gemini-box-office/internal/config"
	"github.com/cloud-gtm/gemini-box-office/internal/middleware"
	"github.com/cloud-gtm/gemini-box-office/internal/models"
	"github.com/cloud-gtm/gemini-box-office/internal/models/dto"
	"github.com/cloud-gtm/gemini-box-office/internal/ports"
)

// GCService implements the "garbage_collection" workflow: for every configured
// project it pages through all licensed users, determines which are stale or
// no longer entitled to any configured group, and revokes their licenses in
// batches.
type GCService struct {
	idp    ports.IdpClient
	gemini ports.GeminiClient
}

// NewGCService constructs a GCService wired to the supplied port
// implementations. Logging is provided per-request via middleware.LoggerFromContext.
func NewGCService(idp ports.IdpClient, gemini ports.GeminiClient) *GCService {
	return &GCService{
		idp:    idp,
		gemini: gemini,
	}
}

// Run executes the garbage-collection workflow against the provided configuration.
//
// It evaluates each licensed user for staleness (last login older than
// StalenessThresholdDays) and entitlement (membership in at least one configured
// group), revoking licences for users who fail either check. When
// StalenessThresholdDays is 0 the staleness check is skipped entirely and only
// the entitlement check runs. When req.DryRun is true the evaluation runs in
// full but no write API calls are made.
func (s *GCService) Run(ctx context.Context, cfg *config.EntitlementConfig, req dto.SyncRemoveRequest) (dto.SyncRemoveResponse, error) {
	logger := middleware.LoggerFromContext(ctx)
	dryRun := false
	if req.DryRun != nil {
		dryRun = *req.DryRun
	}

	start := time.Now()
	logger.InfoContext(ctx, "garbage collection workflow starting",
		slog.Int("project_count", len(cfg.Projects)),
		slog.Int("staleness_threshold_days", cfg.Settings.StalenessThresholdDays),
		slog.Bool("dry_run", dryRun),
	)

	var totalRevoked, totalEvaluated int

	for projectID, projectCfg := range cfg.Projects {
		revoked, evaluated, err := s.processProject(ctx, projectID, projectCfg, cfg.Settings.StalenessThresholdDays, dryRun)
		if err != nil {
			logger.ErrorContext(ctx, "garbage collection workflow failed",
				slog.String("project_id", projectID),
				slog.Any("error", err),
				slog.Int("licenses_revoked_before_failure", totalRevoked),
				slog.Int("users_evaluated_before_failure", totalEvaluated),
			)
			return dto.SyncRemoveResponse{}, err
		}
		totalRevoked += revoked
		totalEvaluated += evaluated
	}

	elapsed := time.Since(start).Milliseconds()
	logger.InfoContext(ctx, "garbage collection workflow complete",
		slog.Int64("duration_ms", elapsed),
		slog.Int("licenses_revoked", totalRevoked),
		slog.Int("users_evaluated", totalEvaluated),
		slog.Bool("dry_run", dryRun),
	)

	return dto.SyncRemoveResponse{
		LicensesRevoked: totalRevoked,
		UsersEvaluated:  totalEvaluated,
		DryRun:          dryRun,
	}, nil
}

// processProject pages through all licensed users for a single GCP project and
// revokes licences from users who are stale or no longer entitled. It returns
// the number of licenses revoked and users evaluated.
//
// Revocation candidates are chunked and flushed per page so that memory usage
// is bounded to one page of candidates at any point rather than accumulating
// the full result set before issuing any writes.
func (s *GCService) processProject(ctx context.Context, projectID string, projectCfg config.ProjectConfig, thresholdDays int, dryRun bool) (licensesRevoked, usersEvaluated int, err error) {
	var pageToken string
	var pageCount int

	for {
		if err := ctx.Err(); err != nil {
			return 0, 0, fmt.Errorf("context cancelled: %w", err)
		}
		if pageCount >= models.MaxPagesPerGroup {
			middleware.LoggerFromContext(ctx).WarnContext(ctx,
				"license listing exceeded page limit, truncating",
				slog.String("project_id", projectID),
				slog.Int("max_pages", models.MaxPagesPerGroup),
			)
			break
		}
		pageCount++
		licenses, next, err := s.gemini.ListUserLicenses(ctx, projectID, pageToken)
		if err != nil {
			return 0, 0, fmt.Errorf("project %q listing licenses: %w", projectID, err)
		}

		var pageRevocations []models.LicenseUpdate

		for _, license := range licenses {
			if err := ctx.Err(); err != nil {
				return 0, 0, fmt.Errorf("context cancelled: %w", err)
			}
			if license.State == models.LicenseStateRevoked {
				continue
			}
			usersEvaluated++

			shouldRevoke, err := s.shouldRevoke(ctx, license, projectCfg, thresholdDays)
			if err != nil {
				return 0, 0, fmt.Errorf("project %q evaluating license: %w", projectID, err)
			}

			if shouldRevoke {
				pageRevocations = append(pageRevocations, models.LicenseUpdate{
					UserEmail:         license.UserEmail,
					LicenseConfigPath: license.LicenseConfigPath,
					Action:            models.LicenseActionRevoke,
				})
			}
		}

		if len(pageRevocations) > 0 {
			if !dryRun {
				for _, chunk := range chunkLicenseUpdates(pageRevocations, models.MaxBatchSize) {
					if err := s.gemini.BatchUpdateUserLicenses(ctx, projectID, chunk); err != nil {
						return 0, 0, fmt.Errorf("project %q batch revoke: %w", projectID, err)
					}
				}
			}
			licensesRevoked += len(pageRevocations)
		}

		if next == "" {
			break
		}
		pageToken = next
	}

	return licensesRevoked, usersEvaluated, nil
}

// shouldRevoke returns true when the user holding license should have it
// revoked. A user is revocable when they are stale OR when they are not a
// member of any configured group. When thresholdDays is 0 the staleness check
// is disabled and only the entitlement check runs. When thresholdDays > 0 the
// staleness check short-circuits the more expensive membership check.
//
// Staleness reference time:
//   - When LastLoginTime is set, it is used as the reference.
//   - When LastLoginTime is zero (the user has never logged in), AssignmentTime
//     is used instead, so that a recently provisioned account is not revoked
//     before the user has had a chance to sign in.
//   - When both are zero (pathological; should not occur in practice), the user
//     is treated as immediately stale and the license is revoked.
func (s *GCService) shouldRevoke(ctx context.Context, license models.UserLicense, projectCfg config.ProjectConfig, thresholdDays int) (bool, error) {
	// Staleness check: only performed when thresholdDays > 0.
	if thresholdDays > 0 {
		ref := license.LastLoginTime
		if ref.IsZero() {
			// Never logged in: fall back to the assignment date so a recently
			// provisioned user is not immediately revoked.
			ref = license.AssignmentTime
		}
		if ref.IsZero() || ref.Before(time.Now().AddDate(0, 0, -thresholdDays)) {
			return true, nil
		}
	}

	// Entitlement check: the user must be a member of at least one group
	// across all entries in the project config.
	for _, entry := range projectCfg {
		for _, groupEmail := range entry.Groups {
			isMember, err := s.idp.HasMember(ctx, groupEmail, license.UserEmail)
			if err != nil {
				return false, fmt.Errorf("checking membership: %w", err)
			}
			if isMember {
				// Still entitled; no revocation needed.
				return false, nil
			}
		}
	}

	// Not a member of any configured group.
	return true, nil
}

// chunkLicenseUpdates splits updates into slices of at most size elements.
func chunkLicenseUpdates(updates []models.LicenseUpdate, size int) [][]models.LicenseUpdate {
	if size <= 0 {
		size = models.MaxBatchSize
	}
	var chunks [][]models.LicenseUpdate
	for i := 0; i < len(updates); i += size {
		end := i + size
		if end > len(updates) {
			end = len(updates)
		}
		chunks = append(chunks, updates[i:end])
	}
	return chunks
}
