package middleware

import (
	"context"
	"log/slog"
	"testing"

	"github.com/stretchr/testify/assert"
)

func TestLoggerFromContext_ReturnsSlogDefaultWhenNotSet(t *testing.T) {
	ctx := context.Background()
	logger := LoggerFromContext(ctx)
	assert.Equal(t, slog.Default(), logger, "LoggerFromContext must return slog.Default() when no logger is stored in context")
}
