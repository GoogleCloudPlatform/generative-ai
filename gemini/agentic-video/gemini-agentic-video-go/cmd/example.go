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
	"context"
	"errors"
	"fmt"
	"os"
	"strconv"
	"strings"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/catalog"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/runner"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/ui"
	"github.com/spf13/cobra"
	"google.golang.org/genai"
)

var exampleShowThoughts bool

// exampleCmd represents the example command.
var exampleCmd = &cobra.Command{
	Use:     "example [id|all|list]",
	GroupID: groupExecution,
	Short:   "Run or list built-in tutorial scenarios (1-6)",
	Long: `Run or inspect preset scenarios illustrating agentic video capabilities,
including YouTube long-form Q&A, static baseline comparison, GCS trail-cam
analysis, YouTube Shorts, multi-video synthesis, and multi-turn conversations.`,
	Example: `  # List all built-in tutorial scenarios
  gemini-agentic-video-go example list

  # Run Scenario 1 (54m Alphabet Earnings Call Q&A)
  gemini-agentic-video-go example 1

  # Run Scenario 3 (GCS Wildlife Trailcam) with Gemini 4 Argon and X-Ray thought trace
  gemini-agentic-video-go example 3 --model gemini-4-argon --show-thoughts

  # Output Scenario 4 results as structured JSON
  gemini-agentic-video-go example 4 --json`,
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx, cancel := withCommandTimeout(cmd.Context())
		defer cancel()

		target := "1"
		if len(args) > 0 {
			target = strings.ToLower(args[0])
		}

		if target == "list" {
			if jsonFlag {
				return writeJSON(catalog.Scenarios)
			}
			printCatalog()
			return nil
		}

		genaiClient, err := InitClient(ctx)
		if err != nil {
			return err
		}

		if target == "all" {
			var errs []error
			var allResults []any
			for _, sc := range catalog.Scenarios {
				result, err := executeScenario(ctx, genaiClient, sc)
				if err != nil {
					fmt.Fprintf(os.Stderr, "Scenario %d failed: %v\n", sc.ID, err)
					errs = append(errs, fmt.Errorf("scenario %d (%s): %w", sc.ID, sc.Name, err))
					continue
				}
				allResults = append(allResults, result)
			}
			if jsonFlag && len(allResults) > 0 {
				_ = writeJSON(allResults)
			}
			return errors.Join(errs...)
		}

		id, err := strconv.Atoi(target)
		if err != nil {
			return fmt.Errorf("invalid example ID %q (must be 1-%d, 'all', or 'list').\nHint: Run 'gemini-agentic-video-go example list' to view available scenarios", target, len(catalog.Scenarios))
		}

		sc, err := catalog.Find(id)
		if err != nil {
			return fmt.Errorf("%w.\nHint: Run 'gemini-agentic-video-go example list' to see valid scenario IDs (1-%d)", err, len(catalog.Scenarios))
		}

		result, err := executeScenario(ctx, genaiClient, *sc)
		if err != nil {
			return err
		}
		if jsonFlag {
			return writeJSON(result)
		}
		return nil
	},
}

func init() {
	RootCmd.AddCommand(exampleCmd)
	exampleCmd.Flags().BoolVar(&exampleShowThoughts, "show-thoughts", false, "Display intermediate Think ➔ Act reasoning hops (X-Ray trace)")
}

func printCatalog() {
	fmt.Println(ui.RenderCatalogTable(catalog.Scenarios))
	fmt.Println()
}

func executeScenario(ctx context.Context, genaiClient *genai.Client, sc catalog.Scenario) (any, error) {
	if !jsonFlag {
		fmt.Printf("-----------------------------------------------------------------\n")
		fmt.Printf("Scenario %d: %s\n", sc.ID, sc.Title)
		fmt.Printf("Description: %s\n", sc.Description)
		if sc.VideoURI != "" {
			fmt.Printf("Video URI:   %s\n", sc.VideoURI)
		}
		if len(sc.MultiVideos) > 0 {
			for i, v := range sc.MultiVideos {
				fmt.Printf("  %s %s\n", ui.RenderVideoBadge(i+1, string(sc.Mode)), v)
			}
		}
		fmt.Printf("Thinking:    %s\n", ui.RenderThinkingBadge(sc.ThinkingLevel))
		if sc.Prompt != "" {
			fmt.Printf("Prompt:      %q\n", sc.Prompt)
		}
		fmt.Printf("-----------------------------------------------------------------\n\n")
	}

	// Multi-turn scenario branch
	if len(sc.MultiTurns) > 0 {
		totalTurns := len(sc.MultiTurns)
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
		results, err := runner.ExecuteMultiTurnWithCallback(ctx, genaiClient, modelFlag, sc.VideoURI, sc.MultiTurns, sc.ThinkingLevel, turnCallback)
		if err != nil {
			return nil, fmt.Errorf("executing multi-turn scenario %d (%d turns): %w", sc.ID, totalTurns, err)
		}
		return results, nil
	}

	// Multi-video scenario branch
	if len(sc.MultiVideos) > 0 {
		var vInputs []runner.VideoInput
		for _, v := range sc.MultiVideos {
			vInputs = append(vInputs, runner.VideoInput{
				URI:  v,
				Mode: genai.MediaProcessingAgentic,
			})
		}
		result, err := runner.ExecuteMultiVideo(ctx, genaiClient, runner.MultiVideoRequest{
			ModelID:         modelFlag,
			Videos:          vInputs,
			Prompt:          sc.Prompt,
			ThinkingLevel:   sc.ThinkingLevel,
			IncludeThoughts: exampleShowThoughts,
		})
		if err != nil {
			return nil, err
		}
		if !jsonFlag {
			if exampleShowThoughts {
				if card := ui.RenderThoughtsCard(result.Thoughts, result.ToolHops); card != "" {
					fmt.Println(card)
				}
			}
			fmt.Println("--- Model Response ---")
			fmt.Println(result.Text)
			fmt.Println("----------------------")
			fmt.Println(ui.RenderTelemetryCard(result.Usage, result.Mode, result.Duration))
		}
		return result, nil
	}

	// Single video scenario branch
	result, err := runner.Execute(ctx, genaiClient, runner.Request{
		ModelID:         modelFlag,
		VideoURI:        sc.VideoURI,
		Prompt:          sc.Prompt,
		Mode:            sc.Mode,
		ThinkingLevel:   sc.ThinkingLevel,
		IncludeThoughts: exampleShowThoughts,
	})
	if err != nil {
		return nil, err
	}

	if !jsonFlag {
		if exampleShowThoughts {
			if card := ui.RenderThoughtsCard(result.Thoughts, result.ToolHops); card != "" {
				fmt.Println(card)
			}
		}
		fmt.Println("--- Model Response ---")
		fmt.Println(result.Text)
		fmt.Println("----------------------")
		fmt.Println(ui.RenderTelemetryCard(result.Usage, result.Mode, result.Duration))
	}
	return result, nil
}
