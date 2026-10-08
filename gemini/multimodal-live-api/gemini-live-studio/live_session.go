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
	"context"
	"encoding/base64"
	"log/slog"
	"net/http"
	"strings"
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"
)

// Durations for the Live session guardrails; variables so tests can shrink them.
var (
	// Proactively cap sessions at 9m55s to avoid the abrupt 10-minute API cutoff.
	sessionCapDuration = 9*time.Minute + 55*time.Second
	// Time between the session_limit_reached notice and the actual close.
	sessionCapGrace = 2 * time.Second
	// Close anyway if the goodbye turn never completes after "End Session".
	goodbyeBackstop = 12 * time.Second
)

const (
	goodbyePrompt       = "The user has clicked the 'End Session' button to disconnect. Please say a very brief, warm goodbye right now."
	defaultVideoCodecs  = "avc1.42C020, mp4a.40.2"
	defaultPCMRateHz    = 24000
	defaultFrameMIME    = "image/jpeg"
	maxLoggedValueRunes = 40
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
type ClientMessage struct {
	Type     string         `json:"type"`
	Action   string         `json:"action"`
	Data     string         `json:"data"`     // base64 encoded audio, or raw text
	MimeType string         `json:"mimeType"` // e.g., "audio/pcm"
	ID       string         `json:"id,omitempty"`
	Name     string         `json:"name,omitempty"`
	Response map[string]any `json:"response,omitempty"`
}

// terminateGate decides when it is safe to close a Live session after a
// client-requested "End Session": it must not close on the TurnComplete of a
// turn that was merely interrupted by the goodbye injection, only on the
// TurnComplete of the goodbye's own turn.
//
// Interrupted and TurnComplete arrive as two separate messages (~140-150ms
// apart in captured wire traces), and every
// interruption produces exactly two TurnComplete events: one for the aborted
// turn and one for the goodbye. So the first TurnComplete after an
// interruption is skipped and the next one closes the session.
type terminateGate struct {
	terminating      atomic.Bool
	pendingInterrupt atomic.Bool
}

func (g *terminateGate) requestTerminate() {
	g.terminating.Store(true)
}

func (g *terminateGate) onInterrupted() {
	g.pendingInterrupt.Store(true)
}

func (g *terminateGate) onTurnComplete() bool {
	if g.pendingInterrupt.CompareAndSwap(true, false) {
		// This TurnComplete wraps up the turn we interrupted, not the goodbye.
		return false
	}
	return g.terminating.Load()
}

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

// liveSessionHandlerForMode bridges a browser WebSocket to a Gemini Live
// session: liveModeAvatar (/ws, fMP4 video) or liveModeAudio (/ws/live, PCM).
func liveSessionHandlerForMode(mode liveMode, connector liveConnector, defaultLiveModel, defaultLiveLocation string) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		conn, err := upgrader.Upgrade(w, r, nil)
		if err != nil {
			slog.Warn("upgrading WebSocket", "err", err)
			return
		}
		ws := &safeWS{conn: conn}
		defer func() { _ = ws.Close() }()

		// The first message may carry a custom avatar image; everything after
		// it is media chunks and text, so the limit is tightened after it.
		conn.SetReadLimit(maxInitialConfigBytes)
		var initialConfig InitialConfig
		if err := ws.ReadJSON(&initialConfig); err != nil {
			slog.Warn("reading initial session config", "err", err)
			return
		}
		conn.SetReadLimit(maxClientMessageBytes)

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

		s := &liveSession{
			mode:     mode,
			ws:       ws,
			upstream: upstream,
			ctx:      ctx,
			cancel:   cancel,
			logger:   logger,
		}
		defer s.shutdown(0, "")
		s.run(model, location, liveGreetingForMode(initialConfig, mode))
	}
}

// liveSession owns one bridged session: the browser socket, the upstream Live
// session, and the timers that end it.
type liveSession struct {
	mode     liveMode
	ws       *safeWS
	upstream liveSessionAdapter
	ctx      context.Context
	cancel   context.CancelFunc
	logger   *slog.Logger

	// sendMu serializes upstream sends, which come from the client loop, the
	// receive loop (tool responses) and the greeting goroutine.
	sendMu       sync.Mutex
	shutdownOnce sync.Once
	gate         terminateGate

	timersMu      sync.Mutex
	capGraceTimer *time.Timer
	backstopTimer *time.Timer

	mediaConfigOnce sync.Once
	warnAudioMIME   sync.Once
	warnVideoMIME   sync.Once
}

// run sends session_info, starts the session cap, and pumps messages in both
// directions until either side ends the session. It returns only after the
// receive loop has exited, so no goroutine outlives the handler.
func (s *liveSession) run(model, location, greeting string) {
	s.logger.Info("Live session established")
	s.writeJSON(map[string]string{
		"type":     "session_info",
		"mode":     string(s.mode),
		"model":    model,
		"location": location,
	})

	capTimer := time.AfterFunc(sessionCapDuration, s.onSessionCap)
	defer func() {
		capTimer.Stop()
		s.stopTimers()
	}()

	receiveDone := make(chan struct{})
	go func() {
		defer close(receiveDone)
		s.receiveLoop(greeting)
	}()
	s.clientLoop()

	// Client left, a close path fired, or the read limit was hit.
	s.shutdown(0, "")
	<-receiveDone
}

// shutdown is the single, idempotent exit path. genai's Live.Connect ignores
// ctx, so cancel() alone closes nothing: both the Live session and the
// browser socket are closed explicitly, which also unblocks
// upstream.Receive() and ws.ReadJSON() so both loops exit. code 0 means
// "close without a close frame".
func (s *liveSession) shutdown(code int, reason string) {
	s.shutdownOnce.Do(func() {
		s.cancel()
		if code != 0 {
			_ = s.ws.WriteClose(code, reason)
		}
		_ = s.upstream.Close()
		_ = s.ws.Close()
	})
}

func (s *liveSession) stopTimers() {
	s.timersMu.Lock()
	defer s.timersMu.Unlock()
	if s.capGraceTimer != nil {
		s.capGraceTimer.Stop()
	}
	if s.backstopTimer != nil {
		s.backstopTimer.Stop()
	}
}

// onSessionCap warns the client, then closes after sessionCapGrace.
func (s *liveSession) onSessionCap() {
	s.logger.Info("session cap reached; closing gracefully")
	s.writeJSON(map[string]string{"type": "status", "error": "session_limit_reached"})
	s.timersMu.Lock()
	defer s.timersMu.Unlock()
	s.capGraceTimer = time.AfterFunc(sessionCapGrace, func() {
		s.shutdown(websocket.CloseNormalClosure, "Session limit reached")
	})
}

// writeJSON sends a control message to the browser. Failures are ignored here:
// a dead socket also fails the next binary write or read, which shuts down.
func (s *liveSession) writeJSON(v any) {
	_ = s.ws.WriteJSON(v)
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

// forward runs an upstream send. A send failure means the Live connection is
// gone, so the session is torn down instead of forwarding into a dead session.
func (s *liveSession) forward(what string, send func() error) {
	if err := send(); err != nil {
		if s.ctx.Err() == nil {
			s.logger.Warn("sending to Live session", "what", what, "err", err)
		}
		s.shutdown(websocket.CloseInternalServerErr, "Session disconnected")
	}
}

// receiveLoop relays Live server messages to the browser until the upstream
// session ends or a close path fires.
func (s *liveSession) receiveLoop(greeting string) {
	for {
		msg, err := s.upstream.Receive()
		if err != nil {
			if s.ctx.Err() == nil {
				s.logger.Warn("Live session receive failed", "err", err)
			}
			s.shutdown(websocket.CloseInternalServerErr, "Session disconnected")
			return
		}

		if msg.SetupComplete != nil {
			// Prompt the assistant to greet first instead of waiting silently.
			s.logger.Debug("setup complete; sending greeting prompt")
			go s.forward("greeting prompt", func() error {
				return s.sendRealtime(genai.LiveSendRealtimeInputParameters{Text: greetingPrompt(greeting)})
			})
		}
		if msg.ServerContent != nil && !s.handleServerContent(msg.ServerContent) {
			return
		}
		if msg.ToolCall != nil {
			s.handleToolCall(msg.ToolCall)
		}
		if msg.ToolCallCancellation != nil && len(msg.ToolCallCancellation.IDs) > 0 {
			s.logger.Info("tool calls cancelled", "ids", msg.ToolCallCancellation.IDs)
			s.writeJSON(map[string]any{"type": "tool_call_cancellation", "ids": msg.ToolCallCancellation.IDs})
		}
	}
}

// handleServerContent relays model output, transcripts and turn signals. It
// returns false when the session has been shut down.
func (s *liveSession) handleServerContent(content *genai.LiveServerContent) bool {
	if content.ModelTurn != nil {
		for _, part := range content.ModelTurn.Parts {
			if part.InlineData != nil {
				s.sendMediaConfigOnce(part.InlineData)
				if err := s.ws.WriteMessage(websocket.BinaryMessage, part.InlineData.Data); err != nil {
					if s.ctx.Err() == nil {
						s.logger.Warn("writing media to browser", "err", err)
					}
					s.shutdown(0, "")
					return false
				}
			} else if part.Text != "" {
				s.writeJSON(map[string]string{"type": "transcript", "text": part.Text})
			}
		}
	}
	s.relayTranscription("input_transcript", content.InputTranscription)
	s.relayTranscription("output_transcript", content.OutputTranscription)

	if content.Interrupted {
		s.logger.Debug("model turn interrupted")
		s.writeJSON(map[string]string{"type": "interrupted"})
		s.gate.onInterrupted()
	}
	if content.TurnComplete && s.gate.onTurnComplete() {
		s.logger.Info("goodbye turn complete; closing session")
		s.shutdown(websocket.CloseNormalClosure, "Session terminated")
		return false
	}
	return true
}

// relayTranscription forwards partial and final transcripts (the frontend
// merges partials). Transcripts are user content, so only their size is logged.
func (s *liveSession) relayTranscription(messageType string, transcription *genai.Transcription) {
	if transcription == nil || transcription.Text == "" {
		return
	}
	s.logger.Debug("transcript", "type", messageType, "chars", len(transcription.Text), "finished", transcription.Finished)
	s.writeJSON(map[string]any{
		"type":     messageType,
		"text":     transcription.Text,
		"finished": transcription.Finished,
	})
}

// sendMediaConfigOnce tells the browser how to decode the media stream, using
// the first chunk: the PCM sample rate (audio mode) or the fMP4 codecs sniffed
// from ftyp/avcC (avatar mode).
func (s *liveSession) sendMediaConfigOnce(media *genai.Blob) {
	s.mediaConfigOnce.Do(func() {
		if s.mode == liveModeAudio {
			sampleRate := parsePCMSampleRate(media.MIMEType)
			if sampleRate == 0 {
				sampleRate = defaultPCMRateHz
			}
			s.writeJSON(map[string]any{"type": "media_config", "mimeType": "audio/pcm", "sampleRate": sampleRate})
			return
		}
		codecs := defaultVideoCodecs
		if sniff := SniffMP4(media.Data); len(sniff.Codecs) > 0 {
			codecs = strings.Join(sniff.Codecs, ", ")
		}
		s.writeJSON(map[string]string{"type": "media_config", "mimeType": "video/mp4", "codecs": codecs})
	})
}

// handleToolCall runs server-side tools, shows each call in the browser, and
// returns the results to the model.
func (s *liveSession) handleToolCall(toolCall *genai.LiveServerToolCall) {
	s.logger.Info("tool call", "calls", len(toolCall.FunctionCalls))
	var responses []*genai.FunctionResponse
	for _, call := range toolCall.FunctionCalls {
		if call == nil {
			continue
		}
		result := executeBuiltInTool(call.Name, call.Args)
		responses = append(responses, &genai.FunctionResponse{ID: call.ID, Name: call.Name, Response: result})
		s.writeJSON(map[string]any{
			"type":   "tool_call",
			"id":     call.ID,
			"name":   call.Name,
			"args":   call.Args,
			"result": result,
		})
	}
	if len(responses) > 0 {
		s.forward("tool response", func() error { return s.sendToolResponses(responses) })
	}
}

// clientLoop reads browser messages and forwards them upstream until the
// browser disconnects or a close path fires.
func (s *liveSession) clientLoop() {
	for s.ctx.Err() == nil {
		var msg ClientMessage
		if err := s.ws.ReadJSON(&msg); err != nil {
			if s.ctx.Err() == nil && websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure, websocket.CloseNormalClosure) {
				s.logger.Warn("reading from browser", "err", err)
			}
			return
		}
		s.handleClientMessage(msg)
	}
}

func (s *liveSession) handleClientMessage(msg ClientMessage) {
	switch msg.Type {
	case "control":
		if msg.Action == "terminate" {
			s.requestTerminate()
		}
	case "text":
		s.forward("text", func() error {
			return s.sendRealtime(genai.LiveSendRealtimeInputParameters{Text: msg.Data})
		})
	case "audio":
		s.forwardAudio(msg)
	case "video":
		s.forwardVideoFrame(msg)
	case "tool_response":
		if msg.Name == "" {
			return
		}
		s.forward("tool response", func() error {
			return s.sendToolResponses([]*genai.FunctionResponse{{ID: msg.ID, Name: msg.Name, Response: msg.Response}})
		})
	}
}

// requestTerminate asks the model for a goodbye; the session closes on the
// goodbye's TurnComplete (terminateGate) or after goodbyeBackstop.
func (s *liveSession) requestTerminate() {
	s.logger.Info("client requested end of session; sending goodbye prompt")
	s.gate.requestTerminate()
	s.forward("goodbye prompt", func() error {
		return s.sendRealtime(genai.LiveSendRealtimeInputParameters{Text: goodbyePrompt})
	})

	s.timersMu.Lock()
	defer s.timersMu.Unlock()
	if s.backstopTimer != nil { // repeated clicks share one backstop
		return
	}
	s.backstopTimer = time.AfterFunc(goodbyeBackstop, func() {
		if s.ctx.Err() == nil {
			s.logger.Info("goodbye backstop expired; closing session")
		}
		s.shutdown(websocket.CloseNormalClosure, "Session terminated")
	})
}

func (s *liveSession) forwardAudio(msg ClientMessage) {
	audio, err := base64.StdEncoding.DecodeString(msg.Data)
	if err != nil {
		s.logger.Warn("dropping audio chunk with invalid base64", "err", err)
		return
	}
	if !validRealtimeAudioMIME(msg.MimeType) {
		s.warnAudioMIME.Do(func() {
			s.logger.Warn("dropping audio with unsupported MIME type (want audio/pcm[;rate=N])", "mimeType", truncateRunes(msg.MimeType, maxLoggedValueRunes))
		})
		return
	}
	s.forward("audio", func() error {
		return s.sendRealtime(genai.LiveSendRealtimeInputParameters{Audio: &genai.Blob{MIMEType: msg.MimeType, Data: audio}})
	})
}

func (s *liveSession) forwardVideoFrame(msg ClientMessage) {
	frame, err := base64.StdEncoding.DecodeString(msg.Data)
	if err != nil {
		s.logger.Warn("dropping video frame with invalid base64", "err", err)
		return
	}
	mimeType := msg.MimeType
	if mimeType == "" {
		mimeType = defaultFrameMIME
	}
	if !realtimeVideoMIMETypes[mimeType] {
		s.warnVideoMIME.Do(func() {
			s.logger.Warn("dropping video frames with unsupported MIME type (want image/jpeg or image/png)", "mimeType", truncateRunes(mimeType, maxLoggedValueRunes))
		})
		return
	}
	// Video, not Media: Media serializes to legacy mediaChunks and fails with 1007.
	s.forward("video frame", func() error {
		return s.sendRealtime(genai.LiveSendRealtimeInputParameters{Video: &genai.Blob{MIMEType: mimeType, Data: frame}})
	})
}
