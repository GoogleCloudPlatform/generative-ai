package config

import (
	"fmt"
	"os"
	"strconv"

	"github.com/cloud-gtm/gemini-box-office/internal/models"
)

// JobSettings holds the Cloud Run Job execution parameters read from
// well-known environment variables injected by the Cloud Run Jobs runtime.
type JobSettings struct {
	JobType   models.WorkflowType
	DryRun    bool
	TaskIndex int
	TaskCount int
}

// LoadJobSettings reads Cloud Run Job configuration from environment variables
// and returns a validated JobSettings. It returns a sentinel-wrapped error on
// every validation failure so callers can use errors.Is.
//
//   - JOB_TYPE (required): must be "joiner" or "garbage_collection".
//   - DRY_RUN (optional, default false): parsed via strconv.ParseBool.
//   - CLOUD_RUN_TASK_INDEX (optional, default 0): non-negative integer.
//   - CLOUD_RUN_TASK_COUNT (optional, default 1): integer >= 1.
//   - TaskIndex must be < TaskCount.
func LoadJobSettings() (*JobSettings, error) {
	// JOB_TYPE — required.
	rawJobType := os.Getenv("JOB_TYPE")
	jobType := models.WorkflowType(rawJobType)
	if jobType != models.WorkflowJoiner && jobType != models.WorkflowGarbageCollection {
		return nil, fmt.Errorf("JOB_TYPE %q is not a recognised workflow type: %w", rawJobType, models.ErrConfigInvalid)
	}

	// DRY_RUN — optional, default false.
	dryRun := false
	if raw := os.Getenv("DRY_RUN"); raw != "" {
		var err error
		dryRun, err = strconv.ParseBool(raw)
		if err != nil {
			return nil, fmt.Errorf("DRY_RUN %q is not a valid boolean: %w", raw, models.ErrConfigInvalid)
		}
	}

	// CLOUD_RUN_TASK_INDEX — optional, default 0.
	taskIndex := 0
	if raw := os.Getenv("CLOUD_RUN_TASK_INDEX"); raw != "" {
		var err error
		taskIndex, err = strconv.Atoi(raw)
		if err != nil || taskIndex < 0 {
			return nil, fmt.Errorf("CLOUD_RUN_TASK_INDEX %q must be a non-negative integer: %w", raw, models.ErrConfigInvalid)
		}
	}

	// CLOUD_RUN_TASK_COUNT — optional, default 1.
	taskCount := 1
	if raw := os.Getenv("CLOUD_RUN_TASK_COUNT"); raw != "" {
		var err error
		taskCount, err = strconv.Atoi(raw)
		if err != nil || taskCount < 1 {
			return nil, fmt.Errorf("CLOUD_RUN_TASK_COUNT %q must be an integer >= 1: %w", raw, models.ErrConfigInvalid)
		}
	}

	// Cross-field: index must be a valid slot within the task pool.
	if taskIndex >= taskCount {
		return nil, fmt.Errorf("CLOUD_RUN_TASK_INDEX (%d) must be < CLOUD_RUN_TASK_COUNT (%d): %w", taskIndex, taskCount, models.ErrConfigInvalid)
	}

	return &JobSettings{
		JobType:   jobType,
		DryRun:    dryRun,
		TaskIndex: taskIndex,
		TaskCount: taskCount,
	}, nil
}
