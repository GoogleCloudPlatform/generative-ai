# Documentation

Documentation for **Gemini Live Studio**, its reusable **`livebridge`** (Go) +
**`src/lib/live/`** (TypeScript) voice-agent kit, and its two reference
applications, organized following [Diataxis](https://diataxis.fr/):

## Diataxis map

| Quadrant                                | Document                                                            | What you will find                                                                                                                       |
| :-------------------------------------- | :------------------------------------------------------------------ | :--------------------------------------------------------------------------------------------------------------------------------------- |
| **Tutorials** _(Learning-oriented)_     | [Quickstart](../README.md#quickstart) & [User Guide](user_guide.md) | Installing, authenticating, and running your first Avatar Studio or Live Audio & Vision session                                          |
| **How-To Guides** _(Task-oriented)_     | [Building Voice & Avatar Agents](building-with-livebridge.md)       | Ready-to-use Go & TypeScript recipes for voice sessions, talking avatars, server tools, WebMCP page tools, and background alerts         |
| **Explanation** _(Understanding)_       | [Developer Guide](developers_guide.md)                              | Why the Switchboard Proxy and `livebridge` exist, Gemini Live API sharp edges solved automatically, and reference application comparison |
| **Reference** _(Specifications & APIs)_ | [Live Wire Protocol & Kit Reference](live-wire-protocol.md)         | Canonical WebSocket JSON/binary framing, RFC 6455 close codes, Go `livebridge` types, and TypeScript `src/lib/live/` APIs                |
| **Reference** _(UI & Design System)_    | [Frontend Components](frontend-components.md)                       | Lit component tiers, Light DOM conventions, design tokens and themes, accessibility, and browser tests                                   |

## Architecture diagram

- [`architecture.png`](architecture.png) — rendered from [`architecture.dot`](architecture.dot)

## Reference applications

1. **[Gemini Live Studio](../README.md)** (repository root) — Dual-mode talking
   avatar (`/ws`, fMP4 MSE) and live audio & vision (`/ws/live`, 24 kHz PCM +
   1 FPS camera/screen) studio with custom `9:16` 2K avatar synthesis.
2. **[Local Code Assistant](../examples/local-code-assistant/README.md)**
   ([`examples/local-code-assistant/`](../examples/local-code-assistant/)) —
   Standalone voice-and-avatar coding agent with server-side filesystem and
   Graphviz tools, dual-channel UI cards, and portable `.skill` packaging.
