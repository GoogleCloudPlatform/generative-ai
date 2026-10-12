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
	"bytes"
	"encoding/binary"
	"net/http"
	"net/http/httptest"
	"testing"
)

// These sequences are transcribed from real Live API wire traces captured
// while ending sessions in idle, mid-answer and mid-greeting states. Each
// represents one call to
// onInterrupted/onTurnComplete in the order the server actually sent them.

func TestTerminateGate_Idle(t *testing.T) {
	var g terminateGate
	g.requestTerminate()

	// Single TurnComplete for the goodbye's own turn; no interruption at all.
	if !g.onTurnComplete() {
		t.Fatal("expected close on the goodbye's own TurnComplete when idle")
	}
}

func TestTerminateGate_GreetingImmediateClick(t *testing.T) {
	var g terminateGate
	g.requestTerminate()

	if !g.onTurnComplete() {
		t.Fatal("expected close on the goodbye's own TurnComplete (no interruption occurred)")
	}
}

func TestTerminateGate_InterruptedMidTurn(t *testing.T) {
	var g terminateGate
	g.requestTerminate()

	g.onInterrupted()
	if g.onTurnComplete() {
		t.Fatal("must NOT close on the interrupted turn's own wrap-up TurnComplete")
	}

	if !g.onTurnComplete() {
		t.Fatal("expected close on the goodbye turn's TurnComplete")
	}
}

func TestTerminateGate_InterruptionBeforeTerminateRequested(t *testing.T) {
	var g terminateGate

	// Normal barge-in during conversation, well before "End Session" is clicked.
	g.onInterrupted()
	if g.onTurnComplete() {
		t.Fatal("must not report close before terminate was ever requested")
	}

	// Now the user clicks End Session while idle.
	g.requestTerminate()
	if !g.onTurnComplete() {
		t.Fatal("expected close on the next TurnComplete after terminate is requested")
	}
}

func TestTerminateGate_MultipleInterruptions(t *testing.T) {
	var g terminateGate
	g.requestTerminate()

	g.onInterrupted()
	if g.onTurnComplete() {
		t.Fatal("first TurnComplete after first interruption must not close")
	}

	g.onInterrupted()
	if g.onTurnComplete() {
		t.Fatal("second TurnComplete after second interruption must not close")
	}

	if !g.onTurnComplete() {
		t.Fatal("third TurnComplete (goodbye's own) must close")
	}
}

func TestTerminateGate_NoCloseBeforeTerminateRequested(t *testing.T) {
	var g terminateGate

	for i := 0; i < 5; i++ {
		if g.onTurnComplete() {
			t.Fatalf("must never close before terminate is requested (iteration %d)", i)
		}
	}
}

func TestParseAvc1Dimensions(t *testing.T) {
	// Construct a minimal synthetic avc1 VisualSampleEntry payload:
	// "avc1" (4B) + 24 bytes of header fields + width (2B) + height (2B)
	var buf bytes.Buffer
	buf.WriteString("avc1")
	buf.Write(make([]byte, 6+2+2+2+12))
	_ = binary.Write(&buf, binary.BigEndian, uint16(704))
	_ = binary.Write(&buf, binary.BigEndian, uint16(1280))

	w, h, ok := parseAvc1Dimensions(buf.Bytes())
	if !ok || w != 704 || h != 1280 {
		t.Fatalf("parseAvc1Dimensions = (%d, %d, %v), want (704, 1280, true)", w, h, ok)
	}
}

func TestDescribeImageHandler_Validation(t *testing.T) {
	h := describeImageHandler(newClientManager("test-project", ""))

	t.Run("Method Not Allowed", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodGet, "/api/describe-image", nil)
		w := httptest.NewRecorder()
		h(w, req)
		if w.Code != http.StatusMethodNotAllowed {
			t.Errorf("got code %d, want %d", w.Code, http.StatusMethodNotAllowed)
		}
	})

	t.Run("Missing Image", func(t *testing.T) {
		req := httptest.NewRequest(http.MethodPost, "/api/describe-image", bytes.NewBufferString("{}"))
		w := httptest.NewRecorder()
		h(w, req)
		if w.Code != http.StatusBadRequest {
			t.Errorf("got code %d, want %d", w.Code, http.StatusBadRequest)
		}
	})
}
