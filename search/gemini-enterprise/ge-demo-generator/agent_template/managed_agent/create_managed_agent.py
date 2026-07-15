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

import json
import os
import sys
import time
import urllib.request
import urllib.error

PROJECT = os.environ.get('PROJECT_ID', '')
OUT_PATH = os.environ.get('MA_OUT', '/tmp/ma_result.txt')
MODE = sys.argv[1] if len(sys.argv) > 1 else 'start'
AGENT_ID = sys.argv[2] if len(sys.argv) > 2 else ''
TOKEN = sys.argv[3] if len(sys.argv) > 3 else ''
SKILLS_SOURCE = sys.argv[4] if len(sys.argv) > 4 else ''
API = 'https://aiplatform.googleapis.com/v1beta1'
BASE = API + '/projects/' + PROJECT + '/locations/global'
CREATE_TIMEOUT_S = 900
# The API accepts exactly ONE base agent version and offers no discovery
# endpoint. Overridable without regeneration via MA_BASE_AGENT; additionally,
# when the API rejects the pinned version it lists the supported values in
# the error message, and the code below self-heals by retrying with the
# newest dated version from that list.
BASE_AGENT = os.environ.get('MA_BASE_AGENT', 'antigravity-preview-05-2026')

def pick_latest_base_agent(err_text):
    marker = 'Supported values'
    pos = err_text.find(marker)
    if pos == -1 or 'base_agent' not in err_text:
        return ''
    parts = err_text[pos:].split(chr(39))
    cands = []
    for i, p in enumerate(parts):
        if i % 2 == 1 and p and ' ' not in p:
            cands.append(p)
    if not cands:
        return ''
    def version_key(name):
        bits = name.split('-')
        try:
            return (int(bits[-1]), int(bits[-2]))
        except Exception:
            return (0, 0)
    cands.sort(key=version_key)
    return cands[-1]

def call(method, url, body=None):
    data = None
    if body is not None:
        data = json.dumps(body).encode('utf-8')
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header('Authorization', 'Bearer ' + TOKEN)
    req.add_header('Content-Type', 'application/json')
    try:
        resp = urllib.request.urlopen(req, timeout=60)
        txt = resp.read().decode('utf-8')
        return resp.getcode(), (json.loads(txt) if txt else {})
    except urllib.error.HTTPError as e:
        txt = e.read().decode('utf-8', 'replace')
        try:
            return e.code, json.loads(txt)
        except Exception:
            return e.code, {'raw': txt[:300]}
    except Exception as e:
        return 0, {'error': str(e)[:300]}

def write_result(value):
    with open(OUT_PATH, 'w') as f:
        f.write(value)

write_result('')

if MODE == 'wait':
    deadline = time.time() + CREATE_TIMEOUT_S
    waited = 0
    while time.time() < deadline:
        code, _b = call('GET', BASE + '/agents/' + AGENT_ID)
        if code == 200:
            print('  Managed agent is ready.')
            write_result(AGENT_ID)
            sys.exit(0)
        time.sleep(10)
        waited += 10
        if waited % 60 == 0:
            print('  ... still provisioning (' + str(waited // 60) + ' min elapsed; typical: 8-10 min total)')
            sys.stdout.flush()
    print('  WARNING: agent did not become ready within ' + str(CREATE_TIMEOUT_S // 60) + ' min.')
    print('  It may still finish in the background - re-run this setup script later to pick it up.')
    sys.exit(0)

INSTR_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'managed_agent_instruction.txt')
with open(INSTR_PATH, 'r') as f:
    instruction = f.read().strip()

env = {'type': 'remote', 'network': {'allowlist': [{'domain': '*'}]}}
if SKILLS_SOURCE:
    env['sources'] = [{'type': 'gcs', 'source': SKILLS_SOURCE, 'target': '/.agent/skills'}]

config = {
    'system_instruction': instruction,
    'tools': [
        {'type': 'code_execution'},
        {'type': 'filesystem'},
        {'type': 'google_search'},
        {'type': 'url_context'},
    ],
    'base_environment': env,
}

code, body = call('GET', BASE + '/agents/' + AGENT_ID)
if code == 200:
    print('  Existing managed agent found - updating it in place...')
    mask = 'system_instruction,tools,base_environment'
    code, body = call('PATCH', BASE + '/agents/' + AGENT_ID + '?update_mask=' + mask, config)
    if code == 200:
        print('  Managed agent updated.')
        write_result('updated')
    else:
        print('  WARNING: in-place update failed (HTTP ' + str(code) + '); keeping the existing agent as-is.')
        write_result('existing')
    sys.exit(0)

payload = dict(config)
payload['id'] = AGENT_ID
payload['base_agent'] = BASE_AGENT
payload['description'] = 'Autonomous background worker for this demo (Antigravity harness).'

base_agent_swapped = False
for attempt in range(4):
    code, body = call('POST', BASE + '/agents', payload)
    if code == 200 and body.get('name'):
        print('  Create accepted (base agent: ' + payload['base_agent'] + ') - provisioning continues in the background (typical: 8-10 min).')
        write_result('accepted')
        sys.exit(0)
    if code == 429:
        time.sleep(20 * (attempt + 1))
        continue
    if code == 400 and not base_agent_swapped:
        newer = pick_latest_base_agent(json.dumps(body))
        if newer and newer != payload['base_agent']:
            print('  Pinned base agent ' + payload['base_agent'] + ' is no longer supported - retrying with ' + newer + '...')
            payload['base_agent'] = newer
            base_agent_swapped = True
            continue
    break

print('  WARNING: managed agent create was rejected (HTTP ' + str(code) + '): ' + json.dumps(body)[:300])
print('  The Managed Agents API is Pre-GA (no allowlist needed). Common causes:')
print('   - aiplatform.googleapis.com not enabled in this project')
print('   - missing roles/aiplatform.user on your account')
print('   - missing roles/aiplatform.serviceAgent on service-<PROJECT_NUMBER>@gcp-sa-aiplatform.iam.gserviceaccount.com')
print('  Docs: https://docs.cloud.google.com/gemini-enterprise-agent-platform/build/managed-agents')
