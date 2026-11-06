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

package main

import (
	"context"
	"log/slog"
	"net/http"
	"time"

	"github.com/gorilla/websocket"

	"gemini-live-studio/livebridge"
)

// Durations for the Live session guardrails; variables so tests can shrink them.
var (
	sessionCapDuration = livebridge.DefaultSessionCap
	sessionCapGrace    = livebridge.DefaultSessionCapGrace
	goodbyeBackstop    = livebridge.DefaultGoodbyeBackstop
)

const (
	goodbyePrompt       = livebridge.DefaultGoodbyePrompt
	maxLoggedValueRunes = livebridge.MaxLoggedValueRunes
)

// InitialConfig is the first WebSocket message: the session configuration.
type InitialConfig struct {
	AvatarType               string   `json:"avatarType"` // "preset" or "custom"
	AvatarData               string   `json:"avatarData"` // "Puck" or "data:image/jpeg;base64,..."
	VoiceName                string   `json:"voiceName"`
	WelcomeMessage           string   `json:"welcomeMessage"`
	SystemInstruction        string   `json:"systemInstruction"`
	GroundingContext         string   `json:"groundingContext,omitempty"`
	LiveModel                string   `json:"liveModel,omitempty"`
	LiveLocation             string   `json:"liveLocation,omitempty"`
	LanguageCode             string   `json:"languageCode,omitempty"`
	SilenceDurationMs        int32    `json:"silenceDurationMs,omitempty"`
	PrefixPaddingMs          int32    `json:"prefixPaddingMs,omitempty"`
	StartOfSpeechSensitivity string   `json:"startOfSpeechSensitivity,omitempty"`
	EndOfSpeechSensitivity   string   `json:"endOfSpeechSensitivity,omitempty"`
	ActivityHandling         string   `json:"activityHandling,omitempty"`
	AdaptationPhrases        []string `json:"adaptationPhrases,omitempty"`
	Temperature              *float32 `json:"temperature,omitempty"`
	TopP                     *float32 `json:"topP,omitempty"`
	TopK                     *float32 `json:"topK,omitempty"`
	MaxOutputTokens          int32    `json:"maxOutputTokens,omitempty"`
	EnableGoogleSearch       *bool    `json:"enableGoogleSearch,omitempty"`
	EnableToolCalling        *bool    `json:"enableToolCalling,omitempty"`
	ProactiveAudio           *bool    `json:"proactiveAudio,omitempty"`
	ContextWindowCompression *bool    `json:"contextWindowCompression,omitempty"`
	CompressionTriggerTokens int64    `json:"compressionTriggerTokens,omitempty"`
}

// ClientMessage is any WebSocket message after InitialConfig.
type ClientMessage = livebridge.ClientMessage

// wsOriginPolicy guards WebSocket upgrades (see http_security.go). main()
// replaces it with the ALLOWED_ORIGINS-aware policy; the zero-config default
// is same-origin plus loopback-dev only.
var wsOriginPolicy = newOriginPolicy("")

var upgrader = websocket.Upgrader{
	CheckOrigin: func(r *http.Request) bool {
		if wsOriginPolicy.Allows(r) {
			return true
		}
		slog.Warn("rejected WebSocket upgrade; set ALLOWED_ORIGINS to permit it", "origin", r.Header.Get("Origin"), "host", r.Host)
		return false
	},
}

func newBuiltInToolRunner() *livebridge.ToolRunner {
	reg := livebridge.NewFuncRegistry()
	for _, decl := range builtInFunctionDeclarations() {
		name := decl.Name
		reg.Register(decl, func(_ context.Context, args map[string]any) (map[string]any, error) {
			return executeBuiltInTool(name, args), nil
		})
	}
	return livebridge.NewToolRunner(livebridge.ToolRunnerConfig{
		Registry: reg,
		Timeout:  30 * time.Second,
	})
}

// liveSessionHandlerForMode bridges a browser WebSocket to a Gemini Live
// session: liveModeAvatar (/ws, fMP4 video) or liveModeAudio (/ws/live, PCM).
func liveSessionHandlerForMode(mode liveMode, connector liveConnector, defaultLiveModel, defaultLiveLocation string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			slog.Warn("upgrading WebSocket", "err", err)
			return
		}
		ws := newSafeWS(conn)
		defer func() { _ = ws.Close() }()

		// The first message may carry a custom avatar image; everything after
		// it is media chunks and text, so the limit is tightened after it.
		ws.SetReadLimit(maxInitialConfigBytes)
		var initialConfig InitialConfig
		if err := ws.ReadJSON(&initialConfig); err != nil {
			slog.Warn("reading initial session config", "err", err)
			return
		}
		ws.SetReadLimit(maxClientMessageBytes)

		model := resolveAllowed("live model", initialConfig.LiveModel, defaultLiveModel, liveModelRegistry)
		location := resolveAllowed("location", initialConfig.LiveLocation, defaultLiveLocation, locationRegistry)
		initialConfig.LiveModel = model
		initialConfig.LiveLocation = location
		logger := slog.With("mode", mode, "model", model, "location", location)

		config, err := buildLiveConnectConfigForMode(initialConfig, mode)
		if err != nil {
			logger.Warn("invalid session config", "err", err)
			_ = ws.WriteClose(websocket.CloseInvalidFramePayloadData, "Invalid session config")
			return
		}

		ctx, cancel := context.WithCancel(r.Context())
		defer cancel()
		upstream, err := connector.Connect(ctx, model, location, config)
		if err != nil {
			logger.Error("connecting to Live API", "err", err)
			_ = ws.WriteClose(websocket.CloseInternalServerErr, "Failed to connect")
			return
		}

		bridge := livebridge.NewBridge(ctx, ws, upstream, livebridge.BridgeConfig{
			Mode:            mode,
			Model:           model,
			Location:        location,
			GreetingPrompt:  greetingPrompt(liveGreetingForMode(initialConfig, mode)),
			GoodbyePrompt:   goodbyePrompt,
			EmitSessionInfo: true,
			Timings: livebridge.Timings{
				SessionCap:      sessionCapDuration,
				SessionCapGrace: sessionCapGrace,
				GoodbyeBackstop: goodbyeBackstop,
			},
			Tools:  newBuiltInToolRunner(),
			Logger: logger,
		})
		defer bridge.Shutdown(0, "")
		bridge.Run()
	}
}
