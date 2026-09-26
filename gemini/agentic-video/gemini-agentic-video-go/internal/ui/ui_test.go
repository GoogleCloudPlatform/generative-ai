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

package ui

import (
	"strings"
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/catalog"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/runner"
	"google.golang.org/genai"
)

func TestRenderBanner(t *testing.T) {
	model, backend, project, location := "gemini-3.7-flash", "enterprise", "test-project", "global"
	out := RenderBanner(model, backend, project, location)
	if !strings.Contains(out, model) {
		t.Errorf("RenderBanner(%q, %q, %q, %q) output missing model ID %q; output:\n%s", model, backend, project, location, model, out)
	}
	if !strings.Contains(out, project) {
		t.Errorf("RenderBanner(%q, %q, %q, %q) output missing project %q; output:\n%s", model, backend, project, location, project, out)
	}
}

func TestRenderCatalogTable(t *testing.T) {
	out := RenderCatalogTable(catalog.Scenarios)
	if out == "" {
		t.Errorf("RenderCatalogTable(Scenarios) = %q, want non-empty formatted table", out)
	}
	if !strings.Contains(out, "youtube-agentic") {
		t.Errorf("RenderCatalogTable(Scenarios) output missing scenario name %q; output:\n%s", "youtube-agentic", out)
	}
}

func TestRenderBenchmarkTable(t *testing.T) {
	agenticUsage := &genai.GenerateContentResponseUsageMetadata{
		TotalTokenCount:      8000,
		PromptTokenCount:     250,
		CandidatesTokenCount: 500,
		ThoughtsTokenCount:   7250,
	}
	staticUsage := &genai.GenerateContentResponseUsageMetadata{
		TotalTokenCount:      185000,
		PromptTokenCount:     184500,
		CandidatesTokenCount: 500,
		ThoughtsTokenCount:   0,
	}

	out := RenderBenchmarkTable(agenticUsage, staticUsage, 15*time.Second, 45*time.Second)
	if !strings.Contains(out, "PERFORMANCE BENCHMARK") {
		t.Errorf("RenderBenchmarkTable(...) output missing title header %q; output:\n%s", "PERFORMANCE BENCHMARK", out)
	}

	// Test graceful handling of nil usage metadata
	nilOut := RenderBenchmarkTable(nil, nil, 0, 0)
	if nilOut == "" {
		t.Errorf("RenderBenchmarkTable(nil, nil, 0, 0) = %q, want fallback table", nilOut)
	}
}

func TestRenderTelemetryCard(t *testing.T) {
	usage := &genai.GenerateContentResponseUsageMetadata{
		TotalTokenCount:      5000,
		PromptTokenCount:     200,
		CandidatesTokenCount: 300,
		ThoughtsTokenCount:   4500,
	}

	out := RenderTelemetryCard(usage, genai.MediaProcessingAgentic, 10*time.Second)
	if !strings.Contains(out, "5000") {
		t.Errorf("RenderTelemetryCard(...) output missing total token count %q; output:\n%s", "5000", out)
	}

	// Test graceful handling of nil usage
	nilOut := RenderTelemetryCard(nil, genai.MediaProcessingAgentic, 10*time.Second)
	if nilOut == "" {
		t.Errorf("RenderTelemetryCard(nil, MediaProcessingAgentic, 10s) = %q, want fallback card", nilOut)
	}
}

func TestRenderBadges(t *testing.T) {
	agenticBadge := RenderModeBadge(genai.MediaProcessingAgentic)
	if !strings.Contains(agenticBadge, "AGENTIC") {
		t.Errorf("RenderModeBadge(MediaProcessingAgentic) = %q, want AGENTIC", agenticBadge)
	}

	staticBadge := RenderModeBadge(genai.MediaProcessingStatic)
	if !strings.Contains(staticBadge, "STATIC") {
		t.Errorf("RenderModeBadge(MediaProcessingStatic) = %q, want STATIC", staticBadge)
	}

	turnBadge := RenderTurnBadge(10, 12)
	if !strings.Contains(turnBadge, "Turn 10/12") {
		t.Errorf("RenderTurnBadge(10, 12) = %q, want to contain %q", turnBadge, "Turn 10/12")
	}

	turnSingleBadge := RenderTurnBadge(3, 0)
	if !strings.Contains(turnSingleBadge, "Turn 3") {
		t.Errorf("RenderTurnBadge(3, 0) = %q, want to contain %q", turnSingleBadge, "Turn 3")
	}

	videoBadge := RenderVideoBadge(10, "agentic")
	if !strings.Contains(videoBadge, "Video 10 (AGENTIC)") {
		t.Errorf("RenderVideoBadge(10, %q) = %q, want to contain %q", "agentic", videoBadge, "Video 10 (AGENTIC)")
	}

	thinkingBadge := RenderThinkingBadge(genai.ThinkingLevelHigh)
	if !strings.Contains(thinkingBadge, "THINKING: HIGH") {
		t.Errorf("RenderThinkingBadge(ThinkingLevelHigh) = %q, want to contain %q", thinkingBadge, "THINKING: HIGH")
	}
}

func TestRenderMultiModelTable(t *testing.T) {
	results := []runner.ModelBenchmarkResult{
		{
			ModelID:  "gemini-3.6-flash",
			Duration: 25 * time.Second,
			Result: &runner.Result{
				Usage: &genai.GenerateContentResponseUsageMetadata{
					TotalTokenCount:      9000,
					PromptTokenCount:     250,
					CandidatesTokenCount: 500,
					ThoughtsTokenCount:   5500,
				},
			},
		},
		{
			ModelID:  "gemini-3.7-flash",
			Duration: 22 * time.Second,
			Result: &runner.Result{
				Usage: &genai.GenerateContentResponseUsageMetadata{
					TotalTokenCount:      8500,
					PromptTokenCount:     250,
					CandidatesTokenCount: 600,
					ThoughtsTokenCount:   5000,
				},
			},
		},
		{
			ModelID:  "gemini-3.8-flash",
			Duration: 14 * time.Second,
			Result: &runner.Result{
				Usage: &genai.GenerateContentResponseUsageMetadata{
					TotalTokenCount:      7800,
					PromptTokenCount:     250,
					CandidatesTokenCount: 700,
					ThoughtsTokenCount:   4200,
				},
			},
		},
	}

	out := RenderMultiModelTable(results)
	if !strings.Contains(out, "gemini-3.6-flash") || !strings.Contains(out, "gemini-3.8-flash") {
		t.Errorf("RenderMultiModelTable(results) output missing model headers; output:\n%s", out)
	}
	if !strings.Contains(out, "7800") {
		t.Errorf("RenderMultiModelTable(results) output missing token count %q; output:\n%s", "7800", out)
	}

	emptyOut := RenderMultiModelTable(nil)
	if emptyOut != "" {
		t.Errorf("RenderMultiModelTable(nil) = %q, want empty string", emptyOut)
	}
}
