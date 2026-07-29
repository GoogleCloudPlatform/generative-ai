package config

import (
	"testing"

	"github.com/stretchr/testify/assert"
	"github.com/stretchr/testify/require"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
)

func TestLoadJobSettings(t *testing.T) {
	tests := []struct {
		name    string
		env     map[string]string
		want    *JobSettings
		wantErr error
	}{
		{
			name: "happy path: only JOB_TYPE set, all others default",
			env: map[string]string{
				"JOB_TYPE": "joiner",
			},
			want: &JobSettings{
				JobType:   models.WorkflowJoiner,
				DryRun:    false,
				TaskIndex: 0,
				TaskCount: 1,
			},
		},
		{
			name: "happy path: all fields set to valid non-default values",
			env: map[string]string{
				"JOB_TYPE":              "garbage_collection",
				"DRY_RUN":               "true",
				"CLOUD_RUN_TASK_INDEX":  "2",
				"CLOUD_RUN_TASK_COUNT":  "5",
			},
			want: &JobSettings{
				JobType:   models.WorkflowGarbageCollection,
				DryRun:    true,
				TaskIndex: 2,
				TaskCount: 5,
			},
		},
		{
			name:    "missing JOB_TYPE",
			env:     map[string]string{},
			wantErr: models.ErrConfigInvalid,
		},
		{
			name: "unrecognised JOB_TYPE",
			env: map[string]string{
				"JOB_TYPE": "gc",
			},
			wantErr: models.ErrConfigInvalid,
		},
		{
			name: "invalid DRY_RUN value",
			env: map[string]string{
				"JOB_TYPE": "joiner",
				"DRY_RUN":  "yes",
			},
			wantErr: models.ErrConfigInvalid,
		},
		{
			name: "invalid CLOUD_RUN_TASK_INDEX",
			env: map[string]string{
				"JOB_TYPE":             "joiner",
				"CLOUD_RUN_TASK_INDEX": "abc",
			},
			wantErr: models.ErrConfigInvalid,
		},
		{
			name: "CLOUD_RUN_TASK_COUNT=0",
			env: map[string]string{
				"JOB_TYPE":             "joiner",
				"CLOUD_RUN_TASK_COUNT": "0",
			},
			wantErr: models.ErrConfigInvalid,
		},
		{
			name: "TaskIndex >= TaskCount",
			env: map[string]string{
				"JOB_TYPE":             "joiner",
				"CLOUD_RUN_TASK_INDEX": "3",
				"CLOUD_RUN_TASK_COUNT": "3",
			},
			wantErr: models.ErrConfigInvalid,
		},
	}

	for _, tc := range tests {
		t.Run(tc.name, func(t *testing.T) {
			// Unset all relevant vars so each sub-test starts from a clean slate,
			// then apply only the vars declared for this case.
			for _, key := range []string{"JOB_TYPE", "DRY_RUN", "CLOUD_RUN_TASK_INDEX", "CLOUD_RUN_TASK_COUNT"} {
				t.Setenv(key, "")
			}
			for k, v := range tc.env {
				t.Setenv(k, v)
			}

			got, err := LoadJobSettings()

			if tc.wantErr != nil {
				assert.ErrorIs(t, err, tc.wantErr)
				assert.Nil(t, got)
				return
			}

			require.NoError(t, err)
			assert.Equal(t, tc.want, got)
		})
	}
}
