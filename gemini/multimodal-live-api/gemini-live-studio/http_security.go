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
	"net"
	"net/http"
	"net/url"
	"os"
	"strings"
	"time"
)

// Request size limits. They are sized for what the frontend actually sends:
//   - The first WebSocket message (InitialConfig) can carry a custom avatar as a
//     base64 data URL (a 2K 9:16 image, a few MB raw, ~1.37x larger as base64)
//     plus up to 32k chars each of system instruction and grounding context.
//   - Later messages are 16 kHz PCM chunks, 1 FPS JPEG frames captured at the
//     camera/screen's native resolution (quality 0.7), and short text.
//   - /api/generate-avatar may carry a reference photo as a data URL.
const (
	maxInitialConfigBytes = 16 << 20 // 16 MiB
	maxClientMessageBytes = 8 << 20  // 8 MiB
	maxGenerateAvatarBody = 16 << 20 // 16 MiB
	maxDescribeImageBody  = 8 << 20  // 8 MiB
)

// originPolicy decides which browser origins may call the API and open the
// Live WebSockets. Without it, any website could open /ws from a visitor's
// browser and spend this project's Gemini quota (cross-site WebSocket
// hijacking), because browsers do not apply CORS to WebSocket upgrades.
//
// Allowed:
//   - requests with no Origin header (curl, server-to-server, same-origin GETs);
//   - same-origin requests (Origin host == request Host);
//   - loopback origins when the server itself was reached on loopback, so the
//     Vite dev server (localhost:5173 proxying to localhost:8080) keeps working;
//   - any origin listed in ALLOWED_ORIGINS (comma-separated, exact
//     scheme://host[:port] match, e.g. "https://avatar.example.com").
type originPolicy struct {
	allowed map[string]bool
}

func newOriginPolicy(allowedCSV string) *originPolicy {
	p := &originPolicy{allowed: map[string]bool{}}
	for _, o := range strings.Split(allowedCSV, ",") {
		o = strings.TrimRight(strings.ToLower(strings.TrimSpace(o)), "/")
		if o != "" {
			p.allowed[o] = true
		}
	}
	return p
}

func newOriginPolicyFromEnv() *originPolicy {
	return newOriginPolicy(os.Getenv("ALLOWED_ORIGINS"))
}

// Allows reports whether the request's Origin is permitted.
func (p *originPolicy) Allows(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return true
	}
	u, err := url.Parse(origin)
	if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") {
		return false
	}
	if p.allowed[strings.ToLower(u.Scheme+"://"+u.Host)] {
		return true
	}
	if strings.EqualFold(u.Host, r.Host) {
		return true
	}
	return isLoopbackHost(u.Hostname()) && isLoopbackHost(hostOnly(r.Host))
}

func hostOnly(hostport string) string {
	if h, _, err := net.SplitHostPort(hostport); err == nil {
		return h
	}
	return strings.Trim(hostport, "[]")
}

func isLoopbackHost(h string) bool {
	if strings.EqualFold(h, "localhost") {
		return true
	}
	ip := net.ParseIP(h)
	return ip != nil && ip.IsLoopback()
}

// withCORS replaces the old "Access-Control-Allow-Origin: *" middleware. It
// rejects disallowed origins outright (403) and only echoes allowed,
// cross-origin Origins back, so browsers never grant a foreign site access.
func (p *originPolicy) withCORS(next http.HandlerFunc) http.HandlerFunc {
	return func(w http.ResponseWriter, r *http.Request) {
		w.Header().Add("Vary", "Origin")
		if !p.Allows(r) {
			http.Error(w, "Origin not allowed", http.StatusForbidden)
			return
		}
		if origin := r.Header.Get("Origin"); origin != "" {
			w.Header().Set("Access-Control-Allow-Origin", origin)
			w.Header().Set("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
			w.Header().Set("Access-Control-Allow-Headers", "Accept, Content-Type, Content-Length, Accept-Encoding, Authorization")
		}
		if r.Method == http.MethodOptions {
			w.WriteHeader(http.StatusNoContent)
			return
		}
		next(w, r)
	}
}

// newHTTPServer returns a server with header and idle timeouts (slowloris
// protection). ReadTimeout/WriteTimeout are deliberately NOT set: they would
// cut off long-lived Live WebSockets (up to ~10 min) and slow image generation.
// Body sizes are capped per handler instead.
func newHTTPServer(addr string, h http.Handler) *http.Server {
	return &http.Server{
		Addr:              addr,
		Handler:           h,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       120 * time.Second,
		MaxHeaderBytes:    64 << 10,
	}
}
