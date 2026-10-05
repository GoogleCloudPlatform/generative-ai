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
package main

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"errors"
	"fmt"
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"sync"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"

	"local-code-assistant/tools"
)

const (
	basePersona        = "You are an expert Software Development Assistant and codebase explorer, specializing in Go, TypeScript, Lit WebComponents, and the Gemini API. You have access to local filesystem tools to list directories and read files, as well as Google Search to look up external documentation. When asked to explain or design architectures, sequence flows, components, or system relationships, you can generate technical diagrams using the 'generate_diagram' tool by providing clean Graphviz DOT syntax. Answer concisely and do not return large blocks of text if you read a file; summarize it or extract the relevant code snippets."
	greetingPrompt     = "Proactively introduce yourself now. Say exactly this: Hello! I am your local file explorer agent. I can read your directory and files. How can I help?"
	defaultVideoCodecs = "avc1.42C020, mp4a.40.2"
)

// The assistant can read local files, so only the page this server serves (or
// another loopback page during development) may open the WebSocket; any other
// website could otherwise drive the tools from a visitor's browser.
var upgrader = websocket.Upgrader{CheckOrigin: allowLocalOrigin}

func allowLocalOrigin(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true
	}
	u, err := url.Parse(origin)
	if err != nil {
		return false
	}
	if strings.EqualFold(u.Host, r.Host) {
		return true
	}
	return isLoopback(u.Hostname()) && isLoopback(hostname(r.Host))
}

func hostname(hostport string) string {
	if h, _, err := net.SplitHostPort(hostport); err == nil {
		return h
	}
	return strings.Trim(hostport, "[]")
}

func isLoopback(host string) bool {
	if strings.EqualFold(host, "localhost") {
		return true
	}
	ip := net.ParseIP(host)
	return ip != nil && ip.IsLoopback()
}

// safeWS serializes writes; gorilla/websocket allows one concurrent writer.
type safeWS struct {
	conn *websocket.Conn
	mu   sync.Mutex
}

func (s *safeWS) WriteJSON(v any) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.WriteJSON(v)
}

func (s *safeWS) WriteMessage(messageType int, data []byte) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.WriteMessage(messageType, data)
}

func (s *safeWS) Close() error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.Close()
}

// ClientMessage is a JSON message from the browser. Non-JSON messages are
// treated as plain text input.
type ClientMessage struct {
	Type     string `json:"type"`
	Data     string `json:"data"`
	MimeType string `json:"mimeType"`
}

func sessionHandler(cfg appConfig, client *genai.Client, registry *tools.Registry) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			slog.Warn("WebSocket upgrade failed", "err", err)
			return
		}
		ws := &safeWS{conn: conn}
		defer func() { _ = ws.Close() }()

		requested := r.URL.Query().Get("model")
		model := resolveAllowed("live model", requested, cfg.model, liveModelRegistry)
		logger := slog.With("model", model)
		if requested != "" && model == strings.TrimSpace(requested) {
			logger.Info("client requested session model override")
		}

		ctx, cancel := context.WithCancel(context.Background())
		defer cancel()

		logger.Info("connecting to Gemini Live")
		upstream, err := client.Live.Connect(ctx, model, buildLiveConfig(cfg, model, registry))
		if err != nil {
			logger.Error("connecting to Gemini Live", "err", err)
			_ = ws.WriteJSON(map[string]any{"type": "error", "message": fmt.Sprintf("Live connect error: %v", err)})
			return
		}
		defer func() { _ = upstream.Close() }()
		logger.Info("Live session established")

		s := &liveSession{cfg: cfg, model: model, ws: ws, upstream: upstream, registry: registry, ctx: ctx, cancel: cancel, logger: logger}
		go s.receiveLoop()
		s.clientLoop()
	}
}

// buildLiveConfig returns the session config: Live avatar video when enabled,
// otherwise audio with proactive audio on models that support it.
func buildLiveConfig(cfg appConfig, model string, registry *tools.Registry) *genai.LiveConnectConfig {
	config := &genai.LiveConnectConfig{
		ResponseModalities: []genai.Modality{genai.ModalityAudio},
		SystemInstruction:  &genai.Content{Parts: []*genai.Part{{Text: systemInstruction(cfg)}}},
		Tools: []*genai.Tool{{
			GoogleSearch:         &genai.GoogleSearch{},
			FunctionDeclarations: registry.Declarations(),
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
	// Full 3.5-flash rejects proactive_audio with 1007; 3.8 and lite accept it.
	if strings.Contains(model, "3.8") || strings.Contains(model, "lite") {
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

// liveSession bridges one browser socket and one Gemini Live session.
type liveSession struct {
	cfg      appConfig
	model    string
	ws       *safeWS
	upstream *genai.Session
	registry *tools.Registry
	ctx      context.Context
	cancel   context.CancelFunc
	logger   *slog.Logger

	sendMu          sync.Mutex // serializes upstream sends
	mediaConfigOnce sync.Once
}

func (s *liveSession) sendRealtime(params genai.LiveSendRealtimeInputParameters) error {
	s.sendMu.Lock()
	defer s.sendMu.Unlock()
	return s.upstream.SendRealtimeInput(params)
}

func (s *liveSession) sendToolResponses(responses []*genai.FunctionResponse) error {
	s.sendMu.Lock()
	defer s.sendMu.Unlock()
	return s.upstream.SendToolResponse(genai.LiveSendToolResponseParameters{FunctionResponses: responses})
}

// disconnect tells the browser the session ended and closes the socket,
// which also ends clientLoop.
func (s *liveSession) disconnect(reason string) {
	_ = s.ws.WriteJSON(map[string]any{"type": "connection_state", "state": "disconnected", "reason": reason})
	_ = s.ws.Close()
	s.cancel()
}

// receiveLoop relays Gemini Live messages to the browser.
func (s *liveSession) receiveLoop() {
	defer s.cancel()
	for s.ctx.Err() == nil {
		msg, err := s.upstream.Receive()
		if err != nil {
			if !errors.Is(err, context.Canceled) && s.ctx.Err() == nil {
				s.logger.Warn("upstream Gemini Live receive ended", "err", err)
				_ = s.ws.WriteJSON(map[string]any{"type": "connection_state", "state": "disconnected", "reason": fmt.Sprintf("Live session ended: %v", err)})
			}
			_ = s.ws.Close()
			return
		}

		if msg.SetupComplete != nil {
			s.logger.Info("setup complete; sending greeting prompt")
			_ = s.ws.WriteJSON(map[string]any{"type": "connection_state", "state": "ready", "model": s.model})
			go func() {
				if err := s.sendRealtime(genai.LiveSendRealtimeInputParameters{Text: greetingPrompt}); err != nil {
					s.logger.Warn("sending greeting prompt", "err", err)
				}
			}()
		}
		if msg.ServerContent != nil {
			s.handleServerContent(msg.ServerContent)
		}
		if msg.ToolCall != nil {
			s.handleToolCall(msg.ToolCall)
		}
	}
}

func (s *liveSession) handleServerContent(content *genai.LiveServerContent) {
	if content.ModelTurn != nil {
		for _, part := range content.ModelTurn.Parts {
			if part.InlineData != nil {
				s.relayMedia(part.InlineData)
			}
		}
	}
	// The page expects "finished" as the string "true"/"false".
	if t := content.InputTranscription; t != nil {
		_ = s.ws.WriteJSON(map[string]any{"type": "input_transcript", "text": t.Text, "finished": fmt.Sprint(t.Finished)})
	}
	if t := content.OutputTranscription; t != nil && t.Text != "" {
		_ = s.ws.WriteJSON(map[string]any{"type": "output_transcript", "text": t.Text, "finished": fmt.Sprint(t.Finished)})
	}
	if content.Interrupted {
		_ = s.ws.WriteJSON(map[string]any{"type": "interrupted"})
	}
}

// relayMedia sends fMP4 video as binary frames (video avatar mode) and audio
// as base64 JSON for the page's audio player.
func (s *liveSession) relayMedia(media *genai.Blob) {
	if s.cfg.videoAvatar() {
		s.mediaConfigOnce.Do(func() {
			s.logger.Info("first media packet; sending media_config", "mimeType", media.MIMEType, "bytes", len(media.Data), "codecs", defaultVideoCodecs)
			_ = s.ws.WriteJSON(map[string]string{"type": "media_config", "mimeType": "video/mp4", "codecs": defaultVideoCodecs})
		})
		if strings.HasPrefix(media.MIMEType, "video/") {
			_ = s.ws.WriteMessage(websocket.BinaryMessage, media.Data)
			return
		}
	}
	_ = s.ws.WriteJSON(map[string]any{"type": "audio", "data": base64.StdEncoding.EncodeToString(media.Data)})
}

// handleToolCall runs local tools, shows each call in the page, and returns
// the results to the model.
func (s *liveSession) handleToolCall(toolCall *genai.LiveServerToolCall) {
	var responses []*genai.FunctionResponse
	for _, call := range toolCall.FunctionCalls {
		if call == nil {
			continue
		}
		result := s.registry.Execute(s.ctx, call.Name, call.Args)
		responses = append(responses, &genai.FunctionResponse{ID: call.ID, Name: call.Name, Response: result})
		_ = s.ws.WriteJSON(map[string]any{"type": "tool_execution", "name": call.Name, "args": call.Args, "result": result})
	}
	s.logger.Info("sending tool responses", "count", len(responses))
	if err := s.sendToolResponses(responses); err != nil {
		s.logger.Warn("sending tool responses", "err", err)
	}
}

// clientLoop forwards browser messages to Gemini Live until the browser
// disconnects or the upstream session fails.
func (s *liveSession) clientLoop() {
	for {
		_, data, err := s.ws.conn.ReadMessage()
		if err != nil {
			s.cancel()
			return
		}
		var msg ClientMessage
		if err := json.Unmarshal(data, &msg); err != nil {
			// Not JSON: treat the raw message as text input.
			msg = ClientMessage{Type: "text", Data: string(data)}
		}
		if !s.handleClientMessage(msg) {
			return
		}
	}
}

// handleClientMessage returns false once the session has been torn down.
func (s *liveSession) handleClientMessage(msg ClientMessage) bool {
	var params genai.LiveSendRealtimeInputParameters
	switch msg.Type {
	case "ping":
		_ = s.ws.WriteJSON(map[string]any{"type": "pong"})
		return true
	case "text":
		params.Text = msg.Data
	case "audio":
		audio, err := base64.StdEncoding.DecodeString(msg.Data)
		if err != nil {
			return true
		}
		params.Audio = &genai.Blob{MIMEType: msg.MimeType, Data: audio}
	default:
		return true
	}
	if err := s.sendRealtime(params); err != nil {
		s.logger.Warn("sending input to Gemini Live", "type", msg.Type, "err", err)
		s.disconnect(fmt.Sprintf("Live session write failed: %v", err))
		return false
	}
	return true
}
