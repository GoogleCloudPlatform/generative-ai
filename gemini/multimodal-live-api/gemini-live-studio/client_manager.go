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
	"context"
	"fmt"
	"net/url"
	"strings"
	"sync"

	"google.golang.org/genai"
)

// defaultLocation is used when no Vertex location is configured or requested.
const defaultLocation = "us-central1"

// clientManager caches one genai.Client per Vertex location so per-session
// model/location overrides reach the right regional endpoint.
type clientManager struct {
	mu        sync.Mutex
	projectID string
	baseURL   string
	clients   map[string]*genai.Client
}

func newClientManager(projectID, baseURL string) *clientManager {
	return &clientManager{
		projectID: projectID,
		baseURL:   baseURL,
		clients:   make(map[string]*genai.Client),
	}
}

// clientFor returns the cached client for location, creating it on first
// use. The client outlives any request, so it is built from
// context.Background(), and the lock is not held while genai.NewClient runs.
// Concurrent first calls for one location may each build a client; the first
// one stored wins.
func (cm *clientManager) clientFor(location string) (*genai.Client, error) {
	if location == "" {
		location = defaultLocation
	}

	cm.mu.Lock()
	cached, ok := cm.clients[location]
	cm.mu.Unlock()
	if ok {
		return cached, nil
	}

	created, err := genai.NewClient(context.Background(), &genai.ClientConfig{
		Backend:     genai.BackendVertexAI,
		Project:     cm.projectID,
		Location:    location,
		HTTPOptions: genai.HTTPOptions{BaseURL: baseURLForLocation(cm.baseURL, location)},
	})
	if err != nil {
		return nil, fmt.Errorf("creating genai client for %q: %w", location, err)
	}

	cm.mu.Lock()
	defer cm.mu.Unlock()
	if existing, ok := cm.clients[location]; ok {
		return existing, nil
	}
	cm.clients[location] = created
	return created, nil
}

// baseURLForLocation adapts a GEMINI_BASE_URL override to the target location.
// Vertex hosts encode the region as a hostname prefix
// ("us-central1-aiplatform.googleapis.com"), while the global endpoint has
// none ("aiplatform.googleapis.com"). Only the
// host's leading label is rewritten, and only for *.googleapis.com hosts, so
// custom proxies and paths are left untouched.
func baseURLForLocation(base, location string) string {
	if base == "" {
		return ""
	}
	u, err := url.Parse(base)
	if err != nil || u.Host == "" {
		return base
	}
	host := u.Hostname()
	if !strings.HasSuffix(strings.ToLower(host), ".googleapis.com") {
		return base
	}
	bareHost := host
	for _, loc := range append([]string{location}, locationRegistry...) {
		if loc != "" && strings.HasPrefix(bareHost, loc+"-") {
			bareHost = strings.TrimPrefix(bareHost, loc+"-")
			break
		}
	}
	newHost := bareHost
	if location != "global" {
		newHost = location + "-" + bareHost
	}
	if port := u.Port(); port != "" {
		newHost += ":" + port
	}
	u.Host = newHost
	return u.String()
}

// liveSessionAdapter abstracts *genai.Session so the WebSocket switchboard
// can be unit-tested offline without dialing the Live API.
type liveSessionAdapter interface {
	SendRealtimeInput(genai.LiveSendRealtimeInputParameters) error
	SendToolResponse(genai.LiveSendToolResponseParameters) error
	Receive() (*genai.LiveServerMessage, error)
	Close() error
}

// liveConnector abstracts establishing a Live Bidi session.
type liveConnector interface {
	Connect(ctx context.Context, model, location string, config *genai.LiveConnectConfig) (liveSessionAdapter, error)
}

// Connect dials a Live session. Note that genai ignores ctx after the dial:
// callers must Close the returned session to end it.
func (cm *clientManager) Connect(ctx context.Context, model, location string, config *genai.LiveConnectConfig) (liveSessionAdapter, error) {
	client, err := cm.clientFor(location)
	if err != nil {
		return nil, err
	}
	session, err := client.Live.Connect(ctx, model, config)
	if err != nil {
		return nil, fmt.Errorf("connecting to Live model %q in %q: %w", model, location, err)
	}
	return session, nil
}
