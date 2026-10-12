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
// Command gemini-live-studio serves the Gemini Live Studio frontend and bridges
// browser WebSockets to Gemini Live API sessions on Google Cloud.
package main

import (
	"log/slog"
	"net/http"
	"os"
	"strings"

	"github.com/joho/godotenv"
)

const (
	defaultImageModel    = "gemini-nano-banana-2.1"
	defaultImageLocation = "global"
	defaultPort          = "8080"
	frontendDistDir      = "frontend/dist"
)

// serverConfig is the process configuration, read from the environment.
type serverConfig struct {
	projectID     string
	liveLocation  string
	liveModel     string
	imageModel    string
	imageLocation string
	baseURL       string
	port          string
}

func main() {
	slog.SetDefault(newLogger())

	// Overload, not Load: the .env file intentionally wins over shell variables.
	if err := godotenv.Overload(".env"); err != nil {
		if err := godotenv.Overload("../.env"); err != nil {
			slog.Info("no .env file found; using environment variables")
		}
	}

	cfg := loadServerConfig()
	if cfg.projectID == "" {
		slog.Error("GOOGLE_CLOUD_PROJECT environment variable is required")
		os.Exit(1)
	}
	slog.Info("server configured",
		"liveModel", cfg.liveModel, "liveLocation", cfg.liveLocation,
		"imageModel", cfg.imageModel, "imageLocation", cfg.imageLocation)

	origins := newOriginPolicyFromEnv()
	wsOriginPolicy = origins
	if len(origins.allowed) > 0 {
		slog.Info("extra allowed origins configured", "count", len(origins.allowed))
	}

	mux := newMux(cfg, newClientManager(cfg.projectID, cfg.baseURL), origins)
	slog.Info("server listening", "port", cfg.port)
	if err := newHTTPServer(":"+cfg.port, mux).ListenAndServe(); err != nil {
		slog.Error("server stopped", "err", err)
		os.Exit(1)
	}
}

func loadServerConfig() serverConfig {
	return serverConfig{
		projectID:    os.Getenv("GOOGLE_CLOUD_PROJECT"),
		liveLocation: envOr("GOOGLE_CLOUD_LOCATION", defaultLocation),
		liveModel:    envOr("GEMINI_LIVE_MODEL", fallbackLiveModel),
		imageModel:   envOr("GEMINI_IMAGE_MODEL", defaultImageModel),
		// Image models are served from a different location than Live models
		// (the Gemini image models are global-only, gemini-3.8-live is
		// us-central1-only), so image generation has its own location.
		imageLocation: envOr("GEMINI_IMAGE_LOCATION", defaultImageLocation),
		baseURL:       os.Getenv("GEMINI_BASE_URL"),
		port:          envOr("PORT", defaultPort),
	}
}

func newMux(cfg serverConfig, cm *clientManager, origins *originPolicy) *http.ServeMux {
	mux := http.NewServeMux()
	mux.HandleFunc("/api/config", origins.withCORS(serverConfigHandler(cfg.liveModel, cfg.liveLocation, cfg.imageModel, cfg.imageLocation)))
	mux.HandleFunc("/api/generate-avatar", origins.withCORS(generateAvatarHandler(cm, cfg.imageModel, cfg.imageLocation)))
	mux.HandleFunc("/api/describe-image", origins.withCORS(describeImageHandler(cm)))
	mux.HandleFunc("/ws", liveSessionHandlerForMode(liveModeAvatar, cm, cfg.liveModel, cfg.liveLocation))
	mux.HandleFunc("/ws/live", liveSessionHandlerForMode(liveModeAudio, cm, cfg.liveModel, cfg.liveLocation))
	mux.HandleFunc("/health", origins.withCORS(healthHandler))
	mux.HandleFunc("/", spaOrStaticHandler(frontendDistDir))
	return mux
}

// newLogger logs JSON on Cloud Run (K_SERVICE is set there) and text
// elsewhere. On Cloud Run, "level" and "msg" are renamed to "severity" and
// "message" so Cloud Logging picks them up. LOG_LEVEL=debug enables
// per-message session logs.
func newLogger() *slog.Logger {
	level := slog.LevelInfo
	if strings.EqualFold(os.Getenv("LOG_LEVEL"), "debug") {
		level = slog.LevelDebug
	}
	opts := &slog.HandlerOptions{Level: level}
	if os.Getenv("K_SERVICE") != "" {
		opts.ReplaceAttr = cloudLoggingAttr
		return slog.New(slog.NewJSONHandler(os.Stdout, opts))
	}
	return slog.New(slog.NewTextHandler(os.Stderr, opts))
}

func envOr(key, fallback string) string {
	if v := os.Getenv(key); v != "" {
		return v
	}
	return fallback
}

func cloudLoggingAttr(groups []string, a slog.Attr) slog.Attr {
	if len(groups) > 0 {
		return a
	}
	switch a.Key {
	case slog.LevelKey:
		a.Key = "severity"
	case slog.MessageKey:
		a.Key = "message"
	}
	return a
}
