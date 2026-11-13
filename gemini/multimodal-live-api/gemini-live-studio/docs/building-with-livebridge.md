# Building Voice & Avatar Agents

Task-oriented recipes for building new real-time voice, avatar, tool-using, and
proactive agents with the in-repo **[`livebridge/`](../livebridge/)** Go package
and **[`frontend/src/lib/live/`](../frontend/src/lib/live/)** TypeScript kit.

> **Diataxis navigation**
>
> - **Tutorials (Learning):** [Quickstart](../README.md#quickstart) and [User Guide](user_guide.md)
> - **How-To Guides (Recipes):** You are here
> - **Explanation (Understanding):** [Developer Guide](developers_guide.md)
> - **Reference (Specifications & APIs):** [Live Wire Protocol & Kit Reference](live-wire-protocol.md) and [Frontend Components](frontend-components.md)

## Contents

- [1. Minimal voice agent](#1-minimal-voice-agent)
- [2. Upgrade to a talking video avatar](#2-upgrade-to-a-talking-video-avatar)
- [3. Add server-side function calling](#3-add-server-side-function-calling)
- [4. Relay browser & WebMCP page tools with visual snapshots](#4-relay-browser--webmcp-page-tools-with-visual-snapshots)
- [5. Broadcast background alerts safely](#5-broadcast-background-alerts-safely)
- [6. Reuse `livebridge` in a standalone Go module](#6-reuse-livebridge-in-a-standalone-go-module)

## 1. Minimal voice agent

A complete credential-isolated 24 kHz voice switchboard takes ~60 lines of Go
and ~40 lines of framework-agnostic TypeScript.

### Backend (`main.go`)

`ClientPool` caches regional Google Cloud clients, `OriginPolicy` blocks cross-site
WebSocket upgrades, `NewHTTPServer` leaves read/write timeouts unset so 10-minute
sessions stay alive, and `Bridge` handles greetings, transcripts, barge-in, the
`9m55s` session cap, graceful farewells, and dual-socket teardown:

```go
package main

import (
  "log"
  "net/http"
  "os"

  "github.com/gorilla/websocket"
  "google.golang.org/genai"

  "gemini-live-studio/livebridge"
)

func main() {
  projectID := os.Getenv("GOOGLE_CLOUD_PROJECT")
  clients := livebridge.NewClientPool(projectID, "")
  origins := livebridge.NewOriginPolicyFromEnv()
  upgrader := origins.Upgrader()

  mux := http.NewServeMux()
  mux.HandleFunc("GET /ws/live", func(w http.ResponseWriter, r *http.Request) {
    rawConn, err := upgrader.Upgrade(w, r, nil)
    if err != nil {
      return
    }
    ws := livebridge.NewSafeConn(rawConn)
    defer func() { _ = ws.Close() }()
    ws.SetReadLimit(livebridge.MaxClientMessageBytes)

    liveCfg := &genai.LiveConnectConfig{
      ResponseModalities: []genai.Modality{genai.ModalityAudio},
      SystemInstruction: &genai.Content{
        Parts: []*genai.Part{{Text: "You are a concise, friendly voice assistant."}},
      },
      SpeechConfig: &genai.SpeechConfig{
        VoiceConfig: &genai.VoiceConfig{
          PrebuiltVoiceConfig: &genai.PrebuiltVoiceConfig{VoiceName: "Puck"},
        },
      },
      InputAudioTranscription:  &genai.AudioTranscriptionConfig{LanguageCodes: []string{"en-US"}},
      OutputAudioTranscription: &genai.AudioTranscriptionConfig{LanguageCodes: []string{"en-US"}},
    }

    upstream, err := clients.Connect(r.Context(), "gemini-3.8-live", livebridge.DefaultLocation, liveCfg)
    if err != nil {
      _ = ws.WriteClose(websocket.CloseInternalServerErr, "Failed to connect")
      return
    }

    bridge := livebridge.NewBridge(r.Context(), ws, upstream, livebridge.BridgeConfig{
      Mode:            livebridge.ModeAudio,
      Model:           "gemini-3.8-live",
      Location:        livebridge.DefaultLocation,
      GreetingPrompt:  "Greet the user warmly in one short sentence.",
      EmitSessionInfo: true,
    })
    defer bridge.Shutdown(0, "")
    bridge.Run()
  })

  srv := livebridge.NewHTTPServer(":8080", mux)
  log.Fatal(srv.ListenAndServe())
}
```

### Browser (`session.ts`)

Import `LiveSocketClient`, `PcmMic`, and `PcmPlayer` from `src/lib/live/`—no UI
framework required:

```ts
import { LiveSocketClient, PcmMic, PcmPlayer } from './lib/live';

const player = new PcmPlayer();
const mic = new PcmMic({
  onError: (err) => console.error('Microphone error:', err),
});
const socket = new LiveSocketClient();

export async function startVoiceSession(): Promise<void> {
  player.init(24000);

  socket.connect({
    endpoint: '/ws/live',
    onMediaConfig: (msg) => {
      if (msg.mimeType === 'audio/pcm' && typeof msg.sampleRate === 'number') {
        player.init(msg.sampleRate);
      }
    },
    onBinaryFrame: (pcmBytes) => player.feed(pcmBytes),
    onInterrupted: () => player.flushAndInterrupt(),
    onBeforeTerminate: () => mic.stop(),
    onDisconnected: () => {
      mic.stop();
      player.destroy();
    },
    onStateChange: () => {
      // socket.status and socket.transcript update immutably on every turn
      console.log(socket.status, socket.transcript);
    },
  });

  await mic.start((base64Pcm) => socket.sendAudioChunk(base64Pcm));
}

export function endVoiceSession(): void {
  // Triggers a spoken farewell via TerminateGate before closing with 1000
  socket.requestGracefulTermination();
}
```

## 2. Upgrade to a talking video avatar

To stream a real-time talking avatar instead of raw PCM:

1. Request **only** `genai.ModalityVideo` (requesting `AUDIO` and `VIDEO`
   together fails with `1007`; audio is muxed inside the fMP4 stream).
2. Provide `AvatarConfig` (either a preset `AvatarName` or `CustomizedAvatar`
   with a `9:16` PNG/JPEG `ImageData` anchor at `704x1280` or higher).
3. Switch `BridgeConfig.Mode` to `livebridge.ModeAvatar`—`Bridge` automatically
   sniffs `ftyp`/`avcC` boxes from the first fragment via `SniffMP4` and emits
   `media_config` with the exact codec string before streaming binary fMP4.

### Backend config diff

```go
liveCfg := &genai.LiveConnectConfig{
  ResponseModalities: []genai.Modality{genai.ModalityVideo},
  AvatarConfig:       &genai.AvatarConfig{AvatarName: "Kira"},
  SpeechConfig: &genai.SpeechConfig{
    VoiceConfig: &genai.VoiceConfig{
      PrebuiltVoiceConfig: &genai.PrebuiltVoiceConfig{VoiceName: "Kore"},
    },
  },
  InputAudioTranscription:  &genai.AudioTranscriptionConfig{LanguageCodes: []string{"en-US"}},
  OutputAudioTranscription: &genai.AudioTranscriptionConfig{LanguageCodes: []string{"en-US"}},
}

bridge := livebridge.NewBridge(r.Context(), ws, upstream, livebridge.BridgeConfig{
  Mode:            livebridge.ModeAvatar,
  Model:           "gemini-3.8-live",
  Location:        livebridge.DefaultLocation,
  GreetingPrompt:  "Say hello and introduce yourself.",
  EmitSessionInfo: true,
})
```

### Browser video binding (`Fmp4Player`)

```ts
import { Fmp4Player, LiveSocketClient } from './lib/live';

const videoEl = document.querySelector('video')!;
const fmp4 = new Fmp4Player({
  onFirstChunk: () => videoEl.classList.add('ready'),
});
fmp4.attach(videoEl);

const socket = new LiveSocketClient();
socket.connect({
  endpoint: '/ws',
  onMediaConfig: (msg) => {
    if (msg.mimeType === 'video/mp4' && typeof msg.codecs === 'string') {
      fmp4.setCodec(msg.codecs);
    }
  },
  onBinaryFrame: (fragment) => fmp4.appendChunk(new Uint8Array(fragment)),
  onInterrupted: () => fmp4.flushAndAbort(),
  onDisconnected: () => fmp4.destroy(),
});
```

## 3. Add server-side function calling

Register tools on a `livebridge.FuncRegistry` and attach a `ToolRunner` to
`BridgeConfig.Tools`. Every tool executes off the `Session.Receive()` goroutine
with its own cancelable `context.Context`. If the user barges in while a tool
is running, `ToolRunner` cancels `ctx` on `ToolCallCancellation` and drops stale
results automatically.

```go
reg := livebridge.NewFuncRegistry()
reg.Register(
  &genai.FunctionDeclaration{
    Name:        "lookup_service_status",
    Description: "Returns current health for an internal service.",
    Parameters: &genai.Schema{
      Type: genai.TypeObject,
      Properties: map[string]*genai.Schema{
        "service": {Type: genai.TypeString, Description: "Service name"},
      },
      Required: []string{"service"},
    },
  },
  func(ctx context.Context, args map[string]any) (map[string]any, error) {
    svc, _ := args["service"].(string)
    // Respect ctx.Done() for external RPCs or subprocesses so barge-in cancels cleanly.
    select {
    case <-ctx.Done():
      return nil, ctx.Err()
    default:
    }
    return map[string]any{
      "service": svc,
      "status":  "healthy",
      "title":   "Service Status",
      "summary": svc + " is healthy (p99 42 ms)",
    }, nil
  },
)

liveCfg.Tools = []*genai.Tool{{FunctionDeclarations: reg.Declarations()}}

tools := livebridge.NewToolRunner(livebridge.ToolRunnerConfig{
  Registry: reg,
})
```

Pass `Tools: tools` in `BridgeConfig`. On completion, `ToolRunner` sends the
`FunctionResponse` upstream **and** forwards a `{"type": "tool_call", "id",
"name", "args", "result"}` JSON event to the browser, which `LiveSocketClient`
parses into a `TranscriptItem` (`type: 'tool'`) automatically. See
[`examples/local-code-assistant/session.go`](../examples/local-code-assistant/session.go)
for a complete multi-tool example.

## 4. Relay browser & WebMCP page tools with visual snapshots

When tools need browser state—such as editing a `<canvas>`, opening a file
picker, or exposing capabilities to Chrome's WebMCP (`document.modelContext`)
API—enable `AllowPageRelay: true` on `ToolRunner` and host tools in the page
with `WebmcpToolHost`.

### Browser (`tools.ts`)

```ts
import {
  LiveSocketClient,
  WebmcpToolError,
  WebmcpToolHost,
} from './lib/live';

const host = new WebmcpToolHost(({ signal }) => ({ signal }));

host.register([
  {
    name: 'draw_badge',
    description: 'Draws a labeled badge on the studio canvas.',
    inputSchema: {
      type: 'object',
      properties: { label: { type: 'string' } },
      required: ['label'],
    },
    // Coalesce identical in-flight calls so interactive UI never opens twice
    coalesceInFlight: true,
    async execute(args, { signal }) {
      const label = String(args.label ?? '').trim();
      if (!label) throw new WebmcpToolError('label is required');
      if (signal.aborted) throw new DOMException('Aborted', 'AbortError');

      const jpegDataUrl = renderBadgeAndCaptureJpeg(label);
      return {
        result: { status: 'drawn', label },
        imageDataUrl: jpegDataUrl,
      };
    },
  },
]);

// Refuse to connect if another script on the page collided with our tool names
if (host.diagnostics.conflicts.length > 0) {
  throw new Error(`Tool conflict: ${host.diagnostics.conflicts.join(', ')}`);
}

const inFlight = new Map<string, AbortController>();
const socket = new LiveSocketClient();

socket.connect({
  endpoint: '/ws/live',
  initialPayload: { tools: await host.list() },
  onCustomMessage: async (msg) => {
    if (msg.type === 'tool_call') {
      const id = String(msg.id);
      const name = String(msg.name);
      const args = (msg.args as Record<string, unknown>) ?? {};
      const ac = new AbortController();
      inFlight.set(id, ac);

      const started = performance.now();
      const out = await host.callWithOutput(name, args, ac.signal, 'live');
      if (ac.signal.aborted || !inFlight.delete(id)) return;

      socket.sendToolResult(id, name, out.result, {
        imageDataUrl: out.imageDataUrl,
        execMs: Math.round(performance.now() - started),
      });
    } else if (msg.type === 'tool_call_cancellation') {
      for (const id of (msg.ids as string[]) ?? []) {
        inFlight.get(id)?.abort();
        inFlight.delete(id);
      }
    }
  },
});
```

### Backend (`ToolRunner` with `AllowPageRelay` & `SeeVisualResults`)

```go
tools := livebridge.NewToolRunner(livebridge.ToolRunnerConfig{
  AllowPageRelay:   true,
  SeeVisualResults: true, // Sends imageDataUrl via {Video: Blob} before SendToolResponse
  EmitTiming:       true, // Emits {"type": "tool_timing", "roundTripMs", "execMs"}
})
```

When `SeeVisualResults` is `true`, `ToolRunner` validates any returned PNG/JPEG
data URL and streams it upstream via `SendRealtimeInput({Video: ...})` _before_
sending `SendToolResponse`, allowing the model to inspect the updated visual
artifact while speaking its reply.

## 5. Broadcast background alerts safely

To let background watchers (SSE streams, webhook receivers, build monitors)
proactively notify every open voice session:

### Backend (`AlertBus` + `FormatUntrustedAlert`)

`AlertBus` buffers up to `maxBacklog` alerts while zero tabs are open, waits
until `SetupComplete` (and the greeting prompt) finishes before flushing the
backlog to the first subscriber, and fans out without blocking across multiple
concurrent tabs:

```go
// Shared across HTTP handlers and background watchers:
alertBus := livebridge.NewAlertBus(16)

// Inside your background watcher goroutine:
alertBus.Publish(livebridge.Alert{
  ID:     "deploy-42",
  Source: "cloud-deploy",
  Type:   "rollout_failed",
  Title:  "Staging rollout failed",
  Text:   untrustedLogSnippet, // May contain arbitrary user/commit text
})

// Inside your WebSocket handler per session:
alerts, unsubscribe := alertBus.Subscribe()
defer unsubscribe()

bridge := livebridge.NewBridge(r.Context(), ws, upstream, livebridge.BridgeConfig{
  Mode:   livebridge.ModeAudio,
  Alerts: alerts,
  FormatAlert: func(a livebridge.Alert) (string, any) {
    prompt := livebridge.FormatUntrustedAlert(
      "Briefly summarize this operational alert for the user in one sentence.",
      map[string]string{"source": a.Source, "event": a.Type, "title": a.Title},
      a.Text,
      800,
    )
    browserCard := map[string]any{
      "type":    "proactive_alert",
      "id":      a.ID,
      "source":  a.Source,
      "summary": a.Title,
    }
    return prompt, browserCard
  },
})
```

If your watcher uses a custom domain struct instead of `livebridge.Alert`, use
the generic `livebridge.NewAlertBusOf[MyEvent](16)`.

### Browser (`ChimeSynth` + `deferPlayback`)

Play a gentle, zero-asset Web Audio cue (`'soft'`, `'subtle'`, or `'off'`) when
`proactive_alert` arrives, and defer incoming speech by the chime duration so
the voice never talks over the tone:

```ts
import { ChimeSynth, LiveSocketClient, PcmPlayer } from './lib/live';

const player = new PcmPlayer();
const chime = new ChimeSynth('soft');
const socket = new LiveSocketClient();

socket.connect({
  endpoint: '/ws/live',
  onProactiveAlert: (alert) => {
    player.init(24000);
    if (player.context) {
      const cueSeconds = chime.playAmbientCue(player.context);
      player.deferPlayback(cueSeconds);
    }
    console.log('Alert:', alert.summary);
  },
});
```

## 6. Reuse `livebridge` in a standalone Go module

Applications inside the root module (`gemini-live-studio`) import
`gemini-live-studio/livebridge` directly. Standalone Go modules—such as
[`examples/local-code-assistant/`](../examples/local-code-assistant/)—keep their
own self-contained `go.mod` without relative `replace` directives so they can be
copied out or containerized independently:

1. Copy `livebridge/*.go` into `<your-app>/internal/livebridge/` and import
   `<your-module>/internal/livebridge`.
2. Within this repository, run `make sync-livebridge` after editing
   `livebridge/*.go` to synchronize standalone copies automatically (`make lint`
   verifies byte-for-byte parity).
