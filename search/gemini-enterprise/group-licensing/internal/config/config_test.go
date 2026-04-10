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
	"os"
	"path/filepath"
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
)

func writeFixture(t *testing.T, content string) string {
	t.Helper()
	path := filepath.Join(t.TempDir(), "entitlements.json")
	if err := os.WriteFile(path, []byte(content), 0600); err != nil {
		t.Fatalf("writeFixture: %v", err)
	}
	return path
}

func TestLoad_ValidConfig(t *testing.T) {
	path := writeFixture(t, `{
		"billing_account_id": "ABCDE-12345-FGHIJ",
		"projects": {
			"acme-prod": [
				{
					"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE",
					"location": "global",
					"groups": ["eng@acme.com"]
				},
				{
					"subscription_tier": "SUBSCRIPTION_TIER_AGENTSPACE_BUSINESS",
					"location": "global",
					"groups": ["mkt@acme.com"]
				}
			]
		},
		"settings": {
			"staleness_threshold_days": 45
		}
	}`)

	cfg, err := Load(path)
	require.NoError(t, err)

	assert.Equal(t, "ABCDE-12345-FGHIJ", cfg.BillingAccountID)

	proj, ok := cfg.Projects["acme-prod"]
	require.True(t, ok, "expected project acme-prod to be present")
	require.Len(t, proj, 2)

	// Find the SUBSCRIPTION_TIER_ENTERPRISE entry and verify its groups.
	var entEntry ProjectEntry
	for _, e := range proj {
		if e.SubscriptionTier == models.SKUEnterprise {
			entEntry = e
			break
		}
	}
	require.Equal(t, models.SKUEnterprise, entEntry.SubscriptionTier)
	require.Len(t, entEntry.Groups, 1)
	assert.Equal(t, "eng@acme.com", entEntry.Groups[0])

	assert.Equal(t, 45, cfg.Settings.StalenessThresholdDays)
}

func TestLoad_MultiProjectConfig(t *testing.T) {
	path := writeFixture(t, `{
		"billing_account_id": "ABCDE-12345-FGHIJ",
		"projects": {
			"proj-alpha": [
				{
					"subscription_tier": "SUBSCRIPTION_TIER_SEARCH_AND_ASSISTANT",
					"location": "global",
					"groups": ["researchers@alpha.com"]
				}
			],
			"proj-beta": [
				{
					"subscription_tier": "SUBSCRIPTION_TIER_FRONTLINE_WORKER",
					"location": "us",
					"groups": ["sales@beta.com"]
				},
				{
					"subscription_tier": "SUBSCRIPTION_TIER_AGENTSPACE_BUSINESS",
					"location": "eu",
					"groups": ["ops@beta.com"]
				}
			],
			"proj-gamma": [
				{
					"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE",
					"location": "global",
					"groups": ["devs@gamma.com"]
				}
			]
		},
		"settings": {
			"staleness_threshold_days": 14
		}
	}`)

	cfg, err := Load(path)
	require.NoError(t, err)

	assert.Len(t, cfg.Projects, 3)
	assert.Contains(t, cfg.Projects, "proj-alpha")
	assert.Contains(t, cfg.Projects, "proj-beta")
	assert.Contains(t, cfg.Projects, "proj-gamma")

	assert.Len(t, cfg.Projects["proj-beta"], 2)
}

func TestLoad_StalenessThresholdZeroMeansDisabled(t *testing.T) {
	// A StalenessThresholdDays of 0 is valid and signals that the staleness
	// check is disabled; the value must be preserved as-is (not normalised to
	// any default).
	path := writeFixture(t, `{
		"billing_account_id": "ABCDE-12345-FGHIJ",
		"projects": {
			"proj-a": [
				{
					"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE",
					"location": "global",
					"groups": ["team@corp.com"]
				}
			]
		},
		"settings": {
			"staleness_threshold_days": 0
		}
	}`)

	cfg, err := Load(path)
	require.NoError(t, err)

	assert.Equal(t, 0, cfg.Settings.StalenessThresholdDays)
}

func TestLoad_FileNotFound(t *testing.T) {
	_, err := Load(filepath.Join(t.TempDir(), "does-not-exist.json"))
	assert.ErrorIs(t, err, models.ErrConfigNotFound)
}

func TestLoad_FileUnreadable(t *testing.T) {
	path := writeFixture(t, `{}`)
	if err := os.Chmod(path, 0000); err != nil {
		t.Skip("cannot change file permissions on this platform")
	}
	t.Cleanup(func() { _ = os.Chmod(path, 0600) })

	_, err := Load(path)
	assert.ErrorIs(t, err, models.ErrConfigUnreadable)
}

func TestLoad_MalformedJSON(t *testing.T) {
	path := writeFixture(t, `{ this is not valid json }`)

	_, err := Load(path)
	assert.ErrorIs(t, err, models.ErrConfigInvalid)
}

func TestLoad_ValidationFailures(t *testing.T) {
	tests := []struct {
		name    string
		json    string
		wantErr error
	}{
		{
			name:    "missing billing_account_id",
			json:    `{"projects": {"proj-x": [{"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE", "location": "global", "groups": ["team@corp.com"]}]}, "settings": {"staleness_threshold_days": 30}}`,
			wantErr: models.ErrConfigInvalid,
		},
		{
			name:    "no projects",
			json:    `{"billing_account_id": "ABCDE-12345-FGHIJ", "projects": {}, "settings": {"staleness_threshold_days": 30}}`,
			wantErr: models.ErrConfigNoProjects,
		},
		{
			name: "project with no entries",
			json: `{
				"billing_account_id": "ABCDE-12345-FGHIJ",
				"projects": {
					"empty-proj": []
				},
				"settings": {"staleness_threshold_days": 30}
			}`,
			wantErr: models.ErrConfigNoGroups,
		},
		{
			name: "invalid SKU",
			json: `{
				"billing_account_id": "ABCDE-12345-FGHIJ",
				"projects": {
					"proj-x": [
						{
							"subscription_tier": "SUBSCRIPTION_TIER_INVALID_UNKNOWN",
							"location": "global",
							"groups": ["team@corp.com"]
						}
					]
				},
				"settings": {"staleness_threshold_days": 30}
			}`,
			wantErr: models.ErrInvalidSKU,
		},
		{
			name: "invalid location",
			json: `{
				"billing_account_id": "ABCDE-12345-FGHIJ",
				"projects": {
					"proj-x": [
						{
							"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE",
							"location": "apac",
							"groups": ["team@corp.com"]
						}
					]
				},
				"settings": {"staleness_threshold_days": 30}
			}`,
			wantErr: models.ErrInvalidLocation,
		},
		{
			name: "entry with empty groups slice",
			json: `{
				"billing_account_id": "ABCDE-12345-FGHIJ",
				"projects": {
					"proj-x": [
						{
							"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE",
							"location": "global",
							"groups": []
						}
					]
				},
				"settings": {"staleness_threshold_days": 30}
			}`,
			wantErr: models.ErrConfigNoGroups,
		},
		{
			name:    "negative staleness threshold",
			json:    `{"billing_account_id": "ABCDE-12345-FGHIJ", "projects": {"proj-x": [{"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE", "location": "global", "groups": ["team@corp.com"]}]}, "settings": {"staleness_threshold_days": -1}}`,
			wantErr: models.ErrConfigInvalid,
		},
		{
			name:    "invalid project ID",
			json:    `{"billing_account_id": "ABCDE-12345-FGHIJ", "projects": {"INVALID_PROJECT!": [{"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE", "location": "global", "groups": ["team@corp.com"]}]}, "settings": {"staleness_threshold_days": 30}}`,
			wantErr: models.ErrConfigInvalid,
		},
		{
			name:    "invalid group email - missing at sign",
			json:    `{"billing_account_id": "ABCDE-12345-FGHIJ", "projects": {"valid-proj-id": [{"subscription_tier": "SUBSCRIPTION_TIER_ENTERPRISE", "location": "global", "groups": ["notanemail"]}]}, "settings": {"staleness_threshold_days": 30}}`,
			wantErr: models.ErrConfigInvalid,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			path := writeFixture(t, tc.json)
			_, err := Load(path)
			assert.ErrorIs(t, err, tc.wantErr)
		})
	}
}
