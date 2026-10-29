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
	mtVideoURI string
	mtThinking string
)

// multiturnCmd represents the multiturn command.
var multiturnCmd = &cobra.Command{
	Use:     "multiturn",
	GroupID: groupExecution,
	Short:   "Demonstrate multi-turn conversation with video context preservation",
	Long: `Demonstrates sequential conversational question-answering across multiple
turns while maintaining video timeline navigation state and ThoughtSignatures
without re-ingesting frames.`,
	Example: `  # Run the default 3-turn dialogue on the 54m Alphabet Earnings Call
  gemini-agentic-video-go multiturn

  # Run multi-turn dialogue with Gemini 4 Argon
  gemini-agentic-video-go multiturn --model gemini-4-argon

  # Emit structured JSON array of all turn results
  gemini-agentic-video-go multiturn --json`,
	RunE: func(cmd *cobra.Command, args []string) error {
		thinking, err := runner.ParseThinkingLevelE(mtThinking)
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

		turns := []string{
			"What were the key revenue figures mentioned in the first 5 minutes?",
			"Who was the speaker during those remarks and what role do they hold?",
			"Did they mention anything about AI or Gemini during that timeframe?",
		}

		if !jsonFlag {
			fmt.Printf("-----------------------------------------------------------------\n")
			fmt.Printf("Multi-Turn Video Dialogue\n")
			fmt.Printf("Video URI:   %s\n", runner.NormalizeVideoURI(mtVideoURI))
			fmt.Printf("Thinking:    %s\n", ui.RenderThinkingBadge(thinking))
			fmt.Printf("Turns:       %d questions\n", len(turns))
			fmt.Printf("-----------------------------------------------------------------\n\n")
		}

		var turnCallback runner.MultiTurnCallback
		if !jsonFlag {
			turnCallback = func(turnIndex, total int, prompt string, result *runner.Result) {
				fmt.Printf("\n%s %q\n", ui.RenderTurnBadge(turnIndex, total), prompt)
				fmt.Println("--- Response ---")
				fmt.Println(result.Text)
				fmt.Println("----------------")
				fmt.Println(ui.RenderTelemetryCard(result.Usage, result.Mode, result.Duration))
			}
		}

		results, err := runner.ExecuteMultiTurnWithCallback(ctx, genaiClient, modelFlag, mtVideoURI, turns, thinking, turnCallback)
		if err != nil {
			return err
		}
		if jsonFlag {
			return writeJSON(results)
		}
		return nil
	},
}

func init() {
	RootCmd.AddCommand(multiturnCmd)

	multiturnCmd.Flags().StringVarP(&mtVideoURI, "video", "v", "https://www.youtube.com/watch?v=LzExSq9DU9w", "Video URI for multi-turn dialogue")
	multiturnCmd.Flags().StringVar(&mtThinking, "thinking", "medium", "Thinking level: 'low', 'medium', or 'high'")
}
