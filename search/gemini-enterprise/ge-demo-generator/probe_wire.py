#!/usr/bin/env python3
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

"""Talk to a deployed demo agent the way Gemini Enterprise does, and print the wire.

When the Cloud Run logs are clean but Gemini Enterprise renders nothing, the
logs cannot help: everything they describe happened before serialization. This
sends a real A2A request with the Gemini Enterprise `X-A2A-Extensions` header and prints
what actually goes over the wire - the extension echo, and every part's kind,
`metadata.mimeType` and A2UI message key.

That is how the v0.9 migration's last bug was found: the parts were perfect and
the MIME was `application/a2ui+json`, which Gemini Enterprise ignores
(AGENTS.md section 13).

Examples:
    python3 probe_wire.py --service my-demo-agent
    python3 probe_wire.py --service my-demo-agent --mode send -m "show me a ranking table"
    python3 probe_wire.py --url https://.../a2a/app --save /tmp/wire

Checklist for a healthy v0.9 turn:
    response X-A2A-Extensions   ->  .../a2ui/v0.9   (blank = every card ignored)
    kind=data mimeType          ->  application/json+a2ui
    keys                        ->  createSurface, then updateComponents
    the final artifact-update   ->  repeats them; some clients render only that
"""

import argparse
import json
import subprocess
import sys
import urllib.error
import urllib.request

A2UI_EXT = 'https://a2ui.org/a2a-extension/a2ui/v0.9'
ADK_EXT = 'https://google.github.io/adk-docs/a2a/a2a-extension/'
GOOD_MIME = 'application/json+a2ui'
A2UI_KEYS = ('createSurface', 'updateComponents', 'updateDataModel', 'deleteSurface')


def run(cmd):
    return subprocess.run(cmd, capture_output=True, text=True, check=True).stdout.strip()


def resolve_url(service, region):
    """Look up a Cloud Run service URL and append the A2A RPC path."""
    url = run(['gcloud', 'run', 'services', 'describe', service,
               '--region', region, '--format', 'value(status.url)'])
    if not url:
        sys.exit('no such Cloud Run service: ' + service)
    return url.rstrip('/') + '/a2a/app'


def describe_part(part):
    """One line per part: what it is, and the two fields that decide rendering."""
    kind = part.get('kind')
    meta = part.get('metadata') or {}
    if kind == 'data':
        data = part.get('data') or {}
        keys = [k for k in A2UI_KEYS if k in data] or [
            k for k in data if k != 'version'] or ['(empty)']
        surfaces = ' '.join(
            str((data[k] or {}).get('surfaceId', '?'))
            for k in A2UI_KEYS if isinstance(data.get(k), dict))
        mime = meta.get('mimeType')
        # Only A2UI messages are judged on their MIME. A turn also carries ADK
        # function_call / function_response DataParts, which have no metadata at
        # all and are none of this tool's business.
        is_a2ui = 'version' in data or any(k in data for k in A2UI_KEYS)
        flag = '' if mime == GOOD_MIME or not is_a2ui else '   <-- Gemini Enterprise ignores this MIME'
        # Which components the turn actually used is the whole question when
        # verifying that MaterialTable replaced a nested-Row pseudo-table, or
        # that VegaChart replaced a generated PNG.
        comps = sorted({c.get('component') for c in
                        ((data.get('updateComponents') or {}).get('components') or [])
                        if isinstance(c, dict)} - {None})
        return ('data  mimeType=%s version=%s %s %s%s%s'
                % (mime, data.get('version'), ','.join(keys), surfaces,
                   ('  [' + ' '.join(comps) + ']') if comps else '', flag))
    if kind == 'text':
        return 'text  ' + repr((part.get('text') or '')[:70])
    if kind == 'file':
        f = part.get('file') or {}
        return 'file  mimeType=%s name=%s' % (f.get('mimeType'), f.get('name'))
    return str(kind) + '  ' + json.dumps(part)[:90]


def walk(obj, where, out):
    """Collect every 'parts' list anywhere in a payload, with its container key."""
    if isinstance(obj, dict):
        if isinstance(obj.get('parts'), list):
            out.append((where, obj['parts']))
        for key, value in obj.items():
            walk(value, key, out)
    elif isinstance(obj, list):
        for value in obj:
            walk(value, where, out)


def show(payload, where, indent='  '):
    found = []
    walk(payload, where, found)
    for container, parts in found:
        for part in parts:
            print(indent + '[' + container + '] ' + describe_part(part))
    return found


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    target = ap.add_mutually_exclusive_group(required=True)
    target.add_argument('--service', help='Cloud Run service name of the demo agent')
    target.add_argument('--url', help='full A2A RPC URL, e.g. https://.../a2a/app')
    ap.add_argument('--region', default='us-central1')
    ap.add_argument('-m', '--message', default='Hello')
    ap.add_argument('--press', metavar='JSON',
                    help='send a button press instead of text: the A2UI v0.9 action '
                         'object, e.g. \'{"name":"preflight_confirm_inline",'
                         '"context":{"prompt":"..."}}\'. This is the inbound DataPart '
                         'shape Gemini Enterprise posts back, and the only way '
                         'to reach anything behind the pre-flight gate.')
    ap.add_argument('--context-id', help='continue an existing conversation')
    ap.add_argument('--task-id', help='continue an existing task')
    ap.add_argument('--mode', choices=('stream', 'send'), default='stream',
                    help='stream = message/stream, what Gemini Enterprise uses')
    ap.add_argument('--ext', default=A2UI_EXT,
                    help='A2UI extension URI to request (use v0.8 to reproduce a '
                         'stale Discovery Engine registration)')
    ap.add_argument('--timeout', type=int, default=300)
    ap.add_argument('--save', help='write the raw response to this path prefix')
    args = ap.parse_args()

    url = args.url or resolve_url(args.service, args.region)
    method = 'message/stream' if args.mode == 'stream' else 'message/send'
    if args.press:
        action = json.loads(args.press)
        action.setdefault('surfaceId', 'probe-surface')
        action.setdefault('sourceComponentId', 'probe-button')
        part = {'kind': 'data', 'data': {'version': 'v0.9', 'action': action},
                'metadata': {'mimeType': GOOD_MIME}}
        print('press: ' + action.get('name', '?'))
    else:
        part = {'kind': 'text', 'text': args.message}
    message = {'role': 'user', 'messageId': 'probe-msg-1', 'parts': [part]}
    if args.context_id:
        message['contextId'] = args.context_id
    if args.task_id:
        message['taskId'] = args.task_id
    body = {'jsonrpc': '2.0', 'id': 'probe-1', 'method': method,
            'params': {'message': message}}

    req = urllib.request.Request(url, method='POST')
    req.add_header('Authorization', 'Bearer ' + run(['gcloud', 'auth',
                                                     'print-identity-token']))
    req.add_header('Content-Type', 'application/json')
    req.add_header('X-A2A-Extensions', args.ext + ', ' + ADK_EXT)
    req.add_header('Accept', 'text/event-stream' if args.mode == 'stream'
                   else 'application/json')

    print(method + ' ' + url)
    print('request  X-A2A-Extensions: ' + args.ext)
    try:
        resp = urllib.request.urlopen(req, json.dumps(body).encode(),
                                      timeout=args.timeout)
    except urllib.error.HTTPError as err:
        print('HTTP %s\n%s' % (err.code, err.read().decode('utf-8', 'replace')[:2000]))
        return 1

    with resp:
        echoed = resp.headers.get('X-A2A-Extensions', '')
        print('response X-A2A-Extensions: ' + (echoed or '(none)')
              + ('' if args.ext in echoed else
                 '   <-- NOT echoed: the extension is INACTIVE and every A2UI '
                 'part will be dropped by the client'))
        print('response Content-Type: ' + str(resp.headers.get('Content-Type')))
        print('-' * 72)

        if args.mode == 'send':
            payload = json.load(resp)
            show(payload, 'result')
            if args.save:
                open(args.save + '.json', 'w').write(json.dumps(payload, indent=2))
                print('\n' + 'raw -> ' + args.save + '.json')
            return 0

        raw, count = [], 0
        for line in resp:
            line = line.decode('utf-8', 'replace')
            raw.append(line)
            if not line.startswith('data:'):
                continue
            count += 1
            try:
                event = json.loads(line[5:].strip())
            except ValueError as err:
                print('event %d: unparseable (%s)' % (count, err))
                continue
            result = event.get('result', event)
            extra = ''
            if result.get('kind') == 'artifact-update':
                extra = ' append=%s lastChunk=%s' % (result.get('append'),
                                                     result.get('lastChunk'))
            print('event %d: kind=%s%s' % (count, result.get('kind', '?'), extra))
            show(result, result.get('kind', '?'), indent='    ')
        if args.save:
            open(args.save + '.sse', 'w').write(''.join(raw))
            print('\n' + 'raw -> ' + args.save + '.sse')
        print('\n%d SSE events' % count)
    return 0


if __name__ == '__main__':
    sys.exit(main())
