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

// Package livebridge provides a reusable, credential-isolated WebSocket
// switchboard between browser voice/avatar clients and the Gemini Live Bidi API.
package livebridge

import (
	"sync"
	"sync/atomic"
	"time"

	"github.com/gorilla/websocket"
)

// SafeConn wraps a gorilla/websocket.Conn with a write mutex. Gorilla allows
// only one concurrent writer, while a Live switchboard writes from the upstream
// receive loop, async tool goroutines, background alert fan-out, and timers.
type SafeConn struct {
	conn *websocket.Conn
	mu   sync.Mutex
}

// NewSafeConn wraps conn for concurrent-safe writes.
func NewSafeConn(conn *websocket.Conn) *SafeConn {
	return &SafeConn{conn: conn}
}

// Conn returns the underlying *websocket.Conn for read configuration such as
// SetReadDeadline. Callers must still perform all writes through SafeConn.
func (s *SafeConn) Conn() *websocket.Conn {
	return s.conn
}

// SetReadLimit sets the maximum size in bytes for inbound messages on the
// underlying connection.
func (s *SafeConn) SetReadLimit(limit int64) {
	s.conn.SetReadLimit(limit)
}

// WriteJSON serializes v as a JSON text frame under the write lock.
func (s *SafeConn) WriteJSON(v any) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.WriteJSON(v)
}

// WriteMessage writes a raw text or binary frame under the write lock.
func (s *SafeConn) WriteMessage(messageType int, data []byte) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.WriteMessage(messageType, data)
}

// ReadJSON reads the next JSON frame. Gorilla allows one reader concurrently
// with one writer, and only the client read loop calls ReadJSON/ReadMessage.
func (s *SafeConn) ReadJSON(v any) error {
	return s.conn.ReadJSON(v)
}

// ReadMessage reads the next raw frame from the peer.
func (s *SafeConn) ReadMessage() (messageType int, p []byte, err error) {
	return s.conn.ReadMessage()
}

// WriteClose sends an RFC 6455 close control frame with a 1-second deadline so
// an unresponsive peer cannot stall session teardown.
func (s *SafeConn) WriteClose(code int, reason string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.WriteControl(
		websocket.CloseMessage,
		websocket.FormatCloseMessage(code, reason),
		time.Now().Add(time.Second),
	)
}

// Close closes the underlying network connection immediately, unblocking any
// concurrent ReadJSON or ReadMessage call.
func (s *SafeConn) Close() error {
	return s.conn.Close()
}

// TerminateGate tracks when it is safe to close a Live session after a
// client-requested graceful termination ("End Session"). When a farewell prompt
// interrupts an in-progress model turn, the Live API emits Interrupted followed
// by two TurnComplete events: one wrapping up the aborted turn and a second for
// the farewell turn itself. TerminateGate skips the aborted turn's TurnComplete
// so the farewell audio is not cut off prematurely.
type TerminateGate struct {
	terminating      atomic.Bool
	pendingInterrupt atomic.Bool
}

// RequestTerminate arms the gate when the client asks to end the session.
func (g *TerminateGate) RequestTerminate() {
	g.terminating.Store(true)
}

// OnInterrupted records that the current model turn was interrupted.
func (g *TerminateGate) OnInterrupted() {
	g.pendingInterrupt.Store(true)
}

// OnTurnComplete reports whether this TurnComplete finishes the farewell turn
// and should close the session.
func (g *TerminateGate) OnTurnComplete() bool {
	if g.pendingInterrupt.CompareAndSwap(true, false) {
		return false
	}
	return g.terminating.Load()
}
