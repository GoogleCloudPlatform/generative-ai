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
	"errors"
	"net/http"
	"net/http/httptest"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
	"google.golang.org/genai"
)

// teardownHarness runs the Live handler against a mock session and records
// when the handler returns, so tests can assert that every exit path closes
// both sides and that nothing outlives the handler.
type teardownHarness struct {
	t           *testing.T
	session     *mockLiveSession
	conn        *websocket.Conn
	handlerDone chan struct{}
}

func newTeardownHarness(t *testing.T) *teardownHarness {
	t.Helper()
	h := &teardownHarness{t: t, session: newMockLiveSession(), handlerDone: make(chan struct{})}
	handler := liveSessionHandlerForMode(liveModeAudio, &mockLiveConnector{session: h.session}, "gemini-3.8-live", "us-central1")
	srv := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		defer close(h.handlerDone)
		handler(w, r)
	}))
	t.Cleanup(srv.Close)

	conn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(srv.URL, "http"), nil)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	t.Cleanup(func() { _ = conn.Close() })
	h.conn = conn
	if err := conn.WriteJSON(InitialConfig{AvatarType: "preset", AvatarData: "Kira"}); err != nil {
		t.Fatalf("write initial config: %v", err)
	}
	return h
}

// readUntilClose drains client messages and returns the close error and the
// JSON "type"s seen before it.
func (h *teardownHarness) readUntilClose(timeout time.Duration) (*websocket.CloseError, []string) {
	h.t.Helper()
	_ = h.conn.SetReadDeadline(time.Now().Add(timeout))
	var types []string
	for {
		var m map[string]any
		if err := h.conn.ReadJSON(&m); err != nil {
			var ce *websocket.CloseError
			if errors.As(err, &ce) {
				return ce, types
			}
			h.t.Fatalf("expected a close frame, got %v (seen %v)", err, types)
		}
		if typ, ok := m["type"].(string); ok {
			types = append(types, typ)
		}
	}
}

func (h *teardownHarness) assertCleanExit() {
	h.t.Helper()
	select {
	case <-h.handlerDone:
	case <-time.After(3 * time.Second):
		h.t.Fatal("handler did not return; Live session / receive loop leaked")
	}
	h.session.mu.Lock()
	defer h.session.mu.Unlock()
	if !h.session.closed {
		h.t.Fatal("Live session was not closed")
	}
}

func shrinkTimers(t *testing.T, capDur, grace, backstop time.Duration) {
	t.Helper()
	oc, og, ob := sessionCapDuration, sessionCapGrace, goodbyeBackstop
	sessionCapDuration, sessionCapGrace, goodbyeBackstop = capDur, grace, backstop
	t.Cleanup(func() { sessionCapDuration, sessionCapGrace, goodbyeBackstop = oc, og, ob })
}

func TestTeardown_SessionCapClosesBothSides(t *testing.T) {
	shrinkTimers(t, 50*time.Millisecond, 50*time.Millisecond, time.Minute)
	h := newTeardownHarness(t)

	ce, types := h.readUntilClose(3 * time.Second)
	if ce.Code != websocket.CloseNormalClosure || ce.Text != "Session limit reached" {
		t.Fatalf("close = %d %q, want 1000 \"Session limit reached\"", ce.Code, ce.Text)
	}
	if !strings.Contains(strings.Join(types, ","), "status") {
		t.Fatalf("expected session_limit_reached status before close, saw %v", types)
	}
	h.assertCleanExit()
}

func TestTeardown_GoodbyeBackstopClosesWhenTurnNeverCompletes(t *testing.T) {
	shrinkTimers(t, time.Minute, time.Second, 100*time.Millisecond)
	h := newTeardownHarness(t)

	for i := 0; i < 3; i++ { // repeated clicks must not break anything
		if err := h.conn.WriteJSON(map[string]string{"type": "control", "action": "terminate"}); err != nil {
			t.Fatalf("write terminate: %v", err)
		}
	}
	ce, _ := h.readUntilClose(3 * time.Second)
	if ce.Code != websocket.CloseNormalClosure {
		t.Fatalf("close code = %d, want 1000", ce.Code)
	}
	h.assertCleanExit()
}

func TestTeardown_GoodbyeTurnCompleteClosesGracefully(t *testing.T) {
	shrinkTimers(t, time.Minute, time.Second, time.Minute)
	h := newTeardownHarness(t)

	if err := h.conn.WriteJSON(map[string]string{"type": "control", "action": "terminate"}); err != nil {
		t.Fatalf("write terminate: %v", err)
	}
	// Wait until the goodbye prompt reached the session, then finish its turn.
	deadline := time.Now().Add(2 * time.Second)
	for {
		h.session.mu.Lock()
		n := len(h.session.realtimeCalls)
		h.session.mu.Unlock()
		if n > 0 {
			break
		}
		if time.Now().After(deadline) {
			t.Fatal("goodbye prompt was never sent")
		}
		time.Sleep(5 * time.Millisecond)
	}
	h.session.recvCh <- &genai.LiveServerMessage{ServerContent: &genai.LiveServerContent{TurnComplete: true}}

	ce, _ := h.readUntilClose(3 * time.Second)
	if ce.Code != websocket.CloseNormalClosure || ce.Text != "Session terminated" {
		t.Fatalf("close = %d %q, want 1000 \"Session terminated\"", ce.Code, ce.Text)
	}
	h.assertCleanExit()
}

func TestTeardown_LiveReceiveErrorClosesClient(t *testing.T) {
	h := newTeardownHarness(t)
	close(h.session.recvCh) // upstream drops

	ce, _ := h.readUntilClose(3 * time.Second)
	if ce.Code != websocket.CloseInternalServerErr {
		t.Fatalf("close code = %d, want 1011", ce.Code)
	}
	h.assertCleanExit()
}

func TestTeardown_SendErrorClosesInsteadOfForwardingIntoDeadSession(t *testing.T) {
	h := newTeardownHarness(t)
	h.session.mu.Lock()
	h.session.sendErr = errors.New("use of closed network connection")
	h.session.mu.Unlock()

	if err := h.conn.WriteJSON(map[string]string{"type": "text", "data": "hello"}); err != nil {
		t.Fatalf("write text: %v", err)
	}
	ce, _ := h.readUntilClose(3 * time.Second)
	if ce.Code != websocket.CloseInternalServerErr {
		t.Fatalf("close code = %d, want 1011", ce.Code)
	}
	h.assertCleanExit()
}

func TestTeardown_ClientDisconnectClosesLiveSession(t *testing.T) {
	h := newTeardownHarness(t)
	// Make sure the handler is past setup before hanging up.
	if err := h.conn.WriteJSON(map[string]string{"type": "text", "data": "hi"}); err != nil {
		t.Fatalf("write text: %v", err)
	}
	_ = h.conn.WriteMessage(websocket.CloseMessage, websocket.FormatCloseMessage(websocket.CloseGoingAway, "bye"))
	_ = h.conn.Close()
	h.assertCleanExit()
}

func TestTeardown_InvalidBase64IsDroppedNotFatal(t *testing.T) {
	h := newTeardownHarness(t)
	for _, typ := range []string{"audio", "video"} {
		if err := h.conn.WriteJSON(map[string]string{"type": typ, "data": "!!not-base64!!"}); err != nil {
			t.Fatalf("write %s: %v", typ, err)
		}
	}
	if err := h.conn.WriteJSON(map[string]string{"type": "text", "data": "still alive"}); err != nil {
		t.Fatalf("write text: %v", err)
	}
	deadline := time.Now().Add(2 * time.Second)
	for {
		h.session.mu.Lock()
		calls := append([]genai.LiveSendRealtimeInputParameters(nil), h.session.realtimeCalls...)
		h.session.mu.Unlock()
		for _, c := range calls {
			if c.Audio != nil || c.Video != nil {
				t.Fatal("invalid base64 media was forwarded")
			}
			if c.Text == "still alive" {
				return
			}
		}
		if time.Now().After(deadline) {
			t.Fatalf("session stopped forwarding after invalid base64; calls=%d", len(calls))
		}
		time.Sleep(5 * time.Millisecond)
	}
}
