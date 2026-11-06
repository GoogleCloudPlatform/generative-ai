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
	"log/slog"
	"net"
	"net/http"
	"net/url"
	"os"
	"slices"
	"strings"
	"time"

	"github.com/gorilla/websocket"
)

// Default request and WebSocket frame size limits.
const (
	MaxInitialConfigBytes = 16 << 20 // 16 MiB (2K 9:16 base64 avatar + persona/grounding)
	MaxClientMessageBytes = 8 << 20  // 8 MiB (16 kHz PCM chunks, 1 FPS JPEG vision frames, tool results)
	MaxGenerateAvatarBody = 16 << 20 // 16 MiB (/api/generate-avatar reference image body)
	MaxDescribeImageBody  = 8 << 20  // 8 MiB (/api/describe-image upload body)
)

// OriginPolicy decides which browser origins may call HTTP APIs and upgrade
// Live WebSockets, preventing cross-site WebSocket hijacking.
//
// Permitted requests:
//   - requests with no Origin header (unless Sec-Fetch-Site explicitly reports cross-site);
//   - same-origin requests (Origin host == request Host);
//   - loopback origins when the server itself was reached on a loopback interface
//     (allowing local Vite dev servers such as localhost:5173 -> localhost:8080);
//   - exact scheme://host[:port] matches listed in ALLOWED_ORIGINS.
type OriginPolicy struct {
	allowed map[string]bool
}

// NewOriginPolicy parses a comma-separated list of allowed origins
// (e.g. "https://avatar.example.com,http://partner.test:3000").
func NewOriginPolicy(allowedCSV string) *OriginPolicy {
	p := &OriginPolicy{allowed: map[string]bool{}}
	for _, o := range strings.Split(allowedCSV, ",") {
		o = strings.TrimRight(strings.ToLower(strings.TrimSpace(o)), "/")
		if o != "" {
			p.allowed[o] = true
		}
	}
	return p
}

// NewOriginPolicyFromEnv constructs an OriginPolicy from ALLOWED_ORIGINS.
func NewOriginPolicyFromEnv() *OriginPolicy {
	return NewOriginPolicy(os.Getenv("ALLOWED_ORIGINS"))
}

// AllowedCount returns the number of explicitly configured ALLOWED_ORIGINS entries.
func (p *OriginPolicy) AllowedCount() int {
	if p == nil {
		return 0
	}
	return len(p.allowed)
}

// Allows reports whether r is permitted by this policy.
func (p *OriginPolicy) Allows(r *http.Request) bool {
	origin := r.Header.Get("Origin")
	if origin == "" {
		return !strings.EqualFold(r.Header.Get("Sec-Fetch-Site"), "cross-site")
	}
	u, err := url.Parse(origin)
	if err != nil || u.Host == "" || (u.Scheme != "http" && u.Scheme != "https") {
		return false
	}
	if p != nil && p.allowed[strings.ToLower(u.Scheme+"://"+u.Host)] {
		return true
	}
	if strings.EqualFold(u.Host, r.Host) {
		return true
	}
	return IsLoopbackHost(u.Hostname()) && IsLoopbackHost(HostOnly(r.Host))
}

// WithCORS wraps next with strict origin validation, rejecting disallowed
// origins with 403 Forbidden and echoing Access-Control-Allow-Origin only for
// permitted origins.
func (p *OriginPolicy) WithCORS(next http.HandlerFunc) http.HandlerFunc {
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

// Upgrader returns a websocket.Upgrader enforcing p.Allows on every upgrade.
func (p *OriginPolicy) Upgrader() websocket.Upgrader {
	return websocket.Upgrader{
		CheckOrigin: func(r *http.Request) bool {
			if p.Allows(r) {
				return true
			}
			slog.Warn("rejected WebSocket upgrade; set ALLOWED_ORIGINS to permit it", "origin", r.Header.Get("Origin"), "host", r.Host)
			return false
		},
	}
}

// HostOnly strips any port or IPv6 brackets from hostport.
func HostOnly(hostport string) string {
	if h, _, err := net.SplitHostPort(hostport); err == nil {
		return h
	}
	return strings.Trim(hostport, "[]")
}

// IsLoopbackHost reports whether h is "localhost" or a loopback IP address.
func IsLoopbackHost(h string) bool {
	if strings.EqualFold(h, "localhost") {
		return true
	}
	ip := net.ParseIP(h)
	return ip != nil && ip.IsLoopback()
}

// NewHTTPServer returns an *http.Server configured with slowloris header and
// idle timeouts, intentionally leaving ReadTimeout and WriteTimeout unset so
// long-lived (~10 minute) Live WebSocket streams and image syntheses are not
// prematurely terminated.
func NewHTTPServer(addr string, h http.Handler) *http.Server {
	return &http.Server{
		Addr:              addr,
		Handler:           h,
		ReadHeaderTimeout: 10 * time.Second,
		IdleTimeout:       120 * time.Second,
		MaxHeaderBytes:    64 << 10,
	}
}

// AllowedValues returns registry with def prepended when def is non-empty and
// not already present.
func AllowedValues(def string, registry []string) []string {
	if def == "" || slices.Contains(registry, def) {
		return slices.Clone(registry)
	}
	return append([]string{def}, registry...)
}

// ResolveAllowed returns requested if it equals def or appears in registry,
// falling back to def and logging a warning otherwise.
func ResolveAllowed(kind, requested, def string, registry []string) string {
	requested = strings.TrimSpace(requested)
	if requested == "" || requested == def {
		return def
	}
	if slices.Contains(registry, requested) {
		return requested
	}
	slog.Warn("rejected client-requested value not in allowlist; using default", "kind", kind, "requested", requested, "default", def)
	return def
}
