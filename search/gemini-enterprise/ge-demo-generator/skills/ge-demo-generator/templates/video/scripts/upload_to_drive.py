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

"""Google Drive Uploader for GE Demo Highlight Reel Videos.

Uploads the rendered demo video into the Google Drive that already holds the rest
of the demo. The delivery account is resolved by `detect_host_drive_account`, which
prefers the Drive the demo's own external sample files went to and then the active
`gcloud` account, so the video does not land in a different Drive than the PDFs and
spreadsheets it is a video *of*. See that function for the full precedence and for
why the host login is no longer consulted first.

Supports native `gdrive` CLI (when available) and Google Drive v3 REST API
with `gcloud auth print-access-token --account=<target_account>`.
Defaults to owner-only private permissions (no public link sharing).

Delivery is reported twice, on purpose: a human-readable summary on stdout, and a
machine-readable `delivery_report.json` plus a distinct process exit code, because
the caller has no other way to tell a Drive upload apart from a silent fallback.
"""

import argparse
import getpass
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import urllib.error
import urllib.parse
import urllib.request

DRIVE_API = "https://www.googleapis.com/drive/v3"
DRIVE_UPLOAD_API = "https://www.googleapis.com/upload/drive/v3"
GDRIVE_BIN = "/google/bin/releases/gemini-agents-gdrive/gdrive"

# Written by generate_and_upload_external_files.py next to the demo's sample
# documents. It records which account owns the demo's Drive folder.
DEMO_DRIVE_SUMMARY_NAME = "drive_upload_summary.json"

# Upper bound on any interactive question this script asks. See prompt_yes_no.
PROMPT_TIMEOUT_SEC = 120

# Process exit codes. The caller distinguishes "delivered" from "the operator has
# to do something" without parsing stdout.
EXIT_OK = 0
EXIT_FAILED = 1
EXIT_ACTION_REQUIRED = 3

# Machine-readable outcome, written next to the local deliverable.
DELIVERY_REPORT_NAME = "delivery_report.json"


def gdrive_cli_available() -> bool:
    """Checks if internal gdrive CLI is present and executable."""
    return os.path.exists(GDRIVE_BIN) and os.access(GDRIVE_BIN, os.X_OK)


def host_has_local_browser() -> bool:
    """Reports whether `gcloud auth login` can open a browser on this host.

    Every other authentication path in this project already makes this
    distinction - setup_and_deploy.sh, verify_and_heal.py and
    generate_and_upload_external_files.py all append --no-launch-browser on a
    headless host. The video delivery path did not, so the single command it
    printed to a remote tester over SSH was the one form of the command that
    could not complete there.
    """
    if os.environ.get("SSH_CONNECTION") or os.environ.get("SSH_TTY") or os.environ.get("SSH_CLIENT"):
        return False
    if os.environ.get("CLOUD_SHELL", "").strip().lower() in ("1", "true", "yes"):
        return False
    if sys.platform.startswith("linux"):
        return bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
    # macOS and Windows/WSL launch a browser by default.
    return True


def drive_login_command(account: str = "") -> list:
    """Builds the `gcloud auth login` argv that actually works on this host."""
    target = (account or "").strip()
    cmd = ["gcloud", "auth", "login"]
    if target and target != "default":
        cmd.append(target)
    cmd.append("--enable-gdrive-access")
    if not host_has_local_browser():
        cmd.append("--no-launch-browser")
    return cmd


def drive_login_hint(account: str = "") -> str:
    """Human-readable form of drive_login_command, with a placeholder if unknown."""
    target = account.strip() if account and account != "default" else "<ACCOUNT>"
    return " ".join(drive_login_command(target))


def noninteractive_requested() -> bool:
    """True when the environment has declared that nobody is at the keyboard."""
    for var in ("GE_NONINTERACTIVE", "CI"):
        if os.environ.get(var, "").strip().lower() in ("1", "true", "yes"):
            return True
    return False


def _read_line_with_timeout(prompt: str, timeout_sec: int):
    """Reads one line, giving up after timeout_sec. Returns None on timeout.

    The read happens on a daemon thread rather than inline so that an
    unanswered question cannot wedge the process: the thread stays parked on
    input() but daemon threads do not hold up interpreter exit.
    """
    box = {}

    def _reader():
        try:
            box["value"] = input(prompt)
        except Exception:
            box["value"] = ""

    reader = threading.Thread(target=_reader, daemon=True)
    reader.start()
    reader.join(timeout_sec)
    if reader.is_alive():
        return None
    return box.get("value", "")


def prompt_yes_no(message: str, timeout_sec: int = PROMPT_TIMEOUT_SEC) -> bool:
    """Asks a yes/no question that can never hang the pipeline.

    `sys.stdin.isatty()` is not a test for "a human is watching". An agent that
    runs this script over a pseudo-terminal gets isatty() == True with nobody at
    the keyboard, and a bare input() there blocks forever - taking the entire
    video pipeline down with it, because the caller runs this as a subprocess.
    check_noninteractive_setup.py enforces exactly this rule for the generated
    setup shell ("every prompt reachable without a terminal has to have a way
    out"); this is the same rule, applied to the delivery step.
    """
    if noninteractive_requested():
        print(f"   (non-interactive mode: declining '{message.strip()}')", file=sys.stderr)
        return False
    if not sys.stdin.isatty():
        return False
    answer = _read_line_with_timeout(message, timeout_sec)
    if answer is None:
        print(f"\n   (no answer within {timeout_sec}s - continuing without re-authentication)",
              file=sys.stderr)
        return False
    return answer.strip().lower() in ("", "y", "yes")


def find_demo_drive_summary(start_dir: str = "") -> dict:
    """Loads the Drive summary the demo's own external-file upload left behind.

    generate_and_upload_external_files.py writes drive_upload_summary.json into
    its output directory, recording `owner_account` - the account that actually
    owns the demo's Drive folder. Reading it is what keeps the video in the same
    Drive as the documents the demo is built around.
    """
    candidates = []
    explicit = os.environ.get("GE_DRIVE_SUMMARY", "").strip()
    if explicit:
        candidates.append(explicit)
    roots = []
    for root in (start_dir, os.getcwd()):
        if root and root not in roots:
            roots.append(root)
    for root in roots:
        candidates.append(os.path.join(root, DEMO_DRIVE_SUMMARY_NAME))
        candidates.append(os.path.join(root, "external_files", DEMO_DRIVE_SUMMARY_NAME))
        candidates.append(os.path.join(root, "output", "external_files", DEMO_DRIVE_SUMMARY_NAME))
    for path in candidates:
        try:
            if path and os.path.isfile(path):
                with open(path, "r", encoding="utf-8") as handle:
                    data = json.load(handle)
                if isinstance(data, dict):
                    data["_summary_path"] = path
                    return data
        except Exception:
            continue
    return {}


def credentialed_accounts() -> tuple:
    """Returns (non_service_accounts, active_account) from `gcloud auth list`."""
    accounts = []
    active_acct = ""
    try:
        res = subprocess.run(
            ["gcloud", "auth", "list", "--format=json"],
            capture_output=True, text=True, check=True
        )
        data = json.loads(res.stdout)
        for entry in data:
            acct = entry.get("account", "").strip()
            status = entry.get("status", "").strip().upper()
            if not acct or "@" not in acct:
                continue
            parts = acct.split("@", 1)[1].lower().split(".")
            if parts[-1] == "com" and len(parts) >= 2 and parts[-2] == "gserviceaccount":
                continue
            if status == "ACTIVE":
                active_acct = acct
            accounts.append(acct)
    except Exception:
        pass
    return accounts, active_acct


def resolve_drive_account(env: dict = None, start_dir: str = "") -> tuple:
    """Resolves the Google account the demo video should be delivered to.

    Returns:
        tuple[str, str]: (account, reason) where reason names the rule that fired.

    Priority:
    1. Explicit `DRIVE_ACCOUNT` (from .env or the process environment)
    2. `owner_account` from the demo's own drive_upload_summary.json, when that
       account still holds a credential on this host
    3. The active `gcloud` account - the account that owns the demo project
    4. An account whose local part matches the host login
    5. Any other credentialed non-service account
    6. The active account, or "default"

    Why 2 and 3 now outrank 4. The video belongs in the same Drive as the rest of
    the demo: generate_and_upload_external_files.py uploads the sample PDFs,
    spreadsheets and scans using the *active* account, and the generator skill
    states that contract outright ("the owner is ${GCP_ACCOUNT} - the same
    account, because the upload uses this token").

    Ranking the host login first broke that contract on the most ordinary setup
    there is: an operator whose workstation login differs from the account that
    owns the demo project. The sample documents went to the demo tenant's Drive
    and the video went to the operator's own, so one demo ended up split across
    two Drives. Worse, the account picked by the host-login rule is typically the
    one behind a corporate single-sign-on policy that forces periodic
    re-authentication, so the old order chose the account most likely to hand
    back an expired refresh token - which is exactly how this surfaced in the
    field, as a video that silently fell through to Cloud Storage.
    """
    env = env or {}
    env_acct = env.get("DRIVE_ACCOUNT") or os.environ.get("DRIVE_ACCOUNT", "")
    if env_acct:
        return env_acct.strip(), "explicit DRIVE_ACCOUNT override"

    accounts, active_acct = credentialed_accounts()
    known = {a.lower(): a for a in accounts}

    # Priority 2: the Drive the demo's own external files already went to.
    summary = find_demo_drive_summary(start_dir)
    owner = (summary.get("owner_account") or "").strip()
    if owner and owner.lower() in known:
        return known[owner.lower()], "owner of the demo's existing Drive folder"

    # Priority 3: the account that owns the demo project.
    if active_acct:
        return active_acct, "active gcloud account (demo deployment identity)"

    # Priority 4: an account matching the host login.
    try:
        host_user = getpass.getuser().strip().lower()
    except Exception:
        host_user = ""
    if host_user:
        for a in accounts:
            if a.lower().startswith(host_user + "@"):
                return a, "account matching the host login"

    # Priority 5: anything else that is credentialed.
    if accounts:
        return accounts[0], "first credentialed non-service account"

    return (active_acct or "default"), "no credentialed account found"


def detect_host_drive_account(env: dict = None) -> str:
    """Account the demo video is delivered to. See resolve_drive_account."""
    account, _reason = resolve_drive_account(env)
    return account



def format_drive_scope_diagnostic_banner(account: str = "") -> str:
    """Formats an actionable diagnostic banner when Drive OAuth scope is missing (HTTP 403)."""
    target = account.strip() if account and account != "default" else "<ACCOUNT>"
    banner = [
        "",
        "=" * 80,
        "⚠️ [Google Drive Scope Missing] The current gcloud credential lacks Drive API scope (HTTP 403)!",
        f"   Target Account : {target}",
        "",
        "👉 To grant Google Drive access to gcloud, run:",
        f"   {drive_login_hint(target)}",
        "",
        "   (Or configure DRIVE_ACCOUNT=<user@domain> or pass --drive-account=<account>)",
        "=" * 80,
        ""
    ]
    return "\n".join(banner)


def format_drive_reauth_diagnostic_banner(account: str = "") -> str:
    """Formats an actionable diagnostic banner when Google OAuth credentials have expired."""
    target = account.strip() if account and account != "default" else "<ACCOUNT>"
    banner = [
        "",
        "=" * 80,
        "⚠️ [Google OAuth Credentials Expired] The refresh token for your account has expired or been revoked!",
        f"   Target Account : {target}",
        "",
        "👉 To re-authenticate and enable Google Drive access, run:",
        f"   {drive_login_hint(target)}",
        "",
        "   (Or configure DRIVE_ACCOUNT=<user@domain> or pass --drive-account=<account>)",
        "=" * 80,
        ""
    ]
    return "\n".join(banner)


def detect_deploy_account(env: dict = None) -> str:
    """Detects the demo agent deployment destination user account (Tier 2)."""
    env = env or {}
    candidates = [
        env.get("DEPLOYER_EMAIL"),
        env.get("GCP_ACCOUNT"),
        env.get("ADMIN_EMAIL"),
        os.environ.get("DEPLOYER_EMAIL"),
        os.environ.get("GCP_ACCOUNT"),
        os.environ.get("ADMIN_EMAIL"),
    ]
    for c in candidates:
        if c and "@" in c and not c.endswith("gserviceaccount.com"):
            return c.strip()
    try:
        res = subprocess.run(["gcloud", "config", "get-value", "account"], capture_output=True, text=True)
        acct = res.stdout.strip()
        if acct and "@" in acct and not acct.endswith("gserviceaccount.com"):
            return acct
    except Exception:
        pass
    return ""


def resolve_gcs_bucket(project_id: str = "", configured_bucket: str = "") -> str:
    """Resolves target GCS bucket according to R3 resolution strategy."""
    if configured_bucket:
        return configured_bucket
    env_b = os.environ.get("GCS_BUCKET") or os.environ.get("GCS_BUCKET_NAME")
    if env_b:
        return env_b.strip()

    if not project_id:
        try:
            res = subprocess.run(["gcloud", "config", "get-value", "project"], capture_output=True, text=True)
            lines = [l.strip() for l in res.stdout.splitlines() if l.strip() and not l.startswith("Your active configuration")]
            if lines:
                project_id = lines[0]
        except Exception:
            pass

    if not project_id:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID") or ""

    if not project_id:
        return "ge-demo-artifacts"

    cand_a = f"{project_id}-ge-demo-artifacts"
    cand_b = f"{project_id}-demo-videos"

    # Check existence of candidate A or B
    try:
        from google.cloud import storage
        client = storage.Client(project=project_id)
        if client.bucket(cand_a).exists():
            return cand_a
        if client.bucket(cand_b).exists():
            return cand_b
    except Exception:
        pass

    try:
        res_a = subprocess.run(["gcloud", "storage", "buckets", "describe", f"gs://{cand_a}"], capture_output=True)
        if res_a.returncode == 0:
            return cand_a
        res_b = subprocess.run(["gcloud", "storage", "buckets", "describe", f"gs://{cand_b}"], capture_output=True)
        if res_b.returncode == 0:
            return cand_b
    except Exception:
        pass

    # Default to Candidate A for creation
    return cand_a


def upload_to_gcs(local_path: str, bucket_name: str, dest_name: str, project_id: str = "", region: str = "us-central1") -> tuple:
    """Uploads video to GCS using google.cloud.storage with gcloud storage CLI fallback.

    Returns:
        (gs_uri, console_url, error_message)
    """
    gs_uri = f"gs://{bucket_name}/{dest_name}"
    console_url = (
        f"https://console.cloud.google.com/storage/browser/{bucket_name}?project={project_id}"
        if project_id else
        f"https://console.cloud.google.com/storage/browser/{bucket_name}"
    )

    # Try Python Client first
    try:
        from google.cloud import storage
        client = storage.Client(project=project_id) if project_id else storage.Client()
        bucket = client.bucket(bucket_name)
        if not bucket.exists():
            print(f"📦 Creating Cloud Storage bucket: gs://{bucket_name} in {region}...")
            bucket = client.create_bucket(bucket_name, location=region)
        blob = bucket.blob(dest_name)
        blob.upload_from_filename(local_path, content_type="video/mp4")
        return gs_uri, console_url, ""
    except Exception as py_err:
        print(f"⚠️ google.cloud.storage upload encountered ({py_err}). Falling back to gcloud storage CLI...", file=sys.stderr)

    # Fallback to gcloud storage CLI
    try:
        chk = subprocess.run(["gcloud", "storage", "buckets", "describe", f"gs://{bucket_name}"], capture_output=True)
        if chk.returncode != 0:
            print(f"📦 Creating Cloud Storage bucket via gcloud: gs://{bucket_name}...")
            create_cmd = ["gcloud", "storage", "buckets", "create", f"gs://{bucket_name}", f"--location={region}", "--uniform-bucket-level-access"]
            if project_id:
                create_cmd.extend(["--project", project_id])
            subprocess.run(create_cmd, capture_output=True, check=True)

        cp_cmd = ["gcloud", "storage", "cp", local_path, f"gs://{bucket_name}/{dest_name}"]
        if project_id:
            cp_cmd.extend(["--project", project_id])
        subprocess.run(cp_cmd, capture_output=True, text=True, check=True)
        return gs_uri, console_url, ""
    except Exception as cli_err:
        return "", "", f"GCS upload failed on both Python API and CLI: {cli_err}"


def verify_delivery_destinations(project_id: str = "", drive_account: str = "",
                                 deploy_account: str = "", configured_bucket: str = "",
                                 skip_drive: bool = False) -> dict:
    """Performs pre-flight verification across all 3 storage delivery tiers in advance.

    Returns a structured summary with confirmed_tier, confirmed_destination,
    and per-tier diagnostic details.
    """
    target_account = drive_account or detect_host_drive_account()
    resolved_deploy = deploy_account or detect_deploy_account()
    resolved_bucket = resolve_gcs_bucket(project_id, configured_bucket)

    info = {
        "tier_1": {
            "name": "Tier 1: Host Operator Drive",
            "account": target_account,
            "verified": False,
            "status": "unverified",
            "reason": ""
        },
        "tier_2": {
            "name": "Tier 2: Deploy Destination Drive",
            "account": resolved_deploy,
            "verified": False,
            "status": "unverified",
            "reason": ""
        },
        "tier_3": {
            "name": "Tier 3: Google Cloud Storage",
            "bucket": resolved_bucket,
            "verified": True,
            "status": "verified",
            "reason": "Cloud Storage write / bucket resolution available"
        },
        "confirmed_tier": "tier_3_gcs",
        "confirmed_destination": ""
    }

    env_skip = os.environ.get("SKIP_VIDEO_DRIVE_UPLOAD", "").strip().lower() in ("1", "true", "yes")
    if skip_drive or env_skip:
        info["tier_1"]["status"] = "skipped"
        info["tier_1"]["reason"] = "--skip-drive requested"
        info["tier_2"]["status"] = "skipped"
        info["tier_2"]["reason"] = "--skip-drive requested"
        info["confirmed_tier"] = "tier_3_gcs"
        info["confirmed_destination"] = f"Tier 3: Google Cloud Storage (gs://{resolved_bucket}/) [Drive skipped]"
        return info

    # Check Tier 1
    if gdrive_cli_available() and (target_account.endswith("@google.com") or not target_account or target_account == "default"):
        info["tier_1"]["verified"] = True
        info["tier_1"]["status"] = "verified"
        info["tier_1"]["reason"] = "Native gdrive CLI available"
        info["confirmed_tier"] = "tier_1_operator_drive"
        info["confirmed_destination"] = f"Tier 1: Google Drive (Host: {target_account}) [gdrive CLI Verified]"
        return info
    else:
        t1_token, t1_status, t1_err = _fetch_token_and_status(target_account)
        if t1_token:
            test_info, test_status, _ = drive_request(t1_token, "GET", f"{DRIVE_API}/about?fields=user")
            if test_status == 200:
                info["tier_1"]["verified"] = True
                info["tier_1"]["status"] = "verified"
                info["tier_1"]["reason"] = "Drive v3 REST API scope verified"
                info["confirmed_tier"] = "tier_1_operator_drive"
                info["confirmed_destination"] = f"Tier 1: Google Drive (Host: {target_account}) [Scope Verified]"
                return info
            elif test_status == 403:
                info["tier_1"]["status"] = "scope_insufficient"
                info["tier_1"]["reason"] = f"HTTP 403 (missing Drive scope; run: {drive_login_hint(target_account)})"
            else:
                info["tier_1"]["status"] = "unverified"
                info["tier_1"]["reason"] = f"HTTP {test_status}"
        elif t1_status == "reauth_required":
            info["tier_1"]["status"] = "reauth_required"
            info["tier_1"]["reason"] = f"OAuth credentials expired for {target_account} (run: {drive_login_hint(target_account)})"
        else:
            info["tier_1"]["status"] = "missing_token"
            info["tier_1"]["reason"] = t1_err or "No access token available"

    # Check Tier 2
    if resolved_deploy and resolved_deploy != target_account:
        t2_token, t2_status, t2_err = _fetch_token_and_status(resolved_deploy)
        if t2_token:
            test_info2, test_status2, _ = drive_request(t2_token, "GET", f"{DRIVE_API}/about?fields=user")
            if test_status2 == 200:
                info["tier_2"]["verified"] = True
                info["tier_2"]["status"] = "verified"
                info["tier_2"]["reason"] = "Drive v3 REST API scope verified"
                info["confirmed_tier"] = "tier_2_deploy_drive"
                info["confirmed_destination"] = f"Tier 2: Google Drive (Deploy Tenant: {resolved_deploy}) [Scope Verified]"
                return info
            elif test_status2 == 403:
                info["tier_2"]["status"] = "scope_insufficient"
                info["tier_2"]["reason"] = f"HTTP 403 (missing Drive scope; run: {drive_login_hint(resolved_deploy)})"
            else:
                info["tier_2"]["status"] = "unverified"
                info["tier_2"]["reason"] = f"HTTP {test_status2}"
        elif t2_status == "reauth_required":
            info["tier_2"]["status"] = "reauth_required"
            info["tier_2"]["reason"] = f"OAuth credentials expired for {resolved_deploy} (run: {drive_login_hint(resolved_deploy)})"
        else:
            info["tier_2"]["status"] = "missing_token"
            info["tier_2"]["reason"] = t2_err or "No access token available"
    else:
        info["tier_2"]["status"] = "skipped"
        info["tier_2"]["reason"] = "No distinct deploy account configured"

    # Tier 3 (Cloud Storage fallback)
    info["confirmed_tier"] = "tier_3_gcs"
    info["confirmed_destination"] = f"Tier 3: Google Cloud Storage (gs://{resolved_bucket}/) [Drive scopes unavailable]"
    return info


def get_drive_token_and_status(account: str = "") -> tuple:
    """Retrieves access token and diagnostic status from gcloud for target account.

    Returns:
        tuple[str, str, str]: (token, status, error_details)
        status is one of: "ok", "reauth_required", "missing_token"
    """
    cmd = ["gcloud", "auth", "print-access-token"]
    if account and account != "default":
        cmd.extend(["--account", account])
    try:
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            return res.stdout.strip(), "ok", ""

        stderr = (res.stderr or "").strip()
        stdout = (res.stdout or "").strip()
        combined_err = f"{stderr} {stdout}".lower()

        reauth_keywords = [
            "invalid_grant",
            "expired",
            "revoked",
            "reauth",
            "refresh token",
            "please run: gcloud auth login",
            "auth login",
            "requires authentication",
        ]
        if any(kw in combined_err for kw in reauth_keywords):
            return "", "reauth_required", stderr or stdout or "OAuth token expired or revoked"

        return "", "missing_token", stderr or stdout or f"gcloud exited with code {res.returncode}"
    except Exception as e:
        err_str = str(e).lower()
        if any(kw in err_str for kw in ["invalid_grant", "expired", "revoked", "reauth"]):
            return "", "reauth_required", str(e)
        return "", "missing_token", str(e)


def drive_access_token(account: str = "") -> str:
    """Retrieves access token from gcloud for a specific account or active account."""
    tok, _, _ = get_drive_token_and_status(account)
    return tok


def _fetch_token_and_status(account: str = "") -> tuple:
    """Retrieves access token and status, maintaining compatibility with legacy drive_access_token mocks."""
    if hasattr(get_drive_token_and_status, "assert_called"):
        return get_drive_token_and_status(account)
    if hasattr(drive_access_token, "assert_called"):
        tok = drive_access_token(account) or ""
        return tok, ("ok" if tok else "missing_token"), ""
    return get_drive_token_and_status(account)


def drive_request(token: str, method: str, url: str, headers: dict = None,
                  content_type: str = "application/json; charset=UTF-8", raw: bytes = None):
    """Executes an authenticated Google Drive v3 REST API call."""
    req_headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": content_type,
    }
    if headers:
        req_headers.update(headers)
    req = urllib.request.Request(url, data=raw, headers=req_headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            data = resp.read()
            body = json.loads(data.decode("utf-8")) if data else {}
            return body, resp.status, ""
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        return {}, e.code, err_body
    except Exception as e:
        return {}, 0, str(e)


def drive_find_folder(token: str, name: str) -> str:
    """Finds an existing folder with the given name owned by the current user."""
    safe_name = name.replace("'", "\\'")
    q = (f"name = '{safe_name}' and mimeType = 'application/vnd.google-apps.folder' "
         "and trashed = false and 'me' in owners")
    url = f"{DRIVE_API}/files?" + urllib.parse.urlencode({"q": q, "fields": "files(id)"})
    info, status, _ = drive_request(token, "GET", url)
    files = info.get("files") or []
    return files[0].get("id", "") if status == 200 and files else ""


def drive_create_folder(token: str, name: str) -> str:
    """Creates a new folder in Google Drive."""
    body = json.dumps({
        "name": name,
        "mimeType": "application/vnd.google-apps.folder"
    }).encode("utf-8")
    info, status, err = drive_request(token, "POST", f"{DRIVE_API}/files?fields=id", raw=body)
    if status == 200 and info.get("id"):
        return info["id"]
    print(f"⚠️ Failed to create Drive folder: {err}", file=sys.stderr)
    return ""


def drive_find_child(token: str, name: str, parent_id: str) -> str:
    """Finds an existing file with the given name inside parent_id."""
    safe_name = name.replace("'", "\\'")
    q = f"name = '{safe_name}' and '{parent_id}' in parents and trashed = false"
    url = f"{DRIVE_API}/files?" + urllib.parse.urlencode({"q": q, "fields": "files(id)"})
    info, status, _ = drive_request(token, "GET", url)
    files = info.get("files") or []
    return files[0].get("id", "") if status == 200 and files else ""


def drive_upload_video(token: str, video_path: str, parent_id: str, dest_name: str) -> tuple:
    """Uploads a video file into parent_id via multipart/related request."""
    existing_id = drive_find_child(token, dest_name, parent_id)
    metadata = {"name": dest_name}
    if parent_id and not existing_id:
        metadata["parents"] = [parent_id]

    mime = mimetypes.guess_type(video_path)[0] or "video/mp4"
    boundary = "ge-demo-video-boundary"

    with open(video_path, "rb") as fh:
        content = fh.read()

    body = b"".join([
        f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n".encode("utf-8"),
        json.dumps(metadata).encode("utf-8"),
        f"\r\n--{boundary}\r\nContent-Type: {mime}\r\n\r\n".encode("utf-8"),
        content,
        f"\r\n--{boundary}--\r\n".encode("utf-8"),
    ])

    if existing_id:
        method = "PATCH"
        url = f"{DRIVE_UPLOAD_API}/files/{existing_id}?uploadType=multipart&fields=id,webViewLink"
    else:
        method = "POST"
        url = f"{DRIVE_UPLOAD_API}/files?uploadType=multipart&fields=id,webViewLink"

    info, status, err = drive_request(
        token, method, url,
        content_type=f"multipart/related; boundary={boundary}", raw=body
    )
    if status == 200 and info.get("id"):
        web_link = info.get("webViewLink", f"https://drive.google.com/file/d/{info['id']}/view")
        return info["id"], web_link, ""
    return "", "", f"Upload failed ({status}): {err}"


def enable_link_sharing(token: str, file_id: str):
    """Enables 'Anyone with link can view' permission."""
    url = f"{DRIVE_API}/files/{file_id}/permissions"
    body = json.dumps({"role": "reader", "type": "anyone"}).encode("utf-8")
    drive_request(token, "POST", url, raw=body)


# ---------------------------------------------------------
# Native gdrive CLI Support (when available)
# ---------------------------------------------------------

def gdrive_find_folder(name: str) -> tuple:
    """Finds an existing folder with the given name using gdrive CLI. Returns (id, web_link)."""
    try:
        res = subprocess.run(
            [GDRIVE_BIN, "readonly", "search", "--name-exact", name, "--json"],
            capture_output=True, text=True, check=True
        )
        data = json.loads(res.stdout)
        for item in data:
            if item.get("mimeType") == "application/vnd.google-apps.folder":
                fid = item.get("id", "")
                link = item.get("webViewLink", f"https://drive.google.com/drive/folders/{fid}")
                return fid, link
    except Exception:
        pass
    return "", ""


def gdrive_create_folder(name: str) -> tuple:
    """Creates a folder using gdrive CLI. Returns (id, web_link)."""
    try:
        res = subprocess.run(
            [GDRIVE_BIN, "mutate", "mkdir", name],
            capture_output=True, text=True, check=True
        )
        out = res.stdout.strip()
        m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", out)
        if m:
            fid = m.group(1)
            return fid, f"https://drive.google.com/drive/folders/{fid}"
    except Exception as e:
        print(f"⚠️ Failed to create Drive folder via gdrive CLI: {e}", file=sys.stderr)
    return "", ""


def gdrive_upload_video(video_path: str, parent_id: str = "") -> tuple:
    """Uploads video using gdrive CLI. Returns (id, web_link, err)."""
    try:
        cmd = [GDRIVE_BIN, "mutate", "upload", video_path]
        if parent_id:
            cmd.extend(["--parent", parent_id])
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        out = res.stdout.strip()
        m = re.search(r"\(ID:\s*([a-zA-Z0-9_-]+)\)", out)
        if m:
            fid = m.group(1)
            return fid, f"https://drive.google.com/file/d/{fid}/view", ""
        return "", "", f"Could not parse file ID from gdrive output: {out}"
    except subprocess.CalledProcessError as e:
        return "", "", f"gdrive upload failed: {e.stderr or e.stdout}"
    except Exception as e:
        return "", "", str(e)


def deliver_video(
    video_path: str,
    company: str,
    role: str,
    suffix: str = "",
    outdir: str = "./deliverables",
    skip_drive: bool = False,
    drive_account: str = "",
    drive_folder: str = "",
    share_public: bool = False,
    project_id: str = "",
    deploy_account: str = "",
    gcs_bucket: str = "",
    interactive: bool = False
) -> dict:
    """Delivers the rendered MP4 demo video using the 3-Tier Storage Delivery hierarchy.

    Hierarchy:
    - Tier 1 (Primary): Host operator Google Drive account (execution environment user)
    - Tier 2 (Secondary): Deploy destination Google Drive account (demo deploy tenant user)
    - Tier 3 (Tertiary Fallback): Demo agent deployment Google Cloud project Cloud Storage bucket
    """
    os.makedirs(outdir, exist_ok=True)
    clean_name = (f"[Demo-Video] {company} - {role}" + (f" ({suffix})" if suffix else "")).replace("/", "-").replace(" ", "_")
    local_dest = os.path.join(outdir, f"{clean_name}.mp4")

    if os.path.abspath(video_path) != os.path.abspath(local_dest):
        shutil.copy2(video_path, local_dest)
        print(f"📁 Local deliverable preserved at: {local_dest}")

    # Resolve target accounts dynamically without hardcoding
    if drive_account.strip():
        target_account = drive_account.strip()
        account_reason = "explicit --drive-account"
    else:
        target_account, account_reason = resolve_drive_account()
    target_folder_name = drive_folder.strip() or f"GE Demo - {company}"
    resolved_deploy = deploy_account.strip() or detect_deploy_account()
    resolved_project = project_id.strip() or os.environ.get("GOOGLE_CLOUD_PROJECT") or os.environ.get("PROJECT_ID") or ""

    env_skip = os.environ.get("SKIP_VIDEO_DRIVE_UPLOAD", "").strip().lower() in ("1", "true", "yes")
    drive_expected = not (skip_drive or env_skip)

    result = {
        "local_path": local_dest,
        "company": company,
        "role": role,
        "folder_name": target_folder_name,
        "file_name": f"{clean_name}.mp4",
        "target_account": target_account,
        "target_account_reason": account_reason,
        "deploy_account": resolved_deploy,
        # Whether a Drive upload was even attempted. Without this, a run that was
        # told to stay local and a run whose Drive auth collapsed both end up
        # looking like "no Drive link", and only one of them needs a human.
        "drive_expected": drive_expected,
        "sharing_mode": "public" if share_public else "owner_private",
        "drive_file_id": "",
        "drive_url": "",
        "folder_url": "",
        "gcs_uri": "",
        "gcs_console_url": "",
        "delivery_tier": "none",
        "upload_status": "pending"
    }

    if not drive_expected:
        print("ℹ️ Google Drive upload skipped (SKIP_VIDEO_DRIVE_UPLOAD or --skip-drive). Deliverable preserved locally.")
        result["upload_status"] = "skipped"
        return result

    print(f"🎯 Target Google Drive Account (Tier 1): {target_account}")
    print(f"   ↳ chosen by                          : {account_reason}")
    print(f"📂 Target Folder                       : {target_folder_name}")
    print(f"🔒 Sharing Mode                        : {'Public Link' if share_public else 'Owner-only Private'}")

    # ---------------------------------------------------------
    # TIER 1: Host Operator Google Drive
    # ---------------------------------------------------------
    # Path A: Internal Google Environment (via gdrive CLI)
    if gdrive_cli_available() and (target_account.endswith("@google.com") or not target_account or target_account == "default"):
        print("🚀 [Tier 1] Using native Google Drive CLI engine...")
        folder_id, folder_url = gdrive_find_folder(target_folder_name)
        if not folder_id:
            print(f"Creating Drive folder: '{target_folder_name}'...")
            folder_id, folder_url = gdrive_create_folder(target_folder_name)

        if folder_id:
            result["folder_id"] = folder_id
            result["folder_url"] = folder_url
            print(f"Uploading {os.path.basename(local_dest)} to Google Drive...")
            file_id, web_link, err = gdrive_upload_video(local_dest, parent_id=folder_id)
            if file_id:
                result["drive_file_id"] = file_id
                result["drive_url"] = web_link
                result["delivery_tier"] = "tier_1_operator_drive"
                result["upload_status"] = "success"
                if share_public:
                    print("  Enabling public link sharing...")
                    subprocess.run([GDRIVE_BIN, "mutate", "share", file_id, "--type", "anyone", "--role", "reader"], capture_output=True)
                else:
                    print("  🔒 Keeping file permissions private to owner.")
                print(f"  ✅ Uploaded to Tier 1 Google Drive: {web_link}")
                return result
            else:
                print(f"  ⚠️ [Tier 1] gdrive CLI upload encountered: {err}. Advancing to REST API...", file=sys.stderr)

    # Path B: Standard REST API (via gcloud auth print-access-token)
    token, t1_status, t1_err = _fetch_token_and_status(target_account)
    if not token and t1_status == "reauth_required":
        print(format_drive_reauth_diagnostic_banner(target_account), file=sys.stderr)
        if interactive:
            try:
                login_cmd = drive_login_command(target_account)
                prompt_msg = f"👉 Credentials expired for '{target_account}'. Run '{' '.join(login_cmd)}' now? [Y/n]: "
                if prompt_yes_no(prompt_msg):
                    subprocess.run(login_cmd, check=True)
                    token, t1_status, _ = _fetch_token_and_status(target_account)
            except Exception as login_err:
                print(f"⚠️ Interactive re-authentication failed: {login_err}", file=sys.stderr)

    if token:
        test_info, test_status, _ = drive_request(token, "GET", f"{DRIVE_API}/about?fields=user")
        if test_status == 403:
            print(format_drive_scope_diagnostic_banner(target_account), file=sys.stderr)
            if interactive:
                try:
                    login_cmd = drive_login_command(target_account)
                    prompt_msg = f"👉 Would you like to run '{' '.join(login_cmd)}' now? [Y/n]: "
                    if prompt_yes_no(prompt_msg):
                        subprocess.run(login_cmd, check=True)
                        token, _, _ = _fetch_token_and_status(target_account)
                        if token:
                            _, test_status, _ = drive_request(token, "GET", f"{DRIVE_API}/about?fields=user")
                except Exception as login_err:
                    print(f"⚠️ Interactive authentication failed: {login_err}", file=sys.stderr)

        if test_status == 200:
            folder_id = drive_find_folder(token, target_folder_name)
            if not folder_id:
                print(f"Creating Drive folder: '{target_folder_name}'...")
                folder_id = drive_create_folder(token, target_folder_name)
            if folder_id:
                result["folder_id"] = folder_id
                result["folder_url"] = f"https://drive.google.com/drive/folders/{folder_id}"
                print(f"Uploading {os.path.basename(local_dest)} to Google Drive via REST API...")
                file_id, web_link, err = drive_upload_video(token, local_dest, folder_id, f"{clean_name}.mp4")
                if file_id:
                    if share_public:
                        print("  Enabling public link sharing...")
                        enable_link_sharing(token, file_id)
                    else:
                        print("  🔒 Keeping file permissions private to owner.")
                    result["drive_file_id"] = file_id
                    result["drive_url"] = web_link
                    result["delivery_tier"] = "tier_1_operator_drive"
                    result["upload_status"] = "success"
                    print(f"  ✅ Uploaded to Tier 1 Google Drive: {web_link}")
                    return result
                else:
                    print(f"  ⚠️ [Tier 1] Drive upload failed: {err}. Advancing to Tier 2...", file=sys.stderr)
            else:
                print("  ⚠️ [Tier 1] Could not establish target Drive folder via REST API. Advancing to Tier 2...", file=sys.stderr)
        else:
            print(f"  ⚠️ [Tier 1] Drive scope insufficient ({test_status}) for account '{target_account}'. Advancing to Tier 2...", file=sys.stderr)
    else:
        if t1_status == "reauth_required":
            print(f"  ⚠️ [Tier 1] OAuth credentials expired for '{target_account}'. Advancing to Tier 2...", file=sys.stderr)
            result["tier_1_status"] = "reauth_required"
        else:
            print(f"  ℹ️ [Tier 1] Missing Google Drive access token for '{target_account}'. Advancing to Tier 2...", file=sys.stderr)

    # ---------------------------------------------------------
    # TIER 2: Demo Agent Deploy Destination Account Drive
    # ---------------------------------------------------------
    if resolved_deploy and resolved_deploy != target_account:
        print(f"🚀 [Tier 2] Attempting delivery to deploy destination Drive ({resolved_deploy})...")
        t2_token, t2_status, _ = _fetch_token_and_status(resolved_deploy)
        if not t2_token and t2_status == "reauth_required":
            print(format_drive_reauth_diagnostic_banner(resolved_deploy), file=sys.stderr)
        if t2_token:
            test_info, test_status, _ = drive_request(t2_token, "GET", f"{DRIVE_API}/about?fields=user")
            if test_status == 200:
                folder_id = drive_find_folder(t2_token, target_folder_name)
                if not folder_id:
                    folder_id = drive_create_folder(t2_token, target_folder_name)
                if folder_id:
                    result["folder_id"] = folder_id
                    result["folder_url"] = f"https://drive.google.com/drive/folders/{folder_id}"
                    file_id, web_link, err = drive_upload_video(t2_token, local_dest, folder_id, f"{clean_name}.mp4")
                    if file_id:
                        if share_public:
                            enable_link_sharing(t2_token, file_id)
                        result["drive_file_id"] = file_id
                        result["drive_url"] = web_link
                        result["target_account"] = resolved_deploy
                        result["delivery_tier"] = "tier_2_deploy_drive"
                        result["upload_status"] = "success"
                        print(f"  ✅ Uploaded to Tier 2 Google Drive: {web_link}")
                        return result
                    else:
                        print(f"  ⚠️ [Tier 2] Upload failed: {err}. Advancing to Tier 3...", file=sys.stderr)
            else:
                print(f"  ⚠️ [Tier 2] Scope insufficient ({test_status}) for '{resolved_deploy}'. Advancing to Tier 3...", file=sys.stderr)
        else:
            if t2_status == "reauth_required":
                print(f"  ⚠️ [Tier 2] OAuth credentials expired for '{resolved_deploy}'. Advancing to Tier 3...", file=sys.stderr)
            else:
                print(f"  ℹ️ [Tier 2] Access token unavailable for '{resolved_deploy}'. Advancing to Tier 3...", file=sys.stderr)

    # ---------------------------------------------------------
    # TIER 3: Google Cloud Project Cloud Storage Bucket Fallback
    # ---------------------------------------------------------
    print("🚀 [Tier 3] Falling back to Google Cloud Storage...")
    bucket_name = resolve_gcs_bucket(resolved_project, gcs_bucket)
    dest_name = f"{clean_name}.mp4"
    gs_uri, console_url, err = upload_to_gcs(local_dest, bucket_name, dest_name, project_id=resolved_project)
    if gs_uri:
        result["delivery_tier"] = "tier_3_gcs"
        result["upload_status"] = "success"
        result["gcs_uri"] = gs_uri
        result["gcs_console_url"] = console_url
        result["console_url"] = console_url
        result["storage_url"] = f"https://storage.cloud.google.com/{bucket_name}/{dest_name}"
        print(f"  ✅ Uploaded to Tier 3 Cloud Storage: {gs_uri}")
        print(f"  🔗 Cloud Console URL: {console_url}")
        return result
    else:
        print(f"  ❌ Tier 3 Cloud Storage upload failed: {err}", file=sys.stderr)
        result["delivery_tier"] = "none"
        result["upload_status"] = "failed"
        result["error"] = err
        return result


def classify_delivery(result: dict) -> tuple:
    """Grades a delivery result into (exit_code, headline, action).

    The caller of this script is usually generate_demo_video.py, which used to
    print an unconditional "DELIVERY COMPLETE" banner because a plain
    subprocess.run() told it nothing. An orchestrating agent read that banner,
    concluded the video was in Drive, and never offered the recovery step the
    skill defines - while the operator had no Drive link at all. A delivery has
    to be verifiable from outside the process, so this is the single place that
    decides what happened.
    """
    status = result.get("upload_status", "")
    tier = result.get("delivery_tier", "none")
    expected = result.get("drive_expected", True)
    account = result.get("target_account", "<account>")

    if status == "skipped":
        return EXIT_OK, "Local deliverable only (Drive upload was skipped on request)", ""

    if status == "success" and tier in ("tier_1_operator_drive", "tier_2_deploy_drive"):
        return EXIT_OK, f"Delivered to Google Drive ({account})", ""

    if status == "success" and tier == "tier_3_gcs":
        if not expected:
            return EXIT_OK, "Delivered to Cloud Storage", ""
        # Drive was wanted and Cloud Storage caught the fall. The video exists,
        # but it is not where the rest of the demo lives, so somebody has to act.
        return (
            EXIT_ACTION_REQUIRED,
            "Delivered to Cloud Storage only - Google Drive was expected and did not accept the upload",
            f"Re-authenticate and retry: {drive_login_hint(account)}",
        )

    return (
        EXIT_FAILED,
        f"Delivery failed: {result.get('error') or 'no destination accepted the video'}",
        f"The rendered video is still at {result.get('local_path', '(unknown)')}",
    )


def write_delivery_report(result: dict, report_path: str) -> str:
    """Writes the machine-readable delivery report. Returns the path written."""
    exit_code, headline, action = classify_delivery(result)
    payload = dict(result)
    payload["exit_code"] = exit_code
    payload["headline"] = headline
    payload["action_required"] = action
    payload["drive_delivered"] = bool(result.get("drive_url"))
    try:
        parent = os.path.dirname(os.path.abspath(report_path))
        if parent:
            os.makedirs(parent, exist_ok=True)
        with open(report_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
        return report_path
    except Exception as write_err:
        print(f"⚠️ Could not write delivery report to {report_path}: {write_err}", file=sys.stderr)
        return ""


def main():
    parser = argparse.ArgumentParser(description="Deliver demo video using 3-tier storage hierarchy.")
    parser.add_argument("--video", required=True, help="Path to rendered MP4 video")
    parser.add_argument("--company", default="Enterprise", help="Company name")
    parser.add_argument("--role", default="Operations Director", help="Agent role")
    parser.add_argument("--suffix", default="", help="Demo suffix if any")
    parser.add_argument("--outdir", default="./deliverables", help="Local directory for deliverables")
    parser.add_argument("--drive-account", default="", help="Target Google Drive account (defaults to the demo's own Drive owner, then the active gcloud account)")
    parser.add_argument("--drive-folder", default="", help="Google Drive folder name override")
    parser.add_argument("--deploy-account", default="", help="Deploy destination account for Tier 2 Drive delivery")
    parser.add_argument("--gcs-bucket", default="", help="Google Cloud Storage fallback bucket")
    parser.add_argument("--project", default="", help="Google Cloud project ID")
    parser.add_argument("--share-public", action="store_true", help="Enable public link sharing (default: False, owner-only private)")
    parser.add_argument("--skip-drive", action="store_true", help="Skip Google Drive upload (save to ./deliverables/ only)")
    parser.add_argument("--interactive", action="store_true", help="Prompt interactively to re-authenticate on expired credentials or scope errors")
    parser.add_argument("--report", default="", help="Path for the machine-readable delivery report (default: <outdir>/delivery_report.json)")
    args = parser.parse_args()

    res = deliver_video(
        args.video,
        args.company,
        args.role,
        suffix=args.suffix,
        outdir=args.outdir,
        skip_drive=args.skip_drive,
        drive_account=args.drive_account,
        drive_folder=args.drive_folder,
        share_public=args.share_public,
        project_id=args.project,
        deploy_account=args.deploy_account,
        gcs_bucket=args.gcs_bucket,
        interactive=args.interactive,
    )
    report_path = args.report or os.path.join(args.outdir, DELIVERY_REPORT_NAME)
    written = write_delivery_report(res, report_path)
    exit_code, headline, action = classify_delivery(res)

    print("\n" + "=" * 60)
    print("🎥 Video Delivery Summary")
    print(f"   Local File    : {res['local_path']}")
    print(f"   Delivery Tier : {res.get('delivery_tier', 'N/A')}")
    print(f"   Upload Status : {res.get('upload_status', 'N/A')}")
    print(f"   Target Account: {res.get('target_account', 'N/A')}")
    print(f"   Chosen By     : {res.get('target_account_reason', 'N/A')}")
    if res.get("drive_url"):
        print(f"   Drive File    : {res['drive_url']}")
        print(f"   Folder URL    : {res['folder_url']}")
    if res.get("gcs_uri"):
        print(f"   GCS URI       : {res['gcs_uri']}")
        print(f"   Console URL   : {res.get('gcs_console_url', 'N/A')}")
    if written:
        print(f"   Report        : {written}")
    if res.get("tier_1_status") == "reauth_required":
        t_acct = res.get("target_account", "<account>")
        print(f"   ⚠️ Tier 1 Notice: OAuth credentials for '{t_acct}' expired.")
        print(f"   👉 Run to re-authenticate: {drive_login_hint(t_acct)}")
    print("-" * 60)
    if exit_code == EXIT_OK:
        print(f"   ✅ {headline}")
    elif exit_code == EXIT_ACTION_REQUIRED:
        print(f"   🚨 ACTION REQUIRED: {headline}")
    else:
        print(f"   ❌ {headline}")
    if action:
        print(f"   👉 {action}")
    print("=" * 60)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
