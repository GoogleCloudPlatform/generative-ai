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

// Package runner executes single-video, multi-video, and multi-turn requests.
package runner

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"github.com/GoogleCloudPlatform/generative-ai/gemini/agentic-video/gemini-agentic-video-go/internal/telemetry"
	"google.golang.org/genai"
)

// Request defines the parameters for a single-video query.
type Request struct {
	ModelID       string
	VideoURI      string
	MIMEType      string
	Prompt        string
	Mode          genai.MediaProcessing
	ThinkingLevel genai.ThinkingLevel
}

// VideoInput represents a video in a multi-video request.
type VideoInput struct {
	URI      string
	MIMEType string
	Mode     genai.MediaProcessing
}

// MultiVideoRequest defines parameters for analyzing multiple videos in one prompt.
type MultiVideoRequest struct {
	ModelID       string
	Videos        []VideoInput
	Prompt        string
	ThinkingLevel genai.ThinkingLevel
}

// Result captures the model output and performance telemetry.
type Result struct {
	Title    string
	Mode     genai.MediaProcessing
	Text     string
	Duration time.Duration
	Usage    *genai.GenerateContentResponseUsageMetadata
}

// BenchmarkResult encapsulates outputs from concurrent Agentic vs. Static execution.
type BenchmarkResult struct {
	AgenticResult  *Result
	AgenticError   error
	StaticResult   *Result
	StaticError    error
	TotalWallClock time.Duration
}

// BenchmarkProgressCallback receives updates when individual benchmark pipelines complete.
type BenchmarkProgressCallback func(agenticDone, staticDone bool, aRes, sRes *Result)

// ModelBenchmarkResult captures the execution output for a specific model.
type ModelBenchmarkResult struct {
	ModelID  string
	Result   *Result
	Error    error
	Duration time.Duration
}

// ModelProgressCallback receives updates when an individual model run finishes.
type ModelProgressCallback func(modelID string, done bool, res *Result, err error)

// Execute performs a single-video understanding request.
func Execute(ctx context.Context, client *genai.Client, req Request) (*Result, error) {
	mimeType := req.MIMEType
	if mimeType == "" {
		mimeType = "video/mp4"
	}

	// 1. Create the video part with selected processing mode
	videoPart := genai.NewPartFromURI(req.VideoURI, mimeType)
	videoPart.MediaProcessing = req.Mode

	// 2. Wrap parts (best practice: text prompt follows video object)
	contents := []*genai.Content{
		genai.NewContentFromParts([]*genai.Part{
			videoPart,
			genai.NewPartFromText(req.Prompt),
		}, genai.RoleUser),
	}

	// 3. Configure generation with reasoning thinking level
	genConfig := &genai.GenerateContentConfig{
		ThinkingConfig: &genai.ThinkingConfig{
			ThinkingLevel: req.ThinkingLevel,
		},
	}

	start := time.Now()
	response, err := client.Models.GenerateContent(ctx, req.ModelID, contents, genConfig)
	duration := time.Since(start)
	if err != nil {
		return nil, fmt.Errorf("generating content: %w", err)
	}

	return &Result{
		Mode:     req.Mode,
		Text:     response.Text(),
		Duration: duration,
		Usage:    response.UsageMetadata,
	}, nil
}

// ExecuteMultiVideo performs comparative synthesis across multiple videos in a single prompt.
func ExecuteMultiVideo(ctx context.Context, client *genai.Client, req MultiVideoRequest) (*Result, error) {
	var parts []*genai.Part

	for _, video := range req.Videos {
		mimeType := video.MIMEType
		if mimeType == "" {
			mimeType = "video/mp4"
		}
		part := genai.NewPartFromURI(video.URI, mimeType)
		part.MediaProcessing = video.Mode
		parts = append(parts, part)
	}

	// Text prompt placed after all video parts
	parts = append(parts, genai.NewPartFromText(req.Prompt))

	contents := []*genai.Content{
		genai.NewContentFromParts(parts, genai.RoleUser),
	}

	genConfig := &genai.GenerateContentConfig{
		ThinkingConfig: &genai.ThinkingConfig{
			ThinkingLevel: req.ThinkingLevel,
		},
	}

	start := time.Now()
	response, err := client.Models.GenerateContent(ctx, req.ModelID, contents, genConfig)
	duration := time.Since(start)
	if err != nil {
		return nil, fmt.Errorf("generating multi-video content: %w", err)
	}

	return &Result{
		Mode:     genai.MediaProcessingAgentic,
		Text:     response.Text(),
		Duration: duration,
		Usage:    response.UsageMetadata,
	}, nil
}

// ExecuteMultiTurn performs a multi-turn conversation preserving video context across turns.
func ExecuteMultiTurn(ctx context.Context, client *genai.Client, modelID, videoURI string, turns []string, thinking genai.ThinkingLevel) ([]*Result, error) {
	if len(turns) == 0 {
		return nil, fmt.Errorf("at least one turn is required")
	}

	genConfig := &genai.GenerateContentConfig{
		ThinkingConfig: &genai.ThinkingConfig{
			ThinkingLevel: thinking,
		},
	}

	var results []*Result
	var conversationHistory []*genai.Content

	for i, prompt := range turns {
		turnNum := i + 1
		fmt.Printf("--- Turn %d Prompt: %q ---\n", turnNum, prompt)

		var userContent *genai.Content
		if i == 0 {
			// First turn includes video part + initial prompt
			videoPart := genai.NewPartFromURI(videoURI, "video/mp4")
			videoPart.MediaProcessing = genai.MediaProcessingAgentic
			userContent = genai.NewContentFromParts([]*genai.Part{
				videoPart,
				genai.NewPartFromText(prompt),
			}, genai.RoleUser)
		} else {
			// Subsequent turns append user prompt to conversation history
			userContent = genai.NewContentFromText(prompt, genai.RoleUser)
		}
		conversationHistory = append(conversationHistory, userContent)

		start := time.Now()
		response, err := client.Models.GenerateContent(ctx, modelID, conversationHistory, genConfig)
		duration := time.Since(start)
		if err != nil {
			return results, fmt.Errorf("turn %d failed: %w", turnNum, err)
		}

		result := &Result{
			Title:    fmt.Sprintf("Turn %d", turnNum),
			Mode:     genai.MediaProcessingAgentic,
			Text:     response.Text(),
			Duration: duration,
			Usage:    response.UsageMetadata,
		}
		results = append(results, result)

		// Echo model response back to conversation history to maintain context
		modelContent := genai.NewContentFromText(response.Text(), genai.RoleModel)
		conversationHistory = append(conversationHistory, modelContent)

		fmt.Println("\nModel Response:")
		fmt.Println(result.Text)
		telemetry.PrintUsage(result.Usage, result.Mode, result.Duration)
	}

	return results, nil
}

// ExecuteConcurrentBenchmark executes Agentic and Static video queries in parallel goroutines.
func ExecuteConcurrentBenchmark(
	ctx context.Context,
	client *genai.Client,
	req Request,
	callback BenchmarkProgressCallback,
) BenchmarkResult {
	start := time.Now()
	var res BenchmarkResult
	var mu sync.Mutex
	var wg sync.WaitGroup

	agenticReq := req
	agenticReq.Mode = genai.MediaProcessingAgentic

	staticReq := req
	staticReq.Mode = genai.MediaProcessingStatic

	wg.Add(2)

	// Goroutine 1: Agentic Processing
	go func() {
		defer wg.Done()
		agenticResult, agenticErr := Execute(ctx, client, agenticReq)
		mu.Lock()
		res.AgenticResult = agenticResult
		res.AgenticError = agenticErr
		if callback != nil {
			callback(true, res.StaticResult != nil || res.StaticError != nil, agenticResult, res.StaticResult)
		}
		mu.Unlock()
	}()

	// Goroutine 2: Static 1-FPS Processing
	go func() {
		defer wg.Done()
		staticResult, staticErr := Execute(ctx, client, staticReq)
		mu.Lock()
		res.StaticResult = staticResult
		res.StaticError = staticErr
		if callback != nil {
			callback(res.AgenticResult != nil || res.AgenticError != nil, true, res.AgenticResult, staticResult)
		}
		mu.Unlock()
	}()

	wg.Wait()
	res.TotalWallClock = time.Since(start)
	return res
}

// ExecuteMultiModelBenchmark runs identical queries across multiple models in parallel goroutines.
func ExecuteMultiModelBenchmark(
	ctx context.Context,
	client *genai.Client,
	modelIDs []string,
	req Request,
	callback ModelProgressCallback,
) []ModelBenchmarkResult {
	results := make([]ModelBenchmarkResult, len(modelIDs))
	var mu sync.Mutex
	var wg sync.WaitGroup

	for i, mID := range modelIDs {
		wg.Add(1)
		idx := i
		modelID := mID
		go func() {
			defer wg.Done()
			modelReq := req
			modelReq.ModelID = modelID
			mStart := time.Now()
			res, err := Execute(ctx, client, modelReq)
			mDur := time.Since(mStart)

			mu.Lock()
			results[idx] = ModelBenchmarkResult{
				ModelID:  modelID,
				Result:   res,
				Error:    err,
				Duration: mDur,
			}
			if callback != nil {
				callback(modelID, true, res, err)
			}
			mu.Unlock()
		}()
	}

	wg.Wait()
	return results
}

// ParseThinkingLevel maps string representation to genai.ThinkingLevel.
func ParseThinkingLevel(level string) genai.ThinkingLevel {
	switch strings.ToLower(level) {
	case "low":
		return genai.ThinkingLevelLow
	case "high":
		return genai.ThinkingLevelHigh
	case "minimal":
		return genai.ThinkingLevelMinimal
	default:
		return genai.ThinkingLevelMedium
	}
}

// ParseProcessingMode maps string representation to genai.MediaProcessing.
func ParseProcessingMode(mode string) genai.MediaProcessing {
	switch strings.ToLower(mode) {
	case "static":
		return genai.MediaProcessingStatic
	default:
		return genai.MediaProcessingAgentic
	}
}
