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
	"net/http"
	"net/http/httptest"
	"slices"
	"testing"

	"google.golang.org/genai"

	"local-code-assistant/tools"
)

func TestResolveAllowed_ModelOverride(t *testing.T) {
	if got := resolveAllowed("live model", "", "gemini-3.8-live", liveModelRegistry); got != "gemini-3.8-live" {
		t.Fatalf("empty requested = %q, want gemini-3.8-live", got)
	}
	if got := resolveAllowed("live model", "gemini-3.8-live", "gemini-3.8-live", liveModelRegistry); got != "gemini-3.8-live" {
		t.Fatalf("registry model = %q, want gemini-3.8-live", got)
	}
	if got := resolveAllowed("live model", "custom-env-model", "custom-env-model", liveModelRegistry); got != "custom-env-model" {
		t.Fatalf("server default model = %q, want custom-env-model", got)
	}
	if got := resolveAllowed("live model", "../../etc/passwd", "gemini-3.8-live", liveModelRegistry); got != "gemini-3.8-live" {
		t.Fatalf("untrusted model = %q, want fallback gemini-3.8-live", got)
	}
	if got := resolveAllowed("live model", "gemini-unlisted-model", "gemini-3.8-live", liveModelRegistry); got != "gemini-3.8-live" {
		t.Fatalf("unlisted model = %q, want fallback gemini-3.8-live", got)
	}
}

func TestAllowedValues_PrependsCustomDefault(t *testing.T) {
	got := allowedValues("custom-live-model", liveModelRegistry)
	want := []string{"custom-live-model", "gemini-3.8-live"}
	if !slices.Equal(got, want) {
		t.Fatalf("allowedValues = %v, want %v", got, want)
	}
}

func TestAllowLocalOrigin(t *testing.T) {
	cases := []struct {
		name, host, origin string
		want               bool
	}{
		{"no origin", "localhost:8081", "", true},
		{"same origin", "localhost:8081", "http://localhost:8081", true},
		{"loopback dev page", "127.0.0.1:8081", "http://localhost:5173", true},
		{"foreign site", "localhost:8081", "https://evil.example", false},
		{"loopback origin, non-loopback host", "devbox.lan:8081", "http://localhost:5173", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			r := httptest.NewRequest(http.MethodGet, "/ws", nil)
			r.Host = tc.host
			if tc.origin != "" {
				r.Header.Set("Origin", tc.origin)
			}
			if got := allowLocalOrigin(r); got != tc.want {
				t.Errorf("allowLocalOrigin(host=%q, origin=%q) = %v, want %v", tc.host, tc.origin, got, tc.want)
			}
		})
	}
}

func TestBuildLiveConfig_Modes(t *testing.T) {
	registry := tools.NewRegistry(tools.NewReadFile())
	audio := buildLiveConfig(appConfig{voice: "Puck"}, "gemini-3.8-live", registry)
	if audio.ResponseModalities[0] != genai.ModalityAudio || audio.AvatarConfig != nil || audio.Proactivity == nil {
		t.Errorf("audio config: modalities=%v avatar=%v proactivity=%v", audio.ResponseModalities, audio.AvatarConfig, audio.Proactivity)
	}
	if flash := buildLiveConfig(appConfig{}, "gemini-3.5-flash-live-preview", registry); flash.Proactivity != nil {
		t.Error("proactive audio must not be set on full 3.5 Flash (1007)")
	}
	video := buildLiveConfig(appConfig{enableAvatar: true, avatarMode: "video", avatarPreset: "Kira"}, "gemini-3.8-live", registry)
	if video.ResponseModalities[0] != genai.ModalityVideo || video.AvatarConfig == nil || video.AvatarConfig.AvatarName != "Kira" {
		t.Errorf("video config: modalities=%v avatar=%+v", video.ResponseModalities, video.AvatarConfig)
	}
}
