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

package tools

import (
	"context"
	"fmt"
	"log/slog"
	"sort"
	"sync"

	"google.golang.org/genai"
)

// Registry manages the collection of tools available to the Gemini Live agent.
type Registry struct {
	mu    sync.RWMutex
	tools map[string]Tool
}

// NewRegistry initializes a Registry with the provided tools.
func NewRegistry(initialTools ...Tool) *Registry {
	r := &Registry{
		tools: make(map[string]Tool),
	}
	for _, t := range initialTools {
		r.Register(t)
	}
	return r
}

// Register registers a tool by its name.
func (r *Registry) Register(t Tool) {
	r.mu.Lock()
	defer r.mu.Unlock()
	r.tools[t.Name()] = t
}

// Lookup returns the tool registered under name.
func (r *Registry) Lookup(name string) (Tool, bool) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	t, ok := r.tools[name]
	return t, ok
}

// Declarations converts all registered tools into Gen AI FunctionDeclarations.
func (r *Registry) Declarations() []*genai.FunctionDeclaration {
	r.mu.RLock()
	defer r.mu.RUnlock()

	names := make([]string, 0, len(r.tools))
	for name := range r.tools {
		names = append(names, name)
	}
	sort.Strings(names) // stable order across sessions
	decls := make([]*genai.FunctionDeclaration, 0, len(names))
	for _, name := range names {
		decls = append(decls, r.tools[name].Declaration())
	}
	return decls
}

// Execute looks up and executes the specified tool, returning a JSON-serializable map.
func (r *Registry) Execute(ctx context.Context, name string, args map[string]any) map[string]any {
	r.mu.RLock()
	t, ok := r.tools[name]
	r.mu.RUnlock()

	if !ok {
		slog.Warn("tool not found", "tool", name)
		return map[string]any{"error": fmt.Sprintf("unknown tool %q", name)}
	}

	slog.Info("executing tool", "tool", name, "args", args)
	result, err := t.Execute(ctx, args)
	if err != nil {
		slog.Warn("tool failed", "tool", name, "err", err)
		return map[string]any{"error": err.Error()}
	}
	return result
}
