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
	"log/slog"
	"slices"
	"strings"
)

// Curated registries of models and locations a browser client may request.
// The server's own env-configured defaults are always allowed in addition, so
// operators can still point the app at any model via GEMINI_LIVE_MODEL etc.
var (
	liveModelRegistry = []string{
		"gemini-3.8-live",
	}
	imageModelRegistry = []string{
		"gemini-nano-banana-2.1",
		"gemini-3.1-flash-image",
		"gemini-3-pro-image",
		"gemini-3.1-flash-lite-image",
	}
	locationRegistry = []string{
		"us-central1",
		"global",
	}
)

// allowedValues returns the registry with the server default prepended when
// it is not already listed.
func allowedValues(def string, registry []string) []string {
	if def == "" || slices.Contains(registry, def) {
		return slices.Clone(registry)
	}
	return append([]string{def}, registry...)
}

// resolveAllowed returns the client-requested value if it is the server
// default or in the registry, and the server default otherwise. Client input
// must never reach the Vertex API unchecked.
func resolveAllowed(kind, requested, def string, registry []string) string {
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
