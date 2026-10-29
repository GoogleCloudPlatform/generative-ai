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
	runVideoURI     string
	runPrompt       string
	runMode         string
	runThinking     string
	runMIME         string
	runShowThoughts bool
	runStream       bool
)

// runCmd represents the run command.
var runCmd = &cobra.Command{
	Use:     "run",
	GroupID: groupExecution,
	Short:   "Execute an ad-hoc video understanding query",
	Long: `Run an ad-hoc query against any YouTube or Google Cloud Storage video
with customizable processing mode ('agentic' or 'static') and thinking level.`,
	Example: `  # Run an Agentic query on a YouTube Short with Gemini 4 Argon
  gemini-agentic-video-go run \
    --model gemini-4-argon \
    --video "https://www.youtube.com/shorts/y-mrGw1wW8E" \
    --prompt "List every distinct scene transition with timestamps."

  # Run a GCS video query with X-Ray thought trace and streaming output
  gemini-agentic-video-go run \
    --video "gs://generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4" \
    --show-thoughts --stream

  # Emit structured JSON output for an automated workflow
  gemini-agentic-video-go run \
    --video "https://www.youtube.com/shorts/y-mrGw1wW8E" --json`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if runVideoURI == "" {
			return fmt.Errorf("--video flag is required.\nHint: Pass --video <youtube-url-or-gs-uri> or run 'gemini-agentic-video-go example 1' for a preset scenario")
		}

		mode, err := runner.ParseProcessingModeE(runMode)
		if err != nil {
			return err
		}
		thinking, err := runner.ParseThinkingLevelE(runThinking)
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
			fmt.Printf("Custom Video Query\n")
			fmt.Printf("Video URI:   %s\n", runner.NormalizeVideoURI(runVideoURI))
			fmt.Printf("MIME Type:   %s\n", runMIME)
			fmt.Printf("Mode:        %s\n", ui.RenderModeBadge(mode))
			fmt.Printf("Thinking:    %s\n", ui.RenderThinkingBadge(thinking))
			fmt.Printf("Prompt:      %q\n", runPrompt)
			fmt.Printf("-----------------------------------------------------------------\n\n")
		}

		req := runner.Request{
			ModelID:         modelFlag,
			VideoURI:        runVideoURI,
			MIMEType:        runMIME,
			Prompt:          runPrompt,
			Mode:            mode,
			ThinkingLevel:   thinking,
			IncludeThoughts: runShowThoughts,
		}

		var result *runner.Result
		if runStream && !jsonFlag {
			fmt.Println("--- Streaming Model Response ---")
			result, err = runner.ExecuteStream(ctx, genaiClient, req, func(chunk string, isThought bool) {
				if !isThought {
					fmt.Print(chunk)
				}
			})
			fmt.Println("\n--------------------------------")
		} else {
			result, err = runner.Execute(ctx, genaiClient, req)
		}
		if err != nil {
			return err
		}

		if jsonFlag {
			return writeJSON(result)
		}

		if runShowThoughts {
			if card := ui.RenderThoughtsCard(result.Thoughts, result.ToolHops); card != "" {
				fmt.Println(card)
			}
		}
		if !runStream {
			fmt.Println("--- Model Response ---")
			fmt.Println(result.Text)
			fmt.Println("----------------------")
		}
		fmt.Println(ui.RenderTelemetryCard(result.Usage, result.Mode, result.Duration))
		return nil
	},
}

func init() {
	RootCmd.AddCommand(runCmd)

	runCmd.Flags().StringVarP(&runVideoURI, "video", "v", "", "Video URI (YouTube URL, gs:// or https:// GCS URI) [required]")
	_ = runCmd.MarkFlagRequired("video")
	runCmd.Flags().StringVar(&runPrompt, "prompt", "Describe this video in detail with timestamps.", "Prompt question or instruction")
	runCmd.Flags().StringVar(&runMode, "mode", "agentic", "Processing mode: 'agentic' or 'static'")
	runCmd.Flags().StringVar(&runThinking, "thinking", "medium", "Thinking level: 'low', 'medium', or 'high'")
	runCmd.Flags().StringVar(&runMIME, "mime", "video/mp4", "Video MIME type (e.g. video/mp4, video/webm, video/mov)")
	runCmd.Flags().BoolVar(&runShowThoughts, "show-thoughts", false, "Display intermediate Think ➔ Act reasoning hops (X-Ray trace)")
	runCmd.Flags().BoolVar(&runStream, "stream", false, "Stream response tokens in real time via GenerateContentStream")
}
