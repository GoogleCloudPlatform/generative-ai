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
	"strings"
	"time"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/runner"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/ui"
	"github.com/spf13/cobra"
	"google.golang.org/genai"
)

var (
	compareVideoURI   string
	comparePrompt     string
	compareThinking   string
	compareConcurrent bool
	compareModels     string
)

// compareCmd represents the compare command
var compareCmd = &cobra.Command{
	Use:   "compare",
	Short: "Benchmark processing modes (Agentic vs. Static) or models (3.6 vs 3.7 vs 3.8)",
	Long: `Executes side-by-side performance comparisons on the same video:

1. Mode Comparison (Default): Compares Agentic timeline navigation vs. Static 1 FPS
   frame ingestion on a single model (gemini-3.7-flash by default).
2. Model Comparison (--models): Compares multiple model generations (e.g. 3.6, 3.7, 3.8)
   running Agentic video understanding concurrently in parallel goroutines.`,
	RunE: func(cmd *cobra.Command, args []string) error {
		ctx := cmd.Context()
		client, err := InitClient(ctx)
		if err != nil {
			return err
		}

		thinking := runner.ParseThinkingLevel(compareThinking)

		// Multi-Model Benchmark branch
		modelsList := resolveModelsList(compareModels)
		if len(modelsList) > 1 {
			tracker := ui.NewMultiModelTracker(modelsList)
			tracker.Start()

			results := runner.ExecuteMultiModelBenchmark(ctx, client, modelsList, runner.Request{
				VideoURI:      compareVideoURI,
				Prompt:        comparePrompt,
				Mode:          genai.MediaProcessingAgentic,
				ThinkingLevel: thinking,
			}, func(mID string, done bool, res *runner.Result, err error) {
				tracker.Update(mID, done, res, err)
			})
			tracker.Stop()

			fmt.Println(ui.RenderMultiModelTable(results))
			return nil
		}

		// Single Model: Concurrent Mode Benchmark (Agentic vs Static)
		if compareConcurrent {
			tracker := ui.NewBenchmarkTracker(compareThinking)
			tracker.Start()

			benchRes := runner.ExecuteConcurrentBenchmark(ctx, client, runner.Request{
				ModelID:       modelFlag,
				VideoURI:      compareVideoURI,
				Prompt:        comparePrompt,
				ThinkingLevel: thinking,
			}, func(agenticDone, staticDone bool, aRes, sRes *runner.Result) {
				tracker.Update(agenticDone, staticDone, aRes, sRes)
			})

			tracker.SetErrors(benchRes.AgenticError, benchRes.StaticError)
			tracker.Stop()

			if benchRes.AgenticError != nil && benchRes.StaticError != nil {
				return fmt.Errorf("both benchmarks failed: agentic: %v; static: %v", benchRes.AgenticError, benchRes.StaticError)
			}
			if benchRes.AgenticError != nil {
				return fmt.Errorf("agentic benchmark failed: %w", benchRes.AgenticError)
			}
			if benchRes.StaticError != nil {
				return fmt.Errorf("static benchmark failed: %w", benchRes.StaticError)
			}

			aUsage := benchRes.AgenticResult.Usage
			sUsage := benchRes.StaticResult.Usage
			fmt.Println(ui.RenderBenchmarkTable(aUsage, sUsage, benchRes.AgenticResult.Duration, benchRes.StaticResult.Duration))
			return nil
		}

		// Sequential fallback
		fmt.Println(">>> Step 1/2: Executing with AGENTIC video processing...")
		aRes, err := runner.Execute(ctx, client, runner.Request{
			ModelID:       modelFlag,
			VideoURI:      compareVideoURI,
			Prompt:        comparePrompt,
			Mode:          genai.MediaProcessingAgentic,
			ThinkingLevel: thinking,
		})
		if err != nil {
			return fmt.Errorf("agentic run failed: %w", err)
		}
		fmt.Printf("    Agentic Run Complete (%v, %d tokens)\n\n",
			aRes.Duration.Round(time.Millisecond),
			totalTokens(aRes))

		fmt.Println(">>> Step 2/2: Executing with STATIC 1-FPS frame ingestion...")
		sRes, err := runner.Execute(ctx, client, runner.Request{
			ModelID:       modelFlag,
			VideoURI:      compareVideoURI,
			Prompt:        comparePrompt,
			Mode:          genai.MediaProcessingStatic,
			ThinkingLevel: thinking,
		})
		if err != nil {
			return fmt.Errorf("static run failed: %w", err)
		}
		fmt.Printf("    Static Run Complete (%v, %d tokens)\n\n",
			sRes.Duration.Round(time.Millisecond),
			totalTokens(sRes))

		fmt.Println(ui.RenderBenchmarkTable(aRes.Usage, sRes.Usage, aRes.Duration, sRes.Duration))
		return nil
	},
}

func totalTokens(res *runner.Result) int32 {
	if res != nil && res.Usage != nil {
		return res.Usage.TotalTokenCount
	}
	return 0
}

func resolveModelsList(flagVal string) []string {
	if flagVal == "" {
		return nil
	}
	raw := strings.Split(flagVal, ",")
	var resolved []string
	for _, item := range raw {
		item = strings.TrimSpace(item)
		if item == "" {
			continue
		}
		switch strings.ToLower(item) {
		case "flash", "all", "generations":
			return []string{"gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"}
		case "3.6", "gemini-3.6":
			resolved = append(resolved, "gemini-3.6-flash")
		case "3.7", "gemini-3.7":
			resolved = append(resolved, "gemini-3.7-flash")
		case "3.8", "gemini-3.8":
			resolved = append(resolved, "gemini-3.8-flash")
		default:
			resolved = append(resolved, item)
		}
	}
	return resolved
}

func init() {
	RootCmd.AddCommand(compareCmd)

	compareCmd.Flags().StringVarP(&compareVideoURI, "video", "v", "https://www.youtube.com/watch?v=LzExSq9DU9w", "Video URI for comparison benchmark")
	compareCmd.Flags().StringVar(&comparePrompt, "prompt", "What were the key revenue figures mentioned by the presenter, and at what timestamp do they appear?", "Prompt for comparison benchmark")
	compareCmd.Flags().StringVar(&compareThinking, "thinking", "medium", "Thinking level: 'low', 'medium', or 'high'")
	compareCmd.Flags().BoolVar(&compareConcurrent, "concurrent", true, "Execute Agentic and Static benchmarks concurrently in parallel goroutines with live telemetry")
	compareCmd.Flags().StringVar(&compareModels, "models", "", "Compare across multiple models (e.g. 'flash' or 'gemini-3.6-flash,gemini-3.7-flash,gemini-3.8-flash')")
}
