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
	"github.com/spf13/cobra"
)

var (
	mtVideoURI string
	mtThinking string
)

// multiturnCmd represents the multiturn command
var multiturnCmd = &cobra.Command{
	Use:   "multiturn",
	Short: "Demonstrate multi-turn conversation with video context preservation",
	Long: `Demonstrates sequential conversational question-answering across multiple
turns while maintaining video timeline navigation state without re-ingesting frames.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx := cmd.Context()
		client, err := InitClient(ctx)
		if err != nil {
			return err
		}

		thinking := runner.ParseThinkingLevel(mtThinking)

		turns := []string{
			"What were the key revenue figures mentioned in the first 5 minutes?",
			"Who was the speaker during those remarks and what role do they hold?",
			"Did they mention anything about AI or Gemini during that timeframe?",
		}

		fmt.Printf("-----------------------------------------------------------------\n")
		fmt.Printf("Multi-Turn Video Dialogue\n")
		fmt.Printf("Video URI:   %s\n", mtVideoURI)
		fmt.Printf("Thinking:    %s\n", thinking)
		fmt.Printf("Turns:       %d questions\n", len(turns))
		fmt.Printf("-----------------------------------------------------------------\n\n")

		_, err = runner.ExecuteMultiTurn(ctx, client, modelFlag, mtVideoURI, turns, thinking)
		return err
	},
}

func init() {
	RootCmd.AddCommand(multiturnCmd)

	multiturnCmd.Flags().StringVarP(&mtVideoURI, "video", "v", "https://www.youtube.com/watch?v=LzExSq9DU9w", "Video URI for multi-turn dialogue")
	multiturnCmd.Flags().StringVar(&mtThinking, "thinking", "medium", "Thinking level: 'low', 'medium', or 'high'")
}
