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

package runner

import (
	"testing"

	"google.golang.org/genai"
)

func TestParseThinkingLevel(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  genai.ThinkingLevel
	}{
		{name: "low_lowercase", input: "low", want: genai.ThinkingLevelLow},
		{name: "low_uppercase", input: "LOW", want: genai.ThinkingLevelLow},
		{name: "medium", input: "medium", want: genai.ThinkingLevelMedium},
		{name: "high", input: "high", want: genai.ThinkingLevelHigh},
		{name: "minimal", input: "minimal", want: genai.ThinkingLevelMinimal},
		{name: "unknown_fallback_medium", input: "unknown", want: genai.ThinkingLevelMedium},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ParseThinkingLevel(tt.input)
			if got != tt.want {
				t.Errorf("ParseThinkingLevel(%q) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

func TestParseProcessingMode(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  genai.MediaProcessing
	}{
		{name: "agentic_lowercase", input: "agentic", want: genai.MediaProcessingAgentic},
		{name: "agentic_uppercase", input: "AGENTIC", want: genai.MediaProcessingAgentic},
		{name: "static_lowercase", input: "static", want: genai.MediaProcessingStatic},
		{name: "static_uppercase", input: "STATIC", want: genai.MediaProcessingStatic},
		{name: "fallback_agentic", input: "anything_else", want: genai.MediaProcessingAgentic},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ParseProcessingMode(tt.input)
			if got != tt.want {
				t.Errorf("ParseProcessingMode(%q) = %v, want %v", tt.input, got, tt.want)
			}
		})
	}
}

func TestBenchmarkResultStruct(t *testing.T) {
	res := BenchmarkResult{
		AgenticResult: &Result{
			Title: "Agentic",
			Mode:  genai.MediaProcessingAgentic,
		},
		StaticResult: &Result{
			Title: "Static",
			Mode:  genai.MediaProcessingStatic,
		},
	}

	if res.AgenticResult.Mode != genai.MediaProcessingAgentic {
		t.Errorf("res.AgenticResult.Mode = %v, want Agentic", res.AgenticResult.Mode)
	}
	if res.StaticResult.Mode != genai.MediaProcessingStatic {
		t.Errorf("res.StaticResult.Mode = %v, want Static", res.StaticResult.Mode)
	}
}
