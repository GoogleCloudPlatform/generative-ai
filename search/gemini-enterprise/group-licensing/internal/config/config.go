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

package config

import (
	"encoding/json"
	"errors"
	"fmt"
	"os"
	"regexp"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
)

// validProjectID matches GCP project IDs: 6–30 chars, starts with a lowercase
// letter, contains only [a-z0-9-], and ends with a letter or digit.
var validProjectID = regexp.MustCompile(`^[a-z][a-z0-9\-]{4,28}[a-z0-9]$`)

// validEmail matches group email addresses that contain exactly one '@' with
// non-empty local and domain parts and at least one dot in the domain.
var validEmail = regexp.MustCompile(`^[^@\s]+@[^@\s]+\.[^@\s]+$`)

// ProjectEntry maps a SKU and location to the list of Google Group email
// addresses whose members are entitled to that SKU at that location within
// a given GCP project.
type ProjectEntry struct {
	SubscriptionTier models.SKU      `json:"subscription_tier"`
	Location         models.Location `json:"location"`
	Groups           []string        `json:"groups"`
}

// ProjectConfig is the ordered list of SKU+location+group entries for a
// single GCP project. Each entry describes one tier of entitlement.
type ProjectConfig []ProjectEntry

// Settings holds operator-controlled knobs for the batch job behaviour.
type Settings struct {
	StalenessThresholdDays int `json:"staleness_threshold_days"`
}

// EntitlementConfig is the top-level structure parsed from the mounted JSON
// file. Projects keys are GCP project IDs.
type EntitlementConfig struct {
	BillingAccountID string                   `json:"billing_account_id"`
	Projects         map[string]ProjectConfig `json:"projects"`
	Settings         Settings                 `json:"settings"`
}

// Load reads, parses, and validates the entitlement config file at path. It
// returns a sentinel-wrapped error on every failure so callers can use errors.Is.
//
// A StalenessThresholdDays of 0 means the staleness check is disabled entirely;
// only the entitlement check will run during garbage collection.
func Load(path string) (*EntitlementConfig, error) {
	data, err := os.ReadFile(path)
	if err != nil {
		if errors.Is(err, os.ErrNotExist) {
			return nil, fmt.Errorf("reading config: %w", models.ErrConfigNotFound)
		}
		return nil, fmt.Errorf("reading config: %w", models.ErrConfigUnreadable)
	}

	var cfg EntitlementConfig
	if err := json.Unmarshal(data, &cfg); err != nil {
		return nil, fmt.Errorf("parsing config: %w", models.ErrConfigInvalid)
	}

	if err := validate(&cfg); err != nil {
		return nil, err
	}

	return &cfg, nil
}

// validate enforces all structural and semantic constraints on the config.
// It is read-only and does not mutate cfg.
func validate(cfg *EntitlementConfig) error {
	if cfg.BillingAccountID == "" {
		return fmt.Errorf("config validation: billing_account_id is required: %w", models.ErrConfigInvalid)
	}

	if len(cfg.Projects) == 0 {
		return fmt.Errorf("config validation: %w", models.ErrConfigNoProjects)
	}

	for projectID, projectCfg := range cfg.Projects {
		if !validProjectID.MatchString(projectID) {
			return fmt.Errorf("project %q is not a valid GCP project ID: %w", projectID, models.ErrConfigInvalid)
		}

		if len(projectCfg) == 0 {
			return fmt.Errorf("project %q has no entries: %w", projectID, models.ErrConfigNoGroups)
		}

		for i, entry := range projectCfg {
			if !entry.SubscriptionTier.IsValid() {
				return fmt.Errorf("project %q entry %d contains unrecognized SKU %q: %w", projectID, i, entry.SubscriptionTier, models.ErrInvalidSKU)
			}

			if !entry.Location.IsValid() {
				return fmt.Errorf("project %q entry %d contains invalid location %q: %w", projectID, i, entry.Location, models.ErrInvalidLocation)
			}

			if len(entry.Groups) == 0 {
				return fmt.Errorf("project %q entry %d has no group emails: %w", projectID, i, models.ErrConfigNoGroups)
			}

			for _, email := range entry.Groups {
				if !validEmail.MatchString(email) {
					return fmt.Errorf("project %q entry %d contains invalid group email %q: %w", projectID, i, email, models.ErrConfigInvalid)
				}
			}
		}
	}

	if cfg.Settings.StalenessThresholdDays < 0 {
		return fmt.Errorf("settings.staleness_threshold_days must be >= 0: %w", models.ErrConfigInvalid)
	}

	return nil
}
