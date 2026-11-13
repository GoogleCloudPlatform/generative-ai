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
	"github.com/gorilla/websocket"

	"gemini-live-studio/livebridge"
)

type safeWS = livebridge.SafeConn

func newSafeWS(conn *websocket.Conn) *safeWS {
	return livebridge.NewSafeConn(conn)
}

// terminateGate delegates to livebridge.TerminateGate for package tests.
type terminateGate struct {
	inner livebridge.TerminateGate
}

func (g *terminateGate) requestTerminate()    { g.inner.RequestTerminate() }
func (g *terminateGate) onInterrupted()       { g.inner.OnInterrupted() }
func (g *terminateGate) onTurnComplete() bool { return g.inner.OnTurnComplete() }
