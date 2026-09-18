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
// Package catalog maintains a registry of demonstration scenarios for Agentic Video.
package catalog

import (
	"fmt"

	"google.golang.org/genai"
)

// Scenario describes a preset demonstration scenario.
type Scenario struct {
	ID            int
	Name          string
	Title         string
	Description   string
	VideoURI      string
	Prompt        string
	Mode          genai.MediaProcessing
	ThinkingLevel genai.ThinkingLevel
	MultiTurns    []string
	MultiVideos   []string
}

// Scenarios is the master registry of built-in agentic video scenarios.
var Scenarios = []Scenario{
	{
		ID:            1,
		Name:          "youtube-agentic",
		Title:         "Agentic Video Understanding (YouTube Long-form)",
		Description:   "Dynamic timeline navigation & transcript triage on an Alphabet earnings call.",
		VideoURI:      "https://www.youtube.com/watch?v=LzExSq9DU9w",
		Prompt:        "What were the key revenue figures mentioned by the presenter, and at what timestamp do they appear?",
		Mode:          genai.MediaProcessingAgentic,
		ThinkingLevel: genai.ThinkingLevelMedium,
	},
	{
		ID:            2,
		Name:          "youtube-static",
		Title:         "Static Video Processing Comparison (YouTube Long-form)",
		Description:   "Runs the exact same query with static 1 FPS ingestion for direct latency/token benchmarking.",
		VideoURI:      "https://www.youtube.com/watch?v=LzExSq9DU9w",
		Prompt:        "What were the key revenue figures mentioned by the presenter, and at what timestamp do they appear?",
		Mode:          genai.MediaProcessingStatic,
		ThinkingLevel: genai.ThinkingLevelMedium,
	},
	{
		ID:            3,
		Name:          "trailcam",
		Title:         "Detailed Timestamp-Based Descriptions (GCS Video)",
		Description:   "High-thinking visual analysis on a wildlife trail-cam video stored in Google Cloud Storage.",
		VideoURI:      "https://storage.googleapis.com/generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4",
		Prompt:        "Describe what happens in this video in detail, with timestamps.",
		Mode:          genai.MediaProcessingAgentic,
		ThinkingLevel: genai.ThinkingLevelHigh,
	},
	{
		ID:            4,
		Name:          "shorts",
		Title:         "YouTube Shorts Video Understanding",
		Description:   "Rapid visual and audio explanation of short-form vertical cricket video.",
		VideoURI:      "https://www.youtube.com/shorts/y-mrGw1wW8E",
		Prompt:        "Explain this video",
		Mode:          genai.MediaProcessingAgentic,
		ThinkingLevel: genai.ThinkingLevelHigh,
	},
	{
		ID:            5,
		Name:          "multivideo",
		Title:         "Multi-Video Comparative Synthesis",
		Description:   "Demonstrates cross-video comparative analysis in a single prompt without blowing token context.",
		Prompt:        "Compare the visual setting, pacing, and subject matter between these two videos.",
		ThinkingLevel: genai.ThinkingLevelMedium,
		MultiVideos: []string{
			"https://www.youtube.com/shorts/y-mrGw1wW8E",
			"https://storage.googleapis.com/generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4",
		},
	},
	{
		ID:            6,
		Name:          "multiturn",
		Title:         "Multi-Turn Video Dialogue with Context Preservation",
		Description:   "Preserves navigated video context across follow-up conversational turns without re-uploading.",
		VideoURI:      "https://www.youtube.com/watch?v=LzExSq9DU9w",
		ThinkingLevel: genai.ThinkingLevelMedium,
		MultiTurns: []string{
			"What were the key revenue figures mentioned in the first 5 minutes?",
			"Who was the speaker during those remarks and what role do they hold?",
			"Did they mention anything about AI or Gemini during that timeframe?",
		},
	},
}

// Find returns a scenario matching the given numeric ID.
func Find(scenarioID int) (*Scenario, error) {
	for _, scenario := range Scenarios {
		if scenario.ID == scenarioID {
			return &scenario, nil
		}
	}
	return nil, fmt.Errorf("scenario %d not found (available: 1-%d)", scenarioID, len(Scenarios))
}
