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
	mvVideo1   string
	mvMode1    string
	mvVideo2   string
	mvMode2    string
	mvPrompt   string
	mvThinking string
)

// multivideoCmd represents the multivideo command
var multivideoCmd = &cobra.Command{
	Use:   "multivideo",
	Short: "Compare multiple videos in a single prompt",
	Long: `Demonstrates cross-video comparative synthesis within a single prompt,
supporting mixed processing modes (e.g. Video 1 Agentic + Video 2 Static)
while staying comfortably within token limits.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx := cmd.Context()
		client, err := InitClient(ctx)
		if err != nil {
			return err
		}

		mode1 := runner.ParseProcessingMode(mvMode1)
		mode2 := runner.ParseProcessingMode(mvMode2)
		thinking := runner.ParseThinkingLevel(mvThinking)

		fmt.Printf("-----------------------------------------------------------------\n")
		fmt.Printf("Multi-Video Comparative Synthesis\n")
		fmt.Printf("Video 1:     %s (mode: %s)\n", mvVideo1, mode1)
		fmt.Printf("Video 2:     %s (mode: %s)\n", mvVideo2, mode2)
		fmt.Printf("Thinking:    %s\n", thinking)
		fmt.Printf("Prompt:      %q\n", mvPrompt)
		fmt.Printf("-----------------------------------------------------------------\n\n")

		videos := []runner.VideoInput{
			{URI: mvVideo1, Mode: mode1},
			{URI: mvVideo2, Mode: mode2},
		}

		res, err := runner.ExecuteMultiVideo(ctx, client, runner.MultiVideoRequest{
			ModelID:       modelFlag,
			Videos:        videos,
			Prompt:        mvPrompt,
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
	RootCmd.AddCommand(multivideoCmd)

	multivideoCmd.Flags().StringVar(&mvVideo1, "video1", "https://www.youtube.com/shorts/y-mrGw1wW8E", "First video URI")
	multivideoCmd.Flags().StringVar(&mvMode1, "mode1", "agentic", "Processing mode for video 1: 'agentic' or 'static'")
	multivideoCmd.Flags().StringVar(&mvVideo2, "video2", "https://storage.googleapis.com/generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4", "Second video URI")
	multivideoCmd.Flags().StringVar(&mvMode2, "mode2", "agentic", "Processing mode for video 2: 'agentic' or 'static'")
	multivideoCmd.Flags().StringVar(&mvPrompt, "prompt", "Compare the visual setting, pacing, and subject matter between these two videos.", "Comparative prompt")
	multivideoCmd.Flags().StringVar(&mvThinking, "thinking", "medium", "Thinking level: 'low', 'medium', or 'high'")
}
