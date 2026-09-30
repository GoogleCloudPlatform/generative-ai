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

// Package ui provides terminal styling, banners, badges, and table renderers for the CLI.
// NOTE: None of these presentation styles are required by the Gemini API.
// For core Agentic Video SDK usage, see internal/runner and internal/telemetry.
package ui

import (
	"fmt"
	"strings"

	"github.com/charmbracelet/lipgloss"
	"google.golang.org/genai"
)

// Colors used across terminal UI components.
var (
	// ColorGeminiBlue is the Google/Gemini primary blue branding color.
	ColorGeminiBlue = lipgloss.Color("#4285F4")
	// ColorGeminiCyan is the Gemini sparkle cyan accent color.
	ColorGeminiCyan = lipgloss.Color("#00C4FF")
	// ColorAgenticPurple is the purple highlight representing agentic reasoning.
	ColorAgenticPurple = lipgloss.Color("#8E44AD")
	// ColorSuccess is the green color for completions and positive deltas.
	ColorSuccess = lipgloss.Color("#34A853")
	// ColorWarning is the amber color for static processing and warnings.
	ColorWarning = lipgloss.Color("#FBBC05")
	// ColorDanger is the red color for errors and failures.
	ColorDanger = lipgloss.Color("#EA4335")
	// ColorMuted is medium gray for secondary notes and labels.
	ColorMuted = lipgloss.Color("#70757A")
	// ColorDim is dark slate for minimal contrast elements.
	ColorDim = lipgloss.Color("#3C4043")
	// ColorWhite is pure white.
	ColorWhite = lipgloss.Color("#FFFFFF")
	// ColorZebraBg is the subtle dark background for alternating table rows.
	ColorZebraBg = lipgloss.Color("#1A1D24")
)

// UI and typography styles used across terminal renderers.
var (
	// TitleStyle formats application banners.
	TitleStyle = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorWhite).
			Background(ColorGeminiBlue).
			Padding(0, 1)

	// SubtitleStyle formats headers and card titles.
	SubtitleStyle = lipgloss.NewStyle().
			Foreground(ColorGeminiCyan).
			Bold(true)

	// HeaderBox defines the border container for the main banner.
	HeaderBox = lipgloss.NewStyle().
			Border(lipgloss.RoundedBorder()).
			BorderForeground(ColorGeminiBlue).
			Padding(0, 1).
			MarginBottom(1)

	// CardBox defines the container border for telemetry cards.
	CardBox = lipgloss.NewStyle().
		Border(lipgloss.RoundedBorder()).
		BorderForeground(ColorMuted).
		Padding(0, 1).
		MarginBottom(1)

	// SectionHeader formats section divider headers.
	SectionHeader = lipgloss.NewStyle().
			Bold(true).
			Foreground(ColorGeminiCyan).
			MarginTop(1).
			MarginBottom(0)

	// MutedStyle styles secondary text in medium gray.
	MutedStyle = lipgloss.NewStyle().Foreground(ColorMuted)
	// BoldWhite styles highlighted text in bold white.
	BoldWhite = lipgloss.NewStyle().Bold(true).Foreground(ColorWhite)
	// GreenStyle styles success messages in bold green.
	GreenStyle = lipgloss.NewStyle().Foreground(ColorSuccess).Bold(true)
	// CyanStyle styles accents in bold cyan.
	CyanStyle = lipgloss.NewStyle().Foreground(ColorGeminiCyan).Bold(true)

	// BadgeAgentic formats the AGENTIC mode badge.
	BadgeAgentic = lipgloss.NewStyle().Bold(true).Foreground(ColorWhite).Background(ColorAgenticPurple).Padding(0, 1)
	// BadgeStatic formats the STATIC mode badge.
	BadgeStatic = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#000000")).Background(ColorWarning).Padding(0, 1)
	// BadgeMultiVideo formats the MULTI-VIDEO mode badge.
	BadgeMultiVideo = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#000000")).Background(ColorGeminiCyan).Padding(0, 1)
	// BadgeMultiTurn formats the MULTI-TURN mode badge.
	BadgeMultiTurn = lipgloss.NewStyle().Bold(true).Foreground(ColorWhite).Background(ColorSuccess).Padding(0, 1)

	// BadgeThinkingHigh formats the high thinking level badge.
	BadgeThinkingHigh = lipgloss.NewStyle().Bold(true).Foreground(ColorWhite).Background(lipgloss.Color("#B02A37")).Padding(0, 1)
	// BadgeThinkingMedium formats the medium thinking level badge.
	BadgeThinkingMedium = lipgloss.NewStyle().Bold(true).Foreground(ColorWhite).Background(lipgloss.Color("#0D6EFD")).Padding(0, 1)
	// BadgeThinkingLow formats the low thinking level badge.
	BadgeThinkingLow = lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#000000")).Background(lipgloss.Color("#6C757D")).Padding(0, 1)
	// BadgeThinkingMinimal formats the minimal thinking level badge.
	BadgeThinkingMinimal = lipgloss.NewStyle().Bold(true).Foreground(ColorWhite).Background(ColorDim).Padding(0, 1)
)

// RenderModeBadge returns a styled Lipgloss badge for a media processing mode.
func RenderModeBadge(mode genai.MediaProcessing) string {
	if mode == genai.MediaProcessingStatic {
		return BadgeStatic.Render("STATIC (1 FPS)")
	}
	return BadgeAgentic.Render("AGENTIC")
}

// RenderScenarioTypeBadge returns a styled badge describing the scenario category.
func RenderScenarioTypeBadge(name string, mode genai.MediaProcessing, isMultiVideo, isMultiTurn bool) string {
	if isMultiVideo {
		return BadgeMultiVideo.Render("MULTI-VIDEO")
	}
	if isMultiTurn {
		return BadgeMultiTurn.Render("MULTI-TURN")
	}
	if mode == genai.MediaProcessingStatic {
		return BadgeStatic.Render("STATIC")
	}
	return BadgeAgentic.Render("AGENTIC")
}

// RenderThinkingBadge returns a styled badge for reasoning thinking level.
func RenderThinkingBadge(level genai.ThinkingLevel) string {
	switch level {
	case genai.ThinkingLevelHigh:
		return BadgeThinkingHigh.Render("THINKING: HIGH")
	case genai.ThinkingLevelLow:
		return BadgeThinkingLow.Render("THINKING: LOW")
	case genai.ThinkingLevelMinimal:
		return BadgeThinkingMinimal.Render("THINKING: MINIMAL")
	default:
		return BadgeThinkingMedium.Render("THINKING: MEDIUM")
	}
}

// RenderTurnBadge formats a conversational turn marker.
func RenderTurnBadge(turnNum, totalTurns int) string {
	label := fmt.Sprintf("Turn %d", turnNum)
	if totalTurns > 0 {
		label = fmt.Sprintf("Turn %d/%d", turnNum, totalTurns)
	}
	return lipgloss.NewStyle().Bold(true).Foreground(ColorWhite).Background(ColorAgenticPurple).Padding(0, 1).Render(label)
}

// RenderVideoBadge formats a multi-video index badge.
func RenderVideoBadge(index int, label string) string {
	text := fmt.Sprintf("Video %d", index)
	if label != "" {
		text = text + " (" + strings.ToUpper(label) + ")"
	}
	return lipgloss.NewStyle().Bold(true).Foreground(lipgloss.Color("#000000")).Background(ColorGeminiCyan).Padding(0, 1).Render(text)
}
