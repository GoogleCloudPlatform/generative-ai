/*
Copyright © 2026 Google LLC

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

	http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
*/

package dto

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"
)

func boolPtr(v bool) *bool { return &v }

func TestSyncAddRequest_Validate(t *testing.T) {
	tests := []struct {
		name    string
		req     SyncAddRequest
		wantErr bool
	}{
		{
			name:    "zero value is valid",
			req:     SyncAddRequest{},
			wantErr: false,
		},
		{
			name:    "dry_run true is valid",
			req:     SyncAddRequest{DryRun: boolPtr(true)},
			wantErr: false,
		},
		{
			name:    "dry_run false is valid",
			req:     SyncAddRequest{DryRun: boolPtr(false)},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.req.Validate()
			if tt.wantErr {
				require.Error(t, err)
			} else {
				require.NoError(t, err)
			}
		})
	}
}

func TestSyncRemoveRequest_Validate(t *testing.T) {
	tests := []struct {
		name    string
		req     SyncRemoveRequest
		wantErr bool
	}{
		{
			name:    "zero value is valid",
			req:     SyncRemoveRequest{},
			wantErr: false,
		},
		{
			name:    "dry_run true is valid",
			req:     SyncRemoveRequest{DryRun: boolPtr(true)},
			wantErr: false,
		},
		{
			name:    "dry_run false is valid",
			req:     SyncRemoveRequest{DryRun: boolPtr(false)},
			wantErr: false,
		},
	}

	for _, tt := range tests {
		t.Run(tt.name, func(t *testing.T) {
			err := tt.req.Validate()
			if tt.wantErr {
				require.Error(t, err)
			} else {
				require.NoError(t, err)
			}
		})
	}
}

func TestSyncAddResponse_HasRequestID(t *testing.T) {
	resp := SyncAddResponse{RequestID: "req-123"}
	assert.Equal(t, "req-123", resp.RequestID)
}

func TestSyncRemoveResponse_HasRequestID(t *testing.T) {
	resp := SyncRemoveResponse{RequestID: "req-456"}
	assert.Equal(t, "req-456", resp.RequestID)
}

// TestSyncAddResponse_ZeroValue ensures the zero value of SyncAddResponse is
// a safe, usable default (dry_run defaults to false, counts default to 0).
func TestSyncAddResponse_ZeroValue(t *testing.T) {
	var resp SyncAddResponse
	assert.False(t, resp.DryRun)
	assert.Equal(t, 0, resp.LicensesGranted)
	assert.Equal(t, 0, resp.GroupsProcessed)
}

// TestSyncRemoveResponse_ZeroValue ensures the zero value of SyncRemoveResponse
// is a safe, usable default.
func TestSyncRemoveResponse_ZeroValue(t *testing.T) {
	var resp SyncRemoveResponse
	assert.False(t, resp.DryRun)
	assert.Equal(t, 0, resp.LicensesRevoked)
	assert.Equal(t, 0, resp.UsersEvaluated)
}
