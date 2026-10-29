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

package cmd

import (
	"fmt"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/runner"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/ui"
	"github.com/spf13/cobra"
)

var (
	mvVideo1       string
	mvMode1        string
	mvVideo2       string
	mvMode2        string
	mvPrompt       string
	mvThinking     string
	mvShowThoughts bool
)

// multivideoCmd represents the multivideo command.
var multivideoCmd = &cobra.Command{
	Use:     "multivideo",
	GroupID: groupExecution,
	Short:   "Compare multiple videos in a single prompt",
	Long: `Demonstrates cross-video comparative synthesis within a single prompt,
supporting mixed processing modes (e.g. Video 1 Agentic + Video 2 Static)
while staying comfortably within token limits.`,
	Example: `  # Run default multi-video comparison (YouTube Short + GCS Trailcam)
  gemini-agentic-video-go multivideo

  # Mix Agentic mode on Video 1 with Static mode on Video 2 using Gemini 4 Argon
  gemini-agentic-video-go multivideo --model gemini-4-argon --mode1 agentic --mode2 static

  # Emit structured JSON output
  gemini-agentic-video-go multivideo --json`,
	RunE: func(cmd *cobra.Command, args []string) error {
		mode1, err := runner.ParseProcessingModeE(mvMode1)
		if err != nil {
			return err
		}
		mode2, err := runner.ParseProcessingModeE(mvMode2)
		if err != nil {
			return err
		}
		thinking, err := runner.ParseThinkingLevelE(mvThinking)
		if err != nil {
			return err
		}
		if err := runner.ValidateThinkingLevel(modelFlag, thinking); err != nil {
			return err
		}

		ctx, cancel := withCommandTimeout(cmd.Context())
		defer cancel()

		genaiClient, err := InitClient(ctx)
		if err != nil {
			return err
		}

		if !jsonFlag {
			fmt.Printf("-----------------------------------------------------------------\n")
			fmt.Printf("Multi-Video Comparative Synthesis\n")
			fmt.Printf("  %s %s\n", ui.RenderVideoBadge(1, string(mode1)), runner.NormalizeVideoURI(mvVideo1))
			fmt.Printf("  %s %s\n", ui.RenderVideoBadge(2, string(mode2)), runner.NormalizeVideoURI(mvVideo2))
			fmt.Printf("Thinking:    %s\n", ui.RenderThinkingBadge(thinking))
			fmt.Printf("Prompt:      %q\n", mvPrompt)
			fmt.Printf("-----------------------------------------------------------------\n\n")
		}

		videos := []runner.VideoInput{
			{URI: mvVideo1, Mode: mode1},
			{URI: mvVideo2, Mode: mode2},
		}

		result, err := runner.ExecuteMultiVideo(ctx, genaiClient, runner.MultiVideoRequest{
			ModelID:         modelFlag,
			Videos:          videos,
			Prompt:          mvPrompt,
			ThinkingLevel:   thinking,
			IncludeThoughts: mvShowThoughts,
		})
		if err != nil {
			return err
		}

		if jsonFlag {
			return writeJSON(result)
		}

		if mvShowThoughts {
			if card := ui.RenderThoughtsCard(result.Thoughts, result.ToolHops); card != "" {
				fmt.Println(card)
			}
		}
		fmt.Println("--- Model Response ---")
		fmt.Println(result.Text)
		fmt.Println("----------------------")
		fmt.Println(ui.RenderTelemetryCard(result.Usage, result.Mode, result.Duration))
		return nil
	},
}

func init() {
	RootCmd.AddCommand(multivideoCmd)

	multivideoCmd.Flags().StringVar(&mvVideo1, "video1", "https://www.youtube.com/shorts/y-mrGw1wW8E", "First video URI")
	multivideoCmd.Flags().StringVar(&mvMode1, "mode1", "agentic", "Processing mode for video 1: 'agentic' or 'static'")
	multivideoCmd.Flags().StringVar(&mvVideo2, "video2", "gs://generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4", "Second video URI")
	multivideoCmd.Flags().StringVar(&mvMode2, "mode2", "agentic", "Processing mode for video 2: 'agentic' or 'static'")
	multivideoCmd.Flags().StringVar(&mvPrompt, "prompt", "Compare the visual setting, pacing, and subject matter between these two videos.", "Comparative prompt")
	multivideoCmd.Flags().StringVar(&mvThinking, "thinking", "medium", "Thinking level: 'low', 'medium', or 'high'")
	multivideoCmd.Flags().BoolVar(&mvShowThoughts, "show-thoughts", false, "Display intermediate Think ➔ Act reasoning hops (X-Ray trace)")
}
