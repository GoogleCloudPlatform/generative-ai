# gemini-agentic-video-go

An idiomatic Go reference implementation and interactive CLI demonstrating [Gemini agentic video understanding](https://docs.cloud.google.com/gemini-enterprise-agent-platform/models/capabilities/video-understanding) with the official Google Gen AI SDK (`google.golang.org/genai`). Provides reusable Go patterns, backend client factories, and production code examples (single-video, multi-video synthesis, multi-turn dialogue, token telemetry) alongside an interactive CLI tool—featuring active Think ➔ Act ➔ Observe dynamic timeline navigation, sub-second precision, and up to 96% token reduction compared to static frame ingestion.

[![Go Version](https://img.shields.io/badge/Go-1.24+-00ADD8?style=flat&logo=go)](https://golang.org)
[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](LICENSE)
[![Google Gen AI SDK](https://img.shields.io/badge/Google%20Gen%20AI%20SDK-v1.70.0-4285F4?logo=google)](https://pkg.go.dev/google.golang.org/genai)
[![User Guide](https://img.shields.io/badge/Documentation-User%20Guide-blue?logo=markdown)](docs/user-guide.md)
[![Developer Guide](https://img.shields.io/badge/Documentation-Developer%20Guide-blueviolet?logo=go)](docs/developers-guide.md)

## Table of Contents

- [Installation](#installation)
- [Usage](#usage)
  - [Common Commands](#common-commands)
  - [Programmatic Go SDK Usage](#programmatic-go-sdk-usage)
- [Development](#development)
  - [Prerequisites](#prerequisites)
  - [Setup and Running](#setup-and-running)
  - [Makefile Targets](#makefile-targets)
  - [CLI Flags](#cli-flags)
  - [Cross-Compilation](#cross-compilation)
- [Contributing](#contributing)
- [License](#license)
- [Deep Dive Documentation](#deep-dive-documentation)
- [Credits & Acknowledgements](#credits--acknowledgements)
- [Disclaimer](#disclaimer)

## Installation

Clone the repository and build from source:

```bash
git clone https://github.com/GoogleCloudPlatform/generative-ai.git
cd generative-ai/gemini/agentic-video/gemini-agentic-video-go
make build
```

The compiled binary will be placed at `./bin/gemini-agentic-video-go`.

## Usage

Run the core agentic video query on an Alphabet earnings call presentation:

```bash
./bin/gemini-agentic-video-go example 1
```

Or run via `make`:

```bash
make run
```

This analyzes a long-form YouTube video using active timeline navigation and transcript triage, extracting revenue figures and timestamps in seconds without decoding all video frames upfront.

### Common Commands

List all available tutorial scenarios:

```bash
./bin/gemini-agentic-video-go example list
```

Run a side-by-side performance benchmark comparing Agentic vs. Static (1 FPS) processing concurrently in parallel goroutines with live elapsed timers and token telemetry:

```bash
make compare
# or: ./bin/gemini-agentic-video-go compare
# sequential fallback: ./bin/gemini-agentic-video-go compare --concurrent=false

# Compare across model generations (3.6 vs 3.7 vs 3.8) in parallel goroutines:
./bin/gemini-agentic-video-go compare --models="flash"
# or: ./bin/gemini-agentic-video-go compare --models="gemini-3.6-flash,gemini-3.7-flash,gemini-3.8-flash"
```

Compare two videos in a single prompt (multi-video comparative synthesis):

```bash
make multivideo
# or: ./bin/gemini-agentic-video-go multivideo
```

Run a multi-turn conversation maintaining video context across questions:

```bash
make multiturn
# or: ./bin/gemini-agentic-video-go multiturn
```

Switch models (e.g. `gemini-3.8-flash`, `gemini-3.6-flash`, or `gemini-3.5-flash-lite`):

```bash
./bin/gemini-agentic-video-go example 1 --model=gemini-3.8-flash
```

Execute an ad-hoc query against any custom YouTube URL or Google Cloud Storage URI:

```bash
./bin/gemini-agentic-video-go run \
  --video="https://www.youtube.com/watch?v=LzExSq9DU9w" \
  --prompt="What were the key cloud milestones mentioned at 02:00?" \
  --mode=agentic \
  --thinking=high
```

### Programmatic Go SDK Usage

To enable Agentic Video in your Go services with `google.golang.org/genai`:

```go
package main

import (
	"context"
	"fmt"
	"os"

	"google.golang.org/genai"
)

func main() {
	ctx := context.Background()

	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		Backend:  genai.BackendEnterprise, // or genai.BackendVertexAI
		Project:  os.Getenv("GOOGLE_CLOUD_PROJECT"),
		Location: "global",
	})
	if err != nil {
		panic(err)
	}

	// 1. Create a video Part with Agentic media processing
	videoPart := genai.NewPartFromURI("https://www.youtube.com/watch?v=LzExSq9DU9w", "video/mp4")
	videoPart.MediaProcessing = genai.MediaProcessingAgentic // Options: MediaProcessingAgentic, MediaProcessingStatic

	// 2. Text prompt placed after video in content parts
	contents := []*genai.Content{
		genai.NewContentFromParts([]*genai.Part{
			videoPart,
			genai.NewPartFromText("What are the key revenue figures and timestamps?"),
		}, genai.RoleUser),
	}

	// 3. Configure reasoning thinking level (LOW, MEDIUM, HIGH)
	config := &genai.GenerateContentConfig{
		ThinkingConfig: &genai.ThinkingConfig{
			ThinkingLevel: genai.ThinkingLevelMedium,
		},
	}

	resp, err := client.Models.GenerateContent(ctx, "gemini-3.7-flash", contents, config)
	if err != nil {
		panic(err)
	}

	fmt.Println(resp.Text())
	fmt.Printf("Total Tokens: %d\n", resp.UsageMetadata.TotalTokenCount)
}
```

## Development

### Prerequisites

- [Go 1.24+](https://golang.org/dl/)
- A Google Cloud Project with the Agent Platform / Vertex AI / Gemini API enabled
- Authenticated credentials via Application Default Credentials (`gcloud auth application-default login`)

### Setup and Running

```bash
cd gemini/agentic-video/gemini-agentic-video-go
go mod download
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="global"
make build
make run
```

### Makefile Targets

| Target | Description |
| :--- | :--- |
| `make build` | Compiles binary to `./bin/gemini-agentic-video-go` |
| `make run` | Runs Example 1 (use `ARGS="..."` for custom flags) |
| `make list` | Lists all tutorial scenarios in the catalog |
| `make compare` | Runs the Agentic vs. Static performance benchmark |
| `make multivideo` | Runs multi-video comparative synthesis |
| `make multiturn` | Runs multi-turn video conversation demonstration |
| `make test` | Runs unit test suite (`go test -v ./...`) |
| `make fmt` | Formats Go source code (`go fmt ./...`) |
| `make vet` | Runs `go vet ./...` static analyzer |
| `make license` | Applies Apache 2.0 license headers using `addlicense` |
| `make license-check` | Verifies presence of license headers |
| `make clean` | Removes `./bin` directory and build artifacts |
| `make help` | Displays list of available make targets |

### CLI Flags

| Flag | Default | Description |
| :--- | :--- | :--- |
| `-m, --model` | `gemini-3.7-flash` | Gemini model ID (`gemini-3.8-flash`, `gemini-3.7-flash`, `gemini-3.6-flash`, `gemini-3.5-flash-lite`) |
| `-p, --project` | `""` | Google Cloud Project ID (falls back to `GOOGLE_CLOUD_PROJECT` or `gcloud config`) |
| `-l, --location` | `"global"` | Google Cloud Location / Region (defaults to `GOOGLE_CLOUD_LOCATION` or `"global"`) |
| `-b, --backend` | `"enterprise"` | Client backend: `enterprise`, `vertex`, or `gemini` (API key) |

### Cross-Compilation

To cross-compile binaries for other platforms:

```bash
# Linux AMD64
GOOS=linux GOARCH=amd64 go build -o bin/gemini-agentic-video-go-linux-amd64 .

# macOS Apple Silicon
GOOS=darwin GOARCH=arm64 go build -o bin/gemini-agentic-video-go-darwin-arm64 .

# Windows AMD64
GOOS=windows GOARCH=amd64 go build -o bin/gemini-agentic-video-go-windows-amd64.exe .
```

## Contributing

Pull requests are welcome! For major architectural changes or new feature proposals, please open an issue first to discuss what you would like to change.

Please make sure all Go code is properly formatted (`make fmt`), passes tests (`make test`), and has license headers verified (`make license-check`) before submitting a pull request.

## License

Code in this repository is licensed under the [Apache 2.0 License](LICENSE).

---

## Deep Dive Documentation

- **[`docs/developers-guide.md`](docs/developers-guide.md)**: **Go API Reference & Engineering Guide**
  - Production Go patterns for `google.golang.org/genai`.
  - Single-video ingestion, Content part ordering, and Thinking configuration.
  - Multi-video comparative synthesis and multi-turn stateful dialogues.
  - Real-time streaming (`GenerateContentStream`) and context timeout enforcement.
  - Token telemetry accounting and headless microservice integration.

- **[`docs/user-guide.md`](docs/user-guide.md)**: **Architectural Overview & Concepts**
  - **[Under the Hood: The `load_video` Tool](docs/user-guide.md#2-under-the-hood-the-load_video-tool)**: Parameters and tool calling mechanisms.
  - **[Four Core Execution Patterns](docs/user-guide.md#3-four-core-execution-patterns)**: Transcript triage, coarse-to-fine search, adaptive high-FPS replay, and tool chaining.
  - **[Empirical Benchmarks](docs/user-guide.md#4-empirical-benchmarks--token-spend-reduction)**: Accuracy deltas and up to 95.7% token spend reduction on long-form benchmarks.
  - **[Token Accounting & Telemetry](docs/user-guide.md#5-critical-developer-pitfall-token-accounting--telemetry)**: Why dynamic video tokens reside in `thoughtsTokenCount` rather than `promptTokenCount`.
  - **[Multi-Video Synthesis & Multi-Turn State](docs/user-guide.md#8-multi-video-comparative-synthesis)**: Technical patterns for multi-video prompts and stateful conversations.

## Credits & Acknowledgements

- Based on the [Google Cloud Generative AI Agentic Video Tutorial](https://github.com/GoogleCloudPlatform/generative-ai/blob/main/gemini/agentic-video/intro_agentic_video.ipynb) by [Eric Dong](https://github.com/gericdong) and [Holt Skinner](https://github.com/holtskinner).

## Disclaimer

> [!CAUTION]
> This is **not** an officially supported Google product.
> This project is not eligible for the [Google Open Source Software Vulnerability Rewards Program](https://bughunters.google.com/open-source-security).
