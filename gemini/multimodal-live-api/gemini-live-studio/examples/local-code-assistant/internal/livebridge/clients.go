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
	"net/url"
	"strings"
	"sync"

	"google.golang.org/genai"
)

// DefaultLocation is the default Google Cloud regional endpoint for Gemini Live.
const DefaultLocation = "us-central1"

// Session abstracts *genai.Session so the switchboard and tool runner can be
// tested hermetically without dialing the Gemini Live API.
type Session interface {
	SendRealtimeInput(genai.LiveSendRealtimeInputParameters) error
	SendToolResponse(genai.LiveSendToolResponseParameters) error
	Receive() (*genai.LiveServerMessage, error)
	Close() error
}

// Connector dials an upstream Gemini Live Bidi session.
type Connector interface {
	Connect(ctx context.Context, model, location string, config *genai.LiveConnectConfig) (Session, error)
}

// ClientPool caches one *genai.Client per Vertex location (e.g. "us-central1"
// for Live Bidi streams and "global" for image or TTS synthesis).
type ClientPool struct {
	mu             sync.Mutex
	projectID      string
	baseURL        string
	knownLocations []string
	clients        map[string]*genai.Client
}

// NewClientPool creates a per-location Vertex *genai.Client cache.
func NewClientPool(projectID, baseURL string, knownLocations ...string) *ClientPool {
	if len(knownLocations) == 0 {
		knownLocations = []string{DefaultLocation, "global"}
	}
	return &ClientPool{
		projectID:      projectID,
		baseURL:        baseURL,
		knownLocations: append([]string(nil), knownLocations...),
		clients:        make(map[string]*genai.Client),
	}
}

// ClientFor returns the cached *genai.Client for location, creating it from
// context.Background() on first use without holding the cache mutex across
// genai.NewClient.
func (p *ClientPool) ClientFor(location string) (*genai.Client, error) {
	if location == "" {
		location = DefaultLocation
	}

	p.mu.Lock()
	cached, ok := p.clients[location]
	p.mu.Unlock()
	if ok {
		return cached, nil
	}

	created, err := genai.NewClient(context.Background(), &genai.ClientConfig{
		Backend:     genai.BackendVertexAI,
		Project:     p.projectID,
		Location:    location,
		HTTPOptions: genai.HTTPOptions{BaseURL: BaseURLForLocation(p.baseURL, location, p.knownLocations...)},
	})
	if err != nil {
		return nil, fmt.Errorf("creating genai client for %q: %w", location, err)
	}

	p.mu.Lock()
	defer p.mu.Unlock()
	if existing, ok := p.clients[location]; ok {
		return existing, nil
	}
	p.clients[location] = created
	return created, nil
}

// Connect dials a Gemini Live session for model and location. Note that
// genai's Live.Connect ignores ctx after dialing; callers must Close the
// returned Session explicitly.
func (p *ClientPool) Connect(ctx context.Context, model, location string, config *genai.LiveConnectConfig) (Session, error) {
	client, err := p.ClientFor(location)
	if err != nil {
		return nil, err
	}
	session, err := client.Live.Connect(ctx, model, config)
	if err != nil {
		return nil, fmt.Errorf("connecting to Live model %q in %q: %w", model, location, err)
	}
	return session, nil
}

// BaseURLForLocation rewrites the regional host prefix on *.googleapis.com
// endpoints ("us-central1-aiplatform.googleapis.com" <-> "aiplatform.googleapis.com")
// while leaving custom proxy hosts, ports, and URL paths untouched.
func BaseURLForLocation(base, location string, knownLocations ...string) string {
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
	if len(knownLocations) == 0 {
		knownLocations = []string{DefaultLocation, "global"}
	}
	bareHost := host
	for _, loc := range append([]string{location}, knownLocations...) {
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
