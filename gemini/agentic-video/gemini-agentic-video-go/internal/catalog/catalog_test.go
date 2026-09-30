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

package catalog

import (
	"testing"
)

func TestCatalogScenarios(t *testing.T) {
	if len(Scenarios) < 6 {
		t.Fatalf("len(Scenarios) = %d, want at least 6", len(Scenarios))
	}

	for i := 1; i <= len(Scenarios); i++ {
		scenario, err := Find(i)
		if err != nil {
			t.Errorf("Find(%d) error = %v, want nil", i, err)
			continue
		}
		if scenario.ID != i {
			t.Errorf("Find(%d).ID = %d, want %d", i, scenario.ID, i)
		}
		if scenario.Title == "" {
			t.Errorf("Find(%d).Title is empty, want non-empty string", i)
		}
	}

	// Test invalid scenario ID returns an error
	if _, err := Find(999); err == nil {
		t.Errorf("Find(999) error = nil, want non-nil")
	}
}
