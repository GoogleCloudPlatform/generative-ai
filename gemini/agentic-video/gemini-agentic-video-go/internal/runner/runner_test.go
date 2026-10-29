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
	"bytes"
	"testing"

	"google.golang.org/genai"
)

func TestParseThinkingLevel(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    genai.ThinkingLevel
		wantErr bool
	}{
		{name: "low_lowercase", input: "low", want: genai.ThinkingLevelLow},
		{name: "low_uppercase", input: "LOW", want: genai.ThinkingLevelLow},
		{name: "medium", input: "medium", want: genai.ThinkingLevelMedium},
		{name: "high", input: "high", want: genai.ThinkingLevelHigh},
		{name: "minimal", input: "minimal", want: genai.ThinkingLevelMinimal},
		{name: "unknown_fallback_medium", input: "unknown", want: genai.ThinkingLevelMedium, wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ParseThinkingLevel(tt.input)
			if got != tt.want {
				t.Errorf("ParseThinkingLevel(%q) = %v, want %v", tt.input, got, tt.want)
			}
			_, err := ParseThinkingLevelE(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParseThinkingLevelE(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
			}
		})
	}
}

func TestValidateThinkingLevel(t *testing.T) {
	tests := []struct {
		name    string
		modelID string
		level   genai.ThinkingLevel
		wantErr bool
	}{
		{name: "argon_medium_ok", modelID: "gemini-4-argon", level: genai.ThinkingLevelMedium, wantErr: false},
		{name: "argon_minimal_rejected", modelID: "gemini-4-argon", level: genai.ThinkingLevelMinimal, wantErr: true},
		{name: "3.7_minimal_rejected", modelID: "gemini-3.7-flash", level: genai.ThinkingLevelMinimal, wantErr: true},
		{name: "3.8_minimal_rejected", modelID: "gemini-3.8-flash", level: genai.ThinkingLevelMinimal, wantErr: true},
		{name: "3.5_lite_minimal_ok", modelID: "gemini-3.5-flash-lite", level: genai.ThinkingLevelMinimal, wantErr: false},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := ValidateThinkingLevel(tt.modelID, tt.level)
			if (err != nil) != tt.wantErr {
				t.Errorf("ValidateThinkingLevel(%q, %q) error = %v, wantErr %v", tt.modelID, tt.level, err, tt.wantErr)
			}
		})
	}
}

func TestParseProcessingMode(t *testing.T) {
	tests := []struct {
		name    string
		input   string
		want    genai.MediaProcessing
		wantErr bool
	}{
		{name: "agentic_lowercase", input: "agentic", want: genai.MediaProcessingAgentic},
		{name: "agentic_uppercase", input: "AGENTIC", want: genai.MediaProcessingAgentic},
		{name: "static_lowercase", input: "static", want: genai.MediaProcessingStatic},
		{name: "static_uppercase", input: "STATIC", want: genai.MediaProcessingStatic},
		{name: "fallback_agentic", input: "anything_else", want: genai.MediaProcessingAgentic, wantErr: true},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := ParseProcessingMode(tt.input)
			if got != tt.want {
				t.Errorf("ParseProcessingMode(%q) = %v, want %v", tt.input, got, tt.want)
			}
			_, err := ParseProcessingModeE(tt.input)
			if (err != nil) != tt.wantErr {
				t.Errorf("ParseProcessingModeE(%q) error = %v, wantErr %v", tt.input, err, tt.wantErr)
			}
		})
	}
}

func TestNormalizeVideoURI(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  string
	}{
		{
			name:  "https_storage_googleapis",
			input: "https://storage.googleapis.com/generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4",
			want:  "gs://generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4",
		},
		{
			name:  "https_storage_cloud_google",
			input: "https://storage.cloud.google.com/my-bucket/clip.mp4",
			want:  "gs://my-bucket/clip.mp4",
		},
		{
			name:  "native_gs_unchanged",
			input: "gs://my-bucket/clip.mp4",
			want:  "gs://my-bucket/clip.mp4",
		},
		{
			name:  "youtube_url_unchanged",
			input: "https://www.youtube.com/watch?v=LzExSq9DU9w",
			want:  "https://www.youtube.com/watch?v=LzExSq9DU9w",
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			if got := NormalizeVideoURI(tt.input); got != tt.want {
				t.Errorf("NormalizeVideoURI(%q) = %q, want %q", tt.input, got, tt.want)
			}
		})
	}
}

func TestExtractModelTurnContentAndDetails(t *testing.T) {
	callSignature := []byte("call-signature")
	resultSignature := []byte("result-signature")
	finalSignature := []byte("final-signature")

	resp := &genai.GenerateContentResponse{
		Candidates: []*genai.Candidate{
			{
				Content: &genai.Content{
					Role: genai.RoleModel,
					Parts: []*genai.Part{
						{Text: "Step 1 reasoning", Thought: true},
						{ThoughtSignature: callSignature},
						{ThoughtSignature: resultSignature},
						{Text: "Step 2 reasoning", Thought: true},
						{Text: "Final synthesized answer", ThoughtSignature: finalSignature},
					},
				},
			},
		},
	}

	thoughts, hops := extractResponseDetails(resp)
	if len(thoughts) != 2 {
		t.Fatalf("len(thoughts) = %d, want 2", len(thoughts))
	}
	if hops != 1 {
		t.Errorf("toolHops = %d, want 1", hops)
	}

	turnContent := ExtractModelTurnContent(resp)
	if len(turnContent.Parts) != 1 {
		t.Fatalf("len(turnContent.Parts) = %d, want 1", len(turnContent.Parts))
	}
	if turnContent.Parts[0].Text != "Final synthesized answer" {
		t.Errorf("turnContent.Parts[0].Text = %q, want %q", turnContent.Parts[0].Text, "Final synthesized answer")
	}
	if !bytes.Equal(turnContent.Parts[0].ThoughtSignature, finalSignature) {
		t.Errorf("turnContent.Parts[0].ThoughtSignature = %q, want %q", turnContent.Parts[0].ThoughtSignature, finalSignature)
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
		t.Errorf("BenchmarkResult.AgenticResult.Mode = %q, want %q", res.AgenticResult.Mode, genai.MediaProcessingAgentic)
	}
	if res.StaticResult.Mode != genai.MediaProcessingStatic {
		t.Errorf("BenchmarkResult.StaticResult.Mode = %q, want %q", res.StaticResult.Mode, genai.MediaProcessingStatic)
	}
}
