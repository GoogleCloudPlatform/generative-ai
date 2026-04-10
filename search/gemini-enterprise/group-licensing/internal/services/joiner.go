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
	"fmt"
	"log/slog"
	"time"

	"github.com/cloud-gtm/gemini-box-office/internal/config"
	"github.com/cloud-gtm/gemini-box-office/internal/middleware"
	"github.com/cloud-gtm/gemini-box-office/internal/models"
	"github.com/cloud-gtm/gemini-box-office/internal/models/dto"
	"github.com/cloud-gtm/gemini-box-office/internal/ports"
)

// JoinerService implements the "joiner" workflow: for every configured project
// it enumerates group memberships, resolves the highest-precedence SKU each
// user is entitled to, and grants the missing licenses in batches.
type JoinerService struct {
	idp    ports.IdpClient
	gemini ports.GeminiClient
	rm     ports.ResourceManagerClient
}

// NewJoinerService constructs a JoinerService wired to the supplied port
// implementations. Logging is provided per-request via middleware.LoggerFromContext.
func NewJoinerService(idp ports.IdpClient, gemini ports.GeminiClient, rm ports.ResourceManagerClient) *JoinerService {
	return &JoinerService{
		idp:    idp,
		gemini: gemini,
		rm:     rm,
	}
}

// Run executes the joiner workflow against the provided configuration.
//
// It first fetches the billing account license config index to resolve
// licenseConfig resource paths for grant operations. For each project it then
// builds a map of userEmail → highest-entitled (SKU, location) by iterating
// every entry in the project config and paging through all group members. It
// issues BatchUpdateUserLicenses calls (chunked to models.MaxBatchSize) for
// the resolved grants. When req.DryRun is true the enumeration runs in full
// but no write API calls are made.
func (s *JoinerService) Run(ctx context.Context, cfg *config.EntitlementConfig, req dto.SyncAddRequest) (dto.SyncAddResponse, error) {
	if err := ctx.Err(); err != nil {
		return dto.SyncAddResponse{}, fmt.Errorf("context cancelled: %w", err)
	}

	logger := middleware.LoggerFromContext(ctx)
	dryRun := false
	if req.DryRun != nil {
		dryRun = *req.DryRun
	}

	licenseIndex, err := s.gemini.FetchLicenseConfigIndex(ctx, cfg.BillingAccountID)
	if err != nil {
		return dto.SyncAddResponse{}, fmt.Errorf("fetching license config index: %w", err)
	}

	// Resolve all configured project IDs to their numeric project numbers once.
	// The Discovery Engine API uses project numbers in licenseConfig resource
	// paths, while the entitlement config uses human-readable project IDs.
	projectNumbers := make(map[string]string, len(cfg.Projects))
	for projectID := range cfg.Projects {
		number, err := s.rm.ResolveProjectNumber(ctx, projectID)
		if err != nil {
			return dto.SyncAddResponse{}, fmt.Errorf("resolving project number for %q: %w", projectID, err)
		}
		projectNumbers[projectID] = number
	}

	start := time.Now()
	logger.InfoContext(ctx, "joiner workflow starting",
		slog.Int("project_count", len(cfg.Projects)),
		slog.Bool("dry_run", dryRun),
	)

	var totalGranted, totalSoftFailed, totalGroups int

	for projectID, projectCfg := range cfg.Projects {
		granted, softFailed, groups, err := s.processProject(ctx, projectID, projectNumbers[projectID], projectCfg, licenseIndex, dryRun)
		if err != nil {
			logger.ErrorContext(ctx, "joiner workflow failed",
				slog.String("project_id", projectID),
				slog.Any("error", err),
				slog.Int("licenses_granted_before_failure", totalGranted),
				slog.Int("groups_processed_before_failure", totalGroups),
			)
			return dto.SyncAddResponse{}, err
		}
		totalGranted += granted
		totalSoftFailed += softFailed
		totalGroups += groups
	}

	elapsed := time.Since(start).Milliseconds()
	logger.InfoContext(ctx, "joiner workflow complete",
		slog.Int64("duration_ms", elapsed),
		slog.Int("licenses_granted", totalGranted),
		slog.Int("licenses_soft_failed", totalSoftFailed),
		slog.Int("groups_processed", totalGroups),
		slog.Bool("dry_run", dryRun),
	)

	return dto.SyncAddResponse{
		LicensesGranted:    totalGranted,
		LicensesSoftFailed: totalSoftFailed,
		GroupsProcessed:    totalGroups,
		DryRun:             dryRun,
	}, nil
}

// userEntitlement pairs the highest-precedence SKU a user is entitled to with
// the location of the group entry that granted it.
type userEntitlement struct {
	SKU      models.SKU
	Location models.Location
}

// processProject enumerates all configured groups for a single GCP project,
// resolves the highest-precedence (SKU, location) per user, looks up the
// licenseConfig resource path from index, and issues the grant batches.
// Updates are grouped by licenseConfigPath so each batch is homogeneous,
// which allows per-SKU exhaustion handling without ambiguity.
// It returns the number of licenses granted, the number of users soft-failed
// due to license pool exhaustion, and the number of groups processed.
func (s *JoinerService) processProject(ctx context.Context, projectID, projectNumber string, projectCfg config.ProjectConfig, index models.LicenseConfigIndex, dryRun bool) (licensesGranted, licensesSoftFailed, groupsProcessed int, err error) {
	// userBestEntitlement maps each user email to the highest-ranked entitlement
	// (SKU + location) across all groups in this project.
	userBestEntitlement := make(map[string]userEntitlement)

	for _, cfgEntry := range projectCfg {
		for _, groupEmail := range cfgEntry.Groups {
			if err := s.collectGroupMembers(ctx, groupEmail, cfgEntry.SubscriptionTier, cfgEntry.Location, userBestEntitlement); err != nil {
				return 0, 0, 0, fmt.Errorf("project %q group %q: %w", projectID, groupEmail, err)
			}
			groupsProcessed++
		}
	}

	// Group updates by licenseConfigPath so each batch is homogeneous.
	// This allows exhaustion handling to target the correct SKU pool.
	pendingByConfig := make(map[string][]models.LicenseUpdate)
	entryByConfigPath := make(map[string]models.LicenseConfigEntry)

	for email, ent := range userBestEntitlement {
		key := models.LicenseConfigKey{SKU: ent.SKU, ProjectNumber: projectNumber, Location: ent.Location}
		idxEntry, ok := index[key]
		if !ok {
			return 0, 0, 0, fmt.Errorf("project %q: no licenseConfig found for SKU %q location %q", projectID, ent.SKU, ent.Location)
		}
		pendingByConfig[idxEntry.Path] = append(pendingByConfig[idxEntry.Path], models.LicenseUpdate{
			UserEmail:         email,
			SKU:               ent.SKU,
			Location:          ent.Location,
			LicenseConfigPath: idxEntry.Path,
			Action:            models.LicenseActionGrant,
		})
		entryByConfigPath[idxEntry.Path] = idxEntry
	}

	for configPath, updates := range pendingByConfig {
		idxEntry := entryByConfigPath[configPath]
		for _, chunk := range chunkLicenseUpdates(updates, models.MaxBatchSize) {
			if dryRun {
				licensesGranted += len(chunk)
				continue
			}
			granted, softFailed, err := s.grantBatch(ctx, projectID, projectNumber, idxEntry, chunk)
			if err != nil {
				return 0, 0, 0, fmt.Errorf("project %q batch grant: %w", projectID, err)
			}
			licensesGranted += granted
			licensesSoftFailed += softFailed
		}
	}

	return licensesGranted, licensesSoftFailed, groupsProcessed, nil
}

// grantBatch issues a BatchUpdateUserLicenses call for a homogeneous batch
// (all updates share the same licenseConfigPath). On license pool exhaustion
// it fetches the current usage stats, retries with however many seats remain,
// and soft-fails the rest. Non-exhaustion errors are returned as hard failures.
// It returns the number of licenses granted and the number soft-failed.
func (s *JoinerService) grantBatch(ctx context.Context, projectID, projectNumber string, entry models.LicenseConfigEntry, batch []models.LicenseUpdate) (granted, softFailed int, err error) {
	logger := middleware.LoggerFromContext(ctx)

	if batchErr := s.gemini.BatchUpdateUserLicenses(ctx, projectID, batch); batchErr == nil {
		return len(batch), 0, nil
	} else if !errors.Is(batchErr, models.ErrLicensesExhausted) {
		return 0, 0, batchErr
	}

	// License pool exhausted. Look up how many seats are still available.
	usageStats, statsErr := s.gemini.FetchLicenseUsageStats(ctx, projectNumber)
	if statsErr != nil {
		return 0, 0, fmt.Errorf("fetching license usage stats after exhaustion: %w", statsErr)
	}

	used := usageStats[entry.Path]
	available := entry.AllocatedCount - used
	if available < 0 {
		available = 0
	}

	logger.WarnContext(ctx, "license pool exhausted, soft-failing remaining users",
		slog.String("project_id", projectID),
		slog.String("license_config_path", entry.Path),
		slog.Int64("available", available),
		slog.Int("soft_failed", len(batch)-int(available)),
	)

	if available == 0 {
		return 0, len(batch), nil
	}

	// Retry with only the available seats. Any error here is a hard failure.
	trimmed := batch[:available]
	if retryErr := s.gemini.BatchUpdateUserLicenses(ctx, projectID, trimmed); retryErr != nil {
		return 0, 0, retryErr
	}
	return int(available), len(batch) - int(available), nil
}

// collectGroupMembers pages through all members of groupEmail and updates
// userBestEntitlement with the supplied (sku, location) when sku is higher
// than any previously recorded SKU for that user.
func (s *JoinerService) collectGroupMembers(ctx context.Context, groupEmail string, sku models.SKU, location models.Location, userBestEntitlement map[string]userEntitlement) error {
	var pageToken string
	var pageCount int

	for {
		if err := ctx.Err(); err != nil {
			return fmt.Errorf("context cancelled: %w", err)
		}
		if pageCount >= models.MaxPagesPerGroup {
			middleware.LoggerFromContext(ctx).WarnContext(ctx,
				"group member enumeration exceeded page limit, truncating",
				slog.String("group_email", groupEmail),
				slog.Int("max_pages", models.MaxPagesPerGroup),
			)
			break
		}
		pageCount++
		members, next, err := s.idp.ListMembers(ctx, groupEmail, pageToken)
		if err != nil {
			return fmt.Errorf("group %q: %w", groupEmail, err)
		}

		for _, m := range members {
			if m.Type != models.MemberTypeUser {
				continue
			}

			existing, seen := userBestEntitlement[m.Email]
			if !seen || sku.HasHigherPrecedenceThan(existing.SKU) {
				userBestEntitlement[m.Email] = userEntitlement{SKU: sku, Location: location}
			}
		}

		if next == "" {
			break
		}
		pageToken = next
	}

	return nil
}
