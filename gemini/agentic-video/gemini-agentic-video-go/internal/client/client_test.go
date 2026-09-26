// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

package client

import (
	"testing"
)

func TestResolveLocation(t *testing.T) {
	tests := []struct {
		name      string
		flagVal   string
		envLoc    string
		envRegion string
		want      string
	}{
		{
			name:    "flag_provided",
			flagVal: "us-central1",
			want:    "us-central1",
		},
		{
			name:    "env_location_set",
			flagVal: "",
			envLoc:  "europe-west1",
			want:    "europe-west1",
		},
		{
			name:      "env_region_set",
			flagVal:   "",
			envRegion: "asia-east1",
			want:      "asia-east1",
		},
		{
			name:    "fallback_to_global",
			flagVal: "",
			want:    "global",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Setenv("GOOGLE_CLOUD_LOCATION", tt.envLoc)
			t.Setenv("GOOGLE_CLOUD_REGION", tt.envRegion)

			got := ResolveLocation(tt.flagVal)
			if got != tt.want {
				t.Errorf("ResolveLocation(%q) = %q, want %q", tt.flagVal, got, tt.want)
			}
		})
	}
}

func TestResolveProject(t *testing.T) {
	tests := []struct {
		name       string
		flagVal    string
		envProject string
		want       string
	}{
		{
			name:    "flag_provided",
			flagVal: "custom-project",
			want:    "custom-project",
		},
		{
			name:       "env_project_set",
			flagVal:    "",
			envProject: "env-project",
			want:       "env-project",
		},
		{
			name:       "placeholder_flag_uses_env",
			flagVal:    "[your-project-id]",
			envProject: "env-project",
			want:       "env-project",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Setenv("GOOGLE_CLOUD_PROJECT", tt.envProject)

			got := ResolveProject(tt.flagVal)
			if got != tt.want {
				t.Errorf("ResolveProject(%q) = %q, want %q", tt.flagVal, got, tt.want)
			}
		})
	}
}

func TestNewClient_BackendValidation(t *testing.T) {
	ctx := t.Context()

	tests := []struct {
		name string
		cfg  Config
	}{
		{
			name: "enterprise_missing_project",
			cfg:  Config{Backend: "enterprise", Project: ""},
		},
		{
			name: "vertex_missing_project",
			cfg:  Config{Backend: "vertex", Project: ""},
		},
		{
			name: "gemini_missing_api_key",
			cfg:  Config{Backend: "gemini", APIKey: ""},
		},
		{
			name: "unsupported_backend",
			cfg:  Config{Backend: "unsupported"},
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			t.Setenv("GEMINI_API_KEY", "")
			t.Setenv("GOOGLE_API_KEY", "")

			_, err := NewClient(ctx, tt.cfg)
			if err == nil {
				t.Errorf("NewClient(ctx, %+v) error = nil, want non-nil error", tt.cfg)
			}
		})
	}
}
