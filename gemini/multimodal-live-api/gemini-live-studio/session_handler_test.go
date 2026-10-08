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
	"io"
	"net/http"
	"net/http/httptest"
	"strings"
	"sync"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"
)

type mockLiveSession struct {
	mu            sync.Mutex
	recvCh        chan *genai.LiveServerMessage
	realtimeCalls []genai.LiveSendRealtimeInputParameters
	toolResponses []genai.LiveSendToolResponseParameters
	toolRespCh    chan genai.LiveSendToolResponseParameters
	closed        bool
	closeCount    int
	done          chan struct{}
	sendErr       error
}

func newMockLiveSession() *mockLiveSession {
	return &mockLiveSession{
		recvCh:     make(chan *genai.LiveServerMessage, 16),
		toolRespCh: make(chan genai.LiveSendToolResponseParameters, 8),
		done:       make(chan struct{}),
	}
}

func (m *mockLiveSession) SendRealtimeInput(p genai.LiveSendRealtimeInputParameters) error {
	m.mu.Lock()
	defer m.mu.Unlock()
	m.realtimeCalls = append(m.realtimeCalls, p)
	return m.sendErr
}

func (m *mockLiveSession) SendToolResponse(p genai.LiveSendToolResponseParameters) error {
	m.mu.Lock()
	m.toolResponses = append(m.toolResponses, p)
	m.mu.Unlock()
	select {
	case m.toolRespCh <- p:
	default:
	}
	return nil
}

func (m *mockLiveSession) Receive() (*genai.LiveServerMessage, error) {
	// Like *genai.Session, Receive unblocks with an error once Close is called.
	select {
	case msg, ok := <-m.recvCh:
		if !ok {
			return nil, io.EOF
		}
		return msg, nil
	case <-m.done:
		return nil, io.ErrClosedPipe
	}
}

func (m *mockLiveSession) Close() error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if !m.closed {
		close(m.done)
	}
	m.closed = true
	m.closeCount++
	return nil
}

type mockLiveConnector struct {
	session   *mockLiveSession
	gotModel  string
	gotLoc    string
	gotConfig *genai.LiveConnectConfig
}

func (c *mockLiveConnector) Connect(_ context.Context, model, location string, config *genai.LiveConnectConfig) (liveSessionAdapter, error) {
	c.gotModel = model
	c.gotLoc = location
	c.gotConfig = config
	return c.session, nil
}

func TestLiveSessionHandler_ToolCallRoundTrip(t *testing.T) {
	mockSess := newMockLiveSession()
	connector := &mockLiveConnector{session: mockSess}

	srv := httptest.NewServer(liveSessionHandlerForMode(liveModeAudio, connector, "gemini-3.8-live", "us-central1"))
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")
	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("dial ws: %v", err)
	}
	defer func() { _ = conn.Close() }()

	trueVal := true
	if err := conn.WriteJSON(InitialConfig{
		VoiceName:         "Puck",
		EnableToolCalling: &trueVal,
		ProactiveAudio:    &trueVal,
	}); err != nil {
		t.Fatalf("write initialConfig: %v", err)
	}

	_ = conn.SetReadDeadline(time.Now().Add(3 * time.Second))
	var sessionInfo map[string]any
	if err := conn.ReadJSON(&sessionInfo); err != nil {
		t.Fatalf("read session_info: %v", err)
	}
	if sessionInfo["type"] != "session_info" || sessionInfo["mode"] != string(liveModeAudio) {
		t.Fatalf("session_info = %+v", sessionInfo)
	}

	// Verify that targetLiveModel was resolved before buildLiveConnectConfigForMode
	// so ProactiveAudio was populated even when InitialConfig.LiveModel was "".
	if connector.gotConfig == nil || connector.gotConfig.Proactivity == nil || connector.gotConfig.Proactivity.ProactiveAudio == nil || !*connector.gotConfig.Proactivity.ProactiveAudio {
		t.Errorf("expected ProactiveAudio=true on resolved default model gemini-3.8-live, got %+v", connector.gotConfig)
	}

	// Simulate Gemini emitting a show_info_card ToolCall.
	mockSess.recvCh <- &genai.LiveServerMessage{
		ToolCall: &genai.LiveServerToolCall{
			FunctionCalls: []*genai.FunctionCall{
				{
					ID:   "call-42",
					Name: "show_info_card",
					Args: map[string]any{
						"title":    "Architecture Summary",
						"summary":  "Switchboard pattern bridging WebSocket and Vertex Bidi.",
						"category": "Architecture",
						"items":    []any{"24kHz PCM", "1 FPS Vision"},
					},
				},
			},
		},
	}

	var toolEvent map[string]any
	if err := conn.ReadJSON(&toolEvent); err != nil {
		t.Fatalf("read tool_call event: %v", err)
	}
	if toolEvent["type"] != "tool_call" || toolEvent["id"] != "call-42" || toolEvent["name"] != "show_info_card" {
		t.Fatalf("tool_call event = %+v", toolEvent)
	}

	select {
	case resp := <-mockSess.toolRespCh:
		if len(resp.FunctionResponses) != 1 || resp.FunctionResponses[0].ID != "call-42" || resp.FunctionResponses[0].Name != "show_info_card" {
			t.Errorf("SendToolResponse = %+v", resp)
		}
	case <-time.After(2 * time.Second):
		t.Fatal("timed out waiting for session.SendToolResponse")
	}

	// Simulate ToolCallCancellation on barge-in.
	mockSess.recvCh <- &genai.LiveServerMessage{
		ToolCallCancellation: &genai.LiveServerToolCallCancellation{
			IDs: []string{"call-42"},
		},
	}

	var cancelEvent map[string]any
	if err := conn.ReadJSON(&cancelEvent); err != nil {
		t.Fatalf("read tool_call_cancellation event: %v", err)
	}
	if cancelEvent["type"] != "tool_call_cancellation" {
		t.Errorf("cancelEvent = %+v", cancelEvent)
	}

	close(mockSess.recvCh)
}

// capturingConnector hands the LiveConnectConfig to the test over a channel
// (safe under -race) and then behaves like mockLiveConnector.
type capturingConnector struct {
	session *mockLiveSession
	configs chan *genai.LiveConnectConfig
}

func (c *capturingConnector) Connect(_ context.Context, _, _ string, config *genai.LiveConnectConfig) (liveSessionAdapter, error) {
	c.configs <- config
	return c.session, nil
}

// A custom avatar sent by the browser must reach the Live API as a
// CustomizedAvatar with the decoded image (end to end through the handler,
// no network).
func TestLiveSessionHandler_CustomAvatarReachesLiveConfig(t *testing.T) {
	connector := &capturingConnector{session: newMockLiveSession(), configs: make(chan *genai.LiveConnectConfig, 1)}
	handler := liveSessionHandlerForMode(liveModeAvatar, connector, "gemini-3.8-live", "us-central1")
	// Wait for the handler to exit before returning: it reads package-level
	// session timers that other tests change.
	handlerDone := make(chan struct{})
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer close(handlerDone)
		handler(w, r)
	}))
	defer srv.Close()
	defer func() {
		select {
		case <-handlerDone:
		case <-time.After(3 * time.Second):
			t.Error("handler did not exit after the client closed")
		}
	}()

	conn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(srv.URL, "http"), nil)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer func() { _ = conn.Close() }() // runs before the handlerDone wait above
	if err := conn.WriteJSON(InitialConfig{AvatarType: "custom", AvatarData: pngDataURL}); err != nil {
		t.Fatalf("write initial config: %v", err)
	}

	var config *genai.LiveConnectConfig
	select {
	case config = <-connector.configs:
	case <-time.After(3 * time.Second):
		t.Fatal("handler never connected to the Live API")
	}
	if len(config.ResponseModalities) != 1 || config.ResponseModalities[0] != genai.ModalityVideo {
		t.Errorf("ResponseModalities = %v, want [VIDEO]", config.ResponseModalities)
	}
	if config.AvatarConfig == nil || config.AvatarConfig.CustomizedAvatar == nil {
		t.Fatalf("AvatarConfig = %+v, want a CustomizedAvatar", config.AvatarConfig)
	}
	custom := config.AvatarConfig.CustomizedAvatar
	if custom.ImageMIMEType != "image/png" || string(custom.ImageData) != "\x89PNG fake" {
		t.Errorf("CustomizedAvatar = {%q, %q}, want the decoded PNG", custom.ImageMIMEType, custom.ImageData)
	}
	if config.AvatarConfig.AvatarName != "" {
		t.Errorf("AvatarName = %q, want empty for a custom avatar", config.AvatarConfig.AvatarName)
	}
}
