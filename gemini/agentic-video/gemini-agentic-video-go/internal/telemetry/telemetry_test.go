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

package telemetry

import (
	"bytes"
	"strings"
	"testing"
	"time"

	"google.golang.org/genai"
)

func TestTokenReductionPct(t *testing.T) {
	tests := []struct {
		name         string
		agenticTotal int64
		staticTotal  int64
		want         float64
	}{
		{
			name:         "typical_reduction",
			agenticTotal: 8000,
			staticTotal:  185000,
			want:         (185000.0 - 8000.0) / 185000.0 * 100.0,
		},
		{
			name:         "zero_static_total",
			agenticTotal: 5000,
			staticTotal:  0,
			want:         0.0,
		},
		{
			name:         "negative_reduction",
			agenticTotal: 1000,
			staticTotal:  500,
			want:         -100.0,
		},
		{
			name:         "equal_tokens",
			agenticTotal: 1000,
			staticTotal:  1000,
			want:         0.0,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := TokenReductionPct(tt.agenticTotal, tt.staticTotal)
			if got != tt.want {
				t.Errorf("TokenReductionPct(%d, %d) = %v, want %v", tt.agenticTotal, tt.staticTotal, got, tt.want)
			}
		})
	}
}

func TestFprintUsage(t *testing.T) {
	t.Run("nil_usage", func(t *testing.T) {
		var buf bytes.Buffer
		FprintUsage(&buf, nil, genai.MediaProcessingAgentic, 1500*time.Millisecond)

		out := buf.String()
		if !strings.Contains(out, "token usage telemetry not returned") {
			t.Errorf("FprintUsage(&buf, nil, ...) output = %q, want to contain %q", out, "token usage telemetry not returned")
		}
		if !strings.Contains(out, "1.5s") {
			t.Errorf("FprintUsage(&buf, nil, ...) output = %q, want to contain %q", out, "1.5s")
		}
	})

	t.Run("agentic_with_thoughts", func(t *testing.T) {
		var buf bytes.Buffer
		usage := &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount:      8000,
			PromptTokenCount:     250,
			CandidatesTokenCount: 500,
			ThoughtsTokenCount:   7250,
		}
		FprintUsage(&buf, usage, genai.MediaProcessingAgentic, 12*time.Second)

		out := buf.String()
		for _, want := range []string{"8000", "250", "500", "7250", "dynamic inspection"} {
			if !strings.Contains(out, want) {
				t.Errorf("FprintUsage(...) output = %q, want to contain %q", out, want)
			}
		}
	})

	t.Run("static_mode", func(t *testing.T) {
		var buf bytes.Buffer
		usage := &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount:      185000,
			PromptTokenCount:     184500,
			CandidatesTokenCount: 500,
		}
		FprintUsage(&buf, usage, genai.MediaProcessingStatic, 45*time.Second)

		out := buf.String()
		for _, want := range []string{"185000", "184500", "1 FPS"} {
			if !strings.Contains(out, want) {
				t.Errorf("FprintUsage(...) output = %q, want to contain %q", out, want)
			}
		}
	})
}

func TestFprintComparison(t *testing.T) {
	t.Run("populated_metadata", func(t *testing.T) {
		var buf bytes.Buffer
		agentic := &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount:      8000,
			PromptTokenCount:     250,
			CandidatesTokenCount: 500,
			ThoughtsTokenCount:   7250,
		}
		static := &genai.GenerateContentResponseUsageMetadata{
			TotalTokenCount:      185000,
			PromptTokenCount:     184500,
			CandidatesTokenCount: 500,
			ThoughtsTokenCount:   0,
		}

		FprintComparison(&buf, agentic, static, 15*time.Second, 45*time.Second)

		out := buf.String()
		for _, want := range []string{"PERFORMANCE BENCHMARK", "8000", "185000", "Telemetry Insight"} {
			if !strings.Contains(out, want) {
				t.Errorf("FprintComparison(...) output = %q, want to contain %q", out, want)
			}
		}
	})

	t.Run("nil_metadata_graceful", func(t *testing.T) {
		var buf bytes.Buffer
		FprintComparison(&buf, nil, nil, 0, 0)

		out := buf.String()
		if !strings.Contains(out, "PERFORMANCE BENCHMARK") {
			t.Errorf("FprintComparison(&buf, nil, nil, ...) output = %q, want to contain %q", out, "PERFORMANCE BENCHMARK")
		}
	})
}
