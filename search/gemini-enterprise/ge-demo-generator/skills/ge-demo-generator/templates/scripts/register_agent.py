# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     https://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Deployed as a runtime template into the user's Cloud Shell (not imported by
# repo tooling); validated by py_compile and end-to-end demo deployments.
# Repo-level strict lint/typing is intentionally skipped for this generated-
# origin runtime code; incremental typing is planned as follow-up.
# flake8: noqa
# pylint: skip-file
# mypy: ignore-errors
# ruff: noqa


import sys
import json
import urllib.request
import urllib.error

endpoint_loc = sys.argv[1]
project_id = sys.argv[2]
location = sys.argv[3]
app_id = sys.argv[4]
token = sys.argv[5]
agent_name = sys.argv[6]
agent_url = sys.argv[7]
if not agent_url.endswith("/a2a/app"):
    agent_url = f"{agent_url.rstrip('/')}/a2a/app"
agent_short_name = sys.argv[8]

one_sentence_summary = sys.argv[9]
auth_id = sys.argv[10] if len(sys.argv) > 10 else ""

endpoint = "discoveryengine.googleapis.com" if endpoint_loc == "global" else f"{endpoint_loc}-discoveryengine.googleapis.com"
url = f"https://{endpoint}/v1alpha/projects/{project_id}/locations/{location}/collections/default_collection/engines/{app_id}/assistants/default_assistant/agents"

headers = {
    "Authorization": f"Bearer {token}",
    "Content-Type": "application/json",
    "X-Goog-User-Project": project_id,
}

data = {
    "name": agent_name,
    "displayName": f"{agent_short_name} ({agent_name})",
    "description": one_sentence_summary,
    "a2aAgentDefinition": {
        "jsonAgentCard": json.dumps({
            "protocolVersion": "1.0",
            "name": agent_name,
            "description": one_sentence_summary,
            "url": agent_url,
            "version": "1.0.0",
            "defaultInputModes": ["text/plain"],
            "defaultOutputModes": ["text/plain", "application/json"],
            "capabilities": {
                "streaming": True,
                # GE does NOT fetch the live agent card at request time - it
                # reads THIS registered inline card. The A2UI version GE
                # requests in X-A2A-Extensions comes from here, so this MUST
                # stay in lockstep with _build_static_agent_card() in
                # fast_api_app.py. A stale v0.8 URI here made GE request v0.8
                # and silently ignore every v0.9 part (2026-08-19).
                "extensions": [
                    {
                        "uri": "https://a2ui.org/a2a-extension/a2ui/v0.9",
                        "description": "Provides agent driven UI using the A2UI JSON format.",
                        "params": {
                            "supportedCatalogIds": [
                                "https://www.gstatic.com/vertexaisearch/a2ui/v0_9/gemini_enterprise_composite_catalog.json"
                            ]
                        }
                    }
                ]
            },
            "preferredTransport": "JSONRPC",
            "skills": [
                {
                    "id": "general",
                    "name": "General Skill",
                    "description": "Handles general queries",
                    "tags": []
                }
            ]
        })
    }
}

import subprocess

# Resolve PROJECT_NUMBER for Discovery Engine Authorization resources
project_number = ""
if project_id.isdigit():
    project_number = project_id
else:
    try:
        res = subprocess.run(["gcloud", "projects", "describe", project_id, "--format=value(projectNumber)"], capture_output=True, text=True)
        if res.returncode == 0 and res.stdout.strip():
            project_number = res.stdout.strip()
    except Exception:
        pass
if not project_number:
    project_number = project_id

if auth_id:
    auth_slug = auth_id.split("/")[-1]
    # Authorization resources are ALWAYS created in "global" and require PROJECT_NUMBER
    data["authorizationConfig"] = { "agentAuthorization": f"projects/{project_number}/locations/global/authorizations/{auth_slug}" }
auth_path = data.get("authorizationConfig", {}).get("agentAuthorization", "")

def call(method, call_url, payload=None):
    body = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(call_url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req) as response:
            return response.getcode(), json.loads(response.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        return e.code, {"error": e.read().decode("utf-8", "replace")[:500]}
    except Exception as e:
        return 0, {"error": str(e)[:500]}

# Idempotent overwrite (v11.34): re-running the setup script for the SAME
# demo must UPDATE the existing registration (display name, description,
# agent card, auth binding) instead of failing with FAILED_PRECONDITION
# "authorization ... is used by another agent". Match by the agent card's
# internal name (the unique demo dirName - same matching the cleanup script
# uses); fall back to whichever agent holds this demo's authorization.
existing = ""
list_code, listing = call("GET", url + "?pageSize=100")
if list_code == 200:
    for a in listing.get("agents", []):
        try:
            card = json.loads((a.get("a2aAgentDefinition") or {}).get("jsonAgentCard") or "{}")
        except Exception:
            card = {}
        if card.get("name") == agent_name:
            existing = a.get("name", "")
            break
    if not existing and auth_path:
        for a in listing.get("agents", []):
            if (a.get("authorizationConfig") or {}).get("agentAuthorization", "") == auth_path:
                existing = a.get("name", "")
                break

def print_agent_id(resource_name):
    print("AGENT_ID:" + resource_name.split("/")[-1])

if existing:
    patch_body = dict(data)
    patch_body["name"] = existing
    patch_code, resp = call("PATCH", f"https://{endpoint}/v1alpha/{existing}", patch_body)
    if patch_code == 200:
        print("Updated the existing agent registration (overwrite deploy):")
        print(json.dumps(resp, indent=2))
        print_agent_id(resp.get("name", "") or existing)
        sys.exit(0)
    # PATCH semantics on this v1alpha surface are not guaranteed - fall back
    # to delete+create. NOTE: this changes the agent resource id (pinned
    # agents / conversation-thread association in the GE UI may reset).
    print(f"PATCH failed ({patch_code}): {resp.get('error', '')} - falling back to delete+create", file=sys.stderr)
    del_code, del_resp = call("DELETE", f"https://{endpoint}/v1alpha/{existing}")
    if del_code not in (200, 204):
        print(f"DELETE of the existing agent also failed ({del_code}): {del_resp.get('error', '')}", file=sys.stderr)
        sys.exit(1)

create_code, resp = call("POST", url, data)
if create_code == 200:
    print("Successfully registered agent:")
    print(json.dumps(resp, indent=2))
    print_agent_id(resp.get("name", ""))
    sys.exit(0)
print(f"Error registering agent ({create_code}): {resp.get('error', '')}", file=sys.stderr)
sys.exit(1)