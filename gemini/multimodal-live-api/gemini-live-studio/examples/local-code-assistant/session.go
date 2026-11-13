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
	"fmt"
	"log/slog"
	"net/http"
	"os"
	"strings"
	"time"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"

	"local-code-assistant/internal/livebridge"
	"local-code-assistant/tools"
)

const (
	basePersona    = "You are an expert Software Development Assistant and codebase explorer, specializing in Go, TypeScript, Lit WebComponents, and the Gemini API. You have access to local filesystem tools to list directories and read files, as well as Google Search to look up external documentation. When asked to explain or design architectures, sequence flows, components, or system relationships, you can generate technical diagrams using the 'generate_diagram' tool by providing clean Graphviz DOT syntax. Answer concisely and do not return large blocks of text if you read a file; summarize it or extract the relevant code snippets."
	greetingPrompt = "Proactively introduce yourself now. Say exactly this: Hello! I am your local file explorer agent. I can read your directory and files. How can I help?"
)

// Guardrail timings kept as variables so unit tests can shrink them.
var (
	sessionCapDuration = livebridge.DefaultSessionCap
	sessionCapGrace    = livebridge.DefaultSessionCapGrace
	toolCallTimeout    = 30 * time.Second
)

// The assistant can read local files, so only the page this server serves (or
// another loopback page during development) may open the WebSocket; any other
// website could otherwise drive the tools from a visitor's browser.
var localOriginPolicy = livebridge.NewOriginPolicyFromEnv()

var upgrader = websocket.Upgrader{CheckOrigin: allowLocalOrigin}

func allowLocalOrigin(r *http.Request) bool {
	return localOriginPolicy.Allows(r)
}

type liveDialer interface {
	Connect(ctx context.Context, model string, cfg *genai.LiveConnectConfig) (livebridge.Session, error)
}

func buildToolRunner(registry *tools.Registry) *livebridge.ToolRunner {
	fnReg := livebridge.NewFuncRegistry()
	if registry != nil {
		for _, decl := range registry.Declarations() {
			name := decl.Name
			fnReg.Register(decl, func(ctx context.Context, args map[string]any) (map[string]any, error) {
				return registry.Execute(ctx, name, args), nil
			})
		}
	}
	return livebridge.NewToolRunner(livebridge.ToolRunnerConfig{
		Registry:            fnReg,
		Timeout:             toolCallTimeout,
		ServerToolEventType: "tool_execution",
	})
}

func sessionHandler(cfg appConfig, dialer liveDialer, registry *tools.Registry) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			slog.Warn("WebSocket upgrade failed", "err", err)
			return
		}
		ws := livebridge.NewSafeConn(conn)
		ws.SetReadLimit(livebridge.MaxClientMessageBytes)
		defer func() { _ = ws.Close() }()

		requested := r.URL.Query().Get("model")
		model := resolveAllowed("live model", requested, cfg.model, liveModelRegistry)
		logger := slog.With("model", model)
		if requested != "" && model == strings.TrimSpace(requested) {
			logger.Info("client requested session model override")
		}

		ctx, cancel := context.WithCancel(r.Context())
		defer cancel()

		logger.Info("connecting to Gemini Live")
		upstream, err := dialer.Connect(ctx, model, buildLiveConfig(cfg, model, registry))
		if err != nil {
			logger.Error("connecting to Gemini Live", "err", err)
			_ = ws.WriteJSON(map[string]any{"type": "error", "message": fmt.Sprintf("Live connect error: %v", err)})
			_ = ws.WriteClose(websocket.CloseInternalServerErr, "Failed to connect")
			return
		}

		mode := livebridge.ModeAudio
		if cfg.videoAvatar() {
			mode = livebridge.ModeAvatar
		}

		bridge := livebridge.NewBridge(ctx, ws, upstream, livebridge.BridgeConfig{
			Mode:                        mode,
			Model:                       model,
			Location:                    cfg.location,
			GreetingPrompt:              greetingPrompt,
			AudioDelivery:               livebridge.AudioDeliveryBase64JSON,
			StringifyTranscriptFinished: true,
			AllowPlainTextFrames:        true,
			Timings: livebridge.Timings{
				SessionCap:      sessionCapDuration,
				SessionCapGrace: sessionCapGrace,
			},
			OnSetupComplete: func(b *livebridge.Bridge) {
				b.WriteJSON(map[string]any{
					"type":  "connection_state",
					"state": "ready",
					"model": model,
				})
			},
			Tools:  buildToolRunner(registry),
			Logger: logger,
		})
		defer bridge.Shutdown(0, "")
		bridge.Run()
	}
}

// buildLiveConfig returns the session config: Live avatar video when enabled,
// otherwise audio with proactive audio on models that support it.
func buildLiveConfig(cfg appConfig, model string, registry *tools.Registry) *genai.LiveConnectConfig {
	var decls []*genai.FunctionDeclaration
	if registry != nil {
		decls = registry.Declarations()
	}
	config := &genai.LiveConnectConfig{
		ResponseModalities: []genai.Modality{genai.ModalityAudio},
		SystemInstruction:  &genai.Content{Parts: []*genai.Part{{Text: systemInstruction(cfg)}}},
		Tools: []*genai.Tool{{
			GoogleSearch:         &genai.GoogleSearch{},
			FunctionDeclarations: decls,
		}},
		SpeechConfig: &genai.SpeechConfig{
			VoiceConfig: &genai.VoiceConfig{PrebuiltVoiceConfig: &genai.PrebuiltVoiceConfig{VoiceName: cfg.voice}},
		},
		InputAudioTranscription:  &genai.AudioTranscriptionConfig{LanguageCodes: []string{"en-US"}},
		OutputAudioTranscription: &genai.AudioTranscriptionConfig{LanguageCodes: []string{"en-US"}},
	}
	if cfg.videoAvatar() {
		// VIDEO alone: audio is muxed into the fMP4 stream, and VIDEO requires AvatarConfig.
		config.ResponseModalities = []genai.Modality{genai.ModalityVideo}
		config.AvatarConfig = &genai.AvatarConfig{AvatarName: cfg.avatarPreset}
		return config
	}
	if livebridge.SupportsProactiveAudio(model, defaultModel) {
		proactive := true
		config.Proactivity = &genai.ProactivityConfig{ProactiveAudio: &proactive}
	}
	return config
}

// systemInstruction is the built-in persona, or SYSTEM_INSTRUCTION_FILE when
// readable, plus AVATAR_EXTRA_CONTEXT.
func systemInstruction(cfg appConfig) string {
	persona := basePersona
	if cfg.instructionFile != "" {
		override, err := os.ReadFile(cfg.instructionFile)
		if err != nil {
			slog.Warn("reading SYSTEM_INSTRUCTION_FILE; using the default persona", "file", cfg.instructionFile, "err", err)
		} else {
			persona = string(override)
			slog.Info("using system instruction override", "file", cfg.instructionFile, "bytes", len(persona))
		}
	}
	if cfg.extraContext != "" {
		persona += "\n\nAdditional Context:\n" + cfg.extraContext
	}
	return persona
}
