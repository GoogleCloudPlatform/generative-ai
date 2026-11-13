# Live Wire Protocol & Kit Reference

Authoritative wire-framing specification and API reference for the
**[`livebridge/`](../livebridge/)** Go package and
**[`frontend/src/lib/live/`](../frontend/src/lib/live/)** TypeScript kit.

> **Diataxis navigation**
>
> - **Tutorials (Learning):** [Quickstart](../README.md#quickstart) and [User Guide](user_guide.md)
> - **How-To Guides (Recipes):** [Building Voice & Avatar Agents](building-with-livebridge.md)
> - **Explanation (Understanding):** [Developer Guide](developers_guide.md)
> - **Reference (Specifications & APIs):** You are here (see also [Frontend Components](frontend-components.md))

## Contents

- [Transport & security envelope](#transport--security-envelope)
- [Client-to-server WebSocket frames](#client-to-server-websocket-frames)
- [Server-to-client WebSocket frames](#server-to-client-websocket-frames)
- [Go package reference](#go-package-reference)
- [TypeScript kit reference](#typescript-kit-reference)
- [Standalone module sync](#standalone-module-sync)

## Transport & security envelope

| Control             | Default / Constant                         | Purpose                                                                  |
| :------------------ | :----------------------------------------- | :----------------------------------------------------------------------- |
| Origin check        | `OriginPolicy` (`ALLOWED_ORIGINS` + local) | Rejects cross-site HTTP and WebSocket upgrades with `403 Forbidden`      |
| Initial frame limit | `16 MiB` (`MaxInitialConfigBytes`)         | Accommodates a 2K `9:16` base64 custom avatar data URL plus persona text |
| Runtime frame limit | `8 MiB` (`MaxClientMessageBytes`)          | Bounds 16 kHz PCM chunks, 1 FPS JPEG vision frames, and tool results     |
| Session cap         | `9m55s` (`DefaultSessionCap`) + `2s` grace | Warns the UI via `session_limit_reached` before the 10-minute API limit  |
| Goodbye backstop    | `12s` (`DefaultGoodbyeBackstop`)           | Bounds graceful farewell turns when `TurnComplete` does not arrive       |
| Tool timeout        | `2m` (`DefaultToolTimeout`)                | Bounds server-side and browser-relayed tool calls                        |
| HTTP header timeout | `10s` (`ReadHeaderTimeout`), `120s` idle   | Protects HTTP endpoints while leaving stream read/write timeouts unset   |

### WebSocket close codes

Both `livebridge.Bridge` and `LiveSocketClient` (`describeCloseEvent`) use
standard RFC 6455 close codes:

| Code   | Reason                                           | Meaning                                                                    |
| :----- | :----------------------------------------------- | :------------------------------------------------------------------------- |
| `1000` | `"Session terminated"`                           | Clean user-initiated disconnect (after farewell turn or backstop)          |
| `1000` | `"Session limit reached"`                        | Proactive `9m55s` session cap reached after `session_limit_reached` status |
| `1007` | `"Invalid session config"`                       | Client sent an invalid avatar or malformed setup payload (closed pre-dial) |
| `1009` | _(RFC 6455 message too big)_                     | Frame exceeded `SetReadLimit` (`16 MiB` setup / `8 MiB` runtime)           |
| `1011` | `"Failed to connect"` / `"Session disconnected"` | Upstream Gemini Live API dial or stream error                              |

## Client-to-server WebSocket frames

All client-to-server frames are UTF-8 JSON text frames (unless
`BridgeConfig.AllowPlainTextFrames` is enabled for legacy pages).

### 1. Optional setup frame (`InitialConfig`)

Dynamic-persona endpoints (`/ws` and `/ws/live` in Gemini Live Studio) read a
JSON setup payload immediately on `WebSocket.onopen` before dialing the Gemini
Live API.
Fixed-persona servers (such as `examples/local-code-assistant`) skip the setup
frame and begin reading runtime `ClientMessage` frames directly.

```json
{
  "avatarType": "preset",
  "avatarData": "Kira",
  "voiceName": "Puck",
  "languageCode": "en-US",
  "systemInstruction": "You are a concise architecture advisor.",
  "enableGoogleSearch": true,
  "enableToolCalling": true,
  "proactiveAudio": true
}
```

### 2. Runtime frames (`livebridge.ClientMessage`)

| `type`                              | Fields                                                                                    | Upstream / Switchboard Action                                                       |
| :---------------------------------- | :---------------------------------------------------------------------------------------- | :---------------------------------------------------------------------------------- |
| `"audio"`                           | `mimeType` (`"audio/pcm;rate=16000"`), `data` (base64 Int16 LE)                           | Validates MIME, decodes base64, calls `SendRealtimeInput({Audio: Blob})`            |
| `"video"`                           | `mimeType` (`"image/jpeg"` or `"image/png"`), `data` (base64)                             | Validates MIME, decodes base64, calls `SendRealtimeInput({Video: Blob})`            |
| `"text"`                            | `data` (non-empty UTF-8 string)                                                           | Truncates to `MaxClientTextRunes` (if `> 0`), calls `SendRealtimeInput({Text})`     |
| `"control"`                         | `action: "terminate"`                                                                     | Arms `TerminateGate`, sends `GoodbyePrompt`, starts `GoodbyeBackstop` timer         |
| `"tool_response"` / `"tool_result"` | `id`, `name`, `response` or `result` (JSON object), optional `image` (data URL), `execMs` | Optional `{Video: Blob}` snapshot (when `SeeVisualResults`) then `SendToolResponse` |
| `"ping"`                            | —                                                                                         | Replies `{"type": "pong"}` without touching the upstream session                    |
| _(custom)_                          | Application-defined fields (`enabled`, `data`, etc.)                                      | Routed to `BridgeConfig.OnCustomClientMessage(bridge, msg)`                         |

## Server-to-client WebSocket frames

### Binary media frames

Once the stream announcement frame (`media_config` or `AudioConfigEventType`)
has been sent, media flows down as **raw binary WebSocket frames**:

- **Audio mode (`ModeAudio`, `AudioDeliveryBinary`):** Signed 16-bit
  little-endian mono PCM bytes at the announced `sampleRate` (default `24000` Hz).
- **Avatar mode (`ModeAvatar`):** ISO BMFF fragmented MP4 (`ftyp`/`moov` +
  `moof`/`mdat`) carrying muxed H.264 video and AAC audio (`avc1.*, mp4a.40.2`).

### JSON control frames

| `type`                                                    | Fields                                                                     | Description                                                                                                  |
| :-------------------------------------------------------- | :------------------------------------------------------------------------- | :----------------------------------------------------------------------------------------------------------- |
| `"session_info"`                                          | `mode` (`"avatar"` \| `"audio"`), `model`, `location`                      | Emitted when `Bridge.Run()` begins (`EmitSessionInfo: true`)                                                 |
| `"media_config"` / _(custom audio type)_                  | `mimeType` (`"audio/pcm"` \| `"video/mp4"`), `sampleRate` or `codecs`      | Emitted once before media frames; fMP4 `codecs` are sniffed from `ftyp`/`avcC` via `SniffMP4`                |
| `"audio"`                                                 | `data` (base64 PCM), `mimeType`                                            | Emitted instead of binary frames only when `AudioDelivery: AudioDeliveryBase64JSON`                          |
| `"input_transcript"`                                      | `text`, `finished` (`boolean`, or string if `StringifyTranscriptFinished`) | User speech transcription; partials **replace** the active user bubble until `finished: true`                |
| `"output_transcript"`                                     | `text`, `finished` (`boolean`, or string if `StringifyTranscriptFinished`) | Model speech transcription; partials **concatenate** onto the active assistant bubble until `finished: true` |
| `"transcript"`                                            | `text`                                                                     | Complete text part emitted from `ModelTurn.Parts`                                                            |
| `"interrupted"`                                           | —                                                                          | User barged in; client flushes PCM/MSE playback buffers and marks any partial bubble `[Interrupted]`         |
| `"turn_complete"`                                         | —                                                                          | Model finished its current turn (`EmitTurnComplete: true`)                                                   |
| `"tool_call"` / _(custom `ServerToolEventType`)_          | `id`, `name`, `args`, optional `result`                                    | Server-executed tool completion (`result` included) or page-relayed invocation (awaits `tool_result`)        |
| `"tool_call_cancellation"` / _(custom `CancelEventType`)_ | `ids` (`string[]`), optional `reason` (`"model"` \| `"timeout"`)           | Cancels in-flight tool calls on barge-in or page-relay timeout                                               |
| `"tool_timing"`                                           | `id`, `name`, `roundTripMs`, `execMs`                                      | Emitted after page-relayed tools complete when `ToolRunnerConfig.EmitTiming: true`                           |
| `"proactive_alert"`                                       | Application-defined (`id`, `source`, `summary`, `metadata`, etc.)          | Browser notification payload returned by `BridgeConfig.FormatAlert` alongside an injected alert prompt       |
| `"status"`                                                | `error: "session_limit_reached"`, `message: "session_limit_reached"`       | Announces impending `1000 "Session limit reached"` close                                                     |
| `"pong"`                                                  | —                                                                          | Heartbeat reply to client `"ping"`                                                                           |

## Go package reference

Import path in the root module: `"gemini-live-studio/livebridge"` (or
`"<module>/internal/livebridge"` in standalone synced modules).

### Session switchboard (`switchboard.go`, `conn.go`)

| Symbol                     | Signature / Purpose                                                                                                                                         |
| :------------------------- | :---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NewBridge`                | `NewBridge(ctx context.Context, ws *SafeConn, upstream Session, cfg BridgeConfig) *Bridge` — creates a bidirectional switchboard session                    |
| `(*Bridge).Run`            | Blocks until the session exits cleanly or with an error; runs `receiveLoop`, `clientLoop`, session-cap timer, and optional `alertLoop`                      |
| `(*Bridge).Shutdown`       | `Shutdown(closeCode int, closeReason string)` — idempotent (`sync.Once`) dual teardown of timers, `ToolRunner`, upstream `Session`, and browser `*SafeConn` |
| `(*Bridge).WriteJSON`      | Sends a JSON frame to the browser, triggering `Shutdown` on write error                                                                                     |
| `(*Bridge).SendRealtime`   | Thread-safe (`sendMu`) wrapper around `upstream.SendRealtimeInput`                                                                                          |
| `(*Bridge).SendTextPrompt` | Injects a text turn upstream via `SendRealtimeInput`                                                                                                        |
| `BridgeConfig`             | Configures `Mode` (`ModeAvatar` \| `ModeAudio`), `GreetingPrompt`, `GoodbyePrompt`, `Timings`, `AudioDelivery`, `Tools`, `Alerts`, `FormatAlert`, and hooks |
| `SafeConn`                 | `NewSafeConn(*websocket.Conn)` — mutex-serialized `WriteJSON`, `WriteMessage`, and 1s-deadline `WriteClose` over `gorilla/websocket`                        |
| `TerminateGate`            | Atomic state machine (`RequestTerminate`, `OnInterrupted`, `OnTurnComplete`) that skips an interrupted turn's `TurnComplete` during farewell generation     |

### Clients, HTTP & origin security (`clients.go`, `security.go`)

| Symbol                             | Signature / Purpose                                                                                                                                |
| :--------------------------------- | :------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NewClientPool`                    | `NewClientPool(projectID, baseURL string, knownLocations ...string) *ClientPool` — caches one `*genai.Client` per Google Cloud location            |
| `(*ClientPool).ClientFor`          | Lazily initializes and caches a regional or `global` `*genai.Client` using `context.Background()`                                                  |
| `(*ClientPool).Connect`            | Implements `Connector`: dials `client.Live.Connect(ctx, model, config)`                                                                            |
| `BaseURLForLocation`               | Rewrites regional host prefixes on `*.googleapis.com` (`us-central1-aiplatform.googleapis.com` <-> `aiplatform.googleapis.com`)                    |
| `NewOriginPolicy` / `FromEnv`      | Parses comma-separated `ALLOWED_ORIGINS`; permits same-origin, loopback dev (`localhost:5173` -> `localhost:8080`), and explicit allowlist matches |
| `(*OriginPolicy).WithCORS`         | Wraps `http.HandlerFunc` with strict origin enforcement (`403` on disallowed origins)                                                              |
| `(*OriginPolicy).Upgrader`         | Returns a `websocket.Upgrader` enforcing `OriginPolicy.Allows`                                                                                     |
| `NewHTTPServer`                    | `NewHTTPServer(addr string, h http.Handler) *http.Server` — sets slowloris header/idle timeouts while leaving stream read/write timeouts unset     |
| `AllowedValues` / `ResolveAllowed` | Enforces server-side model and region allowlists with structured fallback logging                                                                  |

### Tools, alerts, media & validation (`tools.go`, `alerts.go`, `media.go`, `validation.go`)

| Symbol                                          | Signature / Purpose                                                                                                                                 |
| :---------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------- |
| `NewFuncRegistry`                               | Thread-safe server-side `FunctionDeclaration` + `ToolFunc` registry (`Register`, `Has`, `Declarations`, `Execute`)                                  |
| `NewToolRunner`                                 | `NewToolRunner(cfg ToolRunnerConfig) *ToolRunner` — non-blocking server & page-relayed tool execution, per-ID cancellation, timeouts, visual frames |
| `(*ToolRunner).SetSeeVisualResults`             | Dynamically toggles pre-response `{Video: Blob}` injection for page-relayed tool snapshots                                                          |
| `NewAlertBus` / `NewAlertBusOf[T]`              | Multi-subscriber non-blocking fan-out with pre-session backlog (`Publish`, `Subscribe`, `SetEnabled`, `IsEnabled`)                                  |
| `FormatUntrustedAlert`                          | Wraps external alert fields and body inside explicit untrusted-data delimiters with rune caps                                                       |
| `SniffMP4` / `ParseAvc1Dimensions`              | Parses ISO BMFF `ftyp`/`moov`/`avc1`/`avcC` boxes from the first fMP4 fragment to extract MSE codec strings and dimensions                          |
| `ParseImageDataURL`                             | Decodes and validates `data:image/png;base64,...` or `data:image/jpeg;base64,...` payloads (`AvatarImageMIMETypes`, `RealtimeVideoMIMETypes`)       |
| `TruncateRunes`                                 | Truncates UTF-8 strings by rune count without splitting multi-byte characters                                                                       |
| `ValidPresetName` / `ValidLanguageCode`         | Validates voice/preset identifiers and BCP-47 language codes                                                                                        |
| `ValidRealtimeAudioMIME` / `ParsePCMSampleRate` | Validates `audio/pcm[;rate=N]` MIME strings and extracts sample rates                                                                               |
| `InRange` / `SupportsProactiveAudio`            | Validates optional float sampling parameters and gates `ProactivityConfig.ProactiveAudio` by model capability                                       |

## TypeScript kit reference

All modules in [`frontend/src/lib/live/`](../frontend/src/lib/live/) are
reexported from `frontend/src/lib/live/index.ts` and carry zero UI framework
dependencies.

| Module & Primary Exports                                                                            | Key Methods & Capabilities                                                                                                                                                              |
| :-------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **`live-socket.ts`** (`LiveSocketClient`, `describeCloseEvent`)                                     | `connect(opts)`, `sendAudioChunk(b64)`, `sendVideoFrame(b64)`, `sendText(text)`, `sendToolResult(id, name, result, opts)`, `requestGracefulTermination()`, `disconnect()`               |
| **`pcm-mic.ts`** (`PcmMic`, `createPcmCaptureContext`, `computeInt16Rms`)                           | `start(onBase64PcmChunk)`, `stop()`, `toggle(cb)`, `setSoftMuted(muted)` — 16 kHz `AudioWorklet` capture with async `startToken` track-leak protection and RMS level callbacks          |
| **`pcm-player.ts`** (`PcmPlayer`)                                                                   | `init(sampleRate)`, `feed(pcmBuffer)`, `flushAndInterrupt()`, `deferPlayback(seconds)`, `setMuted(muted)`, `toggleMute()`, `destroy()`, `analyser` (`AnalyserNode`)                     |
| **`fmp4-player.ts`** (`Fmp4Player`)                                                                 | `attach(videoEl)`, `setCodec(codecs)`, `appendChunk(uint8)`, `flushAndAbort()`, `destroy()` — MSE `SourceBuffer` queue, barge-in trim, quota eviction, inter-turn gap jump              |
| **`chime-synth.ts`** (`ChimeSynth`, `CHIME_PRESETS`, `normalizeChimePreset`)                        | `playAmbientCue(audioCtx)` (`'soft'` \| `'subtle'` \| `'off'`), `setMode(mode)`, `cycleMode()` — warm G4/C5 low-pass procedural Web Audio notification cues                             |
| **`transcript-assembler.ts`** (`TranscriptAssembler`, `parseToolCallItem`)                          | `appendTurn(role, text, finished, concat)`, `addUserText(text)`, `addToolCall(msg)`, `markToolCallsCancelled(ids)`, `interruptPartialAssistantTurn()`, `finalizeAssistantTurn()`        |
| **`webmcp-host.ts`** (`WebmcpToolHost`, `WebmcpToolError`, `WebmcpCallEvent`, `nativeModelContext`) | `register(defs)`, `unregister(names)`, `list()`, `call(name, args, signal, caller)`, `callWithOutput(...)`, `diagnostics` (`conflicts`, `dropped`, `externalCalls`), `coalesceInFlight` |

## Standalone module sync

[`examples/local-code-assistant/`](../examples/local-code-assistant/) maintains
its own standalone `go.mod` (`module local-code-assistant`) so it can be copied
out of the repository or bundled into a portable `.skill` archive via
`make pack-skill`. Run `make sync-livebridge` from the repository root whenever
files in `livebridge/` change; `make lint` checks that standalone copies stay
byte-for-byte identical.
