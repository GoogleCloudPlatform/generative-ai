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

package livebridge

import (
	"context"
	"encoding/base64"
	"encoding/json"
	"log/slog"
	"strings"
	"sync"
	"time"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"
)

// Default session guardrail timings.
const (
	DefaultSessionCap      = 9*time.Minute + 55*time.Second
	DefaultSessionCapGrace = 2 * time.Second
	DefaultGoodbyeBackstop = 12 * time.Second
	DefaultPCMRateHz       = 24000
	DefaultFrameMIME       = "image/jpeg"
	DefaultGoodbyePrompt   = "The user has clicked the 'End Session' button to disconnect. Please say a very brief, warm goodbye right now."
)

// Mode identifies whether a Live session streams muxed avatar fMP4 video or
// audio-only PCM.
type Mode string

const (
	ModeAvatar Mode = "avatar"
	ModeAudio  Mode = "audio"
)

// AudioDelivery controls how audio-mode InlineData chunks are sent over the
// browser WebSocket.
type AudioDelivery string

const (
	// AudioDeliveryBinary streams raw PCM bytes as binary WebSocket frames
	// preceded once by {"type": "media_config", "mimeType": "audio/pcm", "sampleRate": N}.
	AudioDeliveryBinary AudioDelivery = "binary"
	// AudioDeliveryBase64JSON sends {"type": "audio", "data": "<base64>"} JSON
	// text frames for lightweight single-file HTML clients.
	AudioDeliveryBase64JSON AudioDelivery = "base64_json"
)

// Timings configures session guardrail timers. Zero values use package defaults.
type Timings struct {
	SessionCap      time.Duration
	SessionCapGrace time.Duration
	GoodbyeBackstop time.Duration
}

// ClientMessage represents any runtime JSON frame sent by the browser after
// initial setup.
type ClientMessage struct {
	Type     string         `json:"type"`
	Action   string         `json:"action,omitempty"`
	Data     string         `json:"data,omitempty"`
	MimeType string         `json:"mimeType,omitempty"`
	ID       string         `json:"id,omitempty"`
	Name     string         `json:"name,omitempty"`
	Response map[string]any `json:"response,omitempty"`
	Result   map[string]any `json:"result,omitempty"`
	Image    string         `json:"image,omitempty"`
	Enabled  bool           `json:"enabled,omitempty"`
	ExecMs   int64          `json:"execMs,omitempty"`
}

// BridgeConfig configures a single bridged browser <-> Gemini Live session.
type BridgeConfig struct {
	Mode           Mode
	Model          string
	Location       string
	GreetingPrompt string
	GoodbyePrompt  string
	Timings        Timings

	// EmitSessionInfo emits {"type": "session_info", ...} when Run starts.
	EmitSessionInfo bool
	// EmitTurnComplete forwards {"type": "turn_complete"} on TurnComplete.
	EmitTurnComplete bool
	// StringifyTranscriptFinished emits "finished": "true"/"false" strings
	// instead of JSON booleans for legacy single-file HTML pages.
	StringifyTranscriptFinished bool
	// AllowPlainTextFrames treats non-JSON client text frames as {"type": "text"}.
	AllowPlainTextFrames bool
	// MaxClientTextRunes optionally truncates inbound client text messages (>0).
	MaxClientTextRunes int
	// AudioDelivery defaults to AudioDeliveryBinary.
	AudioDelivery AudioDelivery
	// AudioConfigEventType overrides the JSON "type" emitted once before audio
	// chunks (defaults to "media_config"; set "audio_config" when required).
	AudioConfigEventType string
	// ImmediateSessionCapClose closes the WebSocket immediately after sending the
	// session_limit_reached status message rather than waiting SessionCapGrace.
	ImmediateSessionCapClose bool

	Tools  *ToolRunner
	Alerts <-chan Alert
	// FormatAlert converts an Alert from Alerts into the prompt text injected
	// upstream and an optional JSON payload sent to the browser.
	FormatAlert func(Alert) (prompt string, browserMsg any)

	// OnSetupComplete is an optional hook invoked when upstream SetupComplete arrives.
	OnSetupComplete func(b *Bridge)
	// OnCustomClientMessage handles app-specific client message types (e.g.
	// "see_results", "set_proactive"). Return true if handled.
	OnCustomClientMessage func(b *Bridge, msg ClientMessage) bool

	Logger *slog.Logger
}

// Bridge owns a single browser WebSocket <-> Vertex Gemini Live session pair,
// guaranteeing serialized writes and race-free dual teardown on every exit path.
type Bridge struct {
	ws       *SafeConn
	upstream Session
	cfg      BridgeConfig
	ctx      context.Context
	cancel   context.CancelFunc
	logger   *slog.Logger

	sendMu       sync.Mutex
	shutdownOnce sync.Once
	setupOnce    sync.Once
	setupReady   chan struct{}
	gate         TerminateGate

	timersMu      sync.Mutex
	capGraceTimer *time.Timer
	backstopTimer *time.Timer

	mediaConfigOnce sync.Once
	warnAudioMIME   sync.Once
	warnVideoMIME   sync.Once
}

// NewBridge constructs a Bridge bound to parentCtx.
func NewBridge(parentCtx context.Context, ws *SafeConn, upstream Session, cfg BridgeConfig) *Bridge {
	if parentCtx == nil {
		parentCtx = context.Background()
	}
	if cfg.Timings.SessionCap <= 0 {
		cfg.Timings.SessionCap = DefaultSessionCap
	}
	if cfg.Timings.SessionCapGrace <= 0 {
		cfg.Timings.SessionCapGrace = DefaultSessionCapGrace
	}
	if cfg.Timings.GoodbyeBackstop <= 0 {
		cfg.Timings.GoodbyeBackstop = DefaultGoodbyeBackstop
	}
	if cfg.GoodbyePrompt == "" {
		cfg.GoodbyePrompt = DefaultGoodbyePrompt
	}
	if cfg.AudioDelivery == "" {
		cfg.AudioDelivery = AudioDeliveryBinary
	}
	logger := cfg.Logger
	if logger == nil {
		logger = slog.Default()
	}
	ctx, cancel := context.WithCancel(parentCtx)
	return &Bridge{
		ws:         ws,
		upstream:   upstream,
		cfg:        cfg,
		ctx:        ctx,
		cancel:     cancel,
		logger:     logger,
		setupReady: make(chan struct{}),
	}
}

func (b *Bridge) markSetupReady() {
	b.setupOnce.Do(func() {
		close(b.setupReady)
	})
}

// Context returns the session's cancellation context.
func (b *Bridge) Context() context.Context { return b.ctx }

// WriteJSON sends a JSON control message to the browser.
func (b *Bridge) WriteJSON(v any) {
	_ = b.ws.WriteJSON(v)
}

// SendRealtime sends a serialized RealtimeInput payload to the upstream Live session.
func (b *Bridge) SendRealtime(params genai.LiveSendRealtimeInputParameters) error {
	b.sendMu.Lock()
	defer b.sendMu.Unlock()
	return b.upstream.SendRealtimeInput(params)
}

// SendToolResponses sends serialized FunctionResponses to the upstream Live session.
func (b *Bridge) SendToolResponses(responses []*genai.FunctionResponse) error {
	b.sendMu.Lock()
	defer b.sendMu.Unlock()
	return b.upstream.SendToolResponse(genai.LiveSendToolResponseParameters{FunctionResponses: responses})
}

// Forward executes send and triggers Shutdown(1011) if the upstream session failed.
func (b *Bridge) Forward(what string, send func() error) {
	if err := send(); err != nil {
		b.onUpstreamSendErr(what, err)
	}
}

func (b *Bridge) onUpstreamSendErr(what string, err error) {
	if b.ctx.Err() == nil {
		b.logger.Warn("sending to Live session", "what", what, "err", err)
	}
	b.Shutdown(websocket.CloseInternalServerErr, "Session disconnected")
}

// Run pumps messages in both directions until either side ends the session or a
// guardrail timer fires. Run blocks until all background loops and tool
// goroutines have exited.
func (b *Bridge) Run() {
	b.logger.Info("Live session established")
	if b.cfg.EmitSessionInfo {
		b.WriteJSON(map[string]string{
			"type":     "session_info",
			"mode":     string(b.cfg.Mode),
			"model":    b.cfg.Model,
			"location": b.cfg.Location,
		})
	}

	capTimer := time.AfterFunc(b.cfg.Timings.SessionCap, b.onSessionCap)
	defer func() {
		capTimer.Stop()
		b.stopTimers()
	}()

	var loops sync.WaitGroup
	loops.Add(1)
	go func() {
		defer loops.Done()
		b.receiveLoop()
	}()

	if b.cfg.Alerts != nil && b.cfg.FormatAlert != nil {
		loops.Add(1)
		go func() {
			defer loops.Done()
			b.alertLoop()
		}()
	}

	b.clientLoop()
	b.Shutdown(0, "")
	loops.Wait()
	if b.cfg.Tools != nil {
		b.cfg.Tools.Close()
	}
}

// Shutdown is the single idempotent exit path. Because genai's Live.Connect
// ignores context cancellation after dialing, both the upstream Live session
// and the browser WebSocket are closed explicitly to unblock Receive() and
// ReadMessage(). Pass code == 0 to close without sending a close control frame.
func (b *Bridge) Shutdown(code int, reason string) {
	b.shutdownOnce.Do(func() {
		b.cancel()
		if b.cfg.Tools != nil {
			// Cancel timers/contexts immediately; Run() awaits goroutines.
			b.cfg.Tools.CancelAll()
		}
		if code != 0 {
			_ = b.ws.WriteClose(code, reason)
		}
		_ = b.upstream.Close()
		_ = b.ws.Close()
	})
}

func (b *Bridge) stopTimers() {
	b.timersMu.Lock()
	defer b.timersMu.Unlock()
	if b.capGraceTimer != nil {
		b.capGraceTimer.Stop()
	}
	if b.backstopTimer != nil {
		b.backstopTimer.Stop()
	}
}

func (b *Bridge) onSessionCap() {
	b.logger.Info("session cap reached; closing gracefully")
	b.WriteJSON(map[string]string{
		"type":    "status",
		"error":   "session_limit_reached",
		"message": "session_limit_reached",
	})
	if b.cfg.ImmediateSessionCapClose {
		b.Shutdown(websocket.CloseNormalClosure, "Session limit reached")
		return
	}
	b.timersMu.Lock()
	defer b.timersMu.Unlock()
	b.capGraceTimer = time.AfterFunc(b.cfg.Timings.SessionCapGrace, func() {
		b.Shutdown(websocket.CloseNormalClosure, "Session limit reached")
	})
}

func (b *Bridge) alertLoop() {
	for {
		select {
		case <-b.ctx.Done():
			return
		case alert, ok := <-b.cfg.Alerts:
			if !ok {
				return
			}
			select {
			case <-b.setupReady:
			case <-b.ctx.Done():
				return
			}
			prompt, browserMsg := b.cfg.FormatAlert(alert)
			if browserMsg != nil {
				b.WriteJSON(browserMsg)
			}
			if strings.TrimSpace(prompt) != "" {
				b.Forward("proactive alert", func() error {
					return b.SendRealtime(genai.LiveSendRealtimeInputParameters{Text: prompt})
				})
			}
		}
	}
}

func (b *Bridge) receiveLoop() {
	for {
		msg, err := b.upstream.Receive()
		if err != nil {
			if b.ctx.Err() == nil {
				b.logger.Warn("Live session receive failed", "err", err)
			}
			b.Shutdown(websocket.CloseInternalServerErr, "Session disconnected")
			return
		}

		if msg.SetupComplete != nil {
			if b.cfg.OnSetupComplete != nil {
				b.cfg.OnSetupComplete(b)
			}
			if b.cfg.GreetingPrompt != "" {
				b.logger.Debug("setup complete; sending greeting prompt")
				prompt := b.cfg.GreetingPrompt
				go func() {
					b.Forward("greeting prompt", func() error {
						return b.SendRealtime(genai.LiveSendRealtimeInputParameters{Text: prompt})
					})
					b.markSetupReady()
				}()
			} else {
				b.markSetupReady()
			}
		}
		if msg.ServerContent != nil && !b.handleServerContent(msg.ServerContent) {
			return
		}
		if msg.ToolCall != nil && b.cfg.Tools != nil {
			b.logger.Info("tool call", "calls", len(msg.ToolCall.FunctionCalls))
			b.cfg.Tools.Dispatch(b.ctx, msg.ToolCall, b.WriteJSON, b.SendRealtime, b.SendToolResponses, b.onUpstreamSendErr)
		}
		if msg.ToolCallCancellation != nil && len(msg.ToolCallCancellation.IDs) > 0 {
			b.logger.Info("tool calls cancelled", "ids", msg.ToolCallCancellation.IDs)
			if b.cfg.Tools != nil {
				b.cfg.Tools.Cancel(msg.ToolCallCancellation.IDs, b.WriteJSON)
			} else {
				b.WriteJSON(map[string]any{"type": "tool_call_cancellation", "ids": msg.ToolCallCancellation.IDs})
			}
		}
	}
}

func (b *Bridge) handleServerContent(content *genai.LiveServerContent) bool {
	if content.ModelTurn != nil {
		for _, part := range content.ModelTurn.Parts {
			if part.InlineData != nil {
				if !b.relayInlineMedia(part.InlineData) {
					return false
				}
			} else if part.Text != "" {
				b.WriteJSON(map[string]string{"type": "transcript", "text": part.Text})
			}
		}
	}
	b.relayTranscription("input_transcript", content.InputTranscription)
	b.relayTranscription("output_transcript", content.OutputTranscription)

	if content.Interrupted {
		b.logger.Debug("model turn interrupted")
		b.WriteJSON(map[string]string{"type": "interrupted"})
		b.gate.OnInterrupted()
	}
	if content.TurnComplete {
		if b.cfg.EmitTurnComplete {
			b.WriteJSON(map[string]string{"type": "turn_complete"})
		}
		if b.gate.OnTurnComplete() {
			b.logger.Info("goodbye turn complete; closing session")
			b.Shutdown(websocket.CloseNormalClosure, "Session terminated")
			return false
		}
	}
	return true
}

func (b *Bridge) relayInlineMedia(media *genai.Blob) bool {
	if len(media.Data) == 0 {
		return true
	}
	if b.cfg.Mode == ModeAudio && b.cfg.AudioDelivery == AudioDeliveryBase64JSON {
		if b.cfg.AudioConfigEventType != "" {
			b.sendMediaConfigOnce(media)
		}
		mime := media.MIMEType
		if mime == "" {
			mime = "audio/pcm;rate=24000"
		}
		if err := b.ws.WriteJSON(map[string]any{
			"type":     "audio",
			"data":     base64.StdEncoding.EncodeToString(media.Data),
			"mimeType": mime,
		}); err != nil {
			b.Shutdown(0, "")
			return false
		}
		return true
	}
	b.sendMediaConfigOnce(media)
	if err := b.ws.WriteMessage(websocket.BinaryMessage, media.Data); err != nil {
		if b.ctx.Err() == nil {
			b.logger.Warn("writing media to browser", "err", err)
		}
		b.Shutdown(0, "")
		return false
	}
	return true
}

func (b *Bridge) relayTranscription(messageType string, transcription *genai.Transcription) {
	if transcription == nil || transcription.Text == "" {
		return
	}
	b.logger.Debug("transcript", "type", messageType, "chars", len(transcription.Text), "finished", transcription.Finished)
	var finished any = transcription.Finished
	if b.cfg.StringifyTranscriptFinished {
		if transcription.Finished {
			finished = "true"
		} else {
			finished = "false"
		}
	}
	b.WriteJSON(map[string]any{
		"type":     messageType,
		"text":     transcription.Text,
		"finished": finished,
	})
}

func (b *Bridge) sendMediaConfigOnce(media *genai.Blob) {
	b.mediaConfigOnce.Do(func() {
		if b.cfg.Mode == ModeAudio {
			sampleRate := ParsePCMSampleRate(media.MIMEType)
			if sampleRate == 0 {
				sampleRate = DefaultPCMRateHz
			}
			evtType := b.cfg.AudioConfigEventType
			if evtType == "" {
				evtType = "media_config"
			}
			mime := "audio/pcm"
			if b.cfg.AudioConfigEventType != "" && media.MIMEType != "" {
				mime = media.MIMEType
			}
			b.WriteJSON(map[string]any{"type": evtType, "mimeType": mime, "sampleRate": sampleRate})
			return
		}
		codecs := DefaultVideoCodecs
		if sniff := SniffMP4(media.Data); len(sniff.Codecs) > 0 {
			codecs = strings.Join(sniff.Codecs, ", ")
		}
		b.WriteJSON(map[string]string{"type": "media_config", "mimeType": "video/mp4", "codecs": codecs})
	})
}

func (b *Bridge) clientLoop() {
	for b.ctx.Err() == nil {
		_, data, err := b.ws.ReadMessage()
		if err != nil {
			if b.ctx.Err() == nil && websocket.IsUnexpectedCloseError(err, websocket.CloseGoingAway, websocket.CloseAbnormalClosure, websocket.CloseNormalClosure) {
				b.logger.Warn("reading from browser", "err", err)
			}
			return
		}
		var msg ClientMessage
		if err := json.Unmarshal(data, &msg); err != nil {
			if b.cfg.AllowPlainTextFrames {
				msg = ClientMessage{Type: "text", Data: string(data)}
			} else {
				if b.ctx.Err() == nil {
					b.logger.Warn("reading JSON from browser", "err", err)
				}
				return
			}
		}
		b.handleClientMessage(msg)
	}
}

func (b *Bridge) handleClientMessage(msg ClientMessage) {
	switch msg.Type {
	case "ping":
		b.WriteJSON(map[string]string{"type": "pong"})
	case "control":
		if msg.Action == "terminate" {
			b.requestTerminate()
		}
	case "text":
		text := strings.TrimSpace(msg.Data)
		if text == "" {
			return
		}
		if b.cfg.MaxClientTextRunes > 0 {
			text = TruncateRunes(text, b.cfg.MaxClientTextRunes)
		}
		b.Forward("text", func() error {
			return b.SendRealtime(genai.LiveSendRealtimeInputParameters{Text: text})
		})
	case "audio":
		b.forwardAudio(msg)
	case "video":
		b.forwardVideoFrame(msg)
	case "tool_response", "tool_result":
		payload := msg.Response
		if payload == nil {
			payload = msg.Result
		}
		if b.cfg.Tools != nil {
			b.cfg.Tools.CompletePageCall(msg.ID, msg.Name, payload, msg.Image, msg.ExecMs, b.WriteJSON, b.SendRealtime, b.SendToolResponses, b.onUpstreamSendErr)
			return
		}
		if msg.Name == "" {
			return
		}
		b.Forward("tool response", func() error {
			return b.SendToolResponses([]*genai.FunctionResponse{{ID: msg.ID, Name: msg.Name, Response: payload}})
		})
	default:
		if b.cfg.OnCustomClientMessage != nil {
			b.cfg.OnCustomClientMessage(b, msg)
		}
	}
}

func (b *Bridge) requestTerminate() {
	b.logger.Info("client requested end of session; sending goodbye prompt")
	b.gate.RequestTerminate()
	b.Forward("goodbye prompt", func() error {
		return b.SendRealtime(genai.LiveSendRealtimeInputParameters{Text: b.cfg.GoodbyePrompt})
	})

	b.timersMu.Lock()
	defer b.timersMu.Unlock()
	if b.backstopTimer != nil {
		return
	}
	b.backstopTimer = time.AfterFunc(b.cfg.Timings.GoodbyeBackstop, func() {
		if b.ctx.Err() == nil {
			b.logger.Info("goodbye backstop expired; closing session")
		}
		b.Shutdown(websocket.CloseNormalClosure, "Session terminated")
	})
}

func (b *Bridge) forwardAudio(msg ClientMessage) {
	audio, err := base64.StdEncoding.DecodeString(msg.Data)
	if err != nil {
		b.logger.Warn("dropping audio chunk with invalid base64", "err", err)
		return
	}
	if !ValidRealtimeAudioMIME(msg.MimeType) {
		b.warnAudioMIME.Do(func() {
			b.logger.Warn("dropping audio with unsupported MIME type (want audio/pcm[;rate=N])", "mimeType", TruncateRunes(msg.MimeType, MaxLoggedValueRunes))
		})
		return
	}
	b.Forward("audio", func() error {
		return b.SendRealtime(genai.LiveSendRealtimeInputParameters{Audio: &genai.Blob{MIMEType: msg.MimeType, Data: audio}})
	})
}

func (b *Bridge) forwardVideoFrame(msg ClientMessage) {
	frame, err := base64.StdEncoding.DecodeString(msg.Data)
	if err != nil {
		b.logger.Warn("dropping video frame with invalid base64", "err", err)
		return
	}
	mimeType := msg.MimeType
	if mimeType == "" {
		mimeType = DefaultFrameMIME
	}
	if !RealtimeVideoMIMETypes[mimeType] {
		b.warnVideoMIME.Do(func() {
			b.logger.Warn("dropping video frames with unsupported MIME type (want image/jpeg or image/png)", "mimeType", TruncateRunes(mimeType, MaxLoggedValueRunes))
		})
		return
	}
	b.Forward("video frame", func() error {
		return b.SendRealtime(genai.LiveSendRealtimeInputParameters{Video: &genai.Blob{MIMEType: mimeType, Data: frame}})
	})
}
