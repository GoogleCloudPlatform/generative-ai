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

import datetime
import json
import os
import sys
import time
import urllib.request
import urllib.error

PROJECT = os.environ.get('PROJECT_ID', '')
OUT_PATH = os.environ.get('MA_OUT', '/tmp/ma_env_id.txt')
STATE_COLL = os.environ.get('MA_STATE_COLL', '')
AGENT_ID = sys.argv[1] if len(sys.argv) > 1 else ''
TOKEN = sys.argv[2] if len(sys.argv) > 2 else ''
SKILLS_SOURCE = sys.argv[3] if len(sys.argv) > 3 else ''
URL = 'https://aiplatform.googleapis.com/v1beta1/projects/' + PROJECT + '/locations/global/interactions'

# The interaction-level environment does NOT inherit the agent's
# base_environment (verified live 2026-07-12): a bare remote spec yields a
# standard sandbox WITHOUT skills, and sources without network are rejected.
# So the warm-up restates the full spec; the resulting environment (with the
# skills mounted) is then reused by the runtime via its env id.
env_spec = {'type': 'remote', 'network': {'allowlist': [{'domain': '*'}]}}
if SKILLS_SOURCE:
    env_spec['sources'] = [{'type': 'gcs', 'source': SKILLS_SOURCE, 'target': '/.agent/skills'}]

payload = {
    'agent': AGENT_ID,
    'stream': True,
    'background': True,
    'store': True,
    'environment': env_spec,
    'input': [{'type': 'user_input', 'content': [{'type': 'text', 'text': 'Warm-up and toolchain preparation (installs persist in this environment, so later tasks start with the stack ready): 1) run: pip install python-pptx python-docx reportlab matplotlib japanize-matplotlib pypdf 2) install the Google Workspace CLI static binary (do NOT use npm - its Linux build needs GLIBC 2.39 and this sandbox has an older one) by running: mkdir -p $HOME/bin && curl -sL https://github.com/googleworkspace/cli/releases/latest/download/google-workspace-cli-x86_64-unknown-linux-musl.tar.gz | tar xz -C $HOME/bin ./gws && chmod +x $HOME/bin/gws - then run: $HOME/bin/gws --version. Reply with a single line stating which installs succeeded (include the gws version string if available). If any install fails, note it in the reply and move on (do not retry more than once); if everything fails, reply with the word ready.'}]}],
}

def find_env_id(node):
    if isinstance(node, dict):
        for key, value in node.items():
            if key == 'environment_id' and isinstance(value, str) and value:
                return value
            found = find_env_id(value)
            if found:
                return found
    elif isinstance(node, list):
        for item in node:
            found = find_env_id(item)
            if found:
                return found
    return None

req = urllib.request.Request(URL, data=json.dumps(payload).encode('utf-8'), method='POST')
req.add_header('Authorization', 'Bearer ' + TOKEN)
req.add_header('Content-Type', 'application/json')
req.add_header('Api-Revision', '2026-05-20')

env_id = ''
deadline = time.time() + 360
try:
    resp = urllib.request.urlopen(req, timeout=360)
    for raw in resp:
        if time.time() > deadline:
            break
        line = raw.decode('utf-8', 'replace').strip()
        if not line.startswith('data:'):
            continue
        try:
            event = json.loads(line[5:].strip())
        except Exception:
            continue
        found = find_env_id(event)
        if found:
            env_id = found
            break
except Exception as e:
    print('  warm-up error: ' + str(e)[:200])

if env_id and STATE_COLL and PROJECT:
    doc_url = ('https://firestore.googleapis.com/v1/projects/' + PROJECT
               + '/databases/(default)/documents/' + STATE_COLL + '/current')
    doc = {'fields': {
        'environment_id': {'stringValue': env_id},
        'updated_at': {'stringValue': datetime.datetime.now(datetime.timezone.utc).isoformat()},
    }}
    try:
        fsreq = urllib.request.Request(doc_url, data=json.dumps(doc).encode('utf-8'), method='PATCH')
        fsreq.add_header('Authorization', 'Bearer ' + TOKEN)
        fsreq.add_header('Content-Type', 'application/json')
        urllib.request.urlopen(fsreq, timeout=30)
        print('  Environment id stored in Firestore (' + STATE_COLL + '/current).')
    except Exception as e:
        print('  WARNING: could not store environment id in Firestore: ' + str(e)[:200])

with open(OUT_PATH, 'w') as f:
    f.write(env_id)
