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

package cmd

import (
	"testing"

	"github.com/google/go-cmp/cmp"
)

func TestSubcommandRegistration(t *testing.T) {
	subcommands := []string{"example", "run", "compare", "multivideo", "multiturn"}

	for _, sub := range subcommands {
		cmd, _, err := RootCmd.Find([]string{sub})
		if err != nil {
			t.Errorf("RootCmd.Find(%q) error = %v, want nil", sub, err)
			continue
		}
		if cmd == nil || cmd.Name() != sub {
			t.Errorf("RootCmd.Find(%q) = %v, want command with name %q", sub, cmd, sub)
		}
	}
}

func TestRunCommandRequiredFlags(t *testing.T) {
	cmd, _, err := RootCmd.Find([]string{"run"})
	if err != nil {
		t.Fatalf("RootCmd.Find(%q) error = %v, want nil", "run", err)
	}
	if err := cmd.ParseFlags([]string{}); err != nil {
		t.Fatalf("cmd.ParseFlags(nil) error = %v, want nil", err)
	}
	if err := cmd.ValidateRequiredFlags(); err == nil {
		t.Errorf("runCmd.ValidateRequiredFlags() with missing --video = nil, want non-nil error")
	}

	prevURI := runVideoURI
	t.Cleanup(func() { runVideoURI = prevURI })
	runVideoURI = ""
	if err := runCmd.RunE(runCmd, nil); err == nil {
		t.Errorf("runCmd.RunE(runCmd, nil) with empty video URI = nil, want non-nil error")
	}
}

func TestResolveModelsList(t *testing.T) {
	tests := []struct {
		name  string
		input string
		want  []string
	}{
		{name: "empty", input: "", want: nil},
		{name: "alias_flash", input: "flash", want: []string{"gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"}},
		{name: "alias_all", input: "all", want: []string{"gemini-3.6-flash", "gemini-3.7-flash", "gemini-3.8-flash"}},
		{name: "short_version_numbers", input: "3.6,3.8", want: []string{"gemini-3.6-flash", "gemini-3.8-flash"}},
		{name: "argon_shorthand", input: "3.8,argon", want: []string{"gemini-3.8-flash", "gemini-4-argon"}},
		{name: "full_model_ids", input: "gemini-3.7-flash,gemini-3.8-flash,gemini-4-argon", want: []string{"gemini-3.7-flash", "gemini-3.8-flash", "gemini-4-argon"}},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			got := resolveModelsList(tt.input)
			if diff := cmp.Diff(tt.want, got); diff != "" {
				t.Errorf("resolveModelsList(%q) diff (-want +got):\n%s", tt.input, diff)
			}
		})
	}
}
