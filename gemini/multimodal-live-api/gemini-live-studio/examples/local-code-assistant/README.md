# Local Code Assistant (Standalone Agent)

A real-time, voice-and-avatar codebase exploration assistant built with the **Gemini Live Bidi API** in Go and a modern web console. It autonomously inspects local files, traverses directory trees, and searches external web documentation while verbally explaining its findings.

An example alongside the [Gemini Live Studio](../../README.md) reference app, this application demonstrates how to build production-grade agentic avatars using server-side function calling, dual-channel UI telemetry, and resilient WebSocket streams.

---

## 🛠️ Key Capabilities

- **Autonomous Tool Execution**: The Go backend intercepts Gemini Live function calls, executes local filesystem operations safely, and pipes results back to Gemini in a single continuous audio/video turn.
- **Dual-Channel Visualization**: While the assistant explains findings verbally, raw tool execution telemetry is forwarded concurrently over WebSocket to render syntax-highlighted code blocks, directory grids, and status badges in real time.
- **Dynamic Model Selection**: Select the model in the UI (preflight modal or header dropdown), and the choice persists across sessions. The default is `gemini-3.8-live` (GA, fastest TTFF, native proactive audio). Set `GEMINI_LIVE_MODEL` or `LOCAL_CODE_MODEL` to use another Live model.
- **Dual-Mode Avatar Interface**:
  - **Reactive Orb Mode** (Default when avatar enabled): Ultra-low-latency audio-reactive glowing canvas orb driven by Web Audio `AnalyserNode`.
  - **Video Avatar Mode**: High-definition talking video avatar driven by Gemini Live `AvatarConfig` streaming fMP4 chunks into an embedded MSE `<video>` player with automatic inter-turn gap jumping to eliminate playhead stalling during multi-turn conversations.
- **Thread-Safe Concurrency**: All WebSocket writes are guarded by a `SafeWS` mutex wrapper, and outgoing Live session calls (`SendRealtimeInput`, `SendToolResponse`) are guarded by `sessionMu`.
- **Self-Healing Connection**: 10-second ping/pong heartbeat, 5-second watchdog timer, and exponential backoff auto-reconnection with interactive 5-state UI badges.
- **AudioWorklet PCM Streaming**: Client-side microphone audio is captured at 16kHz PCM on an isolated background `AudioWorkletNode` (`audio-capture-processor`), eliminating UI stutter.

---

## 🧰 Available Agent Tools

The assistant is equipped with two server-side filesystem tools and one built-in Gemini tool declared during session setup:

| Tool Name              | Provider            | Purpose                                                      | Parameters                                                                                     | Return Value                                                                        | Example User Voice Prompt                             |
| :--------------------- | :------------------ | :----------------------------------------------------------- | :--------------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------- | :---------------------------------------------------- |
| **`list_directory`**   | Custom (Go Backend) | Inspects directory contents                                  | `path` _(string, optional)_: Target path (defaults to `"."`)                                   | `{"output": ["file1", "dir1/", ...]}`                                               | _"What files are in this project?"_                   |
| **`read_file`**        | Custom (Go Backend) | Reads file content with 10KB safe truncation                 | `path` _(string, required)_: Path of file to read                                              | `{"output": "..."}` or `{"error": "..."}`                                           | _"Read main.go and summarize its dependencies."_      |
| **`generate_diagram`** | Custom (Go Backend) | Generates architecture & technical diagrams via Graphviz DOT | `dot_code` _(string, required)_, `filename` _(string, optional)_, `title` _(string, optional)_ | `{"dot_path": "...", "png_path": "...", "image_base64": "...", "image_url": "..."}` | _"Draw an architecture diagram of this application."_ |
| **`GoogleSearch`**     | Built-in (Gemini)   | Searches web documentation & external APIs                   | _Managed upstream by Gemini Live_                                                              | Text search results & citations                                                     | _"What is the latest stable Go release?"_             |

### Tool Details & Execution Semantics

#### 1. `list_directory`

- **Declaration**: Declared via `genai.FunctionDeclaration` with an optional `path` property.
- **Behavior**: Inspects the specified local directory using Go's `os.ReadDir()`.
- **Formatting**: Distinguishes directories by appending a trailing slash `/` (e.g. `frontend/`, `main.go`).
- **UI Visualization**: Rendered in the left visualization panel as a responsive two-column icon grid.

#### 2. `read_file`

- **Declaration**: Declared via `genai.FunctionDeclaration` with a required `path` string.
- **Behavior**: Reads file bytes using `os.ReadFile()`.
- **Guardrail (Context Window Protection)**: If file content exceeds 10,000 characters, it is truncated with a trailing `\n...[truncated]` marker to avoid blowing prompt token limits.
- **UI Visualization**: Rendered as a dark-theme syntax-highlighted code card displaying line count and formatted source code.

#### 3. `generate_diagram`

- **Declaration**: Declared via `genai.FunctionDeclaration` with `dot_code` (required), `filename` (optional), and `title` (optional).
- **Behavior**: Saves the agent-generated Graphviz DOT code to `./diagrams/<filename>.dot` and compiles it into a high-resolution PNG using the host `dot` CLI (`dot -Tpng <file.dot> -o <file.png>`).
- **Fallback Handling**: If the host lacks Graphviz, the `.dot` file is safely preserved on disk and an actionable warning with installation instructions (`brew install graphviz`) is returned.
- **UI Visualization**: Rendered as an interactive visual diagram card with click-to-zoom modal, expandable raw DOT code drawer, open in tab link, and direct PNG download button.
- **HTTP Serving**: Diagrams are automatically accessible via HTTP at `/diagrams/<filename>.png`.

#### 4. `GoogleSearch`

- **Declaration**: Declared via `&genai.GoogleSearch{}` in `LiveConnectConfig.Tools`.
- **Behavior**: Executed upstream by Google servers whenever the model requires fresh external knowledge, release notes, or public documentation.

---

## 🔄 Dual-Channel Telemetry Architecture

When Gemini Live decides to call a tool, execution flows across two parallel channels:

```text
┌─────────────────┐       WebSocket       ┌──────────────────┐    Gemini Live Bidi    ┌──────────────────┐
│                 │ <───────────────────> │                  │ <────────────────────> │                  │
│  Lit/Web Console│                       │    Go Backend    │                        │   Gemini Live    │
│   (index.html)  │                       │    (main.go)     │                        │       API        │
└─────────────────┘                       └──────────────────┘                        └──────────────────┘
         │                                          │                                          │
         │                                          │ <── 1. ToolCall(name, args) ────────────│
         │                                          │                                          │
         │                                          │ ─── 2. Execute locally (os.ReadFile)     │
         │                                          │                                          │
         │                                          │ ─── 3. SendToolResponse(result) ───────> │
         │ <── 4a. tool_execution JSON (WS) ─────── │                                          │
         │     (renders UI code card / file grid)   │ <── 4b. Audio/Video Turn Stream ──────── │
         │ <── 4c. Model audio / video chunks ───── │     (spoken summary of results)          │
         │                                          │                                          │
```

1. **Upstream Turn**: The model pauses its verbal response and sends a `msg.ToolCall`.
2. **Local Execution**: The Go backend intercepts the call, executes `executeTool()`, and immediately returns the result upstream via `session.SendToolResponse()`.
3. **Downstream UI Telemetry**: Concurrently, the backend writes a `tool_execution` event over the client WebSocket.
4. **Synchronized Presentation**: The frontend renders the code preview or file grid in the inspection pane while the assistant verbally summarizes the findings.

---

## 📋 Prerequisites

- **Go**: Version `1.23` or higher.
- **Google Cloud Platform**:
  - Project with the Gemini Enterprise Agent Platform (Vertex AI) API enabled (`aiplatform.googleapis.com`).
  - Regional quota for Gemini Live API models (`us-central1`).
- **Application Default Credentials (ADC)**:

  ```bash
  gcloud auth application-default login
  ```

---

## 🚀 Quick Start & Usage

### 1. Clone & Navigate

```bash
cd examples/local-code-assistant
```

### 2. Configure Environment

Export your Google Cloud project and location:

```bash
export GOOGLE_CLOUD_PROJECT="your-project-id"
export GOOGLE_CLOUD_LOCATION="us-central1"
```

### 3. Run in Your Preferred Mode

#### Option A: Audio-Only Assistant (Default — Avatar Disabled)

Fastest turn-around with ultra-low latency audio on `gemini-3.8-live`:

```bash
go run main.go
```

#### Option B: Audio-Reactive Orb Avatar (Ultralight & Snappy)

Interactive glowing canvas orb with speaking, listening, and tool-execution visual states:

```bash
ENABLE_AVATAR=true AVATAR_MODE=reactive go run main.go
```

#### Option C: Full Talking Video Avatar (Gemini Live fMP4 Stream)

Real-time talking video avatar streaming via Gemini Live `AvatarConfig` on `gemini-3.8-live`:

```bash
ENABLE_AVATAR=true AVATAR_MODE=video AVATAR_PRESET=Ben go run main.go
```

### 4. Open the Web Console

Navigate to **`http://localhost:8081`** in your browser, review the preflight status card, and click **"Start Assistant Session"**.

---

## 💬 Sample Interaction Prompts

Once connected, speak into your microphone or type in the bottom console input:

- **Directory Exploration**:
  - _"What files are in the current directory?"_
  - _"Can you list what is inside the frontend folder?"_
- **Source Code Inspection**:
  - _"Read main.go and summarize what tools are registered."_
  - _"Inspect index.html and tell me how the AudioWorklet is implemented."_
- **Technical & Architecture Diagramming**:
  - _"Draw an architecture diagram showing the relationship between the Lit frontend, Go backend switchboard, and the Gemini Live API."_
  - _"Generate a sequence diagram of how WebSocket audio frames flow from the user to the Gemini Live API."_
  - _"Create a flowchart of how tool calls are dispatched and visualized in the UI."_
- **External Web Knowledge**:
  - _"Search for the latest features introduced in Go 1.24."_
  - _"What are the supported codecs for Gemini Live video streaming?"_
- **Combined Reasoning & Tool Chaining**:
  - _"Look at the files in this directory, find the readme, read it, and tell me how to run the app."_

---

## 🧠 Customizing Persona & Context

You can customize the assistant's behavior, domain rules, or role via two environment variables:

### 1. Augmenting Context (`AVATAR_EXTRA_CONTEXT`)

Appends custom instructions, project guidelines, or documentation links to the default software assistant persona:

```bash
# Provide API documentation context
export AVATAR_EXTRA_CONTEXT="Reference https://pkg.go.dev/google.golang.org/genai. Always write unit tests with table tests."
go run main.go
```

### 2. Complete Persona Override (`SYSTEM_INSTRUCTION_FILE`)

Completely replaces the built-in software assistant persona with instructions from an external file:

```bash
# Use a custom role (e.g. SRE investigator, security auditor, or code reviewer)
SYSTEM_INSTRUCTION_FILE="./my_instructions.md" go run main.go
```

If the file cannot be read, the server automatically falls back to the default persona with a clear log warning. Both options can be combined—`AVATAR_EXTRA_CONTEXT` will append to whichever base persona is active.

> 📖 **In-Depth Guide**: For advanced prompt engineering, technical diagramming recipes, aspect ratio framing, audio mute controls, and complete configuration details, see the [Local Code Assistant User Guide](USER_GUIDE.md).

---

## ⚙️ Configuration Reference

All settings can be configured via environment variables or a local `.env` file:

| Variable                  | Default           | Description                                                                                        |
| :------------------------ | :---------------- | :------------------------------------------------------------------------------------------------- |
| `GOOGLE_CLOUD_PROJECT`    | _(Required)_      | Google Cloud project ID                                                                            |
| `GOOGLE_CLOUD_LOCATION`   | `us-central1`     | Regional Vertex endpoint (Gemini Live requires regional endpoint)                                  |
| `ENABLE_AVATAR`           | `false`           | Enables avatar view in the Right Panel (`true` / `false`)                                          |
| `AVATAR_MODE`             | `reactive`        | Avatar rendering style: `reactive` (animated orb) or `video` (fMP4 stream)                         |
| `AVATAR_PRESET`           | `Ben`             | Preset avatar name for video mode (e.g. `Ben`)                                                     |
| `GEMINI_LIVE_MODEL`       | `gemini-3.8-live` | Override the Live model. `gemini-3.8-live` supports audio, the reactive orb, and the video avatar. |
| `GEMINI_LIVE_VOICE`       | `Puck`            | Prebuilt synthesized voice (`Puck`, `Charon`, `Kore`, `Fenrir`, `Aoede`)                           |
| `SYSTEM_INSTRUCTION_FILE` | _(Empty)_         | Path to a Markdown or text file to completely override the built-in base persona                   |
| `AVATAR_EXTRA_CONTEXT`    | _(Empty)_         | Extra documentation or instructions dynamically appended to system persona                         |
| `LOCAL_CODE_ADDR`         | `:8081`           | HTTP and WebSocket server listening address                                                        |

---

## 🩺 Troubleshooting

### Status Stuck in "Standby"

- **Cause**: Browser microphone access was denied or the user hasn't clicked "Start Assistant Session".
- **Fix**: Check your browser URL bar for microphone permissions and click "Start Assistant Session".

### Video Avatar Area Shows Loading Spinner

- **Cause**: Gemini Live is generating initial video keyframes (`~1.5–2.5s` time-to-first-frame).
- **Fix**: The `#avatar-loading` spinner automatically dismisses once the first fMP4 fragment is decoded.

### WebSocket Fails With HTTP 403

- **Cause**: The assistant can read local files, so `/ws` only accepts connections from the page it serves (same origin) or from another `localhost` page while the server itself is reached on `localhost`. Pages on other origins are rejected so a site you visit can't drive the tools.
- **Fix**: Open the UI from the server itself (`http://localhost:8081`), not from a file or another host.

### 1007 Modality / Connect Error

- **Cause**: Incompatible combination of modalities or model deployment region.
- **Fix**: Verify `GOOGLE_CLOUD_LOCATION="us-central1"`. Remember that requesting both `["AUDIO", "VIDEO"]` modalities together fails with `1007`; requesting `["VIDEO"]` alone is required (audio is muxed directly in the fMP4 container).

---

## 📦 Agent Plugin

The app doubles as an **Agent Plugins v1.0.0** package in [`plugin/`](plugin/):

```text
plugin/
├── plugin.json
├── README.md
└── skills/
    └── local-code-assistant/
        ├── SKILL.md
        └── scripts/
            └── launch.sh     # runs this example (or a packed bundle's assets/)
```

There is one copy of the code: the skill launches this directory. `make pack-skill`
at the repository root builds a portable `local-code-assistant.skill` archive that
bundles a copy under `assets/local-code-assistant/`.

---

## 🤝 Contributing

Contributions, bug reports, and suggestions are welcome!

- For major architectural changes or additional tools, please open an issue first.
- Ensure all quality gates pass before submitting a PR:

  ```bash
  go vet ./...
  go test ./...
  ```

---

## 📄 License

This project is licensed under the **Apache-2.0 License**. See the root [`LICENSE`](../../LICENSE) for details.
