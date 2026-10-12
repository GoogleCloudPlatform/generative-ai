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
	"sync"
	"time"

	"github.com/gorilla/websocket"
)

// safeWS wraps a gorilla/websocket.Conn with a write mutex. Gorilla allows
// only one concurrent writer, and a Live session writes from the receive
// loop, the session-cap timer and error paths.
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

// ReadJSON is not locked: gorilla allows one reader concurrently with one
// writer, and only the client loop reads.
func (s *safeWS) ReadJSON(v any) error {
	return s.conn.ReadJSON(v)
}

// WriteClose sends a close frame with a short deadline so a dead peer can't
// stall shutdown.
func (s *safeWS) WriteClose(code int, reason string) error {
	s.mu.Lock()
	defer s.mu.Unlock()
	return s.conn.WriteControl(websocket.CloseMessage, websocket.FormatCloseMessage(code, reason), time.Now().Add(time.Second))
}

func (s *safeWS) Close() error {
	return s.conn.Close()
}
