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

// Package runner executes single-video, multi-video, streaming, and multi-turn requests.
package runner

import (
	"context"
	"fmt"
	"strings"
	"sync"
	"time"

	"google.golang.org/genai"
)

// Request defines the parameters for a single-video query.
type Request struct {
	ModelID         string
	VideoURI        string
	MIMEType        string
	Prompt          string
	Mode            genai.MediaProcessing
	ThinkingLevel   genai.ThinkingLevel
	IncludeThoughts bool
}

// VideoInput represents a video in a multi-video request.
type VideoInput struct {
	URI      string
	MIMEType string
	Mode     genai.MediaProcessing
}

// MultiVideoRequest defines parameters for analyzing multiple videos in one prompt.
type MultiVideoRequest struct {
	ModelID         string
	Videos          []VideoInput
	Prompt          string
	ThinkingLevel   genai.ThinkingLevel
	IncludeThoughts bool
}

// Result captures the model output, reasoning trace, and performance telemetry.
type Result struct {
	Title    string
	Mode     genai.MediaProcessing
	Text     string
	Thoughts []string
	ToolHops int
	Duration time.Duration
	Usage    *genai.GenerateContentResponseUsageMetadata
}

// StreamCallback receives real-time text or thought chunks during streaming generation.
type StreamCallback func(chunkText string, isThought bool)

// MultiTurnCallback receives progress updates as each conversational turn completes.
type MultiTurnCallback func(turnNum, totalTurns int, prompt string, res *Result)

// BenchmarkResult encapsulates outputs from concurrent Agentic vs. Static execution.
type BenchmarkResult struct {
	AgenticResult  *Result
	AgenticError   error
	StaticResult   *Result
	StaticError    error
	TotalWallClock time.Duration
}

// BenchmarkProgressCallback receives updates when individual benchmark pipelines complete.
type BenchmarkProgressCallback func(agenticDone, staticDone bool, aRes, sRes *Result, aErr, sErr error)

// ModelBenchmarkResult captures the execution output for a specific model.
type ModelBenchmarkResult struct {
	ModelID  string
	Result   *Result
	Error    error
	Duration time.Duration
}

// ModelProgressCallback receives updates when an individual model run finishes.
type ModelProgressCallback func(modelID string, done bool, res *Result, err error)

// NormalizeVideoURI converts public Google Cloud Storage HTTPS URLs into native gs:// URIs
// so the server-side load_video tool accesses GCS directly rather than hitting web-fetch size limits.
func NormalizeVideoURI(uri string) string {
	trimmed := strings.TrimSpace(uri)
	for _, prefix := range []string{
		"https://storage.googleapis.com/",
		"http://storage.googleapis.com/",
		"https://storage.cloud.google.com/",
		"http://storage.cloud.google.com/",
	} {
		if strings.HasPrefix(trimmed, prefix) {
			rest := strings.TrimPrefix(trimmed, prefix)
			if rest != "" {
				return "gs://" + rest
			}
		}
	}
	return trimmed
}

// Execute performs a single-video understanding request.
func Execute(ctx context.Context, client *genai.Client, req Request) (*Result, error) {
	if err := ValidateThinkingLevel(req.ModelID, req.ThinkingLevel); err != nil {
		return nil, err
	}

	mimeType := req.MIMEType
	if mimeType == "" {
		mimeType = "video/mp4"
	}

	// 1. Create the video part with selected processing mode
	videoPart := genai.NewPartFromURI(NormalizeVideoURI(req.VideoURI), mimeType)
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
			ThinkingLevel:   req.ThinkingLevel,
			IncludeThoughts: req.IncludeThoughts,
		},
	}

	start := time.Now()
	response, err := client.Models.GenerateContent(ctx, req.ModelID, contents, genConfig)
	duration := time.Since(start)
	if err != nil {
		return nil, fmt.Errorf("generating content: %w", err)
	}

	thoughts, hops := extractResponseDetails(response)

	return &Result{
		Mode:     req.Mode,
		Text:     response.Text(),
		Thoughts: thoughts,
		ToolHops: hops,
		Duration: duration,
		Usage:    response.UsageMetadata,
	}, nil
}

// ExecuteStream performs a streaming single-video understanding request with automatic continuation.
func ExecuteStream(ctx context.Context, client *genai.Client, req Request, onChunk StreamCallback) (*Result, error) {
	if err := ValidateThinkingLevel(req.ModelID, req.ThinkingLevel); err != nil {
		return nil, err
	}

	mimeType := req.MIMEType
	if mimeType == "" {
		mimeType = "video/mp4"
	}

	videoPart := genai.NewPartFromURI(NormalizeVideoURI(req.VideoURI), mimeType)
	videoPart.MediaProcessing = req.Mode

	contents := []*genai.Content{
		genai.NewContentFromParts([]*genai.Part{
			videoPart,
			genai.NewPartFromText(req.Prompt),
		}, genai.RoleUser),
	}

	genConfig := &genai.GenerateContentConfig{
		ThinkingConfig: &genai.ThinkingConfig{
			ThinkingLevel:   req.ThinkingLevel,
			IncludeThoughts: req.IncludeThoughts,
		},
	}

	start := time.Now()
	var textBuilder strings.Builder
	var thoughts []string
	var sigOnlyParts int
	var lastUsage *genai.GenerateContentResponseUsageMetadata

	for chunk, err := range client.Models.GenerateContentStream(ctx, req.ModelID, contents, genConfig) {
		if err != nil {
			return nil, fmt.Errorf("streaming content: %w", err)
		}
		if chunk == nil {
			continue
		}
		if chunk.UsageMetadata != nil {
			lastUsage = chunk.UsageMetadata
		}
		for _, cand := range chunk.Candidates {
			if cand == nil || cand.Content == nil {
				continue
			}
			for _, part := range cand.Content.Parts {
				if part == nil {
					continue
				}
				if part.Thought {
					if part.Text != "" {
						thoughts = append(thoughts, strings.TrimSpace(part.Text))
						if onChunk != nil {
							onChunk(part.Text, true)
						}
					}
					continue
				}
				if part.Text != "" {
					textBuilder.WriteString(part.Text)
					if onChunk != nil {
						onChunk(part.Text, false)
					}
				} else if len(part.ThoughtSignature) > 0 {
					sigOnlyParts++
				}
			}
		}
	}
	duration := time.Since(start)

	return &Result{
		Mode:     req.Mode,
		Text:     textBuilder.String(),
		Thoughts: thoughts,
		ToolHops: (sigOnlyParts + 1) / 2,
		Duration: duration,
		Usage:    lastUsage,
	}, nil
}

// ExecuteMultiVideo performs comparative synthesis across multiple videos in a single prompt.
func ExecuteMultiVideo(ctx context.Context, client *genai.Client, req MultiVideoRequest) (*Result, error) {
	if err := ValidateThinkingLevel(req.ModelID, req.ThinkingLevel); err != nil {
		return nil, err
	}

	var parts []*genai.Part
	allStatic := len(req.Videos) > 0

	for _, video := range req.Videos {
		mimeType := video.MIMEType
		if mimeType == "" {
			mimeType = "video/mp4"
		}
		if video.Mode != genai.MediaProcessingStatic {
			allStatic = false
		}
		part := genai.NewPartFromURI(NormalizeVideoURI(video.URI), mimeType)
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
			ThinkingLevel:   req.ThinkingLevel,
			IncludeThoughts: req.IncludeThoughts,
		},
	}

	start := time.Now()
	response, err := client.Models.GenerateContent(ctx, req.ModelID, contents, genConfig)
	duration := time.Since(start)
	if err != nil {
		return nil, fmt.Errorf("generating multi-video content: %w", err)
	}

	resMode := genai.MediaProcessingAgentic
	if allStatic {
		resMode = genai.MediaProcessingStatic
	}
	thoughts, hops := extractResponseDetails(response)

	return &Result{
		Mode:     resMode,
		Text:     response.Text(),
		Thoughts: thoughts,
		ToolHops: hops,
		Duration: duration,
		Usage:    response.UsageMetadata,
	}, nil
}

// ExecuteMultiTurn performs a multi-turn conversation preserving video context across turns.
func ExecuteMultiTurn(ctx context.Context, client *genai.Client, modelID, videoURI string, turns []string, thinking genai.ThinkingLevel) ([]*Result, error) {
	return ExecuteMultiTurnWithCallback(ctx, client, modelID, videoURI, turns, thinking, nil)
}

// ExecuteMultiTurnWithCallback performs a multi-turn conversation preserving navigated ThoughtSignatures
// across turns and invoking an optional callback after each turn.
func ExecuteMultiTurnWithCallback(
	ctx context.Context,
	client *genai.Client,
	modelID, videoURI string,
	turns []string,
	thinking genai.ThinkingLevel,
	callback MultiTurnCallback,
) ([]*Result, error) {
	if len(turns) == 0 {
		return nil, fmt.Errorf("at least one turn is required")
	}
	if err := ValidateThinkingLevel(modelID, thinking); err != nil {
		return nil, err
	}

	genConfig := &genai.GenerateContentConfig{
		ThinkingConfig: &genai.ThinkingConfig{
			ThinkingLevel: thinking,
		},
	}

	normalizedURI := NormalizeVideoURI(videoURI)
	var results []*Result
	var conversationHistory []*genai.Content

	for i, prompt := range turns {
		turnNum := i + 1

		var userContent *genai.Content
		if i == 0 {
			// First turn includes video part + initial prompt
			videoPart := genai.NewPartFromURI(normalizedURI, "video/mp4")
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

		thoughts, hops := extractResponseDetails(response)
		result := &Result{
			Title:    fmt.Sprintf("Turn %d", turnNum),
			Mode:     genai.MediaProcessingAgentic,
			Text:     response.Text(),
			Thoughts: thoughts,
			ToolHops: hops,
			Duration: duration,
			Usage:    response.UsageMetadata,
		}
		results = append(results, result)

		// Preserve model text parts with their ThoughtSignature so follow-up turns
		// retain navigated timeline state without re-invoking load_video.
		conversationHistory = append(conversationHistory, ExtractModelTurnContent(response))

		if callback != nil {
			callback(turnNum, len(turns), prompt, result)
		}
	}

	return results, nil
}

// ExtractModelTurnContent extracts the non-thought text parts from a model response,
// preserving their ThoughtSignature so multi-turn conversations retain navigated video state
// while filtering out empty-text intermediate tool signature parts.
func ExtractModelTurnContent(resp *genai.GenerateContentResponse) *genai.Content {
	if resp != nil && len(resp.Candidates) > 0 && resp.Candidates[0] != nil && resp.Candidates[0].Content != nil {
		var validParts []*genai.Part
		for _, p := range resp.Candidates[0].Content.Parts {
			if p != nil && p.Text != "" && !p.Thought {
				validParts = append(validParts, p)
			}
		}
		if len(validParts) > 0 {
			return genai.NewContentFromParts(validParts, genai.RoleModel)
		}
	}
	var fallbackText string
	if resp != nil {
		fallbackText = resp.Text()
	}
	return genai.NewContentFromText(fallbackText, genai.RoleModel)
}

func extractResponseDetails(resp *genai.GenerateContentResponse) (thoughts []string, toolHops int) {
	if resp == nil || len(resp.Candidates) == 0 || resp.Candidates[0] == nil || resp.Candidates[0].Content == nil {
		return nil, 0
	}
	sigOnlyParts := 0
	for _, p := range resp.Candidates[0].Content.Parts {
		if p == nil {
			continue
		}
		if p.Thought && p.Text != "" {
			thoughts = append(thoughts, strings.TrimSpace(p.Text))
		} else if !p.Thought && p.Text == "" && len(p.ThoughtSignature) > 0 {
			sigOnlyParts++
		}
	}
	// Each internal load_video tool hop emits a call signature part and a result signature part.
	toolHops = (sigOnlyParts + 1) / 2
	return thoughts, toolHops
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
			callback(true, res.StaticResult != nil || res.StaticError != nil, agenticResult, res.StaticResult, agenticErr, res.StaticError)
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
			callback(res.AgenticResult != nil || res.AgenticError != nil, true, res.AgenticResult, staticResult, res.AgenticError, staticErr)
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

	for i, modelID := range modelIDs {
		wg.Add(1)
		go func() {
			defer wg.Done()
			modelReq := req
			modelReq.ModelID = modelID
			mStart := time.Now()
			result, err := Execute(ctx, client, modelReq)
			mDur := time.Since(mStart)

			mu.Lock()
			results[i] = ModelBenchmarkResult{
				ModelID:  modelID,
				Result:   result,
				Error:    err,
				Duration: mDur,
			}
			if callback != nil {
				callback(modelID, true, result, err)
			}
			mu.Unlock()
		}()
	}

	wg.Wait()
	return results
}

// ParseThinkingLevel maps string representation to genai.ThinkingLevel.
func ParseThinkingLevel(level string) genai.ThinkingLevel {
	parsed, _ := ParseThinkingLevelE(level)
	return parsed
}

// ParseThinkingLevelE maps string representation to genai.ThinkingLevel and returns an error for unknown values.
func ParseThinkingLevelE(level string) (genai.ThinkingLevel, error) {
	switch strings.ToLower(strings.TrimSpace(level)) {
	case "low":
		return genai.ThinkingLevelLow, nil
	case "medium", "":
		return genai.ThinkingLevelMedium, nil
	case "high":
		return genai.ThinkingLevelHigh, nil
	case "minimal":
		return genai.ThinkingLevelMinimal, nil
	default:
		return genai.ThinkingLevelMedium, fmt.Errorf("unsupported thinking level %q\nHint: use --thinking=low, --thinking=medium, or --thinking=high", level)
	}
}

// ValidateThinkingLevel checks whether the selected thinking level is supported by the target model.
func ValidateThinkingLevel(modelID string, level genai.ThinkingLevel) error {
	if level != genai.ThinkingLevelMinimal {
		return nil
	}
	m := strings.ToLower(strings.TrimSpace(modelID))
	if strings.Contains(m, "3.7") || strings.Contains(m, "3.8") || strings.Contains(m, "4-argon") || strings.Contains(m, "argon") {
		return fmt.Errorf("thinking level %q is not supported by model %q\nHint: use --thinking=low, --thinking=medium, or --thinking=high", level, modelID)
	}
	return nil
}

// ParseProcessingMode maps string representation to genai.MediaProcessing.
func ParseProcessingMode(mode string) genai.MediaProcessing {
	m, _ := ParseProcessingModeE(mode)
	return m
}

// ParseProcessingModeE maps string representation to genai.MediaProcessing and returns an error for unknown values.
func ParseProcessingModeE(mode string) (genai.MediaProcessing, error) {
	switch strings.ToLower(strings.TrimSpace(mode)) {
	case "agentic", "":
		return genai.MediaProcessingAgentic, nil
	case "static":
		return genai.MediaProcessingStatic, nil
	default:
		return genai.MediaProcessingAgentic, fmt.Errorf("unsupported processing mode %q\nHint: use --mode=agentic or --mode=static", mode)
	}
}
