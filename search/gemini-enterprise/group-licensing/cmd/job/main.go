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

package main

import (
	"cmp"
	"context"
	"log/slog"
	"maps"
	"os"
	"slices"

	discoveryenginesdk "cloud.google.com/go/discoveryengine/apiv1"
	admin "google.golang.org/api/admin/directory/v1"
	cloudresourcemanager "google.golang.org/api/cloudresourcemanager/v3"
	"google.golang.org/api/option"

	"github.com/cloud-gtm/gemini-box-office/internal/adapters/cloudidentity"
	"github.com/cloud-gtm/gemini-box-office/internal/adapters/discoveryengine"
	"github.com/cloud-gtm/gemini-box-office/internal/adapters/resourcemanager"
	"github.com/cloud-gtm/gemini-box-office/internal/config"
	"github.com/cloud-gtm/gemini-box-office/internal/models"
	"github.com/cloud-gtm/gemini-box-office/internal/models/dto"
	"github.com/cloud-gtm/gemini-box-office/internal/services"
)

func main() {
	// Step 1: plain JSON logger for startup errors, before settings are loaded.
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)))

	// Step 2: load entitlement config.
	cfg, err := config.Load(models.ConfigFilePath)
	if err != nil {
		slog.Error("failed to load entitlement config", slog.Any("error", err))
		os.Exit(1)
	}

	// Step 3: load job settings from Cloud Run Job environment variables.
	settings, err := config.LoadJobSettings()
	if err != nil {
		slog.Error("failed to load job settings", slog.Any("error", err))
		os.Exit(1)
	}

	// Step 4: re-set the default logger with workflow and task_index attributes
	// so that every subsequent log line — including those emitted by the service
	// layer via middleware.LoggerFromContext — carries these fields automatically.
	slog.SetDefault(slog.New(slog.NewJSONHandler(os.Stdout, nil)).With(
		slog.String("workflow", string(settings.JobType)),
		slog.Int("task_index", settings.TaskIndex),
	))

	// Step 5: partition cfg.Projects to only the entries assigned to this task.
	// Iterate project keys in sorted order for determinism across all tasks.
	sortedKeys := slices.SortedFunc(maps.Keys(cfg.Projects), cmp.Compare[string])

	partitioned := make(map[string]config.ProjectConfig, len(sortedKeys))
	for i, key := range sortedKeys {
		if i%settings.TaskCount == settings.TaskIndex {
			partitioned[key] = cfg.Projects[key]
		}
	}

	if len(partitioned) == 0 {
		slog.Info("no projects assigned to this task; nothing to do",
			slog.Int("task_index", settings.TaskIndex),
			slog.Int("task_count", settings.TaskCount),
			slog.Int("total_projects", len(cfg.Projects)),
		)
		os.Exit(0)
	}

	cfg.Projects = partitioned

	ctx := context.Background()

	// Step 6: wire adapters — identical to cmd/server/main.go.
	adminSvc, err := admin.NewService(ctx, option.WithScopes(admin.AdminDirectoryGroupMemberReadonlyScope))
	if err != nil {
		slog.Error("failed to create admin SDK client", slog.Any("error", err))
		os.Exit(1)
	}

	deClient, err := discoveryenginesdk.NewUserLicenseClient(ctx)
	if err != nil {
		slog.Error("failed to create discovery engine client", slog.Any("error", err))
		os.Exit(1)
	}

	crmSvc, err := cloudresourcemanager.NewService(ctx, option.WithScopes(cloudresourcemanager.CloudPlatformReadOnlyScope))
	if err != nil {
		slog.Error("failed to create resource manager client", slog.Any("error", err))
		os.Exit(1)
	}

	idpAdapter := cloudidentity.New(adminSvc)
	geminiAdapter := discoveryengine.New(deClient)
	rmAdapter := resourcemanager.New(crmSvc)

	// Step 7: run the workflow determined by JobType.
	switch settings.JobType {
	case models.WorkflowJoiner:
		req := dto.SyncAddRequest{DryRun: &settings.DryRun}
		if _, err := services.NewJoinerService(idpAdapter, geminiAdapter, rmAdapter).Run(ctx, cfg, req); err != nil {
			slog.Error("joiner workflow failed", slog.Any("error", err))
			os.Exit(1)
		}

	case models.WorkflowGarbageCollection:
		req := dto.SyncRemoveRequest{DryRun: &settings.DryRun}
		if _, err := services.NewGCService(idpAdapter, geminiAdapter).Run(ctx, cfg, req); err != nil {
			slog.Error("garbage collection workflow failed", slog.Any("error", err))
			os.Exit(1)
		}
	}

	// Step 8: clean exit.
	os.Exit(0)
}
