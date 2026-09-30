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
	"fmt"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/client"
	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/ui"
	"github.com/spf13/cobra"
	"google.golang.org/genai"
)

var (
	modelFlag    string
	projectFlag  string
	locationFlag string
	backendFlag  string
)

// RootCmd represents the base command when called without any subcommands.
var RootCmd = &cobra.Command{
	Use:   "gemini-agentic-video-go",
	Short: "Gemini Agentic Video Understanding CLI in Go",
	Long: `A Go CLI demonstrating Gemini agentic video understanding with active
Think ➔ Act ➔ Observe dynamic timeline navigation, sub-second precision,
and up to 96% token reduction compared to static frame ingestion.

Powered by Google Gen AI SDK (google.golang.org/genai) and Gemini 3.7 Flash.`,
}

// Execute adds all child commands to the root command and sets flags appropriately.
func Execute() error {
	return RootCmd.Execute()
}

func init() {
	RootCmd.PersistentFlags().StringVarP(&modelFlag, "model", "m", "gemini-3.7-flash", "Gemini model ID (e.g. gemini-3.7-flash, gemini-3.6-flash, gemini-3.5-flash-lite)")
	RootCmd.PersistentFlags().StringVarP(&projectFlag, "project", "p", "", "Google Cloud project ID (defaults to GOOGLE_CLOUD_PROJECT or active gcloud config)")
	RootCmd.PersistentFlags().StringVarP(&locationFlag, "location", "l", "global", "Google Cloud location / region (defaults to GOOGLE_CLOUD_LOCATION or 'global')")
	RootCmd.PersistentFlags().StringVarP(&backendFlag, "backend", "b", "enterprise", "Client backend: 'enterprise', 'vertex', or 'gemini'")
}

// InitClient initializes and returns the Gen AI client with resolved project configuration.
func InitClient(ctx context.Context) (*genai.Client, error) {
	proj := client.ResolveProject(projectFlag)
	loc := client.ResolveLocation(locationFlag)

	genaiClient, err := client.NewClient(ctx, client.Config{
		Backend:  backendFlag,
		Project:  proj,
		Location: loc,
	})
	if err != nil {
		return nil, fmt.Errorf("initializing Gen AI client: %w", err)
	}

	fmt.Println(ui.RenderBanner(modelFlag, backendFlag, proj, loc))

	return genaiClient, nil
}
