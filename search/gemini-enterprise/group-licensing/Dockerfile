# ---- Builder ----
FROM golang:1.25-alpine AS builder

WORKDIR /app

COPY go.mod go.sum ./
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build \
    -trimpath \
    -ldflags="-s -w" \
    -o /job \
    ./cmd/job

# ---- Runtime ----
# distroless/static includes CA certificates and timezone data but no shell,
# package manager, or other tooling. The :nonroot variant runs as UID 65532.
FROM gcr.io/distroless/static-debian12:nonroot

COPY --from=builder /job /job

ENTRYPOINT ["/job"]
