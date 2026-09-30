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
	"testing"
	"time"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/runner"
	"google.golang.org/genai"
)

func TestBenchmarkTrackerLifecycle(t *testing.T) {
	tracker := NewBenchmarkTracker("medium")
	if tracker == nil {
		t.Fatalf("NewBenchmarkTracker() = nil, want valid tracker")
	}

	// Test non-TTY mode
	tracker.isTTY = false
	tracker.Start()

	// Simulate Agentic finish
	aRes := &runner.Result{
		Title:    "Agentic Run",
		Duration: 15 * time.Second,
		Usage: &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount: 8000,
		},
	}
	tracker.Update(true, false, aRes, nil)

	// Simulate Static finish
	sRes := &runner.Result{
		Title:    "Static Run",
		Duration: 45 * time.Second,
		Usage: &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount: 180000,
		},
	}
	tracker.Update(true, true, aRes, sRes)
	tracker.Stop()
}

func TestBenchmarkTrackerFormatElapsed(t *testing.T) {
	dur := 65400 * time.Millisecond
	got := FormatElapsed(dur)
	want := "01:05.4"
	if got != want {
		t.Errorf("FormatElapsed(%v) = %q, want %q", dur, got, want)
	}
}

func TestMultiModelTrackerLifecycle(t *testing.T) {
	models := []string{"gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"}
	tracker := NewMultiModelTracker(models)
	if tracker == nil {
		t.Fatalf("NewMultiModelTracker() = nil, want valid tracker")
	}

	tracker.isTTY = false
	tracker.Start()

	// Update first model
	tracker.Update("gemini-3.8-flash", true, &runner.Result{
		Title:    "gemini-3.8-flash",
		Duration: 12 * time.Second,
		Usage: &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount: 7500,
		},
	}, nil)

	// Update second model
	tracker.Update("gemini-3.7-flash", true, &runner.Result{
		Title:    "gemini-3.7-flash",
		Duration: 18 * time.Second,
		Usage: &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount: 8200,
		},
	}, nil)

	// Update third model
	tracker.Update("gemini-3.6-flash", true, &runner.Result{
		Title:    "gemini-3.6-flash",
		Duration: 22 * time.Second,
		Usage: &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount: 9100,
		},
	}, nil)

	tracker.Stop()
}
