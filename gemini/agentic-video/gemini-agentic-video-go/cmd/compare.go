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

// compareCmd represents the compare command.
var compareCmd = &cobra.Command{
	Use:     "compare",
	GroupID: groupBenchmarking,
	Short:   "Benchmark processing modes (Agentic vs. Static) or models (3.6 vs 3.7 vs 3.8 vs 4-argon)",
	Long: `Executes side-by-side performance comparisons on the same video:

1. Mode Comparison (Default): Compares Agentic timeline navigation vs. Static 1 FPS
   frame ingestion on a single model (gemini-3.7-flash by default).
2. Model Comparison (--models): Compares multiple model generations (e.g. 3.6, 3.7, 3.8, 4-argon)
   running Agentic video understanding concurrently in parallel goroutines.`,
	Example: `  # Benchmark Agentic vs. Static 1-FPS concurrently on the default 54m earnings call
  gemini-agentic-video-go compare

  # Benchmark Agentic vs. Static on Gemini 4 Argon using a YouTube Short
  gemini-agentic-video-go compare --model gemini-4-argon --video "https://www.youtube.com/shorts/y-mrGw1wW8E"

  # Multi-model shootout across all generations (3.6, 3.7, 3.8, 4-argon)
  gemini-agentic-video-go compare --models all --video "https://www.youtube.com/shorts/y-mrGw1wW8E"

  # Multi-model shootout comparing 3.8 Flash vs. 4 Argon on GCS Trailcam
  gemini-agentic-video-go compare --models 3.8,argon \
    --video "gs://generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4" \
    --prompt "Create a timestamped log of every animal sighting."`,
	RunE: func(cmd *cobra.Command, args []string) error {
		thinking, err := runner.ParseThinkingLevelE(compareThinking)
		if err != nil {
			return err
		}

		ctx, cancel := withCommandTimeout(cmd.Context())
		defer cancel()

		genaiClient, err := InitClient(ctx)
		if err != nil {
			return err
		}

		// Multi-Model Benchmark branch
		modelsList := resolveModelsList(compareModels)
		if len(modelsList) > 1 {
			for _, mID := range modelsList {
				if err := runner.ValidateThinkingLevel(mID, thinking); err != nil {
					return err
				}
			}

			var tracker *ui.MultiModelTracker
			if !jsonFlag {
				tracker = ui.NewMultiModelTracker(modelsList)
				tracker.Start()
			}

			results := runner.ExecuteMultiModelBenchmark(ctx, genaiClient, modelsList, runner.Request{
				VideoURI:      compareVideoURI,
				Prompt:        comparePrompt,
				Mode:          genai.MediaProcessingAgentic,
				ThinkingLevel: thinking,
			}, func(mID string, done bool, result *runner.Result, err error) {
				if tracker != nil {
					tracker.Update(mID, done, result, err)
				}
			})
			if tracker != nil {
				tracker.Stop()
			}

			if jsonFlag {
				return writeJSON(results)
			}
			fmt.Println(ui.RenderMultiModelTable(results))
			return nil
		}

		if err := runner.ValidateThinkingLevel(modelFlag, thinking); err != nil {
			return err
		}

		// Single Model: Concurrent Mode Benchmark (Agentic vs Static)
		if compareConcurrent {
			var tracker *ui.BenchmarkTracker
			if !jsonFlag {
				tracker = ui.NewBenchmarkTracker()
				tracker.Start()
			}

			benchResult := runner.ExecuteConcurrentBenchmark(ctx, genaiClient, runner.Request{
				ModelID:       modelFlag,
				VideoURI:      compareVideoURI,
				Prompt:        comparePrompt,
				ThinkingLevel: thinking,
			}, func(agenticDone, staticDone bool, agenticResult, staticResult *runner.Result, aErr, sErr error) {
				if tracker != nil {
					tracker.Update(agenticDone, staticDone, agenticResult, staticResult, aErr, sErr)
				}
			})

			if tracker != nil {
				tracker.SetErrors(benchResult.AgenticError, benchResult.StaticError)
				tracker.Stop()
			}

			if benchResult.AgenticError != nil && benchResult.StaticError != nil {
				return fmt.Errorf("both benchmarks failed: agentic: %v; static: %v", benchResult.AgenticError, benchResult.StaticError)
			}
			if benchResult.AgenticError != nil {
				return fmt.Errorf("agentic benchmark failed: %w", benchResult.AgenticError)
			}
			if benchResult.StaticError != nil {
				return fmt.Errorf("static benchmark failed: %w", benchResult.StaticError)
			}

			if jsonFlag {
				return writeJSON(benchResult)
			}

			aUsage := benchResult.AgenticResult.Usage
			sUsage := benchResult.StaticResult.Usage
			fmt.Println(ui.RenderBenchmarkTable(aUsage, sUsage, benchResult.AgenticResult.Duration, benchResult.StaticResult.Duration))
			return nil
		}

		// Sequential fallback
		if !jsonFlag {
			fmt.Println(">>> Step 1/2: Executing with AGENTIC video processing...")
		}
		agenticResult, err := runner.Execute(ctx, genaiClient, runner.Request{
			ModelID:       modelFlag,
			VideoURI:      compareVideoURI,
			Prompt:        comparePrompt,
			Mode:          genai.MediaProcessingAgentic,
			ThinkingLevel: thinking,
		})
		if err != nil {
			return fmt.Errorf("agentic run failed: %w", err)
		}
		if !jsonFlag {
			fmt.Printf("    Agentic Run Complete (%v, %d tokens)\n\n",
				agenticResult.Duration.Round(time.Millisecond),
				totalTokens(agenticResult))
			fmt.Println(">>> Step 2/2: Executing with STATIC 1-FPS frame ingestion...")
		}

		staticResult, err := runner.Execute(ctx, genaiClient, runner.Request{
			ModelID:       modelFlag,
			VideoURI:      compareVideoURI,
			Prompt:        comparePrompt,
			Mode:          genai.MediaProcessingStatic,
			ThinkingLevel: thinking,
		})
		if err != nil {
			return fmt.Errorf("static run failed: %w", err)
		}
		if jsonFlag {
			return writeJSON(&runner.BenchmarkResult{
				AgenticResult: agenticResult,
				StaticResult:  staticResult,
			})
		}

		fmt.Printf("    Static Run Complete (%v, %d tokens)\n\n",
			staticResult.Duration.Round(time.Millisecond),
			totalTokens(staticResult))

		fmt.Println(ui.RenderBenchmarkTable(agenticResult.Usage, staticResult.Usage, agenticResult.Duration, staticResult.Duration))
		return nil
	},
}

func totalTokens(result *runner.Result) int32 {
	if result != nil && result.Usage != nil {
		return result.Usage.TotalTokenCount
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
		case "flash":
			return []string{"gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"}
		case "all", "generations":
			return []string{"gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash", "gemini-4-argon"}
		case "3.6", "gemini-3.6":
			resolved = append(resolved, "gemini-3.6-flash")
		case "3.7", "gemini-3.7":
			resolved = append(resolved, "gemini-3.7-flash")
		case "3.8", "gemini-3.8":
			resolved = append(resolved, "gemini-3.8-flash")
		case "4", "argon", "4-argon", "gemini-4", "gemini-4-argon":
			resolved = append(resolved, "gemini-4-argon")
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
	compareCmd.Flags().StringVar(&compareModels, "models", "", "Compare across multiple models (e.g. 'all', 'flash', or '3.7,3.8,argon')")
}
