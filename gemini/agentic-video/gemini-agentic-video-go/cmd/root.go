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

// Package cmd defines the Cobra CLI commands for Gemini Agentic Video.
package cmd

import (
	"context"
	"encoding/json"
	"fmt"
	"os"
	"time"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/client"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/ui"
	"github.com/spf13/cobra"
	"google.golang.org/genai"
)

const (
	groupExecution    = "execution"
	groupBenchmarking = "benchmarking"
)

var (
	modelFlag    string
	projectFlag  string
	locationFlag string
	backendFlag  string
	jsonFlag     bool
	timeoutFlag  time.Duration
)

// RootCmd represents the base command when called without any subcommands.
var RootCmd = &cobra.Command{
	Use:   "gemini-agentic-video-go",
	Short: "Gemini Agentic Video Understanding CLI in Go",
	Long: `A Go CLI demonstrating Gemini agentic video understanding with active
Think ➔ Act ➔ Observe dynamic timeline navigation, sub-second precision,
and up to 96% token reduction compared to static frame ingestion.

Powered by Google Gen AI SDK (google.golang.org/genai) and Gemini 3.7 Flash,
Gemini 3.8 Flash, and Gemini 4 Argon.`,
	Example: `  # List all built-in tutorial scenarios
  gemini-agentic-video-go example list

  # Run Scenario 4 (YouTube Shorts) with Gemini 4 Argon and X-Ray thought trace
  gemini-agentic-video-go example 4 --model gemini-4-argon --show-thoughts

  # Run an ad-hoc query with streaming output
  gemini-agentic-video-go run --video "https://www.youtube.com/shorts/y-mrGw1wW8E" --stream

  # Benchmark all supported models (3.6, 3.7, 3.8, 4-argon) in parallel
  gemini-agentic-video-go compare --models all --video "https://www.youtube.com/shorts/y-mrGw1wW8E"

  # Emit structured JSON for automated pipelines / agents
  gemini-agentic-video-go example list --json`,
}

// Execute adds all child commands to the root command and sets flags appropriately.
func Execute() error {
	return RootCmd.Execute()
}

func init() {
	RootCmd.AddGroup(
		&cobra.Group{ID: groupExecution, Title: "Execution Commands:"},
		&cobra.Group{ID: groupBenchmarking, Title: "Benchmarking & Shootout Commands:"},
	)

	RootCmd.PersistentFlags().StringVarP(&modelFlag, "model", "m", "gemini-3.7-flash", "Gemini model ID (e.g. gemini-4-argon, gemini-3.8-flash, gemini-3.7-flash, gemini-3.6-flash, gemini-3.5-flash-lite)")
	RootCmd.PersistentFlags().StringVarP(&projectFlag, "project", "p", "", "Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT or active gcloud config)")
	RootCmd.PersistentFlags().StringVarP(&locationFlag, "location", "l", "global", "Google Cloud location / region (defaults to GOOGLE_CLOUD_LOCATION or 'global')")
	RootCmd.PersistentFlags().StringVarP(&backendFlag, "backend", "b", "enterprise", "Client backend: 'enterprise', 'vertex', or 'gemini'")
	RootCmd.PersistentFlags().BoolVar(&jsonFlag, "json", false, "Emit structured JSON output for programmatic and A2A consumption")
	RootCmd.PersistentFlags().DurationVar(&timeoutFlag, "timeout", 10*time.Minute, "Maximum execution timeout per command (e.g. 2m, 5m, 10m)")
}

// InitClient initializes and returns the Gen AI client with resolved project configuration.
func InitClient(ctx context.Context) (*genai.Client, error) {
	proj := client.ResolveProject(projectFlag)
	loc := client.ResolveLocation(locationFlag)

	genaiClient, err := client.New(ctx, client.Config{
		Backend:  backendFlag,
		Project:  proj,
		Location: loc,
	})
	if err != nil {
		return nil, fmt.Errorf("initializing Gen AI client: %w", err)
	}

	if !jsonFlag {
		fmt.Println(ui.RenderBanner(modelFlag, backendFlag, proj, loc))
	}

	return genaiClient, nil
}

// withCommandTimeout wraps ctx with timeoutFlag if timeoutFlag > 0.
func withCommandTimeout(ctx context.Context) (context.Context, context.CancelFunc) {
	if ctx == nil {
		ctx = context.Background()
	}
	if timeoutFlag <= 0 {
		return context.WithCancel(ctx)
	}
	return context.WithTimeout(ctx, timeoutFlag)
}

// writeJSON serializes v as indented JSON to stdout.
func writeJSON(v any) error {
	encoder := json.NewEncoder(os.Stdout)
	encoder.SetIndent("", "  ")
	return encoder.Encode(v)
}
