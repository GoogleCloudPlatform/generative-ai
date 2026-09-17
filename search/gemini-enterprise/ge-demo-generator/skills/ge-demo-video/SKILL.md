---
name: ge-demo-video
description: Records, edits, and delivers automated executive demo videos for agents deployed to Gemini Enterprise. Verifies typography fonts across all languages, connects to live Chrome via CDP (:9222) with automatic display/xvfb adaptation, automatically discovers and applies customer logo & corporate palette (default ON, --no-brand to opt out), enforces strict zero-mock live recording of the deployed agent chat interface, applies modern SaaS video styling in Remotion with dynamic zoom/pan and 4x wait-time acceleration, synthesizes Google Cloud TTS neural narration with synchronized subtitles (pure speech narration, optional ambient BGM), and delivers the rendered MP4 to the demo's Google Drive folder. Also triggered by /ge-demo-video.
metadata:
  author: Google Cloud Customer Engineering
  version: 2.2.0
---

# GE Demo Video Generator Skill (v2.2.0)

Automates the end-to-end production and delivery of professional **90–120s executive highlight reel demo videos** showcasing autonomous AI agents deployed on **Gemini Enterprise**.

---

## 🌟 Core Architectural Invariants

1. **Authentic Screen Recording Exclusively (Zero-Mock Invariant)**:
   - The skill **strictly forbids** synthetic mock video generation, mock SVG frames, and fallback presentation slides.
   - Video capture is executed directly against the live Gemini Enterprise chat session (`https://vertexaisearch.cloud.google.com/home/cid/.../r/agent/.../session/-`) of the deployed agent via Chromium DevTools Protocol (CDP, port 9222).
   - The chat interface DOM elements (`div.ProseMirror`, `div[contenteditable="true"]`, or shadow DOM chat inputs) must be probed and verified before recording starts.

2. **Universal Multi-Language Font Verification & Provisioning**:
   - Before recording or rendering, the skill verifies that the necessary typography fonts for the target locale (e.g., Japanese CJK for `ja-JP`, Simplified/Traditional Chinese for `zh`, Korean Hangul for `ko`, Arabic for `ar`, Thai for `th`, Devanagari for `hi`, etc.) are installed on the host environment.
   - If missing, the automated font engine (`ensure_fonts.py`) installs them via system packages (`apt-get`) or downloads Google Noto font assets directly into `~/.local/share/fonts/` followed by `fc-cache` refresh, eliminating tofu (`□`) characters.
   - Remotion composition incorporates Google Web Fonts as a secondary defensive layer.

3. **Mandatory Pre-Recording Demonstration Plan & Interactive Approval Gate**:
   - Before executing any recording commands (`generate_demo_video.py`), the agent **MUST ALWAYS** formulate and present the proposed demo plan to the user for review.
   - In interactive agent environments (e.g. when supported by tools like `ask_question`), the agent **MUST ALWAYS** prompt the user to obtain explicit approval or modifications.
   - No recording or video compilation commands may be executed without explicit user sign-off.

4. **Automated Display & Browser Environment Adaptation**:
   - Chrome launches with a graphical window (`--no-headless`) by default on port 9222 with persistent profile `~/.config/ge-demo-video/chrome-profile`.
   - If executed in a remote terminal or SSH session lacking a display (`DISPLAY` unset), the engine automatically wraps browser launch with `xvfb-run` to maintain authentic DOM rendering and screencast streaming.

---

## 🚀 Execution Lifecycle & Step-by-Step Workflow

```
[Phase 1: Dynamic Demo Plan Formulation]
  ↓ Read .env, target company, role, language, session URL, and 7 demo prompts
[Phase 2: Interactive Plan Presentation & User Approval Gate (ask_question)]
  ↓ Explicit approval received
[Phase 3: Multi-Language Font Verification & Provisioning (ensure_fonts.py)]
  ↓ Host fonts verified / auto-installed, Remotion WebFonts loaded
[Phase 4: Browser Session Verification & Interactive Authentication Handoff]
  ↓ Live Chrome CDP (port 9222) verified, chat input DOM element ready
[Phase 5: Automated Execution, TTS Synthesis & Remotion Video Rendering]
  ↓ Google Cloud TTS, Bézier typing jitter, 4x fast-forward thinking, dynamic camera
[Phase 6: Google Drive Delivery & Local Staging]
```

### Phase 1 & 2: Mandatory Demonstration Plan & Interactive Approval Gate

1. **Pre-Flight Verification & Demonstration Plan Formulation**:
   Dynamically inspect environment and execute pre-flight destination verification:
   - **Company Name**: `${COMPANY_NAME}` (e.g. `Acme Corp`)
   - **Agent Persona**: `${DEMO_DISPLAY_NAME}` or `${AGENT_ROLE}` (e.g. `Supply Chain Director`)
   - **Target Locale & Voice**: `${LANG}` (e.g. `en-US` with Studio Neural2 / Chirp3-HD voice, or `ja-JP`, `de-DE`, etc.)
   - **Session URL**: `${GE_SESSION_URL}` or derived from `CONFIG_ID` and `AGENT_ID`
   - **3-Tier Storage Delivery Hierarchy & Destination Pre-Flight**:
     - **Tier 1 (Primary)**: Host Operator Drive (via `gdrive` CLI if configured and authorized)
     - **Tier 2 (Secondary)**: Deploy Tenant Drive (via `gcloud` ADC credentials of the deploying user/service account)
     - **Tier 3 (Fallback)**: Cloud Storage (`gs://<project-id>-ge-demo-artifacts/` or custom `--gcs-bucket`)
     - **Confirmed Destination**: Locked in prior to presenting the plan (Tier 1 if ready, else Tier 2, else Tier 3 GCS)

2. **Present Structured Demo Plan Table**:
   Output a comprehensive markdown table and verified delivery parameters in chat:

   | Scene # | Scenario / Topic | Prompt Text | Visual & Camera Highlights | Voice Narration (3-Part: Purpose, Results & Benefits) |
   |---|---|---|---|---|
   | **Intro** | Branded Welcome | *(None)* | Google Cloud 4-color strip, title card with company & persona badge | Executive intro greeting (~10s) |
   | **Agenda** | Walkthrough Roadmap | *(None)* | Dedicated `AgendaCard` with 5 scenarios & icons, 180px bottom margin | Roadmap overview (~16s) |
   | **Scene 1** | Welcome & Situational Briefing | `<Prompt 1 from Playbook>` | 1.50x typing zoom, welcome card reveal | Intent, key capabilities, operational value (~24s) |
   | **Scene 2** | Catalog & Metadata Discovery | `<Prompt 2 from Playbook>` | 1.50x typing zoom, shadow DOM smooth scrolling | Intent, catalog structure, eliminating manual lookup (~27s) |
   | **Scene 3** | Cross-Source Anomaly WOW | `<Prompt 3 from Playbook>` | 1.50x typing zoom, 4x fast-forward thinking, A2UI table zoom | Intent, anomaly detection findings, preventing losses (~28s) |
   | **Scene 4** | Workflow Action & Approval | `<Prompt 4 from Playbook>` | 1.50x typing zoom, 1.45x button close-up zoom on click | Intent, one-click execution approval, cycle time reduction (~28s) |
   | **Scene 5** | Operational Summary & Handover | `<Prompt 7 from Playbook>` | 1.50x typing zoom, rating button delta verification | Intent, structured handover report, operational continuity (~27s) |
   | **Outro** | Next Steps & CTA | *(None)* | Google Cloud 4-color strip, outro card with Next Steps CTA | Executive closing & call-to-action (~10s) |

   Display verified pre-flight demonstration plan card:
   ```
   ================================================================================
   🎬 PRE-RECORDING DEMONSTRATION PLAN & PRE-FLIGHT VERIFICATION
   ================================================================================
   🏢 Company Name           : <Company Name>
   🤖 Agent Persona          : <Agent Role>
   🤖 GE Agent Name          : <GE Agent Display Name>
   🔗 GE Direct Agent Link   : <Direct Chat Session URL>
   🌐 Target Locale          : <Target Locale (e.g. en-US, ja-JP)>
   🎙️ Selected Neural Voice  : <Selected Cloud TTS Voice>
   💬 Subtitle Mode          : Clean Lower-Third (Synchronized)
   🎼 Ambient BGM & Ducking  : Disabled (Pure Speech Narration)

   📦 Delivery Destinations (3-Tier Storage Hierarchy):
      • Tier 1 (Primary)     : Host Operator Drive (<account>)
      • Tier 2 (Secondary)   : Deploy Tenant Drive (<deploy_account>)
      • Tier 3 (Fallback)    : Cloud Storage (gs://<bucket>/)

   🔒 Confirmed Destination  : <Tier 1 / Tier 2 / Tier 3 Destination>
   ================================================================================
   ```

   *If Pre-Flight indicates expired credentials (`reauth_required`), append notice:*
   ```
   ⚠️ Note: Credentials expired for <account>. Run to re-authenticate:
      gcloud auth login <account> --enable-gdrive-access [--no-launch-browser]
   ```

   *The pipeline prints the exact command for this host. On a host with no local
   browser it appends `--no-launch-browser`; quote it verbatim rather than
   reconstructing it, because the plain form opens nothing and looks like a hang.*

3. **Mandatory `ask_question` Approval Gate**:
   Execute `ask_question` with the following selectable options.
   *(If `reauth_required` is detected on Tier 1, prioritize the single-click re-authentication action)*:
   - *(If reauth required)*: `(Recommended) Re-authenticate Google account now (Agent will run the re-authentication command the pre-flight printed)`
   - `(Recommended) Approve and proceed with video generation as planned`
   - `Modify demo prompts / Select specific scenarios`
   - `Change language / voice settings (e.g. ja-JP / en-US)`
   - `Enable ambient background music (--enable-bgm)`
   - `Disable voice narration (--no-narration) or subtitles (--no-subtitles)`
   - `Change Google Drive / GCS delivery target`
   - `Cancel video generation`

   *If the user selects re-authentication, execute the login command directly via `run_command` and re-verify pre-flight before continuing.*
   *If the user requests modifications, update the plan and prompt again. Never start recording without explicit user approval.*

---

### Phase 3: Multi-Language Font Verification

Before launching recording or rendering, run font verification to eliminate tofu (`□`) characters:

```bash
python3 skills/ge-demo-generator/templates/video/scripts/ensure_fonts.py --lang "<LANG>"
```

The script automatically detects missing typography (Kanji/Kana, Hanzi, Hangul, Arabic, Thai, Devanagari) and installs the required Noto font family via system packages or downloads them directly to `~/.local/share/fonts/` followed by `fc-cache -fv`.

---

### Phase 4: Browser Session Verification & Authentication Handoff

1. **Port 9222 & Session URL Check**:
   The engine checks if Chrome CDP port 9222 is active. If not listening, it auto-launches Chrome pointing directly to the agent session URL:
   - Default: GUI Chrome (`--no-headless`) with persistent profile `~/.config/ge-demo-video/chrome-profile`.
   - Headless / SSH environments: Auto-detected and launched under `xvfb-run` to provide a full virtual display buffer.

2. **Authentication Step-Up Handoff**:
   If the browser encounters the Google login screen (`accounts.google.com`):
   - The skill **strictly halts** (never falls back to mock).
   - In interactive agent environments, prompt the user (e.g. via `ask_question` or interactive modal):
     > *"Chrome window has been launched. Please complete Google Account login (and 2FA) in the opened browser window, then select 'Login Complete'."*
   - Once confirmed, the engine re-probes the session URL and verifies that the chat input area is active.

3. **Chat Interface Readiness Probe**:
   The engine checks for `div.ProseMirror`, `div[contenteditable="true"]`, or textarea elements (including recursive shadow DOM search). Once verified, live recording proceeds.

---

### Phase 5: Automated Execution & Video Composition

The pipeline executes through `scripts/generate_demo_video.py`.

> **Working directory**: run this, and every other command in this skill, from
> the repository root. Every path here is relative to it, and so are the outputs:
> `./deliverables/` and `./deliverables/delivery_report.json` are written relative
> to the working directory, not to the script.

```bash
# Standard Production Run
python3 scripts/generate_demo_video.py \
  --company "<Company Name>" \
  --role "<Agent Persona>" \
  --lang "<Locale (e.g. ja-JP, en-US)>" \
  --session-url "<Direct Chat Session URL>"

# Optional Flags:
# --enable-bgm        : Enables ambient background music with dynamic ducking
# --no-narration     : Generates video without voice track
# --no-subtitles     : Generates video without subtitle overlays
# --drive-account    : Overrides destination Google Drive account
```

The process exit code is the delivery verdict: `0` delivered, `3` Drive was
expected and Cloud Storage caught the fall, `1` nothing accepted the video. See
Phase 6.

Key execution features:
- **Zero Dead Air**: Voice narration begins immediately at scene start, introducing operational intent during prompt typing.
- **1.50x Prompt Typing Zoom**: Camera zooms into prompt input field `(960, 920)` with natural human typing jitter.
- **⏩ 4x Fast-Forward Thinking**: Accelerates model thinking and tool execution with speedup badge and explanatory narration.
- **1.45x Action Button Zoom**: Dynamically identifies action buttons (e.g. "Execute Reallocation Now"), zooms in, and executes the click.
- **Synchronized Response Scrolling**: Traverses shadow DOM `.chat-mode-scroller` to smoothly scroll tall data tables and A2UI cards.

---

### Phase 6: Delivery to Google Drive / GCS & Local Staging

1. **Delivery Account Precedence (Tier 1 / Tier 2 target)**:
   The video must land in the **same Drive as the rest of the demo** — the PDFs,
   spreadsheets and scans that `generate_and_upload_external_files.py` already
   uploaded. The account is resolved in this order:
   1. Explicit `--drive-account` or `DRIVE_ACCOUNT` (from the environment or `.env`).
   2. `owner_account` in the demo's `drive_upload_summary.json`, if that account
      still has credentials on this host. This is the Drive the demo's own files
      are in.
   3. The active `gcloud` account — the identity the demo was deployed with.
   4. An account whose local part matches the host login name.
   5. Any other credentialed non-service account.
   6. The active account, or `default`.

   > The host login match used to sit near the top, which sent the video to a
   > corporate account under forced re-authentication while the demo itself was
   > in a different tenant's Drive. One demo, two Drives, and a re-authentication
   > prompt for an account nobody asked for.

2. **3-Tier Fallback Storage Delivery Mechanism**:
   - **Tier 1: Host Operator Drive**:
     Uploaded via `gdrive` CLI using operator user credentials if configured. Saves to folder `GE Demo - <Company>` with owner-only private permissions (or `--share-public` if explicitly requested).
   - **Tier 2: Deploy Account Drive**:
     If Tier 1 is unavailable or unconfigured, falls back to Google Drive API using the deploy user/service account ADC credentials (`gcloud auth application-default print-access-token` / service account key).
   - **Tier 3: Google Cloud Storage (GCS) Fallback**:
     If Drive upload cannot proceed or fails, securely delivers the video to Google Cloud Storage (`gs://<project-id>-ge-demo-artifacts/videos/` or custom `--gcs-bucket`), generating an authenticated or signed URL (`https://storage.cloud.google.com/<bucket>/...`).
3. **Local Staging Guarantee**:
   - The final video is **always staged locally** in `./deliverables/[Demo-Video]_<Company>_-<Role>.mp4` regardless of remote upload status.
4. **Read the delivery verdict — never assume success**:
   - Delivery writes `./deliverables/delivery_report.json` and exits with a
     distinct code. The agent **MUST** read one of the two before reporting an
     outcome:

     | Exit code | `headline` means | Agent action |
     |---|---|---|
     | `0` | Delivered to Drive, or Cloud Storage was the intended destination, or the upload was skipped on request | Report the destination URL |
     | `3` | **Cloud Storage caught the fall — Drive was expected and did not accept the upload** | Fire the recovery gate in step 6 |
     | `1` | No destination accepted the video | Report the local path and the error |

   - The report carries `delivery_tier`, `target_account`, `target_account_reason`,
     `drive_url`, `gcs_uri`, `headline` and `action_required`.
   - Exit code `3` is **not** a success. The video exists, but it is not where the
     rest of the demo is.
5. **Present Output**:
   - Display local deliverable path, remote delivery destination (Tier 1 Drive / Tier 2 Drive / Tier 3 GCS), the account it went to and why, video duration, and resolution (1080p 30fps).
6. **Automated Post-Generation Interactive Delivery Recovery Gate**:
   - **Trigger**: delivery exit code `3`, or `delivery_report.json` reporting a
     non-empty `action_required`, or `tier_1_status: reauth_required`.
   - **Zero Copy-Paste Mandate**: If the video was successfully generated and staged in `./deliverables/[Demo-Video]_<Company>_-<Role>.mp4` but Google Drive delivery failed or was skipped due to expired OAuth credentials (`reauth_required`), the agent **MUST NEVER** ask the user to manually copy and paste bash upload commands.
   - **Interactive Recovery via `ask_question`**: The agent **MUST IMMEDIATELY** invoke `ask_question` offering automated re-authentication and recovery upload:
     - `(Recommended) Authenticate now and upload the generated video to Google Drive`
     - `Keep local deliverable only (and Cloud Storage if uploaded)`
   - **Single-Click Automated Execution**: Upon user selection of the recommended option, the agent automatically executes:
     1. Re-authentication via `run_command`. Use the command printed by the
        pipeline verbatim — on a host with no local browser (remote shell, Cloud
        Shell, no `DISPLAY`) it carries `--no-launch-browser`, and without that
        flag the command waits on a browser that will never open:
        ```bash
        gcloud auth login <account> --enable-gdrive-access [--no-launch-browser]
        ```
     2. Standalone Drive delivery via `run_command`, from the repository root:
        ```bash
        python3 skills/ge-demo-generator/templates/video/scripts/upload_to_drive.py \
          --video "./deliverables/[Demo-Video]_${COMPANY}_-_${ROLE}.mp4" \
          --company "${COMPANY}" \
          --role "${ROLE}" \
          --drive-account "${DRIVE_ACCOUNT}"
        ```
        Omit `--drive-account` to let the precedence in step 1 pick the Drive the
        demo already lives in.
     3. Present the confirmed Google Drive file URL and folder URL directly in the chat response.

---

## 🛠️ CLI Options Reference (`generate_demo_video.py`)

| Option | Default | Description |
|---|---|---|
| `--session-url`, `--ge-url` | (from .env) | Direct Gemini Enterprise chat session URL (Required) |
| `--env-file` | `.env` | Path to environment configuration file |
| `--cdp-url` | `http://localhost:9222` | Chrome remote debugging endpoint |
| `--company` | (from .env) | Company name override |
| `--role` | (from .env) | Agent persona / role override |
| `--agent-name` | (from .env) | Gemini Enterprise agent display name override |
| `--lang` | (auto-detected) | Voice & subtitle language (`ja-JP`, `en-US`, `de-DE`, etc.) |
| `--project` | (from .env) | Google Cloud project ID for TTS quota and GCS fallback |
| `--deploy-account` | (auto-detected) | Target deploy Google Cloud account for Tier 2 Drive |
| `--gcs-bucket` | (auto-detected) | Target Google Cloud Storage bucket for Tier 3 delivery |
| `--mock` | `false` | Enable synthetic mock mode for test and offline pipeline execution |
| `--no-headless` | `true` | Launch Chrome with visible GUI window (Default) |
| `--headless` | `false` | Launch Chrome in headless mode |
| `--enable-bgm`, `--bgm` | `false` | Enable ambient background music with dynamic ducking |
| `--no-brand`, `--disable-brand` | `false` | Disable automatic customer logo and corporate palette discovery (default: branding enabled) |
| `--brand-domain` | (auto-detected) | Custom domain override for logo and corporate palette discovery |
| `--no-narration` | `false` | Disable voice narration audio tracks |
| `--no-subtitles` | `false` | Disable subtitle overlays |
| `--skip-recording` | `false` | Reuse existing browser recording from working directory |
| `--skip-tts` | `false` | Reuse existing TTS audio from working directory |
| `--skip-drive` | `false` | Skip Google Drive upload (save to `./deliverables/` only) |
| `--drive-account` | (auto-detected) | Target Google Drive account override (Tier 1) |
| `--drive-folder` | `GE Demo - <Company>` | Google Drive folder name override |
| `--share-public` | `false` | Enable public reader link sharing |
| `--output` | `./output/demo_video/rendered_demo_video.mp4` | Final MP4 output path |

### Delivery environment variables

| Variable | Effect |
|---|---|
| `DRIVE_ACCOUNT` | Highest-precedence delivery account (same as `--drive-account`) |
| `GE_DRIVE_SUMMARY` | Explicit path to the demo's `drive_upload_summary.json`, when it is not beside the deliverables |
| `GE_NONINTERACTIVE` / `CI` | Declines every re-authentication prompt instead of waiting for an answer nobody is there to give |
| `SKIP_VIDEO_DRIVE_UPLOAD` | Skips Drive delivery for the video only (does not affect the demo's other files) |
