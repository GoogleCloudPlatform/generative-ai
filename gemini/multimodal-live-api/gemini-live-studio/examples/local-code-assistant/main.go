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
// Command local-code-assistant is a voice coding assistant: a Gemini Live
// session with local filesystem, Graphviz and Google Search tools.
package main

import (
	"context"
	"embed"
	"encoding/json"
	"log/slog"
	"net/http"
	"os"
	"slices"
	"strings"

	"github.com/joho/godotenv"
	"google.golang.org/genai"

	"local-code-assistant/tools"
)

//go:embed index.html
var content embed.FS

const (
	defaultModel      = "gemini-3.8-live"
	defaultVoice      = "Puck"
	defaultLocation   = "us-central1"
	defaultAddr       = ":8081"
	defaultAvatarMode = "reactive"
	defaultPreset     = "Ben"
	diagramsDir       = "diagrams"
)

var liveModelRegistry = []string{
	"gemini-3.8-live",
}

// appConfig is the process configuration, read from the environment.
type appConfig struct {
	projectID       string
	location        string
	model           string
	voice           string
	enableAvatar    bool
	avatarMode      string // "reactive" (audio + animated avatar) or "video" (Live avatar video)
	avatarPreset    string
	listenAddr      string
	baseURL         string
	instructionFile string
	extraContext    string
}

// videoAvatar reports whether sessions request Live avatar video.
func (c appConfig) videoAvatar() bool {
	return c.enableAvatar && c.avatarMode == "video"
}

func main() {
	slog.SetDefault(slog.New(slog.NewTextHandler(os.Stderr, nil)))
	cfg := loadConfig()

	slog.Info("starting Local Code Assistant",
		"model", cfg.model, "voice", cfg.voice,
		"avatar", cfg.enableAvatar, "avatarMode", cfg.avatarMode, "avatarPreset", cfg.avatarPreset,
		"instructionFile", cfg.instructionFile, "extraContextBytes", len(cfg.extraContext),
		"project", cfg.projectID, "location", cfg.location, "addr", cfg.listenAddr)

	client, err := genai.NewClient(context.Background(), &genai.ClientConfig{
		Backend:     genai.BackendVertexAI,
		Project:     cfg.projectID,
		Location:    cfg.location,
		HTTPOptions: genai.HTTPOptions{BaseURL: cfg.baseURL},
	})
	if err != nil {
		slog.Error("initializing Gen AI client", "err", err)
		os.Exit(1)
	}

	if err := os.MkdirAll(diagramsDir, 0o755); err != nil {
		slog.Warn("creating diagrams directory", "err", err)
	}
	registry := tools.NewRegistry(
		tools.NewListDirectory(),
		tools.NewReadFile(),
		tools.NewGraphviz(diagramsDir),
	)

	mux := http.NewServeMux()
	mux.HandleFunc("/api/status", statusHandler(cfg))
	mux.HandleFunc("/ws", sessionHandler(cfg, client, registry))
	mux.Handle("/diagrams/", http.StripPrefix("/diagrams/", http.FileServer(http.Dir(diagramsDir))))
	mux.HandleFunc("/", indexHandler)

	slog.Info("listening", "url", localURL(cfg.listenAddr))
	if err := http.ListenAndServe(cfg.listenAddr, mux); err != nil {
		slog.Error("server stopped", "err", err)
		os.Exit(1)
	}
}

// loadConfig reads the environment. Model and voice precedence is deliberate:
// LOCAL_CODE_* (shell or .env) wins, then shell-exported GEMINI_LIVE_*, so a
// parent project's .env GEMINI_LIVE_MODEL does not silently change this app's
// model.
func loadConfig() appConfig {
	shellModel := firstEnv("LOCAL_CODE_MODEL", "GEMINI_LIVE_MODEL")
	shellVoice := firstEnv("LOCAL_CODE_VOICE", "GEMINI_LIVE_VOICE")

	// Local .env overrides the shell; parent .env files only fill gaps.
	if err := godotenv.Overload(".env"); err != nil {
		if err := godotenv.Load("../.env"); err != nil {
			_ = godotenv.Load("../../.env")
		}
	}

	location := os.Getenv("GOOGLE_CLOUD_LOCATION")
	if location == "" || location == "global" {
		// The Live API requires a regional endpoint.
		slog.Info("Live API requires a regional endpoint; overriding GOOGLE_CLOUD_LOCATION", "from", location, "to", defaultLocation)
		location = defaultLocation
	}

	return appConfig{
		projectID:       os.Getenv("GOOGLE_CLOUD_PROJECT"),
		location:        location,
		model:           orDefault(firstNonEmpty(os.Getenv("LOCAL_CODE_MODEL"), shellModel), defaultModel),
		voice:           orDefault(firstNonEmpty(shellVoice, firstEnv("LOCAL_CODE_VOICE", "GEMINI_LIVE_VOICE")), defaultVoice),
		enableAvatar:    isTruthy(firstEnv("ENABLE_AVATAR", "LOCAL_CODE_ENABLE_AVATAR")),
		avatarMode:      orDefault(strings.ToLower(os.Getenv("AVATAR_MODE")), defaultAvatarMode),
		avatarPreset:    orDefault(os.Getenv("AVATAR_PRESET"), defaultPreset),
		listenAddr:      orDefault(os.Getenv("LOCAL_CODE_ADDR"), defaultAddr),
		baseURL:         os.Getenv("GEMINI_BASE_URL"),
		instructionFile: os.Getenv("SYSTEM_INSTRUCTION_FILE"),
		extraContext:    os.Getenv("AVATAR_EXTRA_CONTEXT"),
	}
}

func statusHandler(cfg appConfig) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		err := json.NewEncoder(w).Encode(map[string]any{
			"model":                   cfg.model,
			"voice":                   cfg.voice,
			"project":                 cfg.projectID,
			"location":                cfg.location,
			"status":                  "ready",
			"enable_avatar":           cfg.enableAvatar,
			"avatar_mode":             cfg.avatarMode,
			"avatar_preset":           cfg.avatarPreset,
			"system_instruction_file": cfg.instructionFile,
			"available_models":        allowedValues(cfg.model, liveModelRegistry),
		})
		if err != nil {
			slog.Debug("writing status response", "err", err)
		}
	}
}

func indexHandler(w http.ResponseWriter, r *http.Request) {
	page, err := content.ReadFile("index.html")
	if err != nil {
		http.Error(w, "index.html missing from build", http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "text/html")
	_, _ = w.Write(page)
}

// allowedValues returns the registry with the server default prepended when
// it is not already listed.
func allowedValues(def string, registry []string) []string {
	if def == "" || slices.Contains(registry, def) {
		return slices.Clone(registry)
	}
	return append([]string{def}, registry...)
}

// resolveAllowed returns the client-requested value if it is the server
// default or in the registry, and the server default otherwise. Client input
// must never reach the Vertex API unchecked.
func resolveAllowed(kind, requested, def string, registry []string) string {
	requested = strings.TrimSpace(requested)
	if requested == "" || requested == def {
		return def
	}
	if slices.Contains(registry, requested) {
		return requested
	}
	slog.Warn("rejected client-requested value not in allowlist; using default", "kind", kind, "requested", requested, "default", def)
	return def
}

// localURL turns a listen address (":8081" or "127.0.0.1:8081") into a URL to open.
func localURL(addr string) string {
	if strings.HasPrefix(addr, ":") {
		return "http://localhost" + addr
	}
	return "http://" + addr
}

func firstEnv(keys ...string) string {
	for _, key := range keys {
		if v := os.Getenv(key); v != "" {
			return v
		}
	}
	return ""
}

func firstNonEmpty(values ...string) string {
	for _, v := range values {
		if v != "" {
			return v
		}
	}
	return ""
}

func orDefault(value, fallback string) string {
	if value == "" {
		return fallback
	}
	return value
}

func isTruthy(value string) bool {
	switch strings.ToLower(value) {
	case "true", "1", "yes", "on":
		return true
	}
	return false
}
