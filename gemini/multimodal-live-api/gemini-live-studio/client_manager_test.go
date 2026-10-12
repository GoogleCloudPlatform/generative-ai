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
	"sync"
	"testing"
)

func TestBaseURLForLocation(t *testing.T) {
	const regional = "https://us-central1-aiplatform.googleapis.com"
	cases := []struct {
		name, base, loc, want string
	}{
		{"unset", "", "global", ""},
		{"regional to global strips prefix", regional, "global", "https://aiplatform.googleapis.com"},
		{"regional to same region unchanged", regional, "us-central1", regional},
		{"global to regional adds prefix", "https://aiplatform.googleapis.com", "us-central1", regional},
		{"global stays global", "https://aiplatform.googleapis.com", "global", "https://aiplatform.googleapis.com"},
		{"region swap", regional, "europe-west4", "https://europe-west4-aiplatform.googleapis.com"},
		{"path and port preserved", "https://us-central1-aiplatform.googleapis.com:443/v1beta1", "global", "https://aiplatform.googleapis.com:443/v1beta1"},
		// The old strings.Replace rewrote "global" anywhere in the URL.
		{"'global' in path is not rewritten", "https://aiplatform.googleapis.com/global/x", "us-central1", "https://us-central1-aiplatform.googleapis.com/global/x"},
		{"custom proxy untouched", "https://my-global-proxy.example.com", "us-central1", "https://my-global-proxy.example.com"},
		{"unparseable untouched", "://bad", "global", "://bad"},
	}
	for _, tc := range cases {
		t.Run(tc.name, func(t *testing.T) {
			if got := baseURLForLocation(tc.base, tc.loc); got != tc.want {
				t.Fatalf("baseURLForLocation(%q, %q) = %q, want %q", tc.base, tc.loc, got, tc.want)
			}
		})
	}
}

// Concurrent first calls for one location must all get the same cached client.
func TestClientManager_ConcurrentFirstCallsShareClient(t *testing.T) {
	cm := newClientManager("test-project", "")

	var wg sync.WaitGroup
	got := make([]any, 8)
	errs := make([]error, len(got))
	for i := range got {
		wg.Add(1)
		go func(i int) {
			defer wg.Done()
			got[i], errs[i] = cm.clientFor("global")
		}(i)
	}
	wg.Wait()
	for _, err := range errs {
		if err != nil {
			t.Skipf("genai.NewClient needs credentials in this environment: %v", err)
		}
	}
	for i := 1; i < len(got); i++ {
		if got[i] != got[0] {
			t.Fatal("concurrent first calls returned different cached clients")
		}
	}
}
