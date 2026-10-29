# Gemini Agentic Video Understanding: Developer Guide & Architecture

This comprehensive guide details the architecture, technical mechanisms, execution patterns, and operational considerations for building with **Agentic Video Understanding** in Go using the official Google Gen AI SDK (`google.golang.org/genai`) and Gemini 4 Argon / 3.8 / 3.7 / 3.6 / 3.5 models.

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
> **Do not monitor `promptTokenCount` or `thoughtsTokenCount` alone for Agentic Video billing!**
> In `UsageMetadata`, the exact identity is:
> `TotalTokenCount = PromptTokenCount + ToolUsePromptTokenCount + ThoughtsTokenCount + CandidatesTokenCount`

### Static Mode
- All video frames are pre-decoded upfront when the prompt is sent.
- `promptTokenCount` includes 100% of the video input tokens (e.g. `VIDEO: 5,236, TEXT: 21` in `PromptTokensDetails`).
- `toolUsePromptTokenCount` is `0`.
- `candidatesTokenCount` includes only the generated answer text.

### Agentic Mode
- The initial request payload only contains text and URI metadata. `promptTokenCount` contains **0 video frame tokens** (~70–95 tokens).
- Video frames and audio transcripts are dynamically retrieved during the model's iterative Think ➔ Act (`load_video`) loop and billed in **`toolUsePromptTokenCount`** (with per-modality `VIDEO` vs. `TEXT` breakdowns in **`toolUsePromptTokensDetails`**).
- When the model executes multiple sequential `load_video` hops (e.g., `gemini-4-argon` verifying transcript findings against visual slides), reused context from earlier hops is reported in **`cachedContentTokenCount`** (`cacheTokensDetails`).
- **`thoughtsTokenCount`** measures internal Think ➔ Act reasoning and planning tokens.

| Token Metric | Static Mode (`STATIC`) | Agentic Mode (`AGENTIC`) |
| :--- | :--- | :--- |
| **Prompt Tokens (`promptTokenCount`)** | High (100% video frames + text) | Minimal (text + URI metadata only; 0 video frames) |
| **Tool-Use Tokens (`toolUsePromptTokenCount`)** | `0` | **Dynamic video frames (`VIDEO`) & audio captions (`TEXT`) fetched via `load_video`** |
| **Cached Tokens (`cachedContentTokenCount`)** | `0` (unless explicit cache used) | Implicitly cached context across multi-hop `load_video` turns |
| **Thinking Tokens (`thoughtsTokenCount`)** | Standard reasoning | Think ➔ Act timeline planning & synthesis |
| **Candidates Tokens (`candidatesTokenCount`)** | Answer text only | Final synthesized answer text |
| **Total Tokens (`totalTokenCount`)** | High (full video context) | **70%–95% lower on long footage** |

---

## 6. Supported Models & Processing Modes

### Model Support Matrix

| Model ID | Agentic Video Support | Default Mode | Recommended Scenarios |
| :--- | :---: | :---: | :--- |
| `gemini-4-argon` | ✅ Supported | Static (1 FPS) | **Frontier multimodal & multi-hop precision**: 2.06x faster and 77% fewer tokens on pure-visual GCS footage; multi-hop visual + transcript cross-verification |
| `gemini-3.8-flash` | ✅ Supported | Static (1 FPS) | Ultra-fast timeline navigation, fast single-hop transcript triage, interactive video Q&A |
| `gemini-3.7-flash` | ✅ Supported | Static (1 FPS) | Dense visual QA, split-second action analysis, complex multi-step reasoning across 60+ min videos *(Default)* |
| `gemini-3.6-flash` | ✅ Supported | Static (1 FPS) | General video Q&A, lecture summarization, timestamp indexing |
| `gemini-3.5-flash-lite` | ✅ Supported | Static (1 FPS) | High-throughput, cost-sensitive transcript triage & metadata extraction |

### Empirical Multi-Model Shootout (`3.7-flash` vs `3.8-flash` vs `4-argon`)

| Scenario | Model | Mode | Wall-Clock | Total Tokens | Prompt | Tool-Use (`load_video`) | Thoughts | Output |
| :--- | :--- | :--- | ---: | ---: | ---: | ---: | ---: | ---: |
| **Scenario 4: YouTube Short** (`y-mrGw1wW8E`) | `gemini-3.7-flash` | Agentic (`HIGH`) | `19.4s` | `9,348` | `83` | `7,999` (`VIDEO: 6.8K, TEXT: 1.2K`) | `539` | `727` |
| **Scenario 4: YouTube Short** (`y-mrGw1wW8E`) | `gemini-3.8-flash` | Agentic (`MEDIUM`) | `18.7s` | `9,376` | `83` | `7,999` (`VIDEO: 6.8K, TEXT: 1.2K`) | `484` | `810` |
| **Scenario 4: YouTube Short** (`y-mrGw1wW8E`) | **`gemini-4-argon`** | **Agentic (`MEDIUM`)** | **`22.9s`** | **`6,822`** | `83` | **`5,384` (`VIDEO: 4.2K, TEXT: 1.2K`)** | **`456`** | `899` |
| **Scenario 3: GCS Trailcam** (`gs://...`) | `gemini-3.8-flash` | Agentic (`HIGH`) | `4m 32.6s` | `211,965` | `92` | `203,131` (`VIDEO: 194.5K, TEXT: 8.6K`) | `6,881` | `1,861` |
| **Scenario 3: GCS Trailcam** (`gs://...`) | **`gemini-4-argon`** | **Agentic (`HIGH`)** | **`2m 12.0s`** | **`48,825`** | `92` | **`42,110` (`VIDEO: 37.2K, TEXT: 4.9K`)** | **`3,980`** | `2,318` |
| **Scenario 1: 54m Earnings Call** | `gemini-3.8-flash` | Agentic (`MEDIUM`) | `26.2s` | `34,413` | `95` | `13,907` (`TEXT: 13.9K`, 1 hop) | `19,930` | `481` |
| **Scenario 1: 54m Earnings Call** | **`gemini-4-argon`** | **Agentic (`MEDIUM`)** | `4m 20.3s` | `69,138` | `95` | `49,311` (`VIDEO: 47.0K, TEXT: 2.3K`, 3 hops, `29.4K` cached) | `19,179` | `553` |

### Processing Modes Comparison

| Mode | Description | Supported Models | Token Efficiency | When to Use |
| :--- | :--- | :--- | :--- | :--- |
| **Static**<br>*(default)* | Single-pass ingestion at fixed **1 FPS** and **1 Kbps audio** with 1s timestamps. | All Gemini models | Baseline (~300 tokens/sec). Full ingestion required upfront. | • Clips < 2 min<br>• Requires simultaneous full audio & video<br>• Deterministic sampling<br>• Custom clipping (`start_offset`, `end_offset`) |
| **Agentic** | Iterative timeline navigation; dynamically loads frames and audio on-demand. | `gemini-4-argon`<br>`gemini-3.8-flash`<br>`gemini-3.7-flash`<br>`gemini-3.6-flash`<br>`gemini-3.5-flash-lite` | **70%–95% reduction** on long footage; seconds TTFB for transcript queries. | • Videos > 2 min (lectures, meetings, calls)<br>• Verbal / audio-first queries<br>• Localized visual search<br>• Fast-action clips needing high FPS<br>• Cross-video comparisons |

### Multi-Model Shootout (`compare --models`)
Compare cross-generation performance (3.6 vs 3.7 vs 3.8 vs 4-argon) concurrently on the same video:

```bash
# Benchmark all supported generations (3.6, 3.7, 3.8, 4-argon) in parallel goroutines:
./bin/gemini-agentic-video-go compare --models="all"

# Or compare only Flash generations (3.6, 3.7, 3.8):
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
  --video2="gs://generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4" \
  --mode2=agentic \
  --prompt="Compare the setting, visual tone, and pacing of both clips."
```

> [!TIP]
> **Always prefer `gs://` URIs over `https://storage.googleapis.com/` URLs for Google Cloud Storage videos.**
> Passing an HTTPS GCS URL triggers external web-fetch size limits on large videos, whereas `gs://` gives the server-side `load_video` tool direct native bucket access. The runner automatically normalizes `https://storage.googleapis.com/...` URLs to `gs://...` via `runner.NormalizeVideoURI`.

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

### Preserving `ThoughtSignature` Across Multi-Turn History
- When echoing model responses back into `history` for subsequent turns, **preserve the non-thought text `Part`s (including their `ThoughtSignature`)** using `runner.ExtractModelTurnContent(resp)` rather than reconstructing a plain text part (`genai.NewContentFromText(resp.Text(), genai.RoleModel)`).
- Preserving the final `ThoughtSignature` allows the server to reuse navigated video context from Turn 1, dropping Turn 2+ `toolUsePromptTokenCount` to `0` and reducing follow-up turn tokens by ~69%.
- Note: Do not echo empty-text intermediate `processing_call` / `processing_result` signature parts back in `GenerateContent` history, as the API validates that echoed signatures are attached to synthesized text parts.

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
   - *Note: `thinking_level="minimal"` is not supported on `gemini-4-argon`, `gemini-3.8-flash`, or `gemini-3.7-flash` and is rejected upfront with an actionable hint.*

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
- `-m, --model string`: Model ID (default `"gemini-3.7-flash"`; supports `"gemini-4-argon"`, `"gemini-3.8-flash"`, `"gemini-3.7-flash"`, `"gemini-3.6-flash"`, `"gemini-3.5-flash-lite"`).
- `-p, --project string`: Google Cloud project ID (defaults to `GOOGLE_CLOUD_PROJECT` or active `gcloud` config).
- `-l, --location string`: Location / region (defaults to `GOOGLE_CLOUD_LOCATION` or `"global"`).
- `-b, --backend string`: Backend: `"enterprise"` (default), `"vertex"`, or `"gemini"` (API key).
- `--json`: Emit structured JSON output for Agent-to-Agent (A2A) and programmatic consumption.
- `--timeout duration`: Maximum execution timeout per command (default `10m`).

### Commands

#### 1. `example [id|all|list]`
Runs or lists the built-in catalog scenarios:
```bash
gemini-agentic-video-go example list
gemini-agentic-video-go example 1
gemini-agentic-video-go example 3 --model=gemini-4-argon --show-thoughts
```

#### 2. `run [flags]`
Executes an ad-hoc query against any video (supports `--show-thoughts` and `--stream`):
```bash
gemini-agentic-video-go run \
  --model=gemini-4-argon \
  --video="https://www.youtube.com/watch?v=LzExSq9DU9w" \
  --prompt="Summarize the main announcements" \
  --mode=agentic \
  --thinking=high \
  --show-thoughts \
  --stream
```

#### 3. `compare [flags]`
Runs an automated side-by-side benchmark comparing Agentic vs. Static processing or multiple model generations (`--models=all`, `--models=flash`, or `--models=3.8,argon`):
```bash
gemini-agentic-video-go compare \
  --video="https://www.youtube.com/watch?v=LzExSq9DU9w" \
  --prompt="What were the key revenue figures?"

gemini-agentic-video-go compare --models=all \
  --video="https://www.youtube.com/shorts/y-mrGw1wW8E"
```

#### 4. `multivideo [flags]`
Performs comparative synthesis across two videos in a single prompt:
```bash
gemini-agentic-video-go multivideo \
  --video1="https://www.youtube.com/shorts/y-mrGw1wW8E" \
  --video2="gs://generativeai-downloads/videos/Jukin_Trailcam_Videounderstanding.mp4" \
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
