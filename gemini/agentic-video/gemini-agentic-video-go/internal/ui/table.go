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
	"fmt"
	"strconv"
	"time"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/catalog"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/runner"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/telemetry"
	"github.com/charmbracelet/lipgloss"
	"github.com/charmbracelet/lipgloss/table"
	"google.golang.org/genai"
)

// RenderCatalogTable formats the preset scenarios into a styled Lipgloss table.
func RenderCatalogTable(scenarios []catalog.Scenario) string {
	headerStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(ColorWhite).
		Background(ColorGeminiBlue).
		Align(lipgloss.Center).
		Padding(0, 1)

	baseCellStyle := lipgloss.NewStyle().Padding(0, 1)
	zebraStyle := baseCellStyle.Background(ColorZebraBg)

	tbl := table.New().
		Border(lipgloss.RoundedBorder()).
		BorderStyle(lipgloss.NewStyle().Foreground(ColorGeminiBlue)).
		Headers("ID", "Mode", "Identifier", "Title & Capabilities").
		StyleFunc(func(row, col int) lipgloss.Style {
			if row == table.HeaderRow {
				return headerStyle
			}
			style := baseCellStyle
			if row%2 == 0 {
				style = zebraStyle
			}
			switch col {
			case 0:
				return style.Bold(true).Foreground(ColorWhite).Align(lipgloss.Center)
			case 2:
				return style.Foreground(ColorGeminiCyan).Bold(true)
			default:
				return style.Foreground(ColorWhite)
			}
		})

	for _, sc := range scenarios {
		isMultiVideo := len(sc.MultiVideos) > 0
		isMultiTurn := len(sc.MultiTurns) > 0
		typeBadge := RenderScenarioTypeBadge(sc.Mode, isMultiVideo, isMultiTurn)

		tbl.Row(
			strconv.Itoa(sc.ID),
			typeBadge,
			sc.Name,
			sc.Title,
		)
	}

	header := SectionHeader.Render("📋 Built-In Tutorial Scenarios (Run with: ./bin/gemini-agentic-video-go example <id>)")
	return lipgloss.JoinVertical(lipgloss.Left, header, tbl.Render())
}

// RenderBenchmarkTable renders the side-by-side Agentic vs Static benchmark comparison.
func RenderBenchmarkTable(agenticUsage, staticUsage *genai.GenerateContentResponseUsageMetadata, agenticDuration, staticDuration time.Duration) string {
	var agenticTotal, staticTotal int64
	var (
		agenticPrompt, staticPrompt         int32
		agenticCandidates, staticCandidates int32
		agenticToolUse, staticToolUse       int32
		agenticCached, staticCached         int32
		agenticThoughts, staticThoughts     int32
		agenticToolDetails                  string
	)

	if agenticUsage != nil {
		agenticTotal = int64(agenticUsage.TotalTokenCount)
		agenticPrompt = agenticUsage.PromptTokenCount
		agenticToolUse = agenticUsage.ToolUsePromptTokenCount
		agenticCached = agenticUsage.CachedContentTokenCount
		agenticCandidates = agenticUsage.CandidatesTokenCount
		agenticThoughts = agenticUsage.ThoughtsTokenCount
		agenticToolDetails = telemetry.FormatModalityDetails(agenticUsage.ToolUsePromptTokensDetails)
	}
	if staticUsage != nil {
		staticTotal = int64(staticUsage.TotalTokenCount)
		staticPrompt = staticUsage.PromptTokenCount
		staticToolUse = staticUsage.ToolUsePromptTokenCount
		staticCached = staticUsage.CachedContentTokenCount
		staticCandidates = staticUsage.CandidatesTokenCount
		staticThoughts = staticUsage.ThoughtsTokenCount
	}

	tokenDeltaPct := telemetry.TokenReductionPct(agenticTotal, staticTotal)

	headerStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(ColorWhite).
		Background(ColorGeminiBlue).
		Align(lipgloss.Center).
		Padding(0, 1)

	baseCellStyle := lipgloss.NewStyle().Padding(0, 1)
	zebraStyle := baseCellStyle.Background(ColorZebraBg)

	tbl := table.New().
		Border(lipgloss.RoundedBorder()).
		BorderStyle(lipgloss.NewStyle().Foreground(ColorGeminiBlue)).
		Headers("Performance Metric", "Agentic Video", "Static (1 FPS)", "Delta / Observation").
		StyleFunc(func(row, col int) lipgloss.Style {
			if row == table.HeaderRow {
				return headerStyle
			}
			style := baseCellStyle
			if row%2 == 0 {
				style = zebraStyle
			}
			switch col {
			case 0:
				return style.Bold(true).Foreground(ColorWhite)
			case 1:
				return style.Foreground(ColorGeminiCyan).Align(lipgloss.Right)
			case 2:
				return style.Foreground(ColorWarning).Align(lipgloss.Right)
			case 3:
				if row == 0 {
					return style.Foreground(ColorSuccess).Bold(true)
				}
				return style.Foreground(ColorWhite)
			default:
				return style
			}
		})

	totalDeltaStr := fmt.Sprintf("%+.1f%% net spend", tokenDeltaPct)
	if tokenDeltaPct > 0 {
		totalDeltaStr = fmt.Sprintf("🟢 %+.1f%% reduction", tokenDeltaPct)
	}

	promptDeltaStr := fmt.Sprintf("%+d input tokens", agenticPrompt-staticPrompt)
	candDeltaStr := fmt.Sprintf("%+d output tokens", agenticCandidates-staticCandidates)
	latDeltaStr := fmt.Sprintf("%v diff", (agenticDuration - staticDuration).Round(time.Millisecond))

	agenticToolStr := fmt.Sprintf("%d (dynamic frames)", agenticToolUse)
	if agenticToolDetails != "" {
		agenticToolStr = fmt.Sprintf("%d (%s)", agenticToolUse, agenticToolDetails)
	}

	tbl.Row(
		"Total Consumed Tokens",
		fmt.Sprintf("%d", agenticTotal),
		fmt.Sprintf("%d", staticTotal),
		totalDeltaStr,
	)
	tbl.Row(
		"Prompt Tokens (Input)",
		fmt.Sprintf("%d (text only)", agenticPrompt),
		fmt.Sprintf("%d (all frames)", staticPrompt),
		promptDeltaStr,
	)
	tbl.Row(
		"Tool-Use Tokens (load_video)",
		agenticToolStr,
		fmt.Sprintf("%d", staticToolUse),
		"targeted chunk loading",
	)
	if agenticCached > 0 || staticCached > 0 {
		tbl.Row(
			"Cached Tokens (Implicit)",
			fmt.Sprintf("%d", agenticCached),
			fmt.Sprintf("%d", staticCached),
			"multi-hop context reuse",
		)
	}
	tbl.Row(
		"Candidate Tokens (Output)",
		fmt.Sprintf("%d", agenticCandidates),
		fmt.Sprintf("%d", staticCandidates),
		candDeltaStr,
	)
	tbl.Row(
		"Reasoning Thoughts Tokens",
		fmt.Sprintf("%d (planning)", agenticThoughts),
		fmt.Sprintf("%d", staticThoughts),
		"Think ➔ Act navigation",
	)
	tbl.Row(
		"Latency (Wall Clock)",
		fmt.Sprintf("%v", agenticDuration.Round(time.Millisecond)),
		fmt.Sprintf("%v", staticDuration.Round(time.Millisecond)),
		latDeltaStr,
	)

	title := SectionHeader.Render("⚡ PERFORMANCE BENCHMARK: AGENTIC VIDEO vs. STATIC (1 FPS) INGESTION")
	footer := MutedStyle.Render("💡 Insight: In Agentic mode, prompt tokens contain 0 video frames upfront. Targeted video/transcript chunks\n   are fetched on-demand via load_video (Tool-Use Tokens) guided by Think ➔ Act reasoning.")

	return lipgloss.JoinVertical(lipgloss.Left, title, tbl.Render(), footer)
}

// RenderMultiModelTable renders a performance matrix comparing multiple Gemini models on the same video.
func RenderMultiModelTable(results []runner.ModelBenchmarkResult) string {
	if len(results) == 0 {
		return ""
	}

	headerStyle := lipgloss.NewStyle().
		Bold(true).
		Foreground(ColorWhite).
		Background(ColorGeminiBlue).
		Align(lipgloss.Center).
		Padding(0, 1)

	baseCellStyle := lipgloss.NewStyle().Padding(0, 1)
	zebraStyle := baseCellStyle.Background(ColorZebraBg)

	headers := []string{"Performance Metric"}
	for _, res := range results {
		headers = append(headers, res.ModelID)
	}

	tbl := table.New().
		Border(lipgloss.RoundedBorder()).
		BorderStyle(lipgloss.NewStyle().Foreground(ColorGeminiBlue)).
		Headers(headers...).
		StyleFunc(func(row, col int) lipgloss.Style {
			if row == table.HeaderRow {
				return headerStyle
			}
			style := baseCellStyle
			if row%2 == 0 {
				style = zebraStyle
			}
			if col == 0 {
				return style.Bold(true).Foreground(ColorWhite)
			}
			return style.Align(lipgloss.Right)
		})

	// Row 1: Status
	statusRow := []string{"Execution Status"}
	for _, r := range results {
		if r.Error != nil {
			statusRow = append(statusRow, "❌ Failed")
		} else {
			statusRow = append(statusRow, "✅ Completed")
		}
	}
	tbl.Row(statusRow...)

	// Row 2: Latency
	latencyRow := []string{"Latency (Wall Clock)"}
	for _, r := range results {
		if r.Error != nil {
			latencyRow = append(latencyRow, "—")
		} else {
			latencyRow = append(latencyRow, fmt.Sprintf("%v", r.Duration.Round(time.Millisecond)))
		}
	}
	tbl.Row(latencyRow...)

	// Row 3: Total Tokens
	totalTokRow := []string{"Total Consumed Tokens"}
	for _, r := range results {
		if r.Result != nil && r.Result.Usage != nil {
			totalTokRow = append(totalTokRow, fmt.Sprintf("%d", r.Result.Usage.TotalTokenCount))
		} else {
			totalTokRow = append(totalTokRow, "—")
		}
	}
	tbl.Row(totalTokRow...)

	// Row 4: Prompt Tokens
	promptTokRow := []string{"Prompt Tokens (Input)"}
	for _, r := range results {
		if r.Result != nil && r.Result.Usage != nil {
			promptTokRow = append(promptTokRow, fmt.Sprintf("%d (text only)", r.Result.Usage.PromptTokenCount))
		} else {
			promptTokRow = append(promptTokRow, "—")
		}
	}
	tbl.Row(promptTokRow...)

	// Row 5: Tool-Use Tokens
	toolTokRow := []string{"Tool-Use Tokens (load_video)"}
	hasCached := false
	for _, r := range results {
		if r.Result != nil && r.Result.Usage != nil {
			if r.Result.Usage.CachedContentTokenCount > 0 {
				hasCached = true
			}
			details := telemetry.FormatModalityDetails(r.Result.Usage.ToolUsePromptTokensDetails)
			if details != "" {
				toolTokRow = append(toolTokRow, fmt.Sprintf("%d (%s)", r.Result.Usage.ToolUsePromptTokenCount, details))
			} else {
				toolTokRow = append(toolTokRow, fmt.Sprintf("%d", r.Result.Usage.ToolUsePromptTokenCount))
			}
		} else {
			toolTokRow = append(toolTokRow, "—")
		}
	}
	tbl.Row(toolTokRow...)

	// Optional Row: Cached Tokens
	if hasCached {
		cacheTokRow := []string{"Cached Tokens (Implicit)"}
		for _, r := range results {
			if r.Result != nil && r.Result.Usage != nil {
				cacheTokRow = append(cacheTokRow, fmt.Sprintf("%d", r.Result.Usage.CachedContentTokenCount))
			} else {
				cacheTokRow = append(cacheTokRow, "—")
			}
		}
		tbl.Row(cacheTokRow...)
	}

	// Row 6: Candidate Tokens
	candTokRow := []string{"Candidate Output Tokens"}
	for _, r := range results {
		if r.Result != nil && r.Result.Usage != nil {
			candTokRow = append(candTokRow, fmt.Sprintf("%d", r.Result.Usage.CandidatesTokenCount))
		} else {
			candTokRow = append(candTokRow, "—")
		}
	}
	tbl.Row(candTokRow...)

	// Row 7: Reasoning Thoughts
	thoughtTokRow := []string{"Reasoning Thoughts Tokens"}
	for _, r := range results {
		if r.Result != nil && r.Result.Usage != nil {
			thoughtTokRow = append(thoughtTokRow, fmt.Sprintf("%d (planning)", r.Result.Usage.ThoughtsTokenCount))
		} else {
			thoughtTokRow = append(thoughtTokRow, "—")
		}
	}
	tbl.Row(thoughtTokRow...)

	title := SectionHeader.Render("🏎️  MULTI-MODEL BENCHMARK MATRIX (Agentic Video Understanding)")
	footer := MutedStyle.Render("💡 Cross-Model Analysis: Newer generations (e.g., gemini-3.8-flash, gemini-4-argon) optimize timeline\n   exploration efficiency, reducing tool-use and thoughts token budgets while improving answer accuracy.")

	return lipgloss.JoinVertical(lipgloss.Left, title, tbl.Render(), footer)
}
