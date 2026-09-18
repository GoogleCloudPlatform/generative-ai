# Gemini Agentic Video Understanding: Developer Guide & Architecture

This comprehensive guide details the architecture, technical mechanisms, execution patterns, and operational considerations for building with **Agentic Video Understanding** in Go using the official Google Gen AI SDK (`google.golang.org/genai`) and Gemini 3.8 / 3.7 / 3.6 / 3.5 models.

> [!TIP]
> Looking for copy-pasteable Go code examples, backend client factories, streaming patterns, and headless microservice architectures? See the companion **[`docs/developers-guide.md`](developers-guide.md)**.

---

## Table of Contents

1. [What is Agentic Video?](#1-what-is-agentic-video)
2. [Under the Hood: The `load_video` Tool](#2-under-the-hood-the-load_video-tool)
3. [Four Core Execution Patterns](#3-four-core-execution-patterns)
4. [Empirical Benchmarks & Token Spend Reduction](#4-empirical-benchmarks--token-spend-reduction)
5. [Critical Developer Pitfall: Token Accounting & Telemetry](#5-critical-developer-pitfall-token-accounting--telemetry)
6. [Supported Models & Processing Modes](#6-supported-models--processing-modes)
7. [Key Use Cases](#7-key-use-cases)
8. [Multi-Video Comparative Synthesis](#8-multi-video-comparative-synthesis)
9. [Multi-Turn Conversations & Context Preservation](#9-multi-turn-conversations--context-preservation)
10. [Prompting & Steering Best Practices](#10-prompting--steering-best-practices)
11. [Supported Video Formats & MIME Types](#11-supported-video-formats--mime-types)
12. [CLI Command Reference](#12-cli-command-reference)
13. [Programmatic Go SDK Reference](#13-programmatic-go-sdk-reference)

---

## 1. What is Agentic Video?

Traditional multimodal LLMs ingest video passively by extracting static frames at a fixed sampling rate (1 frame per second) alongside audio. For a 60-minute video, 1-FPS static ingestion consumes over 400,000 input tokens, resulting in multi-minute response latencies and high inference costs—even if the user only asked a straightforward verbal question or inquired about a 5-second scene at the end of the footage.

**Agentic Video** transforms video processing from passive frame extraction into an active, iterative **Think ➔ Act ➔ Observe** loop. Equipped with a native timeline exploration tool (`load_video`), the model selectively inspects only the required video streams (captions/ASR, audio waveforms, or visual frames), temporal windows (`start_time`, `end_time`), and sampling resolutions (`fps`).

```
                    ┌────────────────────────┐
                    │      User Prompt       │
                    └───────────┬────────────┘
                                │
                                ▼
                    ┌────────────────────────┐
              ┌────►│  Think: Evaluate need  │
              │     └───────────┬────────────┘
              │                 │
              │                 ▼
              │     ┌────────────────────────┐
              │     │ Act: Call load_video   │
              │     │ (captions, window, fps)│
              │     └───────────┬────────────┘
              │                 │
              │                 ▼
              │     ┌────────────────────────┐
              │     │ Observe: Ingest stream │
              │     │ (only requested frames)│
              │     └───────────┬────────────┘
              │                 │
              └─────────────────┴────────────┐ (Repeat as needed)
                                             │
                                             ▼
                                ┌────────────────────────┐
                                │ Final Synthesized Ans  │
                                └────────────────────────┘
```

---

## 2. Under the Hood: The `load_video` Tool

When `MediaProcessing: genai.MediaProcessingAgentic` is enabled, the model is equipped with a first-party native tool called `load_video`. The backend handles tool invocation and segment delivery automatically.

### Tool Schema

```json
{
  "name": "load_video",
  "description": "Selectively load captions, audio, or visual frames from a video part.",
  "parameters": {
    "type": "OBJECT",
    "properties": {
      "filename": { "type": "STRING", "description": "Internal identifier of the uploaded video" },
      "include_frames": { "type": "BOOLEAN", "description": "Whether to decode visual pixel frames" },
      "include_audio": { "type": "BOOLEAN", "description": "Whether to fetch the audio waveform track" },
      "include_captions": { "type": "BOOLEAN", "description": "Whether to retrieve the transcript / ASR track" },
      "start_time": { "type": "NUMBER", "description": "Start timestamp offset in milliseconds" },
      "end_time": { "type": "NUMBER", "description": "End timestamp offset in milliseconds" },
      "fps": { "type": "NUMBER", "description": "Frame sampling rate per second (e.g., 1, 4, 10)" }
    },
    "required": ["filename"]
  }
}
```

---

## 3. Four Core Execution Patterns

The model dynamically selects among four primary timeline exploration strategies depending on the prompt and query complexity:

1. **Transcript Triage (`include_captions=True`, `include_frames=False`)**:
   For verbal, dialogue-heavy, or documentary Q&A (*"What three action items did the CEO assign during the meeting?"*), the model bypasses visual pixel decoding entirely. It searches the audio transcript and delivers answers in seconds.
2. **Coarse-to-Fine Search**:
   For localized visual events (*"When does the delivery driver place the package on the porch?"*), the model probes broadly at `fps=0.5` across candidate windows, identifies candidate timestamps, and then zooms in with a targeted high-resolution call at `fps=8` or `10` over a tight 5-second interval.
3. **Adaptive High-FPS Replay**:
   For rapid physical motion, sports highlights, industrial QA, or UI glitch analysis, 1-FPS static sampling fails because actions occur in under 1,000 milliseconds. The model dynamically requests `fps=10+` solely across the critical 3–10s event window (+17% accuracy boost).
4. **Multimodal Tool Chaining**:
   The model integrates video timeline inspection with code execution to compute geometric coordinates, track bounding boxes, or plot events over time.

---

## 4. Empirical Benchmarks & Token Spend Reduction

Standard long-video benchmark evaluations comparing Gemini 3.7 Flash Agentic Video against 1-FPS static baseline ingestion show massive token reductions and superior accuracy:

| Benchmark | Clip Duration | Static (1 FPS) Acc / Tokens | Agentic Acc / Tokens | Accuracy Delta | Net Token Spend Reduction |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **1H-VideoQA** | 40–90 min (~1 hr) | 0.87 / 407.0K | 0.91 / 23.4K | **+4.6%** | **−95.1%** |
| **LVBench** | 30–100 min | 0.85 / 317.0K | 0.88 / 19.8K | **+3.5%** | **−95.7%** |
| **Minerva** | ~4.2 min | 0.72 / 83.7K | 0.80 / 18.3K | **+1.1%** | **−78.1%** |
| **Human Evals** | 0–100 min | 0.81 / 102.4K | 0.84 / 12.1K | **+3.7%** | **−88.2%** |
| **Action Atlas** | 0–30 sec (High FPS) | 0.53 / 5.4K | 0.62 / 3.8K | **+17.0%** | **−30.0%** |

---

## 5. Critical Developer Pitfall: Token Accounting & Telemetry

When enabling Agentic Video (`media_processing="agentic"`), token reporting shifts structurally in the API usage metadata:

> [!WARNING]
> **Do not monitor `promptTokenCount` alone for Agentic Video billing!**

### Static Mode
- All video frames are pre-decoded upfront when the prompt is sent.
- `promptTokenCount` includes 100% of the video input tokens (e.g. 7,656 tokens for a 2-minute clip).
- `candidatesTokenCount` includes only the generated answer text.

### Agentic Mode
- The initial request payload only contains text metadata. `promptTokenCount` contains **0 video tokens**.
- Video streams and visual frames are dynamically retrieved during the model's iterative Think ➔ Act (`load_video`) loop.
- Dynamically retrieved frames and audio are accounted for under **`candidatesTokenCount` / `thoughtsTokenCount`**.

| Token Metric | Static Mode (`STATIC`) | Agentic Mode (`AGENTIC`) |
| :--- | :--- | :--- |
| **Prompt Tokens (`promptTokenCount`)** | High (100% video frames + text) | Minimal (text only; 0 video frames) |
| **Thinking Tokens (`thoughtsTokenCount`)** | Standard reasoning | Includes dynamic video frames & inspection |
| **Candidates Tokens (`candidatesTokenCount`)** | Answer text only | Answer text + reasoning tokens |
| **Total Tokens (`totalTokenCount`)** | High (full video context) | **70%–95% lower on long footage** |

---

## 6. Supported Models & Processing Modes

### Model Support Matrix

| Model ID | Agentic Video Support | Default Mode | Recommended Scenarios |
| :--- | :---: | :---: | :--- |
| `gemini-3.8-flash` | ✅ Supported | Static (1 FPS) | Ultra-fast timeline navigation (up to 2.1x faster), speculative frame exploration, interactive video triage |
| `gemini-3.7-flash` | ✅ Supported | Static (1 FPS) | Dense visual QA, split-second action analysis, complex multi-step reasoning across 60+ min videos *(Default)* |
| `gemini-3.6-flash` | ✅ Supported | Static (1 FPS) | General video Q&A, lecture summarization, timestamp indexing |
| `gemini-3.5-flash-lite` | ✅ Supported | Static (1 FPS) | High-throughput, cost-sensitive transcript triage & metadata extraction |

### Processing Modes Comparison

| Mode | Description | Supported Models | Token Efficiency | When to Use |
| :--- | :--- | :--- | :--- | :--- |
| **Static**<br>*(default)* | Single-pass ingestion at fixed **1 FPS** and **1 Kbps audio** with 1s timestamps. | All Gemini models | Baseline (~300 tokens/sec). Full ingestion required upfront. | • Clips < 2 min<br>• Requires simultaneous full audio & video<br>• Deterministic sampling<br>• Custom clipping (`start_offset`, `end_offset`) |
| **Agentic** | Iterative timeline navigation; dynamically loads frames and audio on-demand. | `gemini-3.8-flash`<br>`gemini-3.7-flash`<br>`gemini-3.6-flash`<br>`gemini-3.5-flash-lite` | **70%–95% reduction** on long footage; seconds TTFB for transcript queries. | • Videos > 2 min (lectures, meetings, calls)<br>• Verbal / audio-first queries<br>• Localized visual search<br>• Fast-action clips needing high FPS<br>• Cross-video comparisons |

### Multi-Model Shootout (`compare --models`)
Compare cross-generation performance (3.6 vs 3.7 vs 3.8) concurrently on the same video:

```bash
# Benchmark all Flash generations in parallel goroutines:
./bin/gemini-agentic-video-go compare --models="flash"
```

---

## 7. Key Use Cases

| Use Case | Target Workloads | Why Static Ingestion Fails | The Agentic Advantage |
| :--- | :--- | :--- | :--- |
| **Long-Form Meetings & Earnings Calls** | 30–90+ min meetings, webinars, earnings calls | Decodes all 3,600+ frames statically (400k+ tokens) even for audio-only questions. | **78%–96% token reduction & seconds TTFB**: Performs transcript triage (`include_captions=True`), bypassing visual decoding. |
| **Visual "Needle-in-a-Haystack"** | Slide transitions, diagram edits, specific physical events in hours of footage | 1 FPS dilutes attention across thousands of unneeded frames, requiring external vector databases. | **Coarse-to-fine zoom**: Probes at 0.5 FPS, then zooms into target 5s windows at 8–10 FPS (+3.5% to +4.6% accuracy). |
| **Fast-Action & Anomalies** | Sports highlights, industrial QA, equipment vibrations, UI glitches | 1 FPS misses sub-second actions (<1s). Decoding full clips at 10+ FPS blows token limits. | **Adaptive High-FPS Replay**: Dynamically samples `fps=10+` only on critical 3–10s intervals (+17% accuracy). |
| **Cross-Video Synthesis** | Comparing multiple recordings (product reviews, lecture vs. lab) | Ingesting multiple 30+ min videos statically blows past the 1M token context limit. | **Multi-video feasibility**: Dynamically retrieves only relevant segments across files in a single prompt. |

---

## 8. Multi-Video Comparative Synthesis

Agentic video allows you to include multiple long-form videos in a single prompt without blowing past context limits. Furthermore, you can mix processing modes across videos:

```bash
./bin/gemini-agentic-video-go multivideo \
  --video1="https://www.youtube.com/shorts/y-mrGw1wW8E" \
  --mode1=agentic \
  --video2="https://storage.googleapis.com/generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4" \
  --mode2=agentic \
  --prompt="Compare the setting, visual tone, and pacing of both clips."
```

In the Go SDK, you construct multiple `*genai.Part` objects and append the user prompt afterwards:

```go
video1 := genai.NewPartFromURI("gs://my-bucket/game1.mp4", "video/mp4")
video1.MediaProcessing = genai.MediaProcessingAgentic

video2 := genai.NewPartFromURI("gs://my-bucket/game2.mp4", "video/mp4")
video2.MediaProcessing = genai.MediaProcessingStatic // Mixed mode supported!

contents := []*genai.Content{
    genai.NewContentFromParts([]*genai.Part{
        video1,
        video2,
        genai.NewPartFromText("Compare the offensive strategies between game 1 and game 2."),
    }, genai.RoleUser),
}
```

---

## 9. Multi-Turn Conversations & Context Preservation

Video context is preserved across multiple conversational turns. The model retains navigated timeline state so subsequent questions do not require re-exploring or re-ingesting the video.

### Stateful vs. Stateless Interaction
- **Stateful Mode (Recommended)**: Pass `previous_interaction_id` in subsequent requests. The server retains the navigated timeline state automatically.
- **Stateless Mode**: When echoing conversation history back to the model, responses contain opaque steps encoding video navigation state. You **must echo all steps** back in subsequent requests.

Try the built-in multi-turn demonstration:

```bash
./bin/gemini-agentic-video-go multiturn
```

---

## 10. Prompting & Steering Best Practices

1. **Timestamp References**:
   Always format timestamps as `MM:SS` (e.g. `01:35`, `04:15`, or `12:45`):
   ```
   "What were the key revenue figures mentioned at 01:35 and 21:18?"
   ```
2. **Prompt Ordering**:
   When combining video and text in content parts, always place the text prompt **after** the video part:
   ```go
   // Recommended ordering:
   parts := []*genai.Part{videoPart, genai.NewPartFromText(prompt)}
   ```
3. **Tuning `thinking_level`**:
   - `HIGH`: Dense visual QA, split-second action/sports analysis, or complex multi-step reasoning across 60+ min videos.
   - `MEDIUM` (Default): Optimal balance of latency, cost, and retrieval quality for general video Q&A, meeting summaries, and timestamp indexing.
   - `LOW`: Fast transcript/caption searches and metadata extraction.
   - *Note: `thinking_level="minimal"` is not supported on `gemini-3.7-flash` and returns an API validation error.*

---

## 11. Supported Video Formats & MIME Types

Gemini models support the following 9 video formats via Google Cloud Storage URIs (`gs://`), web URLs (`https://`), and the Files API:

| MIME Type | Container Extension |
| :--- | :--- |
| `video/mp4` | `.mp4` |
| `video/mpeg` | `.mpeg`, `.mpg` |
| `video/mov` | `.mov` |
| `video/avi` | `.avi` |
| `video/x-flv` | `.flv` |
| `video/webm` | `.webm` |
| `video/wmv` | `.wmv` |
| `video/3gpp` | `.3gp` |

---

## 12. CLI Command Reference

```bash
gemini-agentic-video-go [command] [flags]
```

### Global Flags
- `-m, --model string`: Model ID (default `"gemini-3.7-flash"`; supports `"gemini-3.8-flash"`, `"gemini-3.7-flash"`, `"gemini-3.6-flash"`, `"gemini-3.5-flash-lite"`).
- `-p, --project string`: Google Cloud project ID (defaults to `GOOGLE_CLOUD_PROJECT` or active `gcloud` config).
- `-l, --location string`: Location / region (defaults to `GOOGLE_CLOUD_LOCATION` or `"global"`).
- `-b, --backend string`: Backend: `"enterprise"` (default), `"vertex"`, or `"gemini"` (API key).

### Commands

#### 1. `example [id|all|list]`
Runs or lists the built-in catalog scenarios:
```bash
gemini-agentic-video-go example list
gemini-agentic-video-go example 1
gemini-agentic-video-go example 4 --model=gemini-3.6-flash
```

#### 2. `run [flags]`
Executes an ad-hoc query against any video:
```bash
gemini-agentic-video-go run \
  --video="https://www.youtube.com/watch?v=LzExSq9DU9w" \
  --prompt="Summarize the main announcements" \
  --mode=agentic \
  --thinking=high
```

#### 3. `compare [flags]`
Runs an automated side-by-side benchmark comparing Agentic vs. Static processing:
```bash
gemini-agentic-video-go compare \
  --video="https://www.youtube.com/watch?v=LzExSq9DU9w" \
  --prompt="What were the key revenue figures?"
```

#### 4. `multivideo [flags]`
Performs comparative synthesis across two videos in a single prompt:
```bash
gemini-agentic-video-go multivideo \
  --video1="https://www.youtube.com/shorts/y-mrGw1wW8E" \
  --video2="https://storage.googleapis.com/generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4" \
  --prompt="Compare visual pacing and settings."
```

#### 5. `multiturn [flags]`
Demonstrates multi-turn conversation with video context preservation across turns:
```bash
gemini-agentic-video-go multiturn \
  --video="https://www.youtube.com/watch?v=LzExSq9DU9w"
```

---

## 13. Programmatic Go SDK Reference

To implement Agentic Video understanding directly in your own Go services:

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

	// 1. Initialize client with Enterprise Agent Platform or Vertex AI backend
	client, err := genai.NewClient(ctx, &genai.ClientConfig{
		Backend:  genai.BackendEnterprise,
		Project:  os.Getenv("GOOGLE_CLOUD_PROJECT"),
		Location: "global",
	})
	if err != nil {
		panic(err)
	}

	// 2. Configure video part with Agentic media processing
	videoPart := genai.NewPartFromURI("https://www.youtube.com/watch?v=LzExSq9DU9w", "video/mp4")
	videoPart.MediaProcessing = genai.MediaProcessingAgentic

	// 3. Assemble content parts (prompt placed after video)
	contents := []*genai.Content{
		genai.NewContentFromParts([]*genai.Part{
			videoPart,
			genai.NewPartFromText("What are the key revenue figures and timestamps?"),
		}, genai.RoleUser),
	}

	// 4. Configure thinking level
	genConfig := &genai.GenerateContentConfig{
		ThinkingConfig: &genai.ThinkingConfig{
			ThinkingLevel: genai.ThinkingLevelMedium,
		},
	}

	// 5. Generate content
	resp, err := client.Models.GenerateContent(ctx, "gemini-3.7-flash", contents, genConfig)
	if err != nil {
		panic(err)
	}

	fmt.Println(resp.Text())
	fmt.Printf("Total Tokens: %d\n", resp.UsageMetadata.TotalTokenCount)
}
```
