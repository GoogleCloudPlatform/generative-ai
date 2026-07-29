# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Stage 1: Build the Go validation engine binary
FROM golang:1.21-alpine AS builder

WORKDIR /app

# Copy modules files and cache packages download
COPY go.mod ./
# Expose default config copies
RUN go mod download

COPY . .

RUN CGO_ENABLED=0 GOOS=linux go build -o compliance-server cmd/server/main.go

# Stage 2: Bundle execution package inside minimal Alpine container
FROM alpine:latest

RUN apk --no-cache add ca-certificates curl

WORKDIR /root/

COPY --from=builder /app/compliance-server .
COPY --from=builder /app/internal/policies/default_policy.json internal/policies/default_policy.json

EXPOSE 8888

CMD ["./compliance-server", "--port", "8888", "--policy", "internal/policies/default_policy.json"]
