# GEBE Demo Generator

A standalone Google Apps Script web app that generates Google Workspace demo data
(Docs, Sheets, Slides, optional Office/PDF exports, and AI-generated images) directly
into the **accessing user's own My Drive**, organized under a single `My Demos` folder
with a per-demo Guide Doc. Built for Gemini Enterprise Business Edition (GEBE), which
does not support custom ADK agents.

This is a **separate GAS project** that lives as a subdirectory of the GE Demo Generator
repo (same pattern as `experimental/mcp-importer/`). It has its own `scriptId` and
deployment; the root project's `clasp push` does not include it.

## How it works

1. **Plan** (`planGEBEDemo`) — one Gemini call returns the folder name, demo prompts, and
   the file list with content, in the user's language, anchored to today's date.
2. **Folder** (`createDemoFolder`) — find-or-create `My Demos`, then a per-demo subfolder.
3. **Generate** (`generateOneFile`, called once per file from the frontend) — creates each
   Doc/Sheet/Slide/image in the subfolder; attaches Office/PDF exports when requested.
   Per-file calls keep each execution well under the 6-minute GAS limit.
4. **Finalize** (`finalizeDemo`) — writes the `00_Demo Guide` Doc (overview + prompts +
   delete instructions).

## Setup

1. Create the Google Cloud-backed Apps Script project and set `scriptId` in `.clasp.json`
   (or run `clasp create` from inside this directory).
2. From inside `gebe-demo-generator/`, run `clasp push` (uses the local `.clasp.json`,
   not the repo root one).
3. Set Script Properties via the editor: run `initializeProject(projectId)` — or set
   `PROJECT_ID` manually. Optional: `LOCATION` (default `global`), `MODEL`
   (default `gemini-3.5-flash`).
4. Deploy as a Web App with **Execute as: User accessing the web app** and **Access: anyone
   in your domain** (matches `appsscript.json`).
5. Each user grants Drive/Docs/Sheets/Slides + Vertex AI Agent Platform consent on first open, and needs
   `roles/aiplatform.user` on `PROJECT_ID`.

## Files

- `appsscript.json` — manifest (scopes, Drive v3 + Sheets v4 advanced services, `USER_ACCESSING`).
- `Code.gs` — backend (planning, generation, export, guide doc).
- `index.html` — single-page frontend (inputs, progress, result).
- `SetupError.html` — shown by `doGet` when Script Properties are missing.
