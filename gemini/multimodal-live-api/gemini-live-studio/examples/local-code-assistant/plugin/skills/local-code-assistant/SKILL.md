---
name: local-code-assistant
description: Spins up a local Gemini Live Avatar code assistant with server-side function calling (filesystem inspection and Graphviz diagramming) and Google Search. Use when the user requests an interactive voice session to explore, explain, or diagram their codebase.
license: Apache-2.0
compatibility: Requires Go 1.26+, Google Cloud Application Default Credentials (us-central1), and optional Graphviz CLI (dot).
metadata:
  author: ghchinoy
  version: "0.3.0"
---

# Local Code Assistant

This skill spins up a dedicated local Go server with an embedded Lit WebComponent UI that acts as a standalone Gemini Live Avatar. The avatar has been explicitly granted Server-Side Function Calling capabilities (`list_directory`, `read_file`, and Graphviz `generate_diagram`) as well as Google Search, allowing it to explore your workspace, look up documentation, generate architecture diagrams, and answer questions about it verbally.

## Usage

When requested to invoke the Local Code Assistant, execute the bundled launcher script or Go server:

1. Ensure you have a `.env` file or Google Cloud Application Default Credentials (`gcloud auth application-default login`). _(Note: The Gemini Live API requires a regional endpoint, so if your location is empty or set to `global`, the server will automatically default to `us-central1`)_.
2. (Optional) If the user's request pertains to specific documentation (e.g., Gemini SDK docs, Lit, Vite), export the `AVATAR_EXTRA_CONTEXT` environment variable with URLs or summaries before running the server so the Avatar is aware of them.
3. Run the launcher script from the skill directory:

   ```bash
   scripts/launch.sh
   ```

   _Alternatively, run the app directly (from `assets/local-code-assistant` in a packed bundle, or from the example directory in the repository):_

   ```bash
   AVATAR_EXTRA_CONTEXT="Please reference https://pkg.go.dev/google.golang.org/genai" go run .
   ```

4. Instruct the user to open their browser to `http://localhost:8081` and click **"Start Assistant Session"** to begin talking to their local code assistant!
