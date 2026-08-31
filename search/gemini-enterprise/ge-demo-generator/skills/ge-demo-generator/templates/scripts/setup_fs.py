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


"""Seed the demo's Firestore operations collection.

The documents are NOT hardcoded here - this is a template. Phase 3 (data
generation) writes them to a JSON file and this script uploads them, so the
same script works for every domain.

Expected JSON shape (a list of {id, data} objects):

    [
      {
        "id": "TASK-0001",
        "data": {
          "title": "<short operational headline, in the demo's language>",
          "status": "REQUIRES_ACTION",        # REQUIRES_ACTION | IN_PROGRESS | RESOLVED
          "priority": "High",                 # High | Medium | Low
          "assigned_to": "<team or person>",
          "current_department": "<owning department>",
          "workflow_state": {
            "current_step": 2,
            "total_steps": 4,
            "pending_approval": true,
            "auto_actions_taken": ["<what the agent already did>"]
          },
          "notes": "<why this needs a human decision>"
          # ...plus whatever domain-specific fields the demo's scenario needs.
        }
      }
    ]

Usage:
    python3 scripts/setup_fs.py --docs data/firestore_seed.json
"""

import argparse
import json
import os
import sys

from google.cloud import firestore


def seed_firestore(project_id, collection_name, docs):
    db = None
    try:
        import subprocess
        from google.oauth2.credentials import Credentials
        token = subprocess.check_output(["gcloud", "auth", "print-access-token"], stderr=subprocess.DEVNULL).decode().strip()
        if token:
            creds = Credentials(token=token)
            db = firestore.Client(project=project_id, credentials=creds)
    except Exception as exc:
        print("   ⚠️  Could not use gcloud token for Firestore (%s); trying default credentials..." % exc)

    if db is None:
        db = firestore.Client(project=project_id) if project_id else firestore.Client()

    print("🔥 Seeding %d records into Firestore collection '%s'..."
          % (len(docs), collection_name))
    for rec in docs:
        doc_id = rec.get("id")
        data = rec.get("data", {})
        if not doc_id:
            print("   ⚠️  Skipping a record with no 'id'.")
            continue
        db.collection(collection_name).document(doc_id).set(data)
        print("   ✅ Inserted: %s - %s" % (doc_id, str(data.get("title", ""))[:40]))
    print("✨ Firestore seeding completed successfully.")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--project', default=os.environ.get('PROJECT_ID', ''))
    parser.add_argument('--collection',
                        default=os.environ.get('FIRESTORE_COLLECTION', 'demo_tasks'))
    parser.add_argument('--docs', default='data/firestore_seed.json',
                        help='JSON file holding the [{id, data}] seed documents.')
    args = parser.parse_args()

    if not os.path.exists(args.docs):
        print("❌ Seed file not found: %s" % args.docs)
        print("   Generate it in Phase 3 before running this script.")
        return 1

    with open(args.docs, encoding='utf-8') as f:
        docs = json.load(f)
    if not isinstance(docs, list):
        print("❌ %s must contain a JSON list of {id, data} objects." % args.docs)
        return 1

    seed_firestore(args.project, args.collection, docs)
    return 0


if __name__ == '__main__':
    sys.exit(main())
