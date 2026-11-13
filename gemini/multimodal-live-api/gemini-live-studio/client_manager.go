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
	"context"

	"google.golang.org/genai"

	"gemini-live-studio/livebridge"
)

const defaultLocation = livebridge.DefaultLocation

type liveSessionAdapter = livebridge.Session
type liveConnector = livebridge.Connector

type clientManager struct {
	pool *livebridge.ClientPool
}

func newClientManager(projectID, baseURL string) *clientManager {
	return &clientManager{
		pool: livebridge.NewClientPool(projectID, baseURL, locationRegistry...),
	}
}

func (cm *clientManager) clientFor(location string) (*genai.Client, error) {
	return cm.pool.ClientFor(location)
}

func (cm *clientManager) Connect(ctx context.Context, model, location string, config *genai.LiveConnectConfig) (liveSessionAdapter, error) {
	return cm.pool.Connect(ctx, model, location, config)
}

func baseURLForLocation(base, location string) string {
	return livebridge.BaseURLForLocation(base, location, locationRegistry...)
}
