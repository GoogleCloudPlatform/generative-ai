# Local Code Assistant Plugin

An **Agent Plugins v1.0.0 Specification** package that equips AI coding agents with a real-time, voice-and-avatar codebase exploration assistant built on the **Gemini Live Bidi API**.

---

## Capabilities

- **Interactive Live Voice Avatar**: Dual-channel Lit WebComponent console featuring talking avatar video streaming (or audio-reactive glowing orb) driven by Gemini Live (`gemini-3.8-live`).
- **Filesystem Inspection**: Server-side tool execution for safe directory listing (`list_directory`) and file reading with context window guardrails (`read_file`).
- **Graphviz Architecture Diagramming**: Autonomous generation and compilation of technical architecture diagrams (`generate_diagram`) served as interactive PNGs.
- **External Web Knowledge**: Integrated Google Search for up-to-date documentation and release notes.

---

## Installation & Discovery

### Via Gemini CLI (from a checkout)

```bash
gemini skills link examples/local-code-assistant/plugin/skills/local-code-assistant
```

### As a portable bundle

`make pack-skill` (from the repository root) writes
`local-code-assistant.skill`: the skill plus a copy of the app under
`assets/local-code-assistant/`, for agents that install skills from an
archive.

---

## Requirements

- **Go**: `1.26+`
- **Google Cloud SDK**: Application Default Credentials (`gcloud auth application-default login`) with access to the Gemini Live API (`us-central1`).
- **Graphviz** (Optional): `dot` command-line tool (`brew install graphviz`) for PNG rendering.

---

## License

Apache 2.0. See the repository [LICENSE](../../../LICENSE).
