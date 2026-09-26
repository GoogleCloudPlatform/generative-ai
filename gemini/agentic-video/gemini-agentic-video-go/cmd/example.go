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

// exampleCmd represents the example command
var exampleCmd = &cobra.Command{
	Use:   "example [id|all|list]",
	Short: "Run or list built-in tutorial scenarios (1-6)",
	Long: `Run or inspect preset scenarios illustrating agentic video capabilities,
including YouTube long-form Q&A, static baseline comparison, GCS trail-cam
analysis, YouTube Shorts, multi-video synthesis, and multi-turn conversations.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx := cmd.Context()

		target := "1"
		if len(args) > 0 {
			target = strings.ToLower(args[0])
		}

		if target == "list" {
			printCatalog()
			return nil
		}

		client, err := InitClient(ctx)
		if err != nil {
			return err
		}

		if target == "all" {
			var errs []error
			for _, sc := range catalog.Scenarios {
				if err := runScenario(ctx, client, sc); err != nil {
					fmt.Fprintf(os.Stderr, "Scenario %d failed: %v\n", sc.ID, err)
					errs = append(errs, fmt.Errorf("scenario %d (%s): %w", sc.ID, sc.Name, err))
				}
			}
			return errors.Join(errs...)
		}

		id, err := strconv.Atoi(target)
		if err != nil {
			return fmt.Errorf("invalid example ID %q; use 1-%d, 'all', or 'list'", target, len(catalog.Scenarios))
		}

		sc, err := catalog.Find(id)
		if err != nil {
			return err
		}

		return runScenario(ctx, client, *sc)
	},
}

func init() {
	RootCmd.AddCommand(exampleCmd)
}

func printCatalog() {
	fmt.Println(ui.RenderCatalogTable(catalog.Scenarios))
	fmt.Println()
}

func runScenario(ctx context.Context, client *genai.Client, sc catalog.Scenario) error {
	fmt.Printf("-----------------------------------------------------------------\n")
	fmt.Printf("Scenario %d: %s\n", sc.ID, sc.Title)
	fmt.Printf("Description: %s\n", sc.Description)
	if sc.VideoURI != "" {
		fmt.Printf("Video URI:   %s\n", sc.VideoURI)
	}
	if len(sc.MultiVideos) > 0 {
		fmt.Printf("Videos (%d):  %s\n", len(sc.MultiVideos), strings.Join(sc.MultiVideos, ", "))
	}
	fmt.Printf("Thinking:    %s\n", sc.ThinkingLevel)
	if sc.Prompt != "" {
		fmt.Printf("Prompt:      %q\n", sc.Prompt)
	}
	fmt.Printf("-----------------------------------------------------------------\n\n")

	// Multi-turn scenario branch
	if len(sc.MultiTurns) > 0 {
		_, err := runner.ExecuteMultiTurn(ctx, client, modelFlag, sc.VideoURI, sc.MultiTurns, sc.ThinkingLevel)
		return err
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
		res, err := runner.ExecuteMultiVideo(ctx, client, runner.MultiVideoRequest{
			ModelID:       modelFlag,
			Videos:        vInputs,
			Prompt:        sc.Prompt,
			ThinkingLevel: sc.ThinkingLevel,
		})
		if err != nil {
			return err
		}
		fmt.Println("--- Model Response ---")
		fmt.Println(res.Text)
		fmt.Println("----------------------")
		fmt.Println(ui.RenderTelemetryCard(res.Usage, res.Mode, res.Duration))
		return nil
	}

	// Single video scenario branch
	res, err := runner.Execute(ctx, client, runner.Request{
		ModelID:       modelFlag,
		VideoURI:      sc.VideoURI,
		Prompt:        sc.Prompt,
		Mode:          sc.Mode,
		ThinkingLevel: sc.ThinkingLevel,
	})
	if err != nil {
		return err
	}

	fmt.Println("--- Model Response ---")
	fmt.Println(res.Text)
	fmt.Println("----------------------")
	fmt.Println(ui.RenderTelemetryCard(res.Usage, res.Mode, res.Duration))
	return nil
}
