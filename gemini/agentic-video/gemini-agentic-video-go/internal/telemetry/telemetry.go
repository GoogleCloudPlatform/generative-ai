// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
// Package telemetry provides metrics formatting and benchmark comparison for video processing.
package telemetry

import (
	"fmt"
	"io"
	"os"
	"time"

	"google.golang.org/genai"
)

// TokenReductionPct calculates the percentage reduction in token consumption.
func TokenReductionPct(agenticTotal, staticTotal int64) float64 {
	if staticTotal <= 0 {
		return 0.0
	}
	return float64(staticTotal-agenticTotal) / float64(staticTotal) * 100.0
}

// PrintUsage displays a structured breakdown of token consumption to os.Stdout.
func PrintUsage(usage *genai.GenerateContentResponseUsageMetadata, mode genai.MediaProcessing, duration time.Duration) {
	FprintUsage(os.Stdout, usage, mode, duration)
}

// FprintUsage writes a structured breakdown of token consumption to the specified writer.
func FprintUsage(w io.Writer, usage *genai.GenerateContentResponseUsageMetadata, mode genai.MediaProcessing, duration time.Duration) {
	if usage == nil {
		fmt.Fprintf(w, "Processing Duration: %v (token usage telemetry not returned)\n\n", duration.Round(time.Millisecond))
		return
	}

	fmt.Fprintf(w, "Token Telemetry Breakdown:\n")
	fmt.Fprintf(w, "  • Total Token Count:     %d\n", usage.TotalTokenCount)
	fmt.Fprintf(w, "  • Prompt Input Tokens:   %d", usage.PromptTokenCount)
	if mode == genai.MediaProcessingAgentic {
		fmt.Fprintf(w, " (text-only prompt; video frames dynamically fetched on-demand)")
	} else if mode == genai.MediaProcessingStatic {
		fmt.Fprintf(w, " (includes 100%% of video frames statically pre-ingested at 1 FPS)")
	}
	fmt.Fprintln(w)

	fmt.Fprintf(w, "  • Candidates Tokens:     %d\n", usage.CandidatesTokenCount)
	if usage.ThoughtsTokenCount > 0 {
		fmt.Fprintf(w, "  • Thoughts Tokens:       %d", usage.ThoughtsTokenCount)
		if mode == genai.MediaProcessingAgentic {
			fmt.Fprintf(w, " (includes native timeline navigation & dynamic inspection)")
		}
		fmt.Fprintln(w)
	}
	fmt.Fprintf(w, "Processing Duration:       %v\n\n", duration.Round(time.Millisecond))
}

// PrintComparison displays a side-by-side performance comparison table to os.Stdout.
func PrintComparison(agenticUsage, staticUsage *genai.GenerateContentResponseUsageMetadata, agenticDuration, staticDuration time.Duration) {
	FprintComparison(os.Stdout, agenticUsage, staticUsage, agenticDuration, staticDuration)
}

// FprintComparison writes a side-by-side performance comparison table to the specified writer.
func FprintComparison(w io.Writer, agenticUsage, staticUsage *genai.GenerateContentResponseUsageMetadata, agenticDuration, staticDuration time.Duration) {
	fmt.Fprintf(w, "=========================================================================================\n")
	fmt.Fprintf(w, "  PERFORMANCE BENCHMARK: AGENTIC VIDEO vs. STATIC (1 FPS) INGESTION\n")
	fmt.Fprintf(w, "=========================================================================================\n")

	agenticTotal := int64(0)
	staticTotal := int64(0)
	agenticPrompt := int32(0)
	staticPrompt := int32(0)
	agenticCandidates := int32(0)
	staticCandidates := int32(0)
	agenticThoughts := int32(0)
	staticThoughts := int32(0)

	if agenticUsage != nil {
		agenticTotal = int64(agenticUsage.TotalTokenCount)
		agenticPrompt = agenticUsage.PromptTokenCount
		agenticCandidates = agenticUsage.CandidatesTokenCount
		agenticThoughts = agenticUsage.ThoughtsTokenCount
	}
	if staticUsage != nil {
		staticTotal = int64(staticUsage.TotalTokenCount)
		staticPrompt = staticUsage.PromptTokenCount
		staticCandidates = staticUsage.CandidatesTokenCount
		staticThoughts = staticUsage.ThoughtsTokenCount
	}

	tokenDeltaPct := TokenReductionPct(agenticTotal, staticTotal)

	fmt.Fprintf(w, "| Metric                     | Agentic Video        | Static Ingestion     | Observation / Delta       |\n")
	fmt.Fprintf(w, "|:---------------------------|:---------------------|:---------------------|:--------------------------|\n")
	fmt.Fprintf(w, "| Total Consumed Tokens      | %-20d | %-20d | %+.1f%% net token spend   |\n", agenticTotal, staticTotal, tokenDeltaPct)
	fmt.Fprintf(w, "| Prompt Tokens (Input)      | %-20d | %-20d | %-+25s |\n", agenticPrompt, staticPrompt, fmt.Sprintf("%+d input tokens", agenticPrompt-staticPrompt))
	fmt.Fprintf(w, "| Candidate Output Tokens    | %-20d | %-20d | %-+25s |\n", agenticCandidates, staticCandidates, fmt.Sprintf("%+d output tokens", agenticCandidates-staticCandidates))
	fmt.Fprintf(w, "| Reasoning Thoughts Tokens  | %-20d | %-20d | %-+25s |\n", agenticThoughts, staticThoughts, "dynamic frame inspection")
	fmt.Fprintf(w, "| Latency (Duration)         | %-20v | %-20v | %-+25s |\n",
		agenticDuration.Round(time.Millisecond),
		staticDuration.Round(time.Millisecond),
		fmt.Sprintf("diff: %v", (agenticDuration-staticDuration).Round(time.Millisecond)))
	fmt.Fprintf(w, "=========================================================================================\n")
	fmt.Fprintf(w, "💡 Telemetry Insight: In Agentic mode, initial prompt tokens are minimal because video frames\n")
	fmt.Fprintf(w, "   are fetched dynamically during the model's Think ➔ Act timeline loop (accounted under thoughts).\n\n")
}
