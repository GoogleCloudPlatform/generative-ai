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
	runVideoURI string
	runPrompt   string
	runMode     string
	runThinking string
	runMIME     string
)

// runCmd represents the run command
var runCmd = &cobra.Command{
	Use:   "run",
	Short: "Execute an ad-hoc video understanding query",
	Long: `Run an ad-hoc query against any YouTube or Google Cloud Storage video
with customizable processing mode ('agentic' or 'static') and thinking level.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		if runVideoURI == "" {
			return fmt.Errorf("--video flag is required")
		}

		ctx := cmd.Context()
		client, err := InitClient(ctx)
		if err != nil {
			return err
		}

		mode := runner.ParseProcessingMode(runMode)
		thinking := runner.ParseThinkingLevel(runThinking)

		fmt.Printf("-----------------------------------------------------------------\n")
		fmt.Printf("Custom Video Query\n")
		fmt.Printf("Video URI:   %s\n", runVideoURI)
		fmt.Printf("MIME Type:   %s\n", runMIME)
		fmt.Printf("Mode:        %s\n", mode)
		fmt.Printf("Thinking:    %s\n", thinking)
		fmt.Printf("Prompt:      %q\n", runPrompt)
		fmt.Printf("-----------------------------------------------------------------\n\n")

		res, err := runner.Execute(ctx, client, runner.Request{
			ModelID:       modelFlag,
			VideoURI:      runVideoURI,
			MIMEType:      runMIME,
			Prompt:        runPrompt,
			Mode:          mode,
			ThinkingLevel: thinking,
		})
		if err != nil {
			return err
		}

		fmt.Println("--- Model Response ---")
		fmt.Println(res.Text)
		fmt.Println("----------------------")
		fmt.Println(ui.RenderTelemetryCard(res.Usage, res.Mode, res.Duration))
		return nil
	},
}

func init() {
	RootCmd.AddCommand(runCmd)

	runCmd.Flags().StringVarP(&runVideoURI, "video", "v", "", "Video URI (YouTube URL, gs:// or https:// GCS URI) [required]")
	runCmd.Flags().StringVar(&runPrompt, "prompt", "Describe this video in detail with timestamps.", "Prompt question or instruction")
	runCmd.Flags().StringVar(&runMode, "mode", "agentic", "Processing mode: 'agentic' or 'static'")
	runCmd.Flags().StringVar(&runThinking, "thinking", "medium", "Thinking level: 'low', 'medium', or 'high'")
	runCmd.Flags().StringVar(&runMIME, "mime", "video/mp4", "Video MIME type (e.g. video/mp4, video/webm, video/mov)")
}
