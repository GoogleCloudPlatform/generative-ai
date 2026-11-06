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
	"net/http"

	"gemini-live-studio/livebridge"
)

const (
	maxInitialConfigBytes = livebridge.MaxInitialConfigBytes
	maxClientMessageBytes = livebridge.MaxClientMessageBytes
	maxGenerateAvatarBody = livebridge.MaxGenerateAvatarBody
	maxDescribeImageBody  = livebridge.MaxDescribeImageBody
)

type originPolicy struct {
	*livebridge.OriginPolicy
}

func newOriginPolicy(allowedCSV string) *originPolicy {
	return &originPolicy{OriginPolicy: livebridge.NewOriginPolicy(allowedCSV)}
}

func newOriginPolicyFromEnv() *originPolicy {
	return &originPolicy{OriginPolicy: livebridge.NewOriginPolicyFromEnv()}
}

func (p *originPolicy) withCORS(next http.HandlerFunc) http.HandlerFunc {
	return p.WithCORS(next)
}

func newHTTPServer(addr string, h http.Handler) *http.Server {
	return livebridge.NewHTTPServer(addr, h)
}
