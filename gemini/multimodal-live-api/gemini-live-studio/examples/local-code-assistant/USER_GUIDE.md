# Local Code Assistant — User Guide

Welcome to the comprehensive user guide for the **Local Code Assistant**, an interactive agentic application built with the **Gemini Live Bidi API** in Go and modern web standards.

This guide provides in-depth instructions for customizing the assistant's behavior, engineering custom personas, generating technical architecture diagrams, configuring avatar video/audio playback, and navigating local codebases.

---

## Table of Contents

1. [Architecture & Flow](#1-architecture--flow)
2. [Customizing Persona & Instructions](#2-customizing-persona--instructions)
   - [Augmenting Context (`AVATAR_EXTRA_CONTEXT`)](#augmenting-context-avatar_extra_context)
   - [Complete Persona Override (`SYSTEM_INSTRUCTION_FILE`)](#complete-persona-override-system_instruction_file)
   - [Combining Override with Runtime Context](#combining-override-with-runtime-context)
3. [Technical Diagramming with Graphviz](#3-technical-diagramming-with-graphviz)
   - [How Diagramming Works](#how-diagramming-works)
   - [Sample Diagram Prompts](#sample-diagram-prompts)
   - [Interactive Diagram Controls](#interactive-diagram-controls)
4. [Avatar Viewport & Audio Playback](#4-avatar-viewport--audio-playback)
   - [Operational Modes (Reactive Orb vs Video)](#operational-modes)
   - [Playback Mute Controls](#playback-mute-controls)
   - [Dynamic Resizing & S/M/L Presets](#dynamic-resizing--sml-presets)
   - [Aspect Ratio Framing (Fit vs Fill)](#aspect-ratio-framing-fit-vs-fill)
5. [Filesystem Exploration Tools](#5-filesystem-exploration-tools)
   - [`list_directory`](#list_directory)
   - [`read_file` (Context Window Guardrail)](#read_file-context-window-guardrail)
   - [`GoogleSearch`](#googlesearch)
6. [Troubleshooting & Diagnostics](#6-troubleshooting--diagnostics)

---

## 1. Architecture & Flow

```text
┌─────────────────┐       WebSocket (JSON / fMP4)       ┌────────────────────────┐
│  Browser Client │ ◄─────────────────────────────────► │  Go Backend (Switch)  │
│  (Console UI)   │                                     │  (:8081)               │
└─────────────────┘                                     └───────────┬────────────┘
         ▲                                                          │
         │ Audio PCM (16kHz)                                        │ Bidi gRPC / WebRTC
         ▼                                                          ▼
┌─────────────────┐                                     ┌────────────────────────┐
│  Microphone /   │                                     │  Gemini Live API       │
│  AudioWorklet   │                                     │  (us-central1)         │
└─────────────────┘                                     └────────────────────────┘
```

The application uses the **Switchboard Architecture Pattern**:

1. The browser connects via WebSocket to the Go server (`/ws`).
2. The Go server initializes a bidirectional streaming session with the **Gemini Live API** on Google Cloud.
3. Audio spoken by the user is captured at 16kHz PCM via an isolated `AudioWorkletNode` and streamed upstream.
4. When Gemini calls a local tool (`list_directory`, `read_file`, `generate_diagram`), the Go backend executes the tool locally and returns the output to Gemini within the same active turn.
5. Telemetry is simultaneously dispatched to the browser to render live visual cards, code blocks, and diagrams in real time.

---

## 2. Customizing Persona & Instructions

You can tailor the assistant's expertise, communication style, and guardrails using two environment variables.

### Augmenting Context (`AVATAR_EXTRA_CONTEXT`)

Use `AVATAR_EXTRA_CONTEXT` when you want to **keep the built-in software assistant persona** but supply dynamic, task-specific knowledge, such as documentation URLs, coding standards, or project rules.

The content of `AVATAR_EXTRA_CONTEXT` is appended to the system instruction under an `Additional Context:` header.

#### Example 1: Enforcing Go Idioms and Testing

```bash
export AVATAR_EXTRA_CONTEXT="Focus exclusively on Go 1.24 idioms. Always propose table-driven unit tests. Adhere strictly to Uber Go style guidelines."
go run main.go
```

#### Example 2: Referencing API Documentation

```bash
export AVATAR_EXTRA_CONTEXT="Reference Google's official Go SDK: https://pkg.go.dev/google.golang.org/genai. Avoid deprecated cloud.google.com/go/vertexai/genai packages."
go run main.go
```

#### Example 3: Providing Context on an Active Bug or Issue

```bash
export AVATAR_EXTRA_CONTEXT="We are currently investigating bug #402: memory leak during WebSocket reconnections in SafeWS. Inspect main.go concurrency guards."
go run main.go
```

---

### Complete Persona Override (`SYSTEM_INSTRUCTION_FILE`)

Use `SYSTEM_INSTRUCTION_FILE` when you want to **completely replace the built-in persona** with your own instructions authored in a Markdown or text file.

When `SYSTEM_INSTRUCTION_FILE` points to an existing file, the server reads the file and uses its contents directly as the base system instruction. If the file cannot be read, the server logs a warning and falls back safely to the default persona.

#### How to Create a Custom Persona File

Create a file named `my_persona.md`:

```markdown
You are an expert Site Reliability Engineer (SRE) investigating production incidents on Google Cloud.
You have access to local workspace tools:
- list_directory: to check logs and configuration files
- read_file: to inspect deployment manifests and metrics
- generate_diagram: to draw incident dependency graphs and outage blast radiuses

Your communication style:
1. Be calm, methodical, and concise.
2. Formulate hypotheses before inspecting files.
3. Summarize findings in bullet points.
```

#### Launching with the Override

```bash
SYSTEM_INSTRUCTION_FILE="./my_persona.md" go run main.go
```

Upon startup, the server logs the active file:

```text
Starting Local Code Assistant...
  Live Model:      gemini-3.8-live
  Voice:           Puck
  Avatar:          enabled=false, mode=reactive, preset=Ben
  Instruction File: ./my_persona.md
```

---

### Combining Override with Runtime Context

You can combine both mechanisms:

- `SYSTEM_INSTRUCTION_FILE` establishes the **foundation/role**.
- `AVATAR_EXTRA_CONTEXT` injects **ephemeral/session-specific data**.

```bash
SYSTEM_INSTRUCTION_FILE="./sre_persona.md" \
AVATAR_EXTRA_CONTEXT="Incident: Prod cluster eu-west1-b degraded. Current alert: HTTP 504 spike." \
go run main.go
```

---

## 3. Technical Diagramming with Graphviz

The assistant is equipped with the `generate_diagram` tool, allowing it to author Graphviz DOT syntax and produce high-resolution architectural diagrams on demand.

### How Diagramming Works

1. You verbally ask the assistant for a diagram (e.g., _"Draw the architecture of this server"_).
2. Gemini generates valid Graphviz DOT code and calls `generate_diagram(dot_code, filename, title)`.
3. The Go backend writes the DOT file to `./diagrams/<filename>.dot` and invokes the host `dot` CLI:

   ```bash
   dot -Tpng ./diagrams/<filename>.dot -o ./diagrams/<filename>.png
   ```

4. The PNG is base64-encoded and sent over the WebSocket for immediate zero-latency display in the browser, while also being statically served at `/diagrams/<filename>.png`.
5. If Graphviz is not installed, the `.dot` file is safely preserved on disk and an actionable notice (`brew install graphviz`) is returned.

### Sample Diagram Prompts

- **System Architecture**:
  > _"Draw an architecture diagram showing how the client WebSocket connects to our Go backend and how the Go backend routes to the Gemini Live API."_
- **Sequence Diagram**:
  > _"Generate a sequence diagram showing the tool execution flow when list_directory is triggered."_
- **Database / Entity Relationship**:
  > _"Create an ER diagram representing users, sessions, transcript entries, and generated diagrams."_
- **State Machine**:
  > _"Draw a state diagram showing our connection lifecycle: standby, connecting, connected, reconnecting, and error."_

### Interactive Diagram Controls

When a diagram renders in the left inspection panel:

- **Click to Zoom / Lightbox**: Click directly on the diagram image or the **"Enlarge"** button to open a full-screen, high-detail modal. Press `Escape` or click the backdrop to dismiss.
- **Open in Tab**: Opens `/diagrams/<filename>.png` directly in a new browser tab.
- **Download PNG**: Immediately saves the high-resolution PNG to your local downloads.
- **DOT Source Drawer**: Expand the "Graphviz DOT Source" accordion to inspect, copy, or edit the exact DOT code generated by Gemini.

---

## 4. Avatar Viewport & Audio Playback

### Operational Modes

| Mode             | Environment Flag                          | Compatible Models | Playout Engine              | Visual Representation                   |
| :--------------- | :---------------------------------------- | :---------------- | :-------------------------- | :-------------------------------------- |
| **Disabled**     | _(Default)_                               | `gemini-3.8-live` | AudioContext (24kHz PCM)    | Collapsed (full height for transcripts) |
| **Reactive Orb** | `ENABLE_AVATAR=true AVATAR_MODE=reactive` | `gemini-3.8-live` | AudioContext (24kHz PCM)    | Audio-reactive glowing canvas orb       |
| **Video Avatar** | `ENABLE_AVATAR=true AVATAR_MODE=video`    | `gemini-3.8-live` | MSE `<video>` (fMP4 stream) | Photorealistic talking video avatar     |

### Dynamic Model Switching

You can switch the active Gemini Live model directly from the web interface without restarting the server:

- **Preflight Selection**: Select your desired model from the preflight card before starting the session.
- **In-Session Switching**: Change the model via the header dropdown at any time. The client automatically persists your selection to `localStorage` (`lca_selected_model`) and smoothly reconnects the WebSocket session with the new model.
- **Model Comparison**:
  - **`gemini-3.8-live`** _(Default)_: GA Live model with the fastest TTFF (~2.6s video TTFF), full `AvatarConfig` video synthesis, and native `proactive_audio` support. The earlier `gemini-3.8-live-preview`, `gemini-3.5-*-live-preview`, and `gemini-3.1-flash-live-preview-04-2026` IDs returned `1008 Not Found` when checked on 2026-10-03.

### Inter-Turn Buffer Gap Jumping (MSE Underflow Mitigation)

During conversational turns with Gemini Live video avatars:

1. Gemini streams fMP4 video fragments only while actively generating speech or avatar movement.
2. Between turns or while the assistant is waiting for user input, no video packets are emitted, causing browser media engines (Chrome/Safari) to enter `BUFFERING_HAVE_NOTHING` (demuxer underflow).
3. When the next turn arrives at a later presentation timestamp (PTS), the player playhead could previously stall waiting for continuous frames across the gap.
4. The Local Code Assistant MSE player implements **automatic buffer gap jumping**: upon appending incoming video fragments (`updateend`), if the current playhead is behind the latest buffered time range, `videoEl.currentTime` immediately snaps across the unbuffered gap, guaranteeing smooth multi-turn playback without freezing.

### Playback Mute Controls

To silence the assistant's voice without disconnecting or disrupting visual telemetry:

- **Global Header**: Click the **`🔊 Audio On`** button next to the connection badge. It toggles to **`🔇 Muted`** (highlighted in amber).
- **Avatar Toolbar**: Click the **`🔊 Mute`** button in the avatar viewport header.
- **Visual Continuity**: In reactive mode, muting routes audio through an `outputGainNode` set to `0` _after_ the `AnalyserNode`. This means **the visual avatar orb continues to pulsate and animate in response to the assistant's voice**, but no sound is sent to your speakers.
- **Persistence**: Your mute preference is remembered across page reloads in `localStorage` (`lca_playback_muted`).

### Dynamic Resizing & S/M/L Presets

The avatar viewport can be resized freely to balance visual presentation with transcript viewing area:

- **Drag Handle**: Click and drag the horizontal grip bar directly below the avatar viewport. Drag up to compress (down to 180px) or down to expand (up to 640px).
- **Double-Click**: Double-click the drag handle to toggle between compact (`220px`) and expanded (`480px`).
- **Presets**:
  - **`S`** (Small — 220px): Maximizes vertical height for reading code and transcripts.
  - **`M`** (Medium — 340px): Default balanced height.
  - **`L`** (Large — 480px): Expands portrait height for talking video avatars.

### Aspect Ratio Framing (Fit vs Fill)

Because Gemini Live video avatars stream in a **9:16 vertical portrait aspect ratio** (720×1280), two framing modes are available in the avatar header:

- **`Fit`** (`object-contain`): Displays the entire uncropped 9:16 portrait frame with clean dark side letterboxing. Recommended for seeing the full head, shoulders, and torso.
- **`Fill`** (`object-cover object-[center_20%]`): Fills the entire container edge-to-edge with framing anchored to the upper 20% where the face and eyes are centered.

---

## 5. Filesystem Exploration Tools

### `list_directory`

- **Purpose**: Lists files and folders in the target directory.
- **Behavior**: Distinguishes folders by appending a trailing slash `/` (e.g. `frontend/`, `main.go`).
- **Prompt Examples**:
  - _"What files are in this project?"_
  - _"List the contents of tools/."_
  - _"Show me what is in the parent directory."_

### `read_file` (Context Window Guardrail)

- **Purpose**: Reads file contents for code inspection.
- **Safety Guardrail**: Automatically truncates files larger than **10,000 bytes** (`10KB`) with a `...[truncated to protect context window]` marker to prevent exhausting the live session's token window.
- **Prompt Examples**:
  - _"Read main.go and summarize how WebSocket connections are authenticated."_
  - _"Inspect go.mod and tell me what dependencies we are using."_

### `GoogleSearch`

- **Purpose**: Live web search powered upstream by Google Search in Gemini Live.
- **Prompt Examples**:
  - _"Search for the latest release notes of Google Gen AI Go SDK."_
  - _"What are the standard MIME types for fMP4 audio streams?"_

---

## 6. Troubleshooting & Diagnostics

| Symptom                                            | Probable Cause                                         | Resolution                                                                                                                                                             |
| :------------------------------------------------- | :----------------------------------------------------- | :--------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Stuck on "Standby"**                             | Microphone permissions blocked or session not started. | Click "Start Assistant Session" on the preflight overlay and grant browser microphone access.                                                                          |
| **Intro speech sounds distorted / fast**           | Hardware sample rate mismatch (e.g. 48kHz).            | The app uses 16kHz audio constraints. Ensure browser is updated to a modern version supporting standard Web Audio API sample rate conversion.                          |
| **`dot: command not found` warning**               | Graphviz CLI is not installed on the host system.      | Install Graphviz: `brew install graphviz` (macOS) or `apt-get install -y graphviz` (Linux). The `.dot` source file is still preserved under `./diagrams/`.             |
| **Video avatar black or loading spinner persists** | Upstream video turn latency or modality conflict.      | The first video frame requires ~1.5–2s to synthesize keyframes. Ensure `GOOGLE_CLOUD_LOCATION="us-central1"`.                                                          |
| **Error `1007` on connection**                     | Incompatible model/modality combination.               | Ensure regional location `GOOGLE_CLOUD_LOCATION="us-central1"` is configured. Requesting `["AUDIO", "VIDEO"]` together triggers 1007; `VIDEO` alone must be requested. |
