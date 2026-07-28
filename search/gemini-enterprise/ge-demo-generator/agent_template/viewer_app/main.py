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

import os
import time
import uuid
from flask import Flask, render_template_string, jsonify, request
from google.cloud import firestore

app = Flask(__name__)
db = firestore.Client()
COLLECTION = "__GE_FS_COLLECTION__"

_TEMPLATES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "templates")

def _load_template(_name):
    # Served as-is (no Jinja): the pages' inline JavaScript contains brace
    # sequences, and per-demo values are substituted into the files by the
    # setup script before deployment.
    with open(os.path.join(_TEMPLATES_DIR, _name), encoding="utf-8") as _f:
        return "\n" + _f.read()

HTML_TEMPLATE = _load_template("viewer.html")

@app.route('/')
def index():
    return HTML_TEMPLATE

_FS_SCALAR_KEYS = ("stringValue", "booleanValue", "timestampValue", "bytesValue", "referenceValue", "geoPointValue")

def _decode_fs_value(v):
    # Records may be written with raw Firestore REST typed-value wrappers
    # (e.g. {"stringValue": "X"}) stored literally as map fields. Unwrap them to
    # native values so the dashboard never receives an object where it expects a
    # scalar (which would otherwise abort rendering and freeze the KPIs/charts).
    if isinstance(v, dict):
        ks = list(v.keys())
        if len(ks) == 1:
            k = ks[0]
            inner = v[k]
            if k in _FS_SCALAR_KEYS:
                return inner
            if k == "nullValue":
                return None
            if k == "integerValue":
                try:
                    return int(inner)
                except Exception:
                    return inner
            if k == "doubleValue":
                try:
                    return float(inner)
                except Exception:
                    return inner
            if k == "mapValue":
                fields = (inner or {}).get("fields", {}) if isinstance(inner, dict) else {}
                return {kk: _decode_fs_value(vv) for kk, vv in (fields or {}).items()}
            if k == "arrayValue":
                vals = (inner or {}).get("values", []) if isinstance(inner, dict) else []
                return [_decode_fs_value(x) for x in (vals or [])]
        return {kk: _decode_fs_value(vv) for kk, vv in v.items()}
    if isinstance(v, list):
        return [_decode_fs_value(x) for x in v]
    return v

@app.route('/api/data')
def get_data():
    docs = db.collection(COLLECTION).stream()
    data = []
    for doc in docs:
        doc_dict = _decode_fs_value(doc.to_dict() or {})
        if "updated_at" not in doc_dict or not doc_dict["updated_at"]:
            try:
                doc_dict["updated_at"] = doc.update_time.isoformat()
            except Exception:
                if hasattr(doc, 'create_time') and doc.create_time:
                    doc_dict["updated_at"] = doc.create_time.isoformat()
                else:
                    doc_dict["updated_at"] = ""
        data.append({"id": doc.id, "data": doc_dict})
    return jsonify(data)

@app.route('/api/create', methods=['POST'])
def create_data():
    req = request.json
    doc_id = req.get('id')
    doc_data = req.get('data', {})
    if doc_id:
        db.collection(COLLECTION).document(doc_id).set(doc_data)
    return jsonify({"success": True})

@app.route('/api/update', methods=['POST'])
def update_data():
    req = request.json
    doc_id = req.get('id')
    new_status = req.get('status')
    if doc_id and new_status:
        db.collection(COLLECTION).document(doc_id).update({"status": new_status})
    return jsonify({"success": True})

@app.route('/api/delete', methods=['POST'])
def delete_data():
    req = request.json
    doc_id = req.get('id')
    if doc_id:
        db.collection(COLLECTION).document(doc_id).delete()
    return jsonify({"success": True})

# --- Task Management API ---
DEMO_ID = os.environ.get("DEMO_ID", "")

@app.route('/api/tasks')
def list_tasks():
    if not DEMO_ID:
        return jsonify({"tasks": [], "error": "DEMO_ID not set"})
    defs_col = DEMO_ID + "_task_definitions"
    execs_col = DEMO_ID + "_task_executions"
    defs = {d.id: d.to_dict() for d in db.collection(defs_col).stream()}
    execs = {d.id: d.to_dict() for d in db.collection(execs_col).stream()}
    tasks = []
    for tid, defn in defs.items():
        ex = execs.get(tid, {})
        tasks.append({
            "task_id": tid,
            "task_name": defn.get("task_name", ""),
            "task_description": defn.get("task_description", ""),
            "task_type": defn.get("task_type", "immediate"),
            "schedule_cron": defn.get("schedule_cron", ""),
            "created_at": defn.get("created_at", ""),
            "status": ex.get("status") or ("scheduled" if defn.get("task_type") == "scheduled" else "unknown"),
            "progress_pct": ex.get("progress_pct", 0),
            "result_summary": ex.get("result_summary", "")[:300],
            "log_tail": ex.get("log_tail", "")[:200],
            "started_at": ex.get("started_at", ""),
            "completed_at": ex.get("completed_at", ""),
        })
    tasks.sort(key=lambda t: t.get("created_at", ""), reverse=True)
    return jsonify({"tasks": tasks})

@app.route('/api/tasks/<task_id>')
def get_task(task_id):
    if not DEMO_ID:
        return jsonify({"error": "DEMO_ID not set"}), 400
    defn = db.collection(DEMO_ID + "_task_definitions").document(task_id).get()
    ex = db.collection(DEMO_ID + "_task_executions").document(task_id).get()
    if not defn.exists:
        return jsonify({"error": "Task not found"}), 404
    d = defn.to_dict()
    e = ex.to_dict() if ex.exists else {}
    return jsonify({
        "task_id": task_id,
        "task_name": d.get("task_name", ""),
        "task_description": d.get("task_description", ""),
        "task_prompt": d.get("task_prompt", ""),
        "task_type": d.get("task_type", "immediate"),
        "schedule_cron": d.get("schedule_cron", ""),
        "created_at": d.get("created_at", ""),
        "status": e.get("status", "unknown"),
        "progress_pct": e.get("progress_pct", 0),
        "result_summary": e.get("result_summary", ""),
        "log_tail": e.get("log_tail", ""),
        "started_at": e.get("started_at", ""),
        "completed_at": e.get("completed_at", ""),
    })

@app.route('/api/tasks/<task_id>/cancel', methods=['POST'])
def cancel_task(task_id):
    if not DEMO_ID:
        return jsonify({"error": "DEMO_ID not set"}), 400
    ref = db.collection(DEMO_ID + "_task_executions").document(task_id)
    doc = ref.get()
    if not doc.exists:
        return jsonify({"error": "Task not found"}), 404
    s = doc.to_dict().get("status", "")
    if s in ("completed", "failed", "cancelled"):
        return jsonify({"error": "Task already in terminal state: " + s}), 400
    ref.update({"status": "cancelled"})
    return jsonify({"success": True, "task_id": task_id})

@app.route('/api/tasks/<task_id>', methods=['DELETE'])
def delete_task(task_id):
    if not DEMO_ID:
        return jsonify({"error": "DEMO_ID not set"}), 400
    # Check if this is a scheduled task — if so, delete Cloud Scheduler job too
    defn_ref = db.collection(DEMO_ID + "_task_definitions").document(task_id)
    defn_doc = defn_ref.get()
    if defn_doc.exists:
        defn_data = defn_doc.to_dict()
        if defn_data.get("task_type") == "scheduled":
            try:
                from google.cloud import scheduler_v1
                _sc = scheduler_v1.CloudSchedulerClient()
                _pid = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
                _reg = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
                if _reg == "global":
                    _reg = "us-central1"
                _jn = "projects/" + _pid + "/locations/" + _reg + "/jobs/" + DEMO_ID + "-sched-" + task_id
                _sc.delete_job(name=_jn)
            except Exception:
                pass  # Job may not exist
    defn_ref.delete()
    db.collection(DEMO_ID + "_task_executions").document(task_id).delete()
    return jsonify({"success": True, "task_id": task_id})

@app.route('/api/activity')
def list_activity():
    if not DEMO_ID:
        return jsonify({"activities": [], "error": "DEMO_ID not set"})
    col_name = DEMO_ID + "_activity_log"
    try:
        docs = db.collection(col_name).order_by("timestamp", direction=firestore.Query.DESCENDING).limit(50).stream()
        activities = []
        for doc in docs:
            d = doc.to_dict()
            activities.append({
                "id": doc.id,
                "source": d.get("source", "unknown"),
                "operation": d.get("operation", ""),
                "target": d.get("target", ""),
                "detail": d.get("detail", ""),
                "rows_affected": d.get("rows_affected", 0),
                "timestamp": d.get("timestamp", ""),
                "status": d.get("status", "success"),
            })
        return jsonify({"activities": activities})
    except Exception as _e:
        return jsonify({"activities": [], "error": str(_e)})

# --- Computer Use live-view (screencast of the sandbox browser) ---
BROWSER_VIEW_HTML = _load_template("browser_view.html")

@app.route('/browser-view')
def browser_view():
    return render_template_string(BROWSER_VIEW_HTML, session_id=request.args.get("session", ""))

@app.route('/api/browser/<session_id>')
def api_browser(session_id):
    if not DEMO_ID:
        return jsonify({"error": "DEMO_ID not set"}), 400
    doc = db.collection(DEMO_ID + "_browser_sessions").document(session_id).get()
    if not doc.exists:
        return jsonify({"status": "unknown", "step": 0, "intent": "", "url": "", "screenshot_b64": ""})
    d = doc.to_dict()
    return jsonify({
        "status": d.get("status", ""),
        "step": d.get("step", 0),
        "intent": d.get("intent", ""),
        "url": d.get("url", ""),
        "screenshot_b64": d.get("screenshot_b64", ""),
        "confirm_action": d.get("confirm_action", ""),
        "confirm_category": d.get("confirm_category", ""),
        "updated_at": d.get("updated_at", ""),
    })

@app.route('/api/browser/<session_id>/decision', methods=['POST'])
def api_browser_decision(session_id):
    if not DEMO_ID:
        return jsonify({"error": "DEMO_ID not set"}), 400
    body = request.get_json(silent=True) or {}
    decision = body.get("decision", "") or request.args.get("decision", "")
    if decision not in ("approved", "rejected"):
        return jsonify({"error": "decision must be approved or rejected"}), 400
    db.collection(DEMO_ID + "_browser_sessions").document(session_id).set({"confirm_decision": decision}, merge=True)
    return jsonify({"success": True, "decision": decision})

def main(request):
    with app.request_context(request.environ):
        try:
            return app.full_dispatch_request()
        except Exception as e:
            return str(e), 500

