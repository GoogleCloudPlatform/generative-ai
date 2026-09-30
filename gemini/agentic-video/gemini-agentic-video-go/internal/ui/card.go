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
	"strings"
	"time"

	"github.com/charmbracelet/lipgloss"
	"google.golang.org/genai"
)

// RenderBanner creates a styled application header card.
func RenderBanner(model, backend, project, location string) string {
	title := TitleStyle.Render(" ✦ GEMINI AGENTIC VIDEO ✦ ")
	sub := SubtitleStyle.Render("Go SDK Reference (google.golang.org/genai)")

	var lines []string
	lines = append(lines, title+" "+sub)
	lines = append(lines, MutedStyle.Render("Engine:   ")+BoldWhite.Render(model))
	lines = append(lines, MutedStyle.Render("Backend:  ")+CyanStyle.Render(strings.ToUpper(backend)))
	if backend != "gemini" && project != "" {
		lines = append(lines, MutedStyle.Render("Project:  ")+BoldWhite.Render(project)+"  "+MutedStyle.Render("Region: ")+CyanStyle.Render(location))
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return HeaderBox.Render(content)
}

// RenderTelemetryCard formats token usage and latency into a structured card.
func RenderTelemetryCard(usage *genai.GenerateContentResponseUsageMetadata, mode genai.MediaProcessing, duration time.Duration) string {
	header := SubtitleStyle.Render("⚡ Execution Telemetry & Cost Breakdown")
	modeBadge := RenderModeBadge(mode)

	durStr := GreenStyle.Render(fmt.Sprintf("%v", duration.Round(time.Millisecond)))
	durLine := fmt.Sprintf("  • Duration:            %s", durStr)

	if usage == nil {
		content := lipgloss.JoinVertical(lipgloss.Left, header+" "+modeBadge, durLine)
		return CardBox.Render(content)
	}

	totalTok := BoldWhite.Render(fmt.Sprintf("%d", usage.TotalTokenCount))
	promptTokStr := fmt.Sprintf("%d (text prompt only; 0 video frames)", usage.PromptTokenCount)
	if mode == genai.MediaProcessingStatic {
		promptTokStr = fmt.Sprintf("%d (includes 100%% of video frames at 1 FPS)", usage.PromptTokenCount)
	}
	promptTok := MutedStyle.Render(promptTokStr)

	candTok := BoldWhite.Render(fmt.Sprintf("%d", usage.CandidatesTokenCount))

	var lines []string
	lines = append(lines, header+" "+modeBadge)
	lines = append(lines, durLine)
	lines = append(lines, fmt.Sprintf("  • Total Consumed:      %s", totalTok))
	lines = append(lines, fmt.Sprintf("  • Prompt Tokens:       %s", promptTok))
	lines = append(lines, fmt.Sprintf("  • Candidate Output:    %s", candTok))

	if usage.ThoughtsTokenCount > 0 {
		thoughtTokStr := fmt.Sprintf("%d (dynamic frame inspection via Think ➔ Act)", usage.ThoughtsTokenCount)
		if mode == genai.MediaProcessingStatic {
			thoughtTokStr = fmt.Sprintf("%d", usage.ThoughtsTokenCount)
		}
		lines = append(lines, fmt.Sprintf("  • Reasoning Thoughts:  %s", CyanStyle.Render(thoughtTokStr)))
	}

	content := lipgloss.JoinVertical(lipgloss.Left, lines...)
	return CardBox.Render(content)
}
