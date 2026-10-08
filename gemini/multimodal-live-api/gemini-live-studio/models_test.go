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

package main

import (
	"slices"
	"testing"
)

func TestResolveAllowed(t *testing.T) {
	registry := []string{"model-a", "model-b"}
	const def = "env-model"

	tests := []struct {
		name      string
		requested string
		want      string
	}{
		{"empty uses default", "", def},
		{"whitespace uses default", "   ", def},
		{"default is always allowed", def, def},
		{"registry entry is honored", "model-b", "model-b"},
		{"registry entry is trimmed", " model-a ", "model-a"},
		{"unknown model falls back", "model-z", def},
		{"client-supplied string is never passed through unchecked", "projects/other/locations/x/publishers/google/models/evil", def},
		{"case must match exactly", "MODEL-A", def},
	}
	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := resolveAllowed("test", tt.requested, def, registry); got != tt.want {
				t.Errorf("resolveAllowed(%q) = %q, want %q", tt.requested, got, tt.want)
			}
		})
	}
}

func TestAllowedValues(t *testing.T) {
	registry := []string{"a", "b"}
	if got := allowedValues("b", registry); !slices.Equal(got, []string{"a", "b"}) {
		t.Errorf("default already listed: got %v", got)
	}
	if got := allowedValues("env", registry); !slices.Equal(got, []string{"env", "a", "b"}) {
		t.Errorf("default not listed: got %v", got)
	}
	got := allowedValues("", registry)
	got[0] = "mutated"
	if registry[0] != "a" {
		t.Error("allowedValues must not alias the registry")
	}
}

func TestRegistriesIncludeFallbacks(t *testing.T) {
	if !slices.Contains(locationRegistry, "us-central1") {
		t.Error("locationRegistry must include us-central1 (the default location)")
	}
	if !slices.Contains(liveModelRegistry, fallbackLiveModel) {
		t.Errorf("liveModelRegistry must include fallbackLiveModel %q", fallbackLiveModel)
	}
}

func TestImageModelRegistry_DefaultAndAlternatives(t *testing.T) {
	if defaultImageModel != "gemini-nano-banana-2.1" {
		t.Errorf("defaultImageModel = %q", defaultImageModel)
	}
	if imageModelRegistry[0] != defaultImageModel {
		t.Errorf("registry should list the default first, got %v", imageModelRegistry)
	}
	for _, m := range []string{"gemini-3.1-flash-image", "gemini-3-pro-image", "gemini-3.1-flash-lite-image"} {
		if got := resolveAllowed("image model", m, defaultImageModel, imageModelRegistry); got != m {
			t.Errorf("resolveAllowed(%q) = %q, want it selectable", m, got)
		}
	}
}
