package middleware

import (
	"context"
	"log/slog"
)

// loggerKey is the unexported context key used to store the request-scoped logger.
type loggerKey struct{}

// LoggerFromContext retrieves the request-scoped logger stored in ctx.
// When no logger is present (e.g. in unit tests) it returns slog.Default()
// as a safe fallback so callers never need to guard against a nil logger.
func LoggerFromContext(ctx context.Context) *slog.Logger {
	if logger, ok := ctx.Value(loggerKey{}).(*slog.Logger); ok && logger != nil {
		return logger
	}
	return slog.Default()
}
