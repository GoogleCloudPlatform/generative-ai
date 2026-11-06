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

	"local-code-assistant/internal/livebridge"
	"local-code-assistant/tools"
)

type mockSession struct {
	mu       sync.Mutex
	recvCh   chan *genai.LiveServerMessage
	toolResp chan genai.LiveSendToolResponseParameters
	closed   bool
	done     chan struct{}
}

func newMockSession() *mockSession {
	return &mockSession{
		recvCh:   make(chan *genai.LiveServerMessage, 16),
		toolResp: make(chan genai.LiveSendToolResponseParameters, 8),
		done:     make(chan struct{}),
	}
}

func (m *mockSession) SendRealtimeInput(genai.LiveSendRealtimeInputParameters) error { return nil }

func (m *mockSession) SendToolResponse(p genai.LiveSendToolResponseParameters) error {
	select {
	case m.toolResp <- p:
	default:
	}
	return nil
}

func (m *mockSession) Receive() (*genai.LiveServerMessage, error) {
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

func (m *mockSession) Close() error {
	m.mu.Lock()
	defer m.mu.Unlock()
	if !m.closed {
		close(m.done)
		m.closed = true
	}
	return nil
}

type mockDialer struct {
	session *mockSession
}

func (d mockDialer) Connect(context.Context, string, *genai.LiveConnectConfig) (livebridge.Session, error) {
	return d.session, nil
}

type blockingTool struct {
	started chan struct{}
}

func (t *blockingTool) Name() string { return "slow_fs" }
func (t *blockingTool) Declaration() *genai.FunctionDeclaration {
	return &genai.FunctionDeclaration{Name: "slow_fs", Description: "blocks until ctx cancelled"}
}
func (t *blockingTool) Execute(ctx context.Context, _ map[string]any) (map[string]any, error) {
	close(t.started)
	<-ctx.Done()
	return map[string]any{"cancelled": true}, nil
}

func TestSessionHandler_AsyncToolCancellationAndSessionCap(t *testing.T) {
	origCap, origGrace := sessionCapDuration, sessionCapGrace
	sessionCapDuration, sessionCapGrace = 120*time.Millisecond, 30*time.Millisecond
	t.Cleanup(func() {
		sessionCapDuration, sessionCapGrace = origCap, origGrace
	})

	sess := newMockSession()
	slow := &blockingTool{started: make(chan struct{})}
	reg := tools.NewRegistry(slow)

	handlerDone := make(chan struct{})
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer close(handlerDone)
		sessionHandler(appConfig{model: defaultModel, voice: defaultVoice, location: defaultLocation}, mockDialer{session: sess}, reg)(w, r)
	}))
	defer srv.Close()

	wsURL := "ws" + strings.TrimPrefix(srv.URL, "http")

	// Foreign origin must be rejected with 403 before dialing Live.
	if _, resp, err := websocket.DefaultDialer.Dial(wsURL, http.Header{"Origin": {"https://evil.example"}}); err == nil || resp == nil || resp.StatusCode != http.StatusForbidden {
		t.Fatalf("foreign origin upgrade: err=%v resp=%v, want 403", err, resp)
	}

	conn, _, err := websocket.DefaultDialer.Dial(wsURL, nil)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer func() { _ = conn.Close() }()

	sess.recvCh <- &genai.LiveServerMessage{SetupComplete: &genai.LiveServerSetupComplete{}}
	sess.recvCh <- &genai.LiveServerMessage{
		ToolCall: &genai.LiveServerToolCall{
			FunctionCalls: []*genai.FunctionCall{{ID: "c1", Name: "slow_fs"}},
		},
	}

	select {
	case <-slow.started:
	case <-time.After(2 * time.Second):
		t.Fatal("slow_fs did not start asynchronously")
	}

	// Cancel tool mid-execution via barge-in ToolCallCancellation.
	sess.recvCh <- &genai.LiveServerMessage{
		ToolCallCancellation: &genai.LiveServerToolCallCancellation{IDs: []string{"c1"}},
	}

	_ = conn.SetReadDeadline(time.Now().Add(2 * time.Second))
	var sawReady, sawCancel, sawCap bool
	for {
		var m map[string]any
		if err := conn.ReadJSON(&m); err != nil {
			break
		}
		switch m["type"] {
		case "connection_state":
			if m["state"] == "ready" {
				sawReady = true
			}
		case "tool_call_cancellation":
			sawCancel = true
		case "status":
			if m["error"] == "session_limit_reached" {
				sawCap = true
			}
		}
	}

	if !sawReady || !sawCancel || !sawCap {
		t.Fatalf("events seen: ready=%v cancel=%v cap=%v", sawReady, sawCancel, sawCap)
	}

	select {
	case unexpected := <-sess.toolResp:
		t.Fatalf("cancelled tool sent response: %+v", unexpected)
	default:
	}

	select {
	case <-handlerDone:
	case <-time.After(2 * time.Second):
		t.Fatal("handler leaked after session cap")
	}
}
