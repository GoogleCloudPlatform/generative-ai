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
	"context"
	"fmt"
	"log/slog"
	"sync"
	"time"

	"google.golang.org/genai"
)

// DefaultToolTimeout bounds server-side and page-relayed tool executions.
const DefaultToolTimeout = 2 * time.Minute

// ToolFunc executes a server-side Gemini Live function call. Returning an error
// converts it into a structured {"error": ...} FunctionResponse payload rather
// than dropping the session.
type ToolFunc func(ctx context.Context, args map[string]any) (map[string]any, error)

type registeredFunc struct {
	decl *genai.FunctionDeclaration
	fn   ToolFunc
}

// FuncRegistry stores server-side Gemini Live FunctionDeclarations and their
// corresponding Go handlers.
type FuncRegistry struct {
	mu    sync.RWMutex
	order []string
	funcs map[string]registeredFunc
}

// NewFuncRegistry creates an empty server-side function registry.
func NewFuncRegistry() *FuncRegistry {
	return &FuncRegistry{funcs: make(map[string]registeredFunc)}
}

// Register adds or replaces a server-side tool handler.
func (r *FuncRegistry) Register(decl *genai.FunctionDeclaration, fn ToolFunc) {
	if decl == nil || decl.Name == "" || fn == nil {
		return
	}
	r.mu.Lock()
	defer r.mu.Unlock()
	if _, exists := r.funcs[decl.Name]; !exists {
		r.order = append(r.order, decl.Name)
	}
	r.funcs[decl.Name] = registeredFunc{decl: decl, fn: fn}
}

// Has reports whether name is registered on the server.
func (r *FuncRegistry) Has(name string) bool {
	if r == nil {
		return false
	}
	r.mu.RLock()
	defer r.mu.RUnlock()
	_, ok := r.funcs[name]
	return ok
}

// Declarations returns the registered FunctionDeclarations in registration order.
func (r *FuncRegistry) Declarations() []*genai.FunctionDeclaration {
	if r == nil {
		return nil
	}
	r.mu.RLock()
	defer r.mu.RUnlock()
	out := make([]*genai.FunctionDeclaration, 0, len(r.order))
	for _, name := range r.order {
		out = append(out, r.funcs[name].decl)
	}
	return out
}

// Execute invokes name and normalizes nil/error outputs into a non-nil response
// map suitable for genai.FunctionResponse.
func (r *FuncRegistry) Execute(ctx context.Context, name string, args map[string]any) map[string]any {
	if r == nil {
		return map[string]any{"status": "unknown_tool", "error": fmt.Sprintf("unrecognized tool %q", name)}
	}
	r.mu.RLock()
	entry, ok := r.funcs[name]
	r.mu.RUnlock()
	if !ok {
		return map[string]any{"status": "unknown_tool", "error": fmt.Sprintf("unrecognized tool %q", name)}
	}
	res, err := entry.fn(ctx, args)
	if err != nil {
		return map[string]any{"error": err.Error()}
	}
	if res == nil {
		return map[string]any{}
	}
	return res
}

// ToolRunnerConfig configures asynchronous server-side and page-relayed tool
// execution for a Live session.
type ToolRunnerConfig struct {
	// Registry holds server-side Go tools. Optional when AllowPageRelay is true.
	Registry *FuncRegistry
	// AllowPageRelay forwards unregistered FunctionCalls to the browser over
	// WebSocket (e.g. WebMCP page tools) and awaits a tool_response/tool_result.
	AllowPageRelay bool
	// Timeout bounds each server-side or page-relayed tool call. Defaults to 2m.
	Timeout time.Duration
	// SeeVisualResults injects any PNG/JPEG data URL returned by a page tool as
	// a realtime Video frame immediately before SendToolResponse.
	SeeVisualResults bool
	// EmitTiming sends a {"type": "tool_timing", ...} message after page tools complete.
	EmitTiming bool
	// ServerToolEventType overrides the JSON "type" sent to the browser when a
	// server-side tool completes (defaults to "tool_call").
	ServerToolEventType string
	// CancelEventType overrides the JSON "type" sent to the browser when tool
	// calls are cancelled (defaults to "tool_call_cancellation").
	CancelEventType string
}

type pendingPageCall struct {
	name    string
	started time.Time
	timer   *time.Timer
}

// ToolRunner dispatches FunctionCalls off the Live Receive() goroutine, tracks
// in-flight server and browser calls by ID, handles ToolCallCancellation on
// barge-in, and cleans up timers and goroutines on session shutdown.
type ToolRunner struct {
	cfg ToolRunnerConfig

	mu               sync.Mutex
	activeServer     map[string]context.CancelFunc
	pendingPage      map[string]*pendingPageCall
	seeVisualResults bool
	closed           bool

	wg sync.WaitGroup
}

// NewToolRunner constructs a ToolRunner from cfg.
func NewToolRunner(cfg ToolRunnerConfig) *ToolRunner {
	if cfg.Timeout <= 0 {
		cfg.Timeout = DefaultToolTimeout
	}
	if cfg.ServerToolEventType == "" {
		cfg.ServerToolEventType = "tool_call"
	}
	if cfg.CancelEventType == "" {
		cfg.CancelEventType = "tool_call_cancellation"
	}
	return &ToolRunner{
		cfg:              cfg,
		activeServer:     make(map[string]context.CancelFunc),
		pendingPage:      make(map[string]*pendingPageCall),
		seeVisualResults: cfg.SeeVisualResults,
	}
}

// SetSeeVisualResults toggles whether page-relayed tool image snapshots are
// forwarded as realtime Video frames before SendToolResponse.
func (tr *ToolRunner) SetSeeVisualResults(enabled bool) {
	tr.mu.Lock()
	tr.seeVisualResults = enabled
	tr.mu.Unlock()
}

// Dispatch handles a LiveServerToolCall without blocking the caller's Receive() loop.
func (tr *ToolRunner) Dispatch(
	sessionCtx context.Context,
	toolCall *genai.LiveServerToolCall,
	writeJSON func(any),
	sendRealtime func(genai.LiveSendRealtimeInputParameters) error,
	sendResponses func([]*genai.FunctionResponse) error,
	onSendErr func(what string, err error),
) {
	if tr == nil || toolCall == nil {
		return
	}
	for _, call := range toolCall.FunctionCalls {
		if call == nil {
			continue
		}
		if tr.cfg.AllowPageRelay && (tr.cfg.Registry == nil || !tr.cfg.Registry.Has(call.Name)) {
			tr.dispatchPageCall(call, writeJSON, sendResponses, onSendErr)
			continue
		}
		tr.dispatchServerCall(sessionCtx, call, writeJSON, sendResponses, onSendErr)
	}
}

func (tr *ToolRunner) dispatchServerCall(
	sessionCtx context.Context,
	call *genai.FunctionCall,
	writeJSON func(any),
	sendResponses func([]*genai.FunctionResponse) error,
	onSendErr func(what string, err error),
) {
	callCtx, cancel := context.WithTimeout(sessionCtx, tr.cfg.Timeout)

	tr.mu.Lock()
	if tr.closed {
		tr.mu.Unlock()
		cancel()
		return
	}
	if call.ID != "" {
		if prev, ok := tr.activeServer[call.ID]; ok {
			prev()
		}
		tr.activeServer[call.ID] = cancel
	}
	tr.wg.Add(1)
	tr.mu.Unlock()

	go func(c *genai.FunctionCall) {
		defer tr.wg.Done()
		defer cancel()

		result := tr.cfg.Registry.Execute(callCtx, c.Name, c.Args)

		tr.mu.Lock()
		_, stillActive := tr.activeServer[c.ID]
		if c.ID != "" {
			delete(tr.activeServer, c.ID)
		}
		closed := tr.closed
		tr.mu.Unlock()

		// If cancelled via ToolCallCancellation or session shutdown while running,
		// drop the stale response so it never races the next turn.
		if closed || (c.ID != "" && !stillActive) || sessionCtx.Err() != nil {
			return
		}

		writeJSON(map[string]any{
			"type":   tr.cfg.ServerToolEventType,
			"id":     c.ID,
			"name":   c.Name,
			"args":   c.Args,
			"result": result,
		})
		if err := sendResponses([]*genai.FunctionResponse{{ID: c.ID, Name: c.Name, Response: result}}); err != nil && onSendErr != nil {
			onSendErr("tool response", err)
		}
	}(call)
}

func (tr *ToolRunner) dispatchPageCall(
	call *genai.FunctionCall,
	writeJSON func(any),
	sendResponses func([]*genai.FunctionResponse) error,
	onSendErr func(what string, err error),
) {
	id, name := call.ID, call.Name

	tr.mu.Lock()
	if tr.closed {
		tr.mu.Unlock()
		return
	}
	if prev := tr.pendingPage[id]; prev != nil {
		prev.timer.Stop()
	}
	tr.pendingPage[id] = &pendingPageCall{
		name:    name,
		started: time.Now(),
		timer: time.AfterFunc(tr.cfg.Timeout, func() {
			if tr.takePendingPage(id) != nil {
				slog.Warn("page tool call timed out", "name", name)
				writeJSON(map[string]any{
					"type":   tr.cfg.CancelEventType,
					"ids":    []string{id},
					"reason": "timeout",
				})
				errResp := []*genai.FunctionResponse{{
					ID:       id,
					Name:     name,
					Response: map[string]any{"error": "the page did not answer in time"},
				}}
				if err := sendResponses(errResp); err != nil && onSendErr != nil {
					onSendErr("tool timeout response", err)
				}
			}
		}),
	}
	tr.mu.Unlock()

	writeJSON(map[string]any{
		"type": "tool_call",
		"id":   id,
		"name": name,
		"args": call.Args,
	})
}

func (tr *ToolRunner) takePendingPage(id string) *pendingPageCall {
	tr.mu.Lock()
	defer tr.mu.Unlock()
	p := tr.pendingPage[id]
	if p != nil {
		p.timer.Stop()
		delete(tr.pendingPage, id)
	}
	return p
}

// CompletePageCall processes a browser tool_response / tool_result frame. When
// SeeVisualResults is enabled and imageDataURL holds a PNG/JPEG data URL, the
// decoded frame is injected via sendRealtime({Video: ...}) strictly before
// sendResponses so the model sees the visual result before speaking.
func (tr *ToolRunner) CompletePageCall(
	id, fallbackName string,
	result map[string]any,
	imageDataURL string,
	execMs int64,
	writeJSON func(any),
	sendRealtime func(genai.LiveSendRealtimeInputParameters) error,
	sendResponses func([]*genai.FunctionResponse) error,
	onSendErr func(what string, err error),
) bool {
	if tr == nil {
		return false
	}
	p := tr.takePendingPage(id)
	name := fallbackName
	var roundTripMs int64
	if p != nil {
		name = p.name
		roundTripMs = time.Since(p.started).Milliseconds()
	} else if tr.cfg.AllowPageRelay {
		// Unknown, already cancelled, or timed out page call.
		return false
	}
	if name == "" {
		return false
	}
	if result == nil {
		result = map[string]any{}
	}

	tr.mu.Lock()
	see := tr.seeVisualResults
	tr.mu.Unlock()

	if see && imageDataURL != "" && sendRealtime != nil {
		if mimeType, data, err := ParseImageDataURL(imageDataURL, RealtimeVideoMIMETypes); err == nil {
			if err := sendRealtime(genai.LiveSendRealtimeInputParameters{
				Video: &genai.Blob{MIMEType: mimeType, Data: data},
			}); err != nil {
				if onSendErr != nil {
					onSendErr("tool result image", err)
				}
				return true
			}
		}
	}

	if err := sendResponses([]*genai.FunctionResponse{{ID: id, Name: name, Response: result}}); err != nil {
		if onSendErr != nil {
			onSendErr("tool response", err)
		}
		return true
	}

	if p != nil && tr.cfg.EmitTiming && writeJSON != nil {
		writeJSON(map[string]any{
			"type":        "tool_timing",
			"id":          id,
			"name":        name,
			"roundTripMs": roundTripMs,
			"execMs":      execMs,
		})
	}
	return true
}

// Cancel aborts in-flight server-side or page-relayed tool calls matching ids
// and notifies the browser.
func (tr *ToolRunner) Cancel(ids []string, writeJSON func(any)) {
	if tr == nil || len(ids) == 0 {
		return
	}
	var cancelledPageIDs []string

	tr.mu.Lock()
	for _, id := range ids {
		if cancel, ok := tr.activeServer[id]; ok {
			delete(tr.activeServer, id)
			cancel()
		}
		if p, ok := tr.pendingPage[id]; ok {
			p.timer.Stop()
			delete(tr.pendingPage, id)
			cancelledPageIDs = append(cancelledPageIDs, id)
		}
	}
	tr.mu.Unlock()

	if writeJSON == nil {
		return
	}
	if tr.cfg.AllowPageRelay {
		if len(cancelledPageIDs) > 0 {
			writeJSON(map[string]any{
				"type":   tr.cfg.CancelEventType,
				"ids":    cancelledPageIDs,
				"reason": "model",
			})
		}
		return
	}
	writeJSON(map[string]any{
		"type": tr.cfg.CancelEventType,
		"ids":  ids,
	})
}

// CancelAll aborts all active server-side tool contexts and stops all pending
// page-tool timers without waiting for goroutines (safe to call inside Shutdown).
func (tr *ToolRunner) CancelAll() {
	if tr == nil {
		return
	}
	tr.mu.Lock()
	tr.closed = true
	for id, cancel := range tr.activeServer {
		delete(tr.activeServer, id)
		cancel()
	}
	for id, p := range tr.pendingPage {
		p.timer.Stop()
		delete(tr.pendingPage, id)
	}
	tr.mu.Unlock()
}

// Close cancels all active server-side tool contexts, stops pending page-tool
// timers, and waits for server-side tool goroutines to return.
func (tr *ToolRunner) Close() {
	if tr == nil {
		return
	}
	tr.CancelAll()
	tr.wg.Wait()
}
