#!/usr/bin/env python3
# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Top-Level Orchestrator for Gemini Enterprise Demo Video Generation.

Executes the end-to-end automated video production pipeline:
1. Browser screen recording of Gemini Enterprise Web UI via Playwright CDP.
2. Voice narration audio & subtitle timecode synthesis via Google Cloud TTS.
3. Timeline and dynamic camera manifest compilation for Remotion.
4. Programmatic video composition & rendering via Remotion.
5. Automated delivery to the demo's Google Drive folder & local deliverables.
"""

import argparse
import json
import math
import os
import shutil
import subprocess
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
VIDEO_TEMPLATE_DIR = os.path.join(REPO_ROOT, "skills/ge-demo-generator/templates/video")
VIDEO_SCRIPTS_DIR = os.path.join(VIDEO_TEMPLATE_DIR, "scripts")

# Delivery can prompt for re-authentication. Bound it so an unattended run fails
# loudly instead of hanging forever on a question nobody is there to answer.
DELIVERY_TIMEOUT_SEC = 900


def _delivery_module():
    """Imports the uploader module, or returns None if it is unavailable."""
    try:
        if VIDEO_SCRIPTS_DIR not in sys.path:
            sys.path.insert(0, VIDEO_SCRIPTS_DIR)
        import upload_to_drive
        return upload_to_drive
    except Exception:
        return None


def drive_login_hint(account: str) -> str:
    """Returns the exact re-authentication command for this host.

    Deliberately delegates to the uploader so the operator is never told to run
    a command that differs from the one the uploader itself would run. On a host
    with no local browser the plain form opens nothing and appears to hang, so
    the uploader appends --no-launch-browser there.
    """
    module = _delivery_module()
    if module is not None:
        try:
            return module.drive_login_hint(account)
        except Exception:
            pass
    return f"gcloud auth login {account or '<ACCOUNT>'} --enable-gdrive-access"



def ensure_prerequisites() -> None:
    """Ensures Python virtual environment and required libraries are ready."""
    # 1. Check if running inside .venv or if workspace has .venv
    in_venv = (sys.prefix != sys.base_prefix)
    workspace_venv_py = os.path.join(REPO_ROOT, ".venv", "bin", "python3")

    if not in_venv and os.path.exists(workspace_venv_py) and sys.executable != workspace_venv_py:
        # Re-execute with the workspace venv python
        os.execv(workspace_venv_py, [workspace_venv_py] + sys.argv)

    # 2. Check and auto-install required python libraries
    required_packages = {
        "playwright": "playwright>=1.40.0",
        "google.cloud.texttospeech": "google-cloud-texttospeech>=2.14.0",
        "google.cloud.storage": "google-cloud-storage>=2.14.0",
        "googleapiclient": "google-api-python-client>=2.100.0",
        "google.auth": "google-auth>=2.20.0",
        "PIL": "pillow>=10.0.0"
    }
    missing = []
    for mod, pkg in required_packages.items():
        try:
            __import__(mod)
        except ImportError:
            missing.append(pkg)

    if missing:
        print(f"📦 [Prerequisites] Missing Python packages detected: {missing}")
        print("   Automatically installing required packages...")
        if shutil.which("uv"):
            cmd = ["uv", "pip", "install"] + missing
        else:
            cmd = [sys.executable, "-m", "pip", "install", "--prefer-binary"] + missing
        res = subprocess.run(cmd)
        if res.returncode != 0:
            print("⚠️ Automatic package install failed. Please check network/permissions.", file=sys.stderr)
        else:
            print("✅ All required Python packages installed successfully.")


def load_env(env_file: str) -> dict:
    """Loads key-value pairs from .env file if it exists."""
    env = {}
    if os.path.exists(env_file):
        with open(env_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def resolve_session_url(args, env: dict) -> str:
    """Dynamically resolves the Gemini Enterprise chat session URL without hardcoded IDs."""
    # 1. Explicit CLI argument takes highest precedence
    session_url = args.session_url or getattr(args, "ge_url", "")
    if session_url:
        return session_url

    # 2. Direct session URL from .env or environment variable
    if env.get("GE_SESSION_URL") or os.environ.get("GE_SESSION_URL"):
        return env.get("GE_SESSION_URL") or os.environ.get("GE_SESSION_URL")

    # 3. If .env has CONFIG_ID and AGENT_ID
    if env.get("CONFIG_ID") and env.get("AGENT_ID"):
        config_id = env["CONFIG_ID"]
        agent_id = env["AGENT_ID"]
        return f"https://vertexaisearch.cloud.google.com/home/cid/{config_id}/r/agent/{agent_id}/session/-"

    # 4. Check for .ge_direct_url generated during setup/deploy
    if os.path.exists(".ge_direct_url"):
        try:
            with open(".ge_direct_url", "r", encoding="utf-8") as f:
                url = f.read().strip()
                if url.startswith("https://"):
                    return url
        except Exception:
            pass

    # 5. Dynamic Discovery via Discovery Engine API in active Google Cloud project
    project_id = env.get("PROJECT_ID") or os.environ.get("PROJECT_ID")
    if not project_id:
        res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
        project_id = res.stdout.strip()

    if project_id:
        try:
            token_res = subprocess.run(["gcloud", "auth", "print-access-token"], capture_output=True, text=True)
            token = token_res.stdout.strip()
            if token:
                import urllib.request
                for loc in ["global", "us", "eu"]:
                    engines_url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{loc}/collections/default_collection/engines"
                    req = urllib.request.Request(engines_url, headers={
                        "Authorization": f"Bearer {token}",
                        "X-Goog-User-Project": project_id
                    })
                    try:
                        with urllib.request.urlopen(req, timeout=5) as resp:
                            engines_data = json.loads(resp.read().decode("utf-8"))
                            engines = engines_data.get("engines", [])
                            for eng in engines:
                                eng_name = eng.get("name", "")
                                app_id = eng_name.split("/")[-1]
                                wc_url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{loc}/collections/default_collection/engines/{app_id}/widgetConfigs/default_search_widget_config"
                                wc_req = urllib.request.Request(wc_url, headers={
                                    "Authorization": f"Bearer {token}",
                                    "X-Goog-User-Project": project_id
                                })
                                try:
                                    with urllib.request.urlopen(wc_req, timeout=5) as wc_resp:
                                        wc_data = json.loads(wc_resp.read().decode("utf-8"))
                                        cid = wc_data.get("configId", "")
                                        if cid:
                                            ag_url = f"https://discoveryengine.googleapis.com/v1alpha/projects/{project_id}/locations/{loc}/collections/default_collection/engines/{app_id}/assistants/default_assistant/agents?pageSize=10"
                                            ag_req = urllib.request.Request(ag_url, headers={
                                                "Authorization": f"Bearer {token}",
                                                "X-Goog-User-Project": project_id
                                            })
                                            with urllib.request.urlopen(ag_req, timeout=5) as ag_resp:
                                                ag_data = json.loads(ag_resp.read().decode("utf-8"))
                                                agents = ag_data.get("agents", [])
                                                if agents:
                                                    agent_id = agents[0].get("name", "").split("/")[-1]
                                                    return f"https://vertexaisearch.cloud.google.com/home/cid/{cid}/r/agent/{agent_id}/session/-"
                                except Exception:
                                    continue
                    except Exception:
                        continue
        except Exception:
            pass

    return ""


def extract_brand_colors(image_path: str) -> tuple:
    """Extracts dominant primary and soft accent brand colors from an image using Pillow.

    Returns:
        (primary_color_hex, accent_color_hex) e.g. ("#D01020", "#F9E2E4")
    """
    try:
        from PIL import Image
        im = Image.open(image_path).convert("RGBA").resize((64, 64))
        pixels = im.load()
        w, h = im.size
        bins = {}
        for x in range(w):
            for y in range(h):
                r, g, b, a = pixels[x, y]
                # Skip transparent and near-white pixels
                if a < 128 or (r > 240 and g > 240 and b > 240):
                    continue
                key = (r // 16 * 16, g // 16 * 16, b // 16 * 16)
                max_c = max(r, g, b)
                min_c = min(r, g, b)
                sat = (max_c - min_c) / max(1, max_c)
                bins[key] = bins.get(key, 0) + (0.3 + sat)

        if bins:
            top = max(bins.items(), key=lambda x: x[1])[0]
            primary = f"#{top[0]:02X}{top[1]:02X}{top[2]:02X}"
            # Soft pastel tint for badge pill and card accents (mix with 88% white)
            ar = int(top[0] * 0.12 + 255 * 0.88)
            ag = int(top[1] * 0.12 + 255 * 0.88)
            ab = int(top[2] * 0.12 + 255 * 0.88)
            accent = f"#{ar:02X}{ag:02X}{ab:02X}"
            return primary, accent
    except Exception as e:
        print(f"⚠️ [Brand Color Extraction] Non-fatal error extracting colors: {e}", file=sys.stderr)

    return "#1A73E8", "#E8F0FE"


def discover_brand_assets(company: str, domain_slug: str, custom_domain: str, work_dir: str, remotion_public_dir: str, disable_brand: bool = False) -> dict:
    """Discovers customer logo and corporate palette from target domain.

    Enabled by default, with --no-brand / --disable-brand opt-out.
    """
    brand_config = {
        "enabled": False,
        "company": company,
        "domain": "",
        "logoFile": "",
        "primaryColor": "#1A73E8",
        "accentColor": "#E8F0FE"
    }

    if disable_brand:
        print("🎨 [Branding] Customer branding disabled by user flag (--no-brand). Using default Google Cloud theme.")
        return brand_config

    # Resolve domain
    target_domain = custom_domain.strip() if custom_domain else ""
    if not target_domain:
        if "." in domain_slug:
            target_domain = domain_slug
        else:
            comp_clean = company.strip().lower()
            if any(comp_clean.endswith(ext) for ext in [".com", ".co.jp", ".org", ".net", ".io", ".de", ".fr", ".uk"]):
                target_domain = comp_clean
            else:
                target_domain = f"{domain_slug}.com"

    # Sanitize domain
    target_domain = target_domain.lower().replace("https://", "").replace("http://", "").split("/")[0].split(":")[0].strip()

    print(f"🎨 [Branding] Discovering customer logo and corporate palette for '{company}' (domain: {target_domain})...")

    brand_dir = os.path.join(work_dir, "brand")
    os.makedirs(brand_dir, exist_ok=True)
    local_logo_path = os.path.join(brand_dir, "logo.png")

    remotion_brand_dir = os.path.join(remotion_public_dir, "brand")
    os.makedirs(remotion_brand_dir, exist_ok=True)
    remotion_logo_path = os.path.join(remotion_brand_dir, "logo.png")

    logo_downloaded = False
    favicon_url = f"https://www.google.com/s2/favicons?domain={target_domain}&sz=256"
    try:
        import urllib.request
        req = urllib.request.Request(favicon_url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            content = resp.read()
            if len(content) > 500:
                with open(local_logo_path, "wb") as f:
                    f.write(content)
                logo_downloaded = True
    except Exception as e:
        print(f"⚠️ [Branding] Could not download favicon for {target_domain}: {e}", file=sys.stderr)

    if not logo_downloaded and os.path.exists(local_logo_path) and os.path.getsize(local_logo_path) > 500:
        logo_downloaded = True

    primary_color = "#1A73E8"
    accent_color = "#E8F0FE"
    logo_rel_file = ""

    if logo_downloaded and os.path.exists(local_logo_path):
        primary_color, accent_color = extract_brand_colors(local_logo_path)
        shutil.copy2(local_logo_path, remotion_logo_path)
        logo_rel_file = "brand/logo.png"
        print(f"  ✅ Logo downloaded and staged: {remotion_logo_path}")
        print(f"  ✅ Corporate palette extracted: Primary={primary_color}, Accent={accent_color}")
    else:
        print(f"  ℹ️ Using corporate name '{company}' with default keynote styling.")

    brand_config = {
        "enabled": True,
        "company": company,
        "domain": target_domain,
        "logoFile": logo_rel_file,
        "primaryColor": primary_color,
        "accentColor": accent_color
    }

    brand_json_path = os.path.join(work_dir, "brand.json")
    try:
        with open(brand_json_path, "w", encoding="utf-8") as f:
            json.dump(brand_config, f, indent=2)
    except Exception:
        pass

    return brand_config


def generate_mock_recording_data(recording_dir: str, narration_file: str, prompts: list = None, lang: str = "en-US") -> tuple:
    """Generates synthetic actions telemetry and mock video for offline/test builds."""
    os.makedirs(recording_dir, exist_ok=True)
    video_path = os.path.join(recording_dir, "raw_recording.mp4")

    prompt_scenes = []
    if os.path.exists(narration_file):
        try:
            with open(narration_file, "r", encoding="utf-8") as f:
                narr = json.load(f)
            prompt_scenes = [s for s in narr.get("scenes", []) if s["scene_id"].startswith("prompt_")]
        except Exception:
            pass

    if not prompt_scenes:
        prompts_to_use = prompts or [f"Prompt {i}" for i in range(1, 4)]
        prompt_scenes = [{"scene_id": f"prompt_{i+1}", "title": f"Scene {i+1}", "narration_text": p, "duration_sec": 12.0} for i, p in enumerate(prompts_to_use)]

    actions = []
    current_time = 0.0
    for idx, sc in enumerate(prompt_scenes):
        sc_dur = sc.get("duration_sec", 12.0)
        dur_typing = min(4.0, max(2.0, sc_dur * 0.25))
        dur_thinking = min(3.0, max(1.5, sc_dur * 0.2))
        dur_response = max(4.0, sc_dur - dur_typing - dur_thinking)

        t_type_start = round(current_time + 0.5, 2)
        t_type_end = round(t_type_start + dur_typing, 2)
        t_submit = round(t_type_end + 0.2, 2)
        t_wait_start = t_submit
        t_response_start = round(t_wait_start + dur_thinking, 2)
        t_response_complete = round(t_response_start + dur_response, 2)

        actions.append({
            "scene_id": sc["scene_id"],
            "title": sc.get("title", f"Scene {idx + 1}"),
            "prompt_text": sc.get("narration_text", f"Demonstration prompt {idx + 1}"),
            "t_type_start": t_type_start,
            "t_type_end": t_type_end,
            "t_submit": t_submit,
            "t_wait_start": t_wait_start,
            "t_response_start": t_response_start,
            "t_response_complete": t_response_complete,
            "focus_rect": {"x": 360, "y": 160, "width": 1120, "height": 730}
        })
        current_time = t_response_complete

    total_dur = max(30.0, math.ceil(current_time + 5.0))
    # Generate synthetic 1080p 30fps MP4 using ffmpeg
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c=0x1a1a24:s=1920x1080:r=30:d={total_dur}",
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        video_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
    except Exception:
        with open(video_path, "wb") as f:
            f.write(b"\x00" * 1024)

    actions_data = {
        "session_url": "https://vertexaisearch.cloud.google.com/home/cid/mock/r/agent/mock/session/-",
        "raw_video_path": video_path,
        "actions": actions
    }
    actions_file = os.path.join(recording_dir, "actions.json")
    with open(actions_file, "w", encoding="utf-8") as f:
        json.dump(actions_data, f, indent=2)

    return video_path, actions_data


def format_demo_plan_overview(
    company: str,
    role: str,
    lang: str,
    voice: str = "",
    enable_subtitles: bool = True,
    enable_bgm: bool = False,
    project_id: str = "",
    drive_account: str = "",
    deploy_account: str = "",
    gcs_bucket: str = "",
    skip_drive: bool = False,
    prompts: list = None,
    session_url: str = "",
    agent_name: str = ""
) -> dict:
    """Formats the pre-recording demonstration plan overview with pre-flight verification across all settings."""
    # 1. Resolve Voice
    selected_voice = voice
    if not selected_voice:
        try:
            if VIDEO_SCRIPTS_DIR not in sys.path:
                sys.path.insert(0, VIDEO_SCRIPTS_DIR)
            import synthesize_tts
            v_info = synthesize_tts.resolve_voice_for_language(lang)
            selected_voice = v_info.get("voice", f"{lang}-Chirp3-HD-Achernar")
        except Exception:
            selected_voice = f"{lang}-Chirp3-HD-Achernar"

    # Resolve Agent Display Name
    if agent_name:
        resolved_agent_name = agent_name
    elif company and role:
        resolved_agent_name = role if company in role else f"{company} {role}"
    else:
        resolved_agent_name = role or company or "Demo Agent"

    # 2. Pre-flight Delivery Destination Verification
    try:
        if VIDEO_SCRIPTS_DIR not in sys.path:
            sys.path.insert(0, VIDEO_SCRIPTS_DIR)
        import upload_to_drive
        dest_info = upload_to_drive.verify_delivery_destinations(
            project_id=project_id,
            drive_account=drive_account,
            deploy_account=deploy_account,
            configured_bucket=gcs_bucket,
            skip_drive=skip_drive
        )
    except Exception as e:
        dest_info = {
            "tier_1": {"account": drive_account or "auto-detected", "status": "unverified", "reason": str(e)},
            "tier_2": {"account": deploy_account or "auto-detected", "status": "unverified", "reason": str(e)},
            "tier_3": {"bucket": gcs_bucket or f"{project_id}-ge-demo-artifacts", "status": "unverified", "reason": str(e)},
            "confirmed_tier": "tier_3_gcs",
            "confirmed_destination": f"Tier 3: Google Cloud Storage (gs://{gcs_bucket or 'ge-demo-artifacts'}/)"
        }

    sub_text = "Clean Lower-Third (Synchronized)" if enable_subtitles else "Disabled"
    bgm_text = "Ducked: 10% on speech, 28% ambient" if enable_bgm else "Disabled (Pure Speech Narration)"
    t1_acct = dest_info["tier_1"]["account"] or "auto-detected"
    t2_acct = dest_info["tier_2"]["account"] or "N/A"
    t3_bucket = dest_info["tier_3"]["bucket"]

    lines = [
        "",
        "=" * 80,
        "🎬 PRE-RECORDING DEMONSTRATION PLAN & PRE-FLIGHT VERIFICATION",
        "=" * 80,
        f"🏢 Company Name           : {company}",
        f"🤖 Agent Persona          : {role}",
        f"🤖 GE Agent Name          : {resolved_agent_name}",
        f"🔗 GE Direct Agent Link   : {session_url or '(Not configured or local offline mode)'}",
        f"🌐 Target Locale          : {lang}",
        f"🎙️ Selected Neural Voice  : {selected_voice}",
        f"💬 Subtitle Mode          : {sub_text}",
        f"🎼 Ambient BGM & Ducking  : {bgm_text}",
        "",
        "📦 Delivery Destinations (3-Tier Storage Hierarchy):",
        f"   • Tier 1 (Primary)     : Host Operator Drive ({t1_acct})",
        f"   • Tier 2 (Secondary)   : Deploy Tenant Drive ({t2_acct})",
        f"   • Tier 3 (Fallback)    : Cloud Storage (gs://{t3_bucket}/)",
        "",
        f"🔒 Confirmed Destination  : {dest_info['confirmed_destination']}",
    ]

    if dest_info.get("tier_1", {}).get("status") == "reauth_required":
        lines.extend([
            "",
            f"⚠️ Note: Credentials expired for {t1_acct}. Run to re-authenticate:",
            f"   {drive_login_hint(t1_acct)}"
        ])
    elif dest_info.get("tier_1", {}).get("status") == "scope_insufficient":
        lines.extend([
            "",
            f"💡 Note: Drive scope missing for {t1_acct}. Run to enable:",
            f"   {drive_login_hint(t1_acct)}"
        ])

    lines.extend([
        "=" * 80,
        ""
    ])
    presentation_text = "\n".join(lines)

    return {
        "presentation_text": presentation_text,
        "company": company,
        "role": role,
        "agent_name": resolved_agent_name,
        "session_url": session_url,
        "language": lang,
        "voice": selected_voice,
        "subtitles_enabled": enable_subtitles,
        "bgm_enabled": enable_bgm,
        "confirmed_destination": dest_info["confirmed_destination"],
        "confirmed_tier": dest_info["confirmed_tier"],
        "tier_1": dest_info["tier_1"],
        "tier_2": dest_info["tier_2"],
        "tier_3": dest_info["tier_3"]
    }


def sync_manifest_to_template(props_file: str, dest_manifest: str = None) -> str:
    """Synchronizes compiled video props directly into the Remotion template manifest."""
    target = dest_manifest or os.path.join(VIDEO_TEMPLATE_DIR, "src/manifest.json")
    os.makedirs(os.path.dirname(os.path.abspath(target)), exist_ok=True)
    shutil.copy2(props_file, target)
    return target


def run_pipeline(args):
    """Executes the complete demo video generation pipeline."""
    env = load_env(args.env_file)
    company = args.company or env.get("COMPANY_NAME", "Enterprise Demo")
    role = args.role or env.get("AGENT_ROLE") or env.get("DEMO_DISPLAY_NAME", "AI Operations Director")
    agent_name = getattr(args, "agent_name", "") or env.get("DEMO_DISPLAY_NAME") or env.get("AGENT_NAME") or (f"{company} {role}" if company not in role else role)
    suffix = args.suffix or env.get("SUFFIX", "")
    lang = args.lang or ("ja-JP" if env.get("CURRENCY_SYMBOL") in ("¥", "円") else "en-US")
    project_id = getattr(args, "project", "") or env.get("PROJECT_ID", "")
    domain_slug = env.get("DOMAIN_SLUG") or company.lower().replace(" ", "").replace("-", "")
    
    # Dynamically resolve Gemini Enterprise chat session URL
    session_url = resolve_session_url(args, env)
    if not session_url and not getattr(args, "mock", False):
        print("⚠️ [Session Resolution] Could not auto-resolve Gemini Enterprise chat session URL.", file=sys.stderr)
        print("   If browser recording fails, pass --session-url directly or ensure .env contains GE_SESSION_URL.", file=sys.stderr)

    # ---------------------------------------------------------
    # Typography & Multi-Language Font Verification
    # ---------------------------------------------------------
    ensure_fonts_script = os.path.join(VIDEO_TEMPLATE_DIR, "scripts/ensure_fonts.py")
    if os.path.exists(ensure_fonts_script):
        print(f"🔤 [Typography] Verifying system typography and fonts for locale '{lang}'...")
        res_fonts = subprocess.run([sys.executable, ensure_fonts_script, "--lang", lang])
        if res_fonts.returncode != 0:
            print(f"⚠️ [Typography] System font verification returned non-zero code for '{lang}'. Proceeding with WebFont fallbacks.", file=sys.stderr)

    if getattr(args, "skip_drive", False):
        os.environ["SKIP_VIDEO_DRIVE_UPLOAD"] = "1"
    elif os.environ.get("SKIP_DRIVE_UPLOAD", "").strip().lower() in ("1", "true", "yes"):
        if os.environ.get("SKIP_VIDEO_DRIVE_UPLOAD", "").strip().lower() not in ("1", "true", "yes"):
            print("ℹ️ Note: SKIP_DRIVE_UPLOAD is present in the environment (from demo asset setup), but video Google Drive delivery remains active.")

    work_dir = os.path.abspath(args.work_dir)
    os.makedirs(work_dir, exist_ok=True)
    recording_dir = os.path.join(work_dir, "recording")
    narration_dir = os.path.join(work_dir, "narration")
    public_assets_dir = os.path.join(VIDEO_TEMPLATE_DIR, "public")
    os.makedirs(public_assets_dir, exist_ok=True)

    # ---------------------------------------------------------
    # Discover Customer Brand Assets (Default ON, --no-brand to disable)
    # ---------------------------------------------------------
    disable_brand = getattr(args, "no_brand", False)
    brand_domain = getattr(args, "brand_domain", "") or env.get("CUSTOMER_DOMAIN", "") or env.get("DOMAIN", "")
    brand_info = discover_brand_assets(
        company=company,
        domain_slug=domain_slug,
        custom_domain=brand_domain,
        work_dir=work_dir,
        remotion_public_dir=public_assets_dir,
        disable_brand=disable_brand
    )

    # ---------------------------------------------------------
    # Pre-Flight Verification & Demonstration Plan Presentation
    # ---------------------------------------------------------
    plan_overview = format_demo_plan_overview(
        company=company,
        role=role,
        lang=lang,
        voice="",
        enable_subtitles=not getattr(args, "no_subtitles", False),
        enable_bgm=getattr(args, "enable_bgm", False),
        project_id=project_id,
        drive_account=getattr(args, "drive_account", ""),
        deploy_account=getattr(args, "deploy_account", ""),
        gcs_bucket=getattr(args, "gcs_bucket", ""),
        skip_drive=getattr(args, "skip_drive", False),
        prompts=args.prompts,
        session_url=session_url,
        agent_name=agent_name
    )
    print(plan_overview["presentation_text"])

    if brand_info and brand_info.get("enabled"):
        print(f"🎨 Brand Palette  : Primary={brand_info.get('primaryColor')}, Accent={brand_info.get('accentColor')}")
    if session_url:
        print(f"💬 Session Link   : {session_url}")
    print(f"📁 Workspace Dir  : {work_dir}\n")

    # ---------------------------------------------------------
    # Launch Background Music Synthesis Concurrently (Optional)
    # ---------------------------------------------------------
    bgm_proc = None
    bgm_log_file = None
    bgm_output = os.path.join(public_assets_dir, "audio/bgm.mp3")
    if getattr(args, "enable_bgm", False):
        print("🎼 [BGM Pipeline] Spawning Background Music synthesis in parallel with recording...")
        bgm_script = os.path.join(VIDEO_TEMPLATE_DIR, "scripts/generate_bgm.py")
        cmd_bgm = [
            sys.executable, bgm_script,
            "--output", bgm_output,
            "--company", company,
            "--role", role,
            "--domain", domain_slug,
        ]
        if getattr(args, "bgm_prompt", ""):
            cmd_bgm.extend(["--prompt", args.bgm_prompt])
        if env.get("PROJECT_ID"):
            cmd_bgm.extend(["--project", env["PROJECT_ID"]])

        bgm_log_path = os.path.join(work_dir, "bgm_synthesis.log")
        bgm_log_file = open(bgm_log_path, "w", encoding="utf-8")
        bgm_proc = subprocess.Popen(cmd_bgm, stdout=bgm_log_file, stderr=subprocess.STDOUT)

    # ---------------------------------------------------------
    # STAGE 1: Voice Narration & Subtitles (Google Cloud TTS)
    # ---------------------------------------------------------
    narration_file = os.path.join(narration_dir, "narration_manifest.json")
    if getattr(args, "skip_tts", False) and os.path.exists(narration_file):
        print("\n⏩ [Stage 1/5] Skipping Voice Narration (Reusing existing TTS narration)...")
    else:
        print("🎙️ [Stage 1/5] Synthesizing Voice Narration & Subtitle Timecodes...")
        tts_script = os.path.join(VIDEO_TEMPLATE_DIR, "scripts/synthesize_tts.py")
        cmd_tts = [
            sys.executable, tts_script,
            "--outdir", narration_dir,
            "--company", company,
            "--role", role,
            "--lang", lang,
        ]
        if project_id:
            cmd_tts.extend(["--project", project_id])
        if getattr(args, "mock", False):
            cmd_tts.append("--mock")
        if args.prompts:
            cmd_tts.extend(["--prompts", *args.prompts])

        res = subprocess.run(cmd_tts)
        if res.returncode != 0:
            print("❌ Stage 1 failed. Aborting pipeline.", file=sys.stderr)
            sys.exit(1)

        # Verification: in non-mock, non-skipped mode, ensure audio files exist and are non-empty
        if not getattr(args, "mock", False) and not getattr(args, "no_narration", False):
            mp3_files = [f for f in os.listdir(narration_dir) if f.endswith(".mp3") and os.path.getsize(os.path.join(narration_dir, f)) > 0]
            if not mp3_files:
                print("❌ [Audio Verification] No non-empty MP3 audio files found after TTS synthesis.", file=sys.stderr)
                sys.exit(1)

    # Copy generated audio into Remotion public/audio directory
    remotion_audio_dir = os.path.join(public_assets_dir, "audio")
    os.makedirs(remotion_audio_dir, exist_ok=True)
    for fname in os.listdir(narration_dir):
        if fname.endswith(".mp3"):
            shutil.copy2(os.path.join(narration_dir, fname), os.path.join(remotion_audio_dir, fname))

    # ---------------------------------------------------------
    # STAGE 2: Browser Recording (Playwright CDP)
    # ---------------------------------------------------------
    actions_file = os.path.join(recording_dir, "actions.json")
    if getattr(args, "skip_recording", False) and os.path.exists(actions_file):
        print("\n⏩ [Stage 2/5] Skipping Browser Recording (Reusing existing recording)...")
        with open(actions_file, "r", encoding="utf-8") as f:
            actions_data = json.load(f)
    elif getattr(args, "mock", False):
        print("\n🤖 [Stage 2/5] Synthesizing Mock Browser Recording Data (--mock enabled)...")
        generate_mock_recording_data(recording_dir, narration_file, prompts=args.prompts, lang=lang)
        with open(actions_file, "r", encoding="utf-8") as f:
            actions_data = json.load(f)
    else:
        print("\n🎥 [Stage 2/5] Recording Gemini Enterprise Web UI Session...")
        rec_script = os.path.join(VIDEO_TEMPLATE_DIR, "scripts/record_ge_web.py")
        cmd_record = [
            sys.executable, rec_script,
            "--cdp-url", args.cdp_url,
            "--outdir", recording_dir,
            "--lang", lang,
            "--narration", narration_file,
        ]
        if session_url:
            cmd_record.extend(["--session-url", session_url])
        if getattr(args, "headless", False):
            cmd_record.append("--headless")
        else:
            cmd_record.append("--no-headless")
        if args.prompts:
            cmd_record.extend(["--prompts", *args.prompts])

        res = subprocess.run(cmd_record)
        if res.returncode == 2:
            print("❌ Stage 2 aborted: Google Accounts authentication required.", file=sys.stderr)
            print("   Synthetic mock video generation is strictly prohibited.", file=sys.stderr)
            print("   Please complete login and 2FA in the opened Chrome window and retry.", file=sys.stderr)
            sys.exit(2)
        elif res.returncode != 0:
            print("❌ Stage 2 failed. Aborting pipeline.", file=sys.stderr)
            sys.exit(1)

        with open(actions_file, "r", encoding="utf-8") as f:
            actions_data = json.load(f)

    # Stage raw video into Remotion public/recordings directory
    raw_video = actions_data.get("raw_video_path", "")
    if raw_video and os.path.exists(raw_video):
        remotion_rec_dir = os.path.join(public_assets_dir, "recordings")
        os.makedirs(remotion_rec_dir, exist_ok=True)
        shutil.copy2(raw_video, os.path.join(remotion_rec_dir, os.path.basename(raw_video)))

    # ---------------------------------------------------------
    # STAGE 2.5: Synchronize Background Music (Optional)
    # ---------------------------------------------------------
    if bgm_proc is not None:
        print("\n🎼 [Stage 2.5/5] Synchronizing Background Music Synthesis...")
        bgm_res = bgm_proc.wait()
        if bgm_log_file:
            try:
                bgm_log_file.close()
            except Exception:
                pass
        if bgm_res == 0 and os.path.exists(bgm_output):
            print("  ✅ Background music synthesis completed and verified.")
        else:
            print(f"  ⚠️ Background music process exited with code {bgm_res}; check {work_dir}/bgm_synthesis.log", file=sys.stderr)

    # ---------------------------------------------------------
    # STAGE 3: Build Remotion Props & Manifest
    # ---------------------------------------------------------
    print("\n📐 [Stage 3/5] Compiling Dynamic Video Manifest & Props...")
    manifest_script = os.path.join(VIDEO_TEMPLATE_DIR, "scripts/build_video_manifest.py")
    props_file = os.path.join(work_dir, "video_props.json")
    cmd_manifest = [
        sys.executable, manifest_script,
        "--actions", actions_file,
        "--narration", narration_file,
        "--output", props_file
    ]
    if getattr(args, "no_narration", False):
        cmd_manifest.append("--no-narration")
    if getattr(args, "no_subtitles", False):
        cmd_manifest.append("--no-subtitles")
    if getattr(args, "enable_bgm", False):
        cmd_manifest.append("--enable-bgm")
    if brand_info and brand_info.get("enabled"):
        brand_json_path = os.path.join(work_dir, "brand.json")
        if os.path.exists(brand_json_path):
            cmd_manifest.extend(["--brand-file", brand_json_path])
    res = subprocess.run(cmd_manifest)
    if res.returncode != 0:
        print("❌ Stage 3 failed. Aborting pipeline.", file=sys.stderr)
        sys.exit(1)

    # Stage 3.5: Synchronize manifest into Remotion source tree
    template_manifest = os.path.join(VIDEO_TEMPLATE_DIR, "src/manifest.json")
    try:
        sync_manifest_to_template(props_file, template_manifest)
        print(f"  ✅ Video manifest synchronized: {template_manifest}")
    except Exception as e:
        print(f"  ⚠️ Could not copy manifest to template src/manifest.json: {e}", file=sys.stderr)

    # ---------------------------------------------------------
    # STAGE 4: Programmatic Video Composition & Rendering
    # ---------------------------------------------------------
    print("\n🎨 [Stage 4/5] Rendering Video Composition via Remotion...")
    output_mp4 = os.path.abspath(args.output or os.path.join(work_dir, "rendered_demo_video.mp4"))
    os.makedirs(os.path.dirname(output_mp4), exist_ok=True)

    # Check if npm / node is available
    remotion_success = False
    render_cmd = (
        f'source "$HOME/.nvm/nvm.sh" 2>/dev/null || true; '
        f'cd "{VIDEO_TEMPLATE_DIR}" && '
        f'if [ ! -d "node_modules" ]; then npm install --prefer-offline --no-audit --no-fund; fi && '
        f'npx remotion render src/index.ts DemoHighlightReel "{output_mp4}" --props="{props_file}"'
    )

    # Say what is missing before spending a dependency install finding out.
    # "Remotion rendering failed" after several silent minutes is not a
    # diagnosis a remote tester can act on.
    probe = subprocess.run(
        ["bash", "-c", 'source "$HOME/.nvm/nvm.sh" 2>/dev/null || true; command -v node && command -v npx'],
        capture_output=True, text=True,
    )
    if probe.returncode != 0:
        print("❌ [Rendering Error] Node.js and npx are required to render, and neither was found.", file=sys.stderr)
        print("   Install Node.js 20 or later, or make an existing install visible on PATH", file=sys.stderr)
        print("   (a Node Version Manager install is picked up from $HOME/.nvm/nvm.sh).", file=sys.stderr)
        sys.exit(1)

    try:
        print("Running Remotion rendering engine (streaming output)...")
        # Streamed, not captured. A render takes minutes, and a process that
        # prints nothing for minutes is indistinguishable from one that has hung
        # - which is how this stage got reported as a freeze. The tail is kept
        # for the failure summary so the useful lines are not lost in the scroll.
        tail = []
        proc = subprocess.Popen(
            ["bash", "-c", render_cmd],
            stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1,
        )
        for line in proc.stdout:
            line = line.rstrip()
            print(f"  | {line}", flush=True)
            tail.append(line)
            if len(tail) > 60:
                tail.pop(0)
        returncode = proc.wait()
        if returncode == 0 and os.path.exists(output_mp4) and os.path.getsize(output_mp4) > 1000:
            remotion_success = True
            print(f"  ✅ Remotion render successful: {output_mp4}")
        else:
            print(f"  ⚠️ Remotion command finished with code {returncode}.")
            if tail:
                print("  --- Remotion output (tail) ---")
                print("\n".join(tail))
    except Exception as e:
        print(f"  ⚠️ Remotion invocation exception: {e}")

    if not remotion_success:
        print("❌ [Rendering Error] Remotion rendering failed. Synthetic fallback slides are strictly prohibited.", file=sys.stderr)
        print("   Please review the Remotion stderr logs above and ensure Node/Remotion dependencies are ready.", file=sys.stderr)
        sys.exit(1)

    # ---------------------------------------------------------
    # STAGE 5: Delivery to Google Drive & Local Deliverables
    # ---------------------------------------------------------
    print("\n📦 [Stage 5/5] Delivering Video to Google Drive & Local Staging...")
    delivery_script = os.path.join(VIDEO_TEMPLATE_DIR, "scripts/upload_to_drive.py")
    cmd_deliver = [
        sys.executable, delivery_script,
        "--video", output_mp4,
        "--company", company,
        "--role", role,
        "--suffix", suffix,
        "--outdir", "./deliverables"
    ]
    if getattr(args, "drive_account", ""):
        cmd_deliver.extend(["--drive-account", args.drive_account])
    if getattr(args, "deploy_account", ""):
        cmd_deliver.extend(["--deploy-account", args.deploy_account])
    if getattr(args, "project", "") or project_id:
        cmd_deliver.extend(["--project", getattr(args, "project", "") or project_id])
    if getattr(args, "gcs_bucket", ""):
        cmd_deliver.extend(["--gcs-bucket", args.gcs_bucket])
    if getattr(args, "drive_folder", ""):
        cmd_deliver.extend(["--drive-folder", args.drive_folder])
    if getattr(args, "share_public", False):
        cmd_deliver.append("--share-public")
    if getattr(args, "skip_drive", False) or os.environ.get("SKIP_VIDEO_DRIVE_UPLOAD", "").strip().lower() in ("1", "true", "yes"):
        cmd_deliver.append("--skip-drive")
    delivery_report = os.path.abspath(os.path.join("./deliverables", "delivery_report.json"))
    cmd_deliver.extend(["--report", delivery_report])
    if sys.stdin.isatty():
        cmd_deliver.append("--interactive")

    # The uploader is the only component that knows where the video actually
    # landed. Read its verdict rather than assuming success: a silent fallback to
    # Cloud Storage used to be announced here as a completed Drive delivery, so
    # the operator was told to look in a folder that had no video in it.
    try:
        os.makedirs("./deliverables", exist_ok=True)
    except Exception:
        pass
    if os.path.exists(delivery_report):
        # A stale report from an earlier run must never be mistaken for this one.
        try:
            os.remove(delivery_report)
        except Exception:
            pass

    try:
        proc = subprocess.run(cmd_deliver, timeout=DELIVERY_TIMEOUT_SEC)
        delivery_code = proc.returncode
    except subprocess.TimeoutExpired:
        print(f"  ⚠️ Delivery timed out after {DELIVERY_TIMEOUT_SEC}s.", file=sys.stderr)
        delivery_code = 1
    except Exception as deliver_err:
        print(f"  ⚠️ Delivery invocation exception: {deliver_err}", file=sys.stderr)
        delivery_code = 1

    report = {}
    try:
        with open(delivery_report, "r", encoding="utf-8") as handle:
            report = json.load(handle)
    except Exception:
        report = {}

    local_hint = report.get("local_path") or f"./deliverables/[Demo-Video]_{company.replace(' ', '_')}_-_{role.replace(' ', '_')}.mp4"
    headline = report.get("headline", "")
    action = report.get("action_required", "")
    drive_url = report.get("drive_url", "")
    gcs_uri = report.get("gcs_uri", "")

    print("\n" + "=" * 80)
    if delivery_code == 0:
        print("🎉 DEMO VIDEO PRODUCTION & DELIVERY COMPLETE!")
    elif delivery_code == 3:
        print("🚨 ACTION REQUIRED: GOOGLE DRIVE DELIVERY DID NOT COMPLETE")
    else:
        print("❌ DEMO VIDEO RENDERED, BUT DELIVERY FAILED")
    if headline:
        print(f"   Outcome           : {headline}")
    print(f"   Local Deliverable : {local_hint}")
    if drive_url:
        print(f"   Google Drive      : {drive_url}")
    if gcs_uri:
        print(f"   Cloud Storage     : {gcs_uri}")
    if action:
        print(f"   👉 Next Step       : {action}")
    if os.path.exists(delivery_report):
        print(f"   Delivery Report   : {delivery_report}")
    print("=" * 80 + "\n")

    if delivery_code != 0:
        sys.exit(delivery_code)


def main():
    ensure_prerequisites()

    parser = argparse.ArgumentParser(description="Generate complete Gemini Enterprise demo video.")
    parser.add_argument("--env-file", default=".env", help="Path to .env configuration")
    parser.add_argument("--session-url", default="", help="Direct Gemini Enterprise chat session URL")
    parser.add_argument("--ge-url", default="", help="Alias for --session-url")
    parser.add_argument("--cdp-url", default="http://localhost:9222", help="Chrome CDP URL")
    parser.add_argument("--company", default="", help="Company name override")
    parser.add_argument("--role", default="", help="Agent role override")
    parser.add_argument("--agent-name", default="", help="Gemini Enterprise agent display name override")
    parser.add_argument("--suffix", default="", help="Suffix override")
    parser.add_argument("--lang", default="", help="Language code (e.g. ja-JP, en-US)")
    parser.add_argument("--work-dir", default="./output/demo_video", help="Intermediate working directory")
    parser.add_argument("--project", default="", help="Google Cloud project ID")
    parser.add_argument("--mock", action="store_true", default=False, help="Enable mock synthetic mode for test/offline execution")
    parser.add_argument("--output", default="", help="Custom output MP4 path")
    parser.add_argument("--headless", action="store_true", default=False, help="Launch Chrome in headless mode (default: False)")
    parser.add_argument("--no-headless", action="store_false", dest="headless", help="Launch Chrome with graphical UI (default: True)")
    parser.add_argument("--skip-drive", action="store_true", help="Skip Google Drive upload (save to ./deliverables/ only)")
    parser.add_argument("--skip-recording", action="store_true", help="Skip browser recording and reuse existing actions/video in work-dir")
    parser.add_argument("--skip-tts", action="store_true", help="Skip TTS synthesis and reuse existing audio in work-dir")
    parser.add_argument("--drive-account", default="", help="Target Google Drive account (defaults to execution environment account)")
    parser.add_argument("--deploy-account", default="", help="Target deploy Google Cloud account for Tier 2 Drive")
    parser.add_argument("--gcs-bucket", default="", help="Target Google Cloud Storage bucket for Tier 3 delivery")
    parser.add_argument("--drive-folder", default="", help="Google Drive folder name override")
    parser.add_argument("--share-public", action="store_true", help="Enable public link sharing (default: False, owner-only private)")
    parser.add_argument("--no-narration", action="store_true", help="Disable voice narration audio tracks")
    parser.add_argument("--no-subtitles", action="store_true", help="Disable subtitle overlays")
    parser.add_argument("--enable-bgm", "--bgm", action="store_true", help="Enable professional ambient background music track")
    parser.add_argument("--bgm-prompt", default="", help="Custom soundscape prompt for background music")
    parser.add_argument("--no-brand", "--disable-brand", action="store_true", default=False, help="Disable automatic customer branding and logo discovery (default: branding enabled)")
    parser.add_argument("--brand-domain", default="", help="Custom domain for brand logo and color discovery (defaults to domain slug or company name)")
    parser.add_argument("--prompts", nargs="+", help="Custom demo prompts to execute")
    args = parser.parse_args()

    if args.skip_drive:
        os.environ["SKIP_DRIVE_UPLOAD"] = "1"

    run_pipeline(args)


if __name__ == "__main__":
    main()
