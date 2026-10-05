// Copyright 2026 Google LLC
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//	http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.
package main

import (
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"unicode/utf8"

	"google.golang.org/genai"
)

// Text models for /api/describe-image when GEMINI_TEXT_MODEL is unset; the
// fallback is tried once if the preferred model fails.
const (
	defaultDescribeModel  = "gemini-3-flash-preview"
	fallbackDescribeModel = "gemini-2.5-flash"
	describeImagePrompt   = "Provide a detailed, clear, and factual textual summary/description of the contents, key text, and visual details of this image. Focus on details that would be helpful as reference background context for a conversational AI assistant."
)

type GenerateAvatarRequest struct {
	Prompt   string `json:"prompt"`
	Image    string `json:"image,omitempty"`
	Model    string `json:"model,omitempty"`
	Location string `json:"location,omitempty"`
}

type GenerateAvatarResponse struct {
	Image string `json:"image"`
	Error string `json:"error,omitempty"`
}

type ServerConfigResponse struct {
	LiveModel            string   `json:"liveModel"`
	LiveLocation         string   `json:"liveLocation"`
	ImageModel           string   `json:"imageModel"`
	ImageLocation        string   `json:"imageLocation"`
	AvailableLiveModels  []string `json:"availableLiveModels"`
	AvailableLocations   []string `json:"availableLocations"`
	AvailableImageModels []string `json:"availableImageModels"`
}

type DescribeImageRequest struct {
	Image string `json:"image"` // base64 data URL or raw base64
}

type DescribeImageResponse struct {
	Description string `json:"description,omitempty"`
	Error       string `json:"error,omitempty"`
}

// writeJSON writes v as a JSON response. Encoding errors can only mean the
// client went away mid-response, so they are logged, not returned.
func writeJSON(w http.ResponseWriter, status int, v any) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	if err := json.NewEncoder(w).Encode(v); err != nil {
		slog.Debug("writing JSON response", "err", err)
	}
}

func generateAvatarHandler(cm *clientManager, defaultImageModel, defaultImageLocation string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		r.Body = http.MaxBytesReader(w, r.Body, maxGenerateAvatarBody)
		var req GenerateAvatarRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			var tooBig *http.MaxBytesError
			if errors.As(err, &tooBig) {
				http.Error(w, "Request body too large", http.StatusRequestEntityTooLarge)
				return
			}
			http.Error(w, "Invalid request body", http.StatusBadRequest)
			return
		}

		if req.Prompt == "" && req.Image == "" {
			http.Error(w, "Prompt or Image is required", http.StatusBadRequest)
			return
		}
		if utf8.RuneCountInString(req.Prompt) > maxImagePromptChars {
			http.Error(w, fmt.Sprintf("Prompt exceeds %d characters", maxImagePromptChars), http.StatusBadRequest)
			return
		}

		var refMIME string
		var refBytes []byte
		if req.Image != "" {
			var err error
			refMIME, refBytes, err = parseImageDataURL(req.Image, avatarImageMIMETypes)
			if err != nil {
				http.Error(w, "Invalid reference image: "+err.Error(), http.StatusBadRequest)
				return
			}
		}

		model := resolveAllowed("image model", req.Model, defaultImageModel, imageModelRegistry)
		location := resolveAllowed("location", req.Location, defaultImageLocation, locationRegistry)
		logger := slog.With("model", model, "location", location)
		// Prompts are user content: log their size, not their text.
		logger.Info("generating avatar image", "promptChars", utf8.RuneCountInString(req.Prompt), "referenceBytes", len(refBytes))

		client, err := cm.clientFor(location)
		if err != nil {
			logger.Error("initializing genai client", "err", err)
			writeJSON(w, http.StatusInternalServerError, GenerateAvatarResponse{Error: "Failed to initialize AI client for location " + location})
			return
		}

		parts := []*genai.Part{{Text: req.Prompt}}
		if refBytes != nil {
			parts = []*genai.Part{{InlineData: &genai.Blob{MIMEType: refMIME, Data: refBytes}}, {Text: req.Prompt}}
		}
		contents := []*genai.Content{{Role: "user", Parts: parts}}

		imageConfig := &genai.ImageConfig{AspectRatio: "9:16"}
		if !strings.Contains(model, "lite") {
			imageConfig.ImageSize = "2K"
		}

		response, err := client.Models.GenerateContent(r.Context(), model, contents, &genai.GenerateContentConfig{ImageConfig: imageConfig})
		if err != nil {
			logger.Error("generating image", "err", err)
			writeJSON(w, http.StatusInternalServerError, GenerateAvatarResponse{Error: "Failed to generate image"})
			return
		}

		image := firstInlineImage(response)
		if image == nil {
			logger.Error("no inline image in model response")
			writeJSON(w, http.StatusInternalServerError, GenerateAvatarResponse{Error: "No image generated"})
			return
		}
		mimeType := image.MIMEType
		if mimeType == "" {
			mimeType = "image/jpeg"
		}
		dataURI := fmt.Sprintf("data:%s;base64,%s", mimeType, base64.StdEncoding.EncodeToString(image.Data))
		writeJSON(w, http.StatusOK, GenerateAvatarResponse{Image: dataURI})
	}
}

// firstInlineImage returns the first non-empty inline blob in the first
// candidate, or nil.
func firstInlineImage(response *genai.GenerateContentResponse) *genai.Blob {
	if response == nil || len(response.Candidates) == 0 || response.Candidates[0].Content == nil {
		return nil
	}
	for _, part := range response.Candidates[0].Content.Parts {
		if part.InlineData != nil && len(part.InlineData.Data) > 0 {
			return part.InlineData
		}
	}
	return nil
}

// describeImageHandler asks Gemini for a textual description of an image,
// used as grounding reference material for a conversation.
func describeImageHandler(cm *clientManager) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		if r.Method != http.MethodPost {
			http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}

		r.Body = http.MaxBytesReader(w, r.Body, maxDescribeImageBody)
		var req DescribeImageRequest
		if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
			http.Error(w, "Invalid request body or image exceeds 8MB limit", http.StatusBadRequest)
			return
		}
		if strings.TrimSpace(req.Image) == "" {
			http.Error(w, "Image is required", http.StatusBadRequest)
			return
		}

		mimeType, payload := splitImagePayload(req.Image)
		if !strings.HasPrefix(strings.ToLower(mimeType), "image/") {
			http.Error(w, "Only image data URLs are supported", http.StatusBadRequest)
			return
		}
		imageBytes, err := base64.StdEncoding.DecodeString(payload)
		if err != nil {
			http.Error(w, "Invalid base64 image data", http.StatusBadRequest)
			return
		}

		client, err := cm.clientFor("global")
		if err != nil {
			slog.Error("initializing genai client for describe-image", "err", err)
			http.Error(w, "Failed to initialize AI client", http.StatusInternalServerError)
			return
		}

		contents := []*genai.Content{{
			Role: "user",
			Parts: []*genai.Part{
				{InlineData: &genai.Blob{MIMEType: mimeType, Data: imageBytes}},
				{Text: describeImagePrompt},
			},
		}}

		configuredModel := os.Getenv("GEMINI_TEXT_MODEL")
		model := configuredModel
		if model == "" {
			model = defaultDescribeModel
		}
		response, err := client.Models.GenerateContent(r.Context(), model, contents, nil)
		if err != nil && configuredModel == "" {
			slog.Warn("describe-image failed; retrying with fallback model", "model", model, "fallback", fallbackDescribeModel, "err", err)
			response, err = client.Models.GenerateContent(r.Context(), fallbackDescribeModel, contents, nil)
		}
		if err != nil {
			slog.Error("describing image", "err", err)
			http.Error(w, "Failed to analyze image", http.StatusInternalServerError)
			return
		}

		description := strings.TrimSpace(response.Text())
		if description == "" {
			http.Error(w, "No description returned from model", http.StatusInternalServerError)
			return
		}
		writeJSON(w, http.StatusOK, DescribeImageResponse{Description: description})
	}
}

// splitImagePayload splits a "data:<mime>;base64,<payload>" URL into its MIME
// type and payload. Raw base64 (no data: prefix) is treated as JPEG.
func splitImagePayload(image string) (mimeType, payload string) {
	header, payload, ok := strings.Cut(image, ";base64,")
	if !ok {
		return "image/jpeg", image
	}
	if mime, isDataURL := strings.CutPrefix(header, "data:"); isDataURL {
		return mime, payload
	}
	return "image/jpeg", payload
}

func serverConfigHandler(liveModel, liveLocation, imageModel, imageLocation string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		writeJSON(w, http.StatusOK, ServerConfigResponse{
			LiveModel:            liveModel,
			LiveLocation:         liveLocation,
			ImageModel:           imageModel,
			ImageLocation:        imageLocation,
			AvailableLiveModels:  allowedValues(liveModel, liveModelRegistry),
			AvailableLocations:   allowedValues(liveLocation, locationRegistry),
			AvailableImageModels: allowedValues(imageModel, imageModelRegistry),
		})
	}
}

func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	if _, err := w.Write([]byte("OK")); err != nil {
		slog.Debug("writing health response", "err", err)
	}
}

// spaOrStaticHandler serves the built frontend, returning index.html for the
// client-side routes so deep links and reloads work.
func spaOrStaticHandler(distDir string) http.HandlerFunc {
	files := http.FileServer(http.Dir(distDir))
	return func(w http.ResponseWriter, r *http.Request) {
		switch strings.Trim(r.URL.Path, "/") {
		case "live", "avatar", "settings":
			http.ServeFile(w, r, distDir+"/index.html")
		default:
			files.ServeHTTP(w, r)
		}
	}
}
