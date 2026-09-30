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

// Package client provides configuration and initialization helpers for the Google Gen AI client.
package client

import (
	"context"
	"fmt"
	"os"
	"os/exec"
	"strings"

	"google.golang.org/genai"
)

// Config encapsulates configuration for the Google Gen AI client.
type Config struct {
	Backend  string
	Project  string
	Location string
	APIKey   string
}

// NewClient initializes a Google Gen AI Client with the selected backend.
func NewClient(ctx context.Context, cfg Config) (*genai.Client, error) {
	clientCfg := &genai.ClientConfig{}

	switch strings.ToLower(cfg.Backend) {
	case "enterprise":
		if cfg.Project == "" {
			return nil, fmt.Errorf("project ID is required for Enterprise Agent Platform backend; set --project or GOOGLE_CLOUD_PROJECT")
		}
		clientCfg.Backend = genai.BackendEnterprise
		clientCfg.Project = cfg.Project
		clientCfg.Location = cfg.Location
	case "vertex":
		if cfg.Project == "" {
			return nil, fmt.Errorf("project ID is required for Vertex AI / Agent Platform backend; set --project or GOOGLE_CLOUD_PROJECT")
		}
		clientCfg.Backend = genai.BackendVertexAI
		clientCfg.Project = cfg.Project
		clientCfg.Location = cfg.Location
	case "gemini":
		clientCfg.Backend = genai.BackendGeminiAPI
		apiKey := cfg.APIKey
		if apiKey == "" {
			apiKey = os.Getenv("GEMINI_API_KEY")
		}
		if apiKey == "" {
			apiKey = os.Getenv("GOOGLE_API_KEY")
		}
		if apiKey == "" {
			return nil, fmt.Errorf("API key required for Gemini API backend; set GEMINI_API_KEY or GOOGLE_API_KEY")
		}
		clientCfg.APIKey = apiKey
	default:
		return nil, fmt.Errorf("unsupported backend %q; use 'enterprise', 'vertex', or 'gemini'", cfg.Backend)
	}

	return genai.NewClient(ctx, clientCfg)
}

// ResolveProject determines the Google Cloud project ID from flag, env, or gcloud CLI.
func ResolveProject(flagValue string) string {
	if flagValue != "" && flagValue != "[your-project-id]" {
		return flagValue
	}
	if envVal := os.Getenv("GOOGLE_CLOUD_PROJECT"); envVal != "" && envVal != "[your-project-id]" {
		return envVal
	}
	// Fallback to active gcloud config
	out, err := exec.Command("gcloud", "config", "get-value", "project").Output()
	if err == nil {
		p := strings.TrimSpace(string(out))
		if p != "" && p != "(unset)" {
			return p
		}
	}
	return ""
}

// ResolveLocation determines the Google Cloud location/region from flag or environment.
func ResolveLocation(flagValue string) string {
	if flagValue != "" {
		return flagValue
	}
	if envVal := os.Getenv("GOOGLE_CLOUD_LOCATION"); envVal != "" {
		return envVal
	}
	if envVal := os.Getenv("GOOGLE_CLOUD_REGION"); envVal != "" {
		return envVal
	}
	return "global"
}
