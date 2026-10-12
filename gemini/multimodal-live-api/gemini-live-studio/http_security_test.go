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
	"encoding/json"
	"net/http"
	"net/http/httptest"
	"os"
	"path/filepath"
	"slices"
	"strings"
	"testing"
	"time"

	"github.com/gorilla/websocket"
)

func TestOriginPolicy_Allows(t *testing.T) {
	p := newOriginPolicy(" https://Avatar.Example.com/ , http://partner.test:3000")
	cases := []struct {
		name, host, origin string
		want               bool
	}{
		{"no origin (curl)", "app.run.app", "", true},
		{"same origin", "app.run.app", "https://app.run.app", true},
		{"same origin case-insensitive", "App.Run.App", "https://app.run.app", true},
		{"foreign origin", "app.run.app", "https://evil.example", false},
		{"allowlisted origin", "app.run.app", "https://avatar.example.com", true},
		{"allowlisted origin with port", "app.run.app", "http://partner.test:3000", true},
		{"allowlist is exact (scheme)", "app.run.app", "http://avatar.example.com", false},
		{"allowlist is exact (port)", "app.run.app", "http://partner.test:4000", false},
		{"vite dev proxy", "localhost:8080", "http://localhost:5173", true},
		{"loopback ip dev", "127.0.0.1:8080", "http://127.0.0.1:5173", true},
		{"ipv6 loopback dev", "[::1]:8080", "http://[::1]:5173", true},
		{"loopback origin vs public host", "app.run.app", "http://localhost:5173", false},
		{"null origin", "app.run.app", "null", false},
		{"non-http scheme", "app.run.app", "file://app.run.app", false},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			r := httptest.NewRequest(http.MethodGet, "/ws", nil)
			r.Host = tc.host
			if tc.origin != "" {
				r.Header.Set("Origin", tc.origin)
			}
			if got := p.Allows(r); got != tc.want {
				t.Fatalf("Allows(host=%q, origin=%q) = %v, want %v", tc.host, tc.origin, got, tc.want)
			}
		})
	}
}

func TestWithCORS(t *testing.T) {
	p := newOriginPolicy("https://partner.example")
	h := p.withCORS(func(w http.ResponseWriter, r *http.Request) { w.WriteHeader(http.StatusTeapot) })

	do := func(method, origin string) *httptest.ResponseRecorder {
		r := httptest.NewRequest(method, "http://app.run.app/api/config", nil)
		if origin != "" {
			r.Header.Set("Origin", origin)
		}
		w := httptest.NewRecorder()
		h(w, r)
		return w
	}

	if w := do(http.MethodPost, "https://evil.example"); w.Code != http.StatusForbidden || w.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Errorf("foreign origin: code=%d ACAO=%q, want 403 and no ACAO", w.Code, w.Header().Get("Access-Control-Allow-Origin"))
	}
	if w := do(http.MethodGet, ""); w.Code != http.StatusTeapot || w.Header().Get("Access-Control-Allow-Origin") != "" {
		t.Errorf("no origin: code=%d ACAO=%q, want handler and no ACAO", w.Code, w.Header().Get("Access-Control-Allow-Origin"))
	}
	if w := do(http.MethodGet, "https://partner.example"); w.Code != http.StatusTeapot || w.Header().Get("Access-Control-Allow-Origin") != "https://partner.example" {
		t.Errorf("allowlisted origin: code=%d ACAO=%q", w.Code, w.Header().Get("Access-Control-Allow-Origin"))
	}
	if w := do(http.MethodOptions, "https://partner.example"); w.Code != http.StatusNoContent {
		t.Errorf("preflight: code=%d, want 204", w.Code)
	}
	if w := do(http.MethodGet, "https://partner.example"); !strings.Contains(strings.Join(w.Header().Values("Vary"), ","), "Origin") {
		t.Errorf("missing Vary: Origin")
	}
}

func TestLiveSessionHandler_RejectsForeignOrigin(t *testing.T) {
	connector := &mockLiveConnector{session: newMockLiveSession()}
	srv := httptest.NewServer(liveSessionHandlerForMode(liveModeAudio, connector, "gemini-3.8-live", "us-central1"))
	defer srv.Close()
	url := "ws" + strings.TrimPrefix(srv.URL, "http")

	_, resp, err := websocket.DefaultDialer.Dial(url, http.Header{"Origin": {"https://evil.example"}})
	if err == nil {
		t.Fatal("foreign-origin WebSocket upgrade succeeded, want rejection")
	}
	if resp == nil || resp.StatusCode != http.StatusForbidden {
		t.Fatalf("foreign-origin upgrade: resp=%v, want 403", resp)
	}
	if connector.gotModel != "" {
		t.Fatal("Live API was dialed for a rejected origin")
	}

	conn, _, err := websocket.DefaultDialer.Dial(url, http.Header{"Origin": {srv.URL}})
	if err != nil {
		t.Fatalf("same-origin upgrade failed: %v", err)
	}
	_ = conn.Close()
}

func TestLiveSessionHandler_ClientMessageReadLimit(t *testing.T) {
	session := newMockLiveSession()
	connector := &mockLiveConnector{session: session}
	srv := httptest.NewServer(liveSessionHandlerForMode(liveModeAudio, connector, "gemini-3.8-live", "us-central1"))
	defer srv.Close()

	conn, _, err := websocket.DefaultDialer.Dial("ws"+strings.TrimPrefix(srv.URL, "http"), nil)
	if err != nil {
		t.Fatalf("dial: %v", err)
	}
	defer func() { _ = conn.Close() }()
	if err := conn.WriteJSON(InitialConfig{AvatarType: "preset", AvatarData: "Kira"}); err != nil {
		t.Fatalf("write initial config: %v", err)
	}

	big := map[string]string{"type": "text", "data": strings.Repeat("a", maxClientMessageBytes+1)}
	if err := conn.WriteJSON(big); err != nil {
		t.Fatalf("write oversized message: %v", err)
	}

	_ = conn.SetReadDeadline(time.Now().Add(5 * time.Second))
	for {
		if _, _, err := conn.ReadMessage(); err != nil {
			if !websocket.IsCloseError(err, websocket.CloseMessageTooBig) && !strings.Contains(err.Error(), "close") && !strings.Contains(err.Error(), "EOF") && !strings.Contains(err.Error(), "reset") {
				t.Fatalf("expected the server to close the connection, got %v", err)
			}
			break
		}
	}
	session.mu.Lock()
	defer session.mu.Unlock()
	for _, c := range session.realtimeCalls {
		if len(c.Text) > maxClientMessageBytes {
			t.Fatal("oversized message was forwarded to the Live session")
		}
	}
}

func TestGenerateAvatarHandler_BodyTooLarge(t *testing.T) {
	h := generateAvatarHandler(newClientManager("test-project", ""), "gemini-3.1-flash-image", "global")
	body := `{"prompt":"x","image":"` + strings.Repeat("A", maxGenerateAvatarBody) + `"}`
	r := httptest.NewRequest(http.MethodPost, "/api/generate-avatar", bytes.NewBufferString(body))
	w := httptest.NewRecorder()
	h(w, r)
	if w.Code != http.StatusRequestEntityTooLarge {
		t.Fatalf("code=%d, want 413", w.Code)
	}
}

func TestNewHTTPServer_Timeouts(t *testing.T) {
	s := newHTTPServer(":0", http.NewServeMux())
	if s.ReadHeaderTimeout <= 0 || s.IdleTimeout <= 0 || s.MaxHeaderBytes <= 0 {
		t.Fatalf("missing slowloris protections: %+v", s)
	}
	if s.ReadTimeout != 0 || s.WriteTimeout != 0 {
		t.Fatal("ReadTimeout/WriteTimeout would cut off long-lived Live WebSockets")
	}
}

func TestServerConfigHandler(t *testing.T) {
	h := serverConfigHandler("custom-live-model", "europe-west4", "gemini-3.1-flash-image", "global")
	r := httptest.NewRequest(http.MethodGet, "/api/config", nil)
	w := httptest.NewRecorder()
	h(w, r)

	if w.Code != http.StatusOK {
		t.Fatalf("code=%d, want 200", w.Code)
	}
	var got ServerConfigResponse
	if err := json.NewDecoder(w.Body).Decode(&got); err != nil {
		t.Fatalf("decode /api/config: %v", err)
	}
	if got.LiveModel != "custom-live-model" || got.LiveLocation != "europe-west4" || got.ImageModel != "gemini-3.1-flash-image" || got.ImageLocation != "global" {
		t.Fatalf("unexpected config defaults: %+v", got)
	}
	if !slices.Contains(got.AvailableLiveModels, "custom-live-model") || !slices.Contains(got.AvailableLiveModels, "gemini-3.8-live") {
		t.Errorf("AvailableLiveModels = %v", got.AvailableLiveModels)
	}
	if !slices.Contains(got.AvailableLocations, "europe-west4") || !slices.Contains(got.AvailableLocations, "us-central1") {
		t.Errorf("AvailableLocations = %v", got.AvailableLocations)
	}
}

func TestSpaOrStaticHandler(t *testing.T) {
	dir := t.TempDir()
	indexHTML := []byte("<!doctype html><title>SPA</title>")
	assetJS := []byte("console.log('asset');")
	if err := os.WriteFile(filepath.Join(dir, "index.html"), indexHTML, 0644); err != nil {
		t.Fatal(err)
	}
	if err := os.WriteFile(filepath.Join(dir, "app.js"), assetJS, 0644); err != nil {
		t.Fatal(err)
	}

	h := spaOrStaticHandler(dir)
	for _, spaPath := range []string{"/", "/live", "/live/", "/avatar", "/avatar/", "/settings", "/settings/"} {
		r := httptest.NewRequest(http.MethodGet, spaPath, nil)
		w := httptest.NewRecorder()
		h(w, r)
		if w.Code != http.StatusOK || !bytes.Equal(w.Body.Bytes(), indexHTML) {
			t.Errorf("GET %s: code=%d body=%q, want 200 index.html", spaPath, w.Code, w.Body.String())
		}
	}

	// Static file should be served as-is
	rAsset := httptest.NewRequest(http.MethodGet, "/app.js", nil)
	wAsset := httptest.NewRecorder()
	h(wAsset, rAsset)
	if wAsset.Code != http.StatusOK || !bytes.Equal(wAsset.Body.Bytes(), assetJS) {
		t.Errorf("GET /app.js: code=%d body=%q", wAsset.Code, wAsset.Body.String())
	}

	// Unknown route should 404
	r404 := httptest.NewRequest(http.MethodGet, "/unknown-route", nil)
	w404 := httptest.NewRecorder()
	h(w404, r404)
	if w404.Code != http.StatusNotFound {
		t.Errorf("GET /unknown-route: code=%d, want 404", w404.Code)
	}
}
