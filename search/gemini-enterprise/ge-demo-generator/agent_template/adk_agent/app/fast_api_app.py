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

import os
import logging
import asyncio
import ast as _ast
import re
import json
import time
import contextvars
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import datetime, timezone
import uuid

import google.auth
from a2a.server.apps import A2AFastAPIApplication
from a2a.server.request_handlers import DefaultRequestHandler
from a2a.server.tasks import InMemoryTaskStore
from a2a.types import AgentCapabilities, AgentCard, Artifact, Message, Role, TaskArtifactUpdateEvent, TaskState, TaskStatus, TaskStatusUpdateEvent
from a2a.server.agent_execution import RequestContext
from a2a.server.events.event_queue import EventQueue
from a2a.utils.constants import (
    AGENT_CARD_WELL_KNOWN_PATH,
    EXTENDED_AGENT_CARD_PATH,
)
from fastapi import FastAPI
from google.adk.a2a.executor.a2a_agent_executor import A2aAgentExecutor
from google.adk.a2a.converters.utils import _get_adk_metadata_key
from google.adk.a2a.utils.agent_card_builder import AgentCardBuilder
from google.adk.artifacts import InMemoryArtifactService
from google.adk.apps.app import App, EventsCompactionConfig
from google.adk.plugins import ReflectAndRetryToolPlugin, LoggingPlugin
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.cloud import logging as google_cloud_logging
from google.genai import types as genai_types
from a2a import types as a2a_types
from a2ui.schema.constants import VERSION_0_8
from a2ui.schema.manager import A2uiSchemaManager
from a2ui.basic_catalog.provider import BasicCatalog
from a2ui.parser.streaming import A2uiStreamParser
from a2ui.parser.response_part import ResponsePart
from a2ui.a2a.parts import create_a2ui_part as _original_create_a2ui_part
from a2ui.a2a.extension import get_a2ui_agent_extension

def _find_balanced_block(text: str, start_pos: int, open_char: str = '{', close_char: str = '}') -> int:
    # Find the end position (exclusive) of a balanced block starting from start_pos.
    depth = 0
    in_string = False
    string_char = None
    escaped = False
    
    for i in range(start_pos, len(text)):
        c = text[i]
        if escaped:
            escaped = False
            continue
        if c == '\\':
            escaped = True
            continue
        if in_string:
            if c == string_char:
                in_string = False
            continue
        if c == chr(34) or c == chr(39):
            in_string = True
            string_char = c
            continue
        if c == open_char:
            depth += 1
        elif c == close_char:
            depth -= 1
            if depth == 0:
                return i + 1
    return -1

def _parse_loose_json(sub_str: str):
    # Try to parse a string as JSON, falling back to ast.literal_eval for Python dicts.
    try:
        import json as _json_local
        return _json_local.loads(sub_str)
    except Exception:
        pass
        
    try:
        return _ast.literal_eval(sub_str)
    except Exception:
        pass
        
    return None

def _rewrite_suggestions_a2ui(msg):
    """Insert spacer before button groups in A2UI surfaces.
    Two strategies:
    1. surfaceId='suggestions': Wrap in Column with spacer (proven v10.32 approach)
    2. Other surfaces: Find existing Column and insert spacer before button children
    """
    if not isinstance(msg, dict):
        return msg

    # --- Strategy 1: suggestions surface (flat button list) ---
    # Wrap with a Column that has a spacer above the original root.
    if "beginRendering" in msg:
        _br = msg["beginRendering"]
        if _br.get("surfaceId") == "suggestions" and _br.get("root") == "root":
            _br["root"] = "suggestions_wrapper"
        return msg

    if "surfaceUpdate" not in msg:
        return msg

    _su = msg["surfaceUpdate"]
    _comps = _su.get("components", [])
    if not _comps:
        return msg

    if _su.get("surfaceId") == "suggestions":
        _has_wrapper = any(c.get("id") == "suggestions_wrapper" for c in _comps)
        if not _has_wrapper:
            _has_root = any(c.get("id") == "root" for c in _comps)
            if _has_root:
                _wrapper = {
                    "id": "suggestions_wrapper",
                    "component": {
                        "Column": {
                            "children": {"explicitList": ["suggestions_spacer", "root"]},
                            "alignment": "stretch",
                            "distribution": "start"
                        }
                    }
                }
                _spacer = {
                    "id": "suggestions_spacer",
                    "component": {
                        "Text": {
                            "text": {"literalString": " "},
                            "usageHint": "body"
                        }
                    }
                }
                _comps.insert(0, _wrapper)
                _comps.insert(1, _spacer)
        return msg

    # --- Strategy 2: other surfaces (Card + buttons in same surface) ---
    # Find the first Column and insert spacer before button children.
    _cmap = {}
    for _c in _comps:
        if isinstance(_c, dict) and _c.get('id'):
            _cmap[_c['id']] = _c

    def _leads_to_buttons(_child_id):
        _cc = _cmap.get(_child_id, {}).get('component', {})
        if 'Button' in _cc:
            return True
        if 'Row' in _cc:
            _rc = _cc['Row'].get('children', {}).get('explicitList', [])
            return any('Button' in _cmap.get(_r, {}).get('component', {}) for _r in _rc if _r in _cmap)
        return False

    for _c in _comps:
        _ct = _c.get('component', {})
        if 'Column' not in _ct:
            continue
        _children = _ct['Column'].get('children', {}).get('explicitList')
        if not _children or len(_children) < 2:
            break

        _btn_start = None
        for _i, _cid in enumerate(_children):
            if _leads_to_buttons(_cid):
                _btn_start = _i
                break

        if _btn_start is not None and _btn_start > 0:
            _sp_id = 'sp_' + _c.get('id', 'root')
            _children.insert(_btn_start, _sp_id)
            _comps.append({
                'id': _sp_id,
                'component': {
                    'Text': {
                        'text': {'literalString': ' '},
                        'usageHint': 'body'
                    }
                }
            })
        break

    return msg

def _heal_buttons_in_a2ui(msg):
    if not isinstance(msg, dict):
        return msg
    if 'surfaceUpdate' in msg:
        su = msg['surfaceUpdate']
        if 'components' in su and isinstance(su['components'], list):
            comps = su['components']
            new_comps = []
            for comp in comps:
                if not isinstance(comp, dict):
                    continue
                if 'component' in comp and isinstance(comp['component'], dict):
                    c_type = list(comp['component'].keys())[0] if comp['component'] else None
                    if c_type == 'Button':
                        btn = comp['component']['Button']
                        if isinstance(btn, dict):
                            # Capture and remove accidental usageHint on the Button component itself to prevent validation failure
                            btn_usage_hint = btn.pop('usageHint', None)
                            
                            has_child = 'child' in btn
                            label_val = btn.get('label') or btn.get('text')
                            
                            if has_child and isinstance(btn['child'], dict):
                                child_obj = btn['child']
                                c_type = list(child_obj.keys())[0] if child_obj else None
                                if c_type == 'Text':
                                    text_body = child_obj['Text']
                                    if isinstance(text_body, dict) and 'usageHint' not in text_body:
                                        if btn_usage_hint:
                                            text_body['usageHint'] = btn_usage_hint
                                        else:
                                            text_body['usageHint'] = 'body'
                                    
                                    parent_id = comp.get('id') or 'btn'
                                    child_id = parent_id + '_lbl'
                                    btn['child'] = child_id
                                    new_text = {
                                        'id': child_id,
                                        'component': child_obj
                                    }
                                    new_comps.append(new_text)
                            elif not has_child and label_val:
                                label_str = ''
                                if isinstance(label_val, dict):
                                    label_str = label_val.get('literalString') or ''
                                else:
                                    label_str = str(label_val)
                                if label_str:
                                    parent_id = comp.get('id') or 'btn'
                                    child_id = parent_id + '_lbl'
                                    btn['child'] = child_id
                                    if 'label' in btn:
                                        del btn['label']
                                    if 'text' in btn:
                                        del btn['text']
                                    
                                    # Use the captured usageHint for the child Text component, or default to 'body'
                                    target_hint = btn_usage_hint if btn_usage_hint else 'body'
                                    
                                    new_text = {
                                        'id': child_id,
                                        'component': {
                                            'Text': {
                                                'text': { 'literalString': label_str },
                                                'usageHint': target_hint
                                            }
                                        }
                                    }
                                    new_comps.append(new_text)
            comps.extend(new_comps)

            # --- Dangling-label pass (v11.4) ---
            # A Button whose 'child' is a string id with NO matching component in
            # this surfaceUpdate renders as an EMPTY pill in GE (confirmed live
            # 2026-07-15: Next Actions chips showed as blank blue ovals because
            # the model emitted the Buttons but omitted their label Text
            # components). Synthesize the missing Text from the button's own
            # label/text property, a literalString nested in an inline child
            # object, or its sendText context text (every chip carries one),
            # truncated to a chip-sized label.
            _defined_ids = set()
            for _dc in comps:
                if isinstance(_dc, dict) and isinstance(_dc.get('id'), str):
                    _defined_ids.add(_dc['id'])
            def _find_literal(_n):
                if isinstance(_n, dict):
                    _ls = _n.get('literalString')
                    if isinstance(_ls, str) and _ls.strip():
                        return _ls
                    for _v in _n.values():
                        _r = _find_literal(_v)
                        if _r:
                            return _r
                elif isinstance(_n, list):
                    for _v in _n:
                        _r = _find_literal(_v)
                        if _r:
                            return _r
                return ''
            _extra_labels = []
            for comp in comps:
                if not isinstance(comp, dict):
                    continue
                _cd = comp.get('component')
                if not (isinstance(_cd, dict) and isinstance(_cd.get('Button'), dict)):
                    continue
                btn = _cd['Button']
                _child = btn.get('child')
                if isinstance(_child, str) and _child in _defined_ids:
                    continue  # healthy: the label Text exists in this surfaceUpdate
                # Label source 1: leftover label/text property on the Button
                _label = ''
                _lv = btn.get('label') or btn.get('text')
                if isinstance(_lv, dict):
                    _label = str(_lv.get('literalString') or '')
                elif _lv:
                    _label = str(_lv)
                # Label source 2: literalString nested inside an inline child object
                if (not _label) and isinstance(_child, dict):
                    _label = _find_literal(_child)
                # Label source 3: the button's own sendText context text
                if not _label:
                    _act = btn.get('action')
                    _ctx = _act.get('context') if isinstance(_act, dict) else None
                    for _ce in (_ctx or []):
                        if isinstance(_ce, dict) and _ce.get('key') == 'text':
                            _cv = _ce.get('value')
                            if isinstance(_cv, dict) and isinstance(_cv.get('literalString'), str):
                                _label = _cv['literalString']
                            elif isinstance(_cv, str):
                                _label = _cv
                            break
                _label = ' '.join(str(_label).split())
                if len(_label) > 48:
                    _label = _label[:47] + '...'
                if not _label:
                    continue  # nothing usable - leave the button untouched
                _cid = _child if (isinstance(_child, str) and _child) else (str(comp.get('id') or 'btn') + '_lbl')
                if _cid in _defined_ids:
                    _cid = _cid + '_x'
                btn.pop('label', None)
                btn.pop('text', None)
                btn['child'] = _cid
                _extra_labels.append({'id': _cid, 'component': {'Text': {'text': {'literalString': _label}, 'usageHint': 'body'}}})
                _defined_ids.add(_cid)
            if _extra_labels:
                comps.extend(_extra_labels)
                try:
                    logger.log_text('[button_heal] synthesized ' + str(len(_extra_labels)) + ' missing button label Text component(s)')
                except Exception:
                    pass

            # Normalize Text.text given as a bare string: GE requires the
            # {'literalString': ...} shape; a bare string renders as empty.
            for _tc in comps:
                if not isinstance(_tc, dict):
                    continue
                _tcd = _tc.get('component')
                if isinstance(_tcd, dict) and isinstance(_tcd.get('Text'), dict):
                    _tv = _tcd['Text'].get('text')
                    if isinstance(_tv, str):
                        _tcd['Text']['text'] = {'literalString': _tv}
    return msg

# --- A2UI Icon Normalization ---
# The A2UI stream parser validates icon names against a strict enum.
# LLMs frequently generate icon names outside this list (e.g. 'analytics',
# 'dashboard', 'trending_up'), causing ValueError that triggers the
# fallback+safety-net duplicate parts bug.
# This pre-processor maps common invalid icons to the closest valid icon.
_VALID_A2UI_ICONS = frozenset([
    'accountCircle', 'add', 'arrowBack', 'arrowForward', 'attachFile',
    'calendarToday', 'call', 'camera', 'check', 'close', 'delete',
    'download', 'edit', 'event', 'error', 'favorite', 'favoriteOff',
    'folder', 'help', 'home', 'info', 'locationOn', 'lock', 'lockOpen',
    'mail', 'menu', 'moreVert', 'moreHoriz', 'notificationsOff',
    'notifications', 'payment', 'person', 'phone', 'photo', 'print',
    'refresh', 'search', 'send', 'settings', 'share', 'shoppingCart',
    'star', 'starHalf', 'starOff', 'upload', 'visibility', 'visibilityOff',
    'warning',
])
_ICON_FALLBACK_MAP = {
    'analytics': 'info',
    'bar_chart': 'info',
    'dashboard': 'home',
    'trending_up': 'arrowForward',
    'trending_down': 'arrowBack',
    'inventory': 'shoppingCart',
    'inventory_2': 'shoppingCart',
    'local_shipping': 'send',
    'receipt': 'folder',
    'receipt_long': 'folder',
    'description': 'attachFile',
    'assessment': 'info',
    'insights': 'info',
    'query_stats': 'search',
    'monitoring': 'visibility',
    'schedule': 'calendarToday',
    'access_time': 'calendarToday',
    'timer': 'calendarToday',
    'group': 'person',
    'groups': 'person',
    'people': 'person',
    'support_agent': 'person',
    'handshake': 'person',
    'savings': 'payment',
    'account_balance': 'payment',
    'credit_card': 'payment',
    'monetization_on': 'payment',
    'attach_money': 'payment',
    'money': 'payment',
    'currency_exchange': 'payment',
    'price_check': 'payment',
    'store': 'shoppingCart',
    'storefront': 'shoppingCart',
    'shopping_bag': 'shoppingCart',
    'construction': 'settings',
    'build': 'settings',
    'tune': 'settings',
    'manage_accounts': 'settings',
    'admin_panel_settings': 'settings',
    'speed': 'info',
    'task': 'check',
    'task_alt': 'check',
    'check_circle': 'check',
    'done': 'check',
    'verified': 'check',
    'assignment': 'folder',
    'article': 'folder',
    'note': 'edit',
    'data_usage': 'info',
    'pie_chart': 'info',
    'show_chart': 'info',
    'leaderboard': 'info',
    'table_chart': 'info',
    'auto_graph': 'info',
    'stacked_bar_chart': 'info',
    'donut_large': 'info',
    'map': 'locationOn',
    'place': 'locationOn',
    'my_location': 'locationOn',
    'explore': 'locationOn',
    'public': 'locationOn',
    'language': 'locationOn',
    'flag': 'info',
    'bookmark': 'star',
    'label': 'info',
    'category': 'folder',
    'list': 'menu',
    'list_alt': 'menu',
    'view_list': 'menu',
    'format_list_bulleted': 'menu',
    'toc': 'menu',
    'link': 'attachFile',
    'open_in_new': 'arrowForward',
    'launch': 'arrowForward',
    'cloud': 'upload',
    'cloud_upload': 'upload',
    'cloud_download': 'download',
    'security': 'lock',
    'shield': 'lock',
    'verified_user': 'lock',
    'gpp_good': 'lock',
    'policy': 'lock',
    'emoji_objects': 'info',
    'lightbulb': 'info',
    'tips_and_updates': 'info',
    'school': 'info',
    'workspace_premium': 'star',
    'military_tech': 'star',
    'grade': 'star',
    'thumb_up': 'favorite',
    'recommend': 'favorite',
    'sentiment_satisfied': 'favorite',
    'local_offer': 'info',
    'sell': 'payment',
    'point_of_sale': 'payment',
    'electric_bolt': 'warning',
    'flash_on': 'warning',
    'report': 'warning',
    'report_problem': 'warning',
    'priority_high': 'warning',
    'crisis_alert': 'warning',
    'notifications_active': 'notifications',
    'campaign': 'notifications',
    'announcement': 'notifications',
    'mark_email_read': 'mail',
    'forward_to_inbox': 'mail',
    'drafts': 'mail',
    'contact_mail': 'mail',
    'chat': 'mail',
    'forum': 'mail',
    'comment': 'mail',
    'sms': 'mail',
    'message': 'mail',
    'contact_support': 'help',
    'quiz': 'help',
    'live_help': 'help',
    'question_answer': 'help',
}

import re as _a2ui_debris_re_mod
# Stray A2UI tag debris emitted as TEXT (e.g. a leaked "a2ui-json>" fragment) when
# the opening <a2ui-json> tag is split across stream chunks and the parser consumes
# only the leading "<". The leading "<" and trailing ">" are both optional so a
# fragment like "a2ui-json>" or "<a2ui-json" is still removed (v10.100).
_A2UI_TAG_DEBRIS_RE = _a2ui_debris_re_mod.compile(r'<\s*/?\s*a2ui[-_]json\s*>?|a2ui[-_]json\s*>', _a2ui_debris_re_mod.IGNORECASE)

def _sanitize_a2ui_text_icons(text):
    import re as _re
    import json as _json
    _tag_re = _re.compile(r'(<a2ui-json>)(.*?)(</a2ui-json>)', _re.DOTALL)
    def _fix_block(match):
        prefix, body, suffix = match.group(1), match.group(2), match.group(3)
        try:
            parsed = _json.loads(body)
            changed = _normalize_a2ui_icons_in_data(parsed)
            return prefix + _json.dumps(changed) + suffix
        except Exception:
            return match.group(0)
    if '<a2ui-json>' in text:
        return _tag_re.sub(_fix_block, text)
    return text

def _normalize_a2ui_icons_in_data(data):
    if isinstance(data, list):
        return [_normalize_a2ui_icons_in_data(item) for item in data]
    if isinstance(data, dict):
        if 'Icon' in data and isinstance(data['Icon'], dict):
            name_obj = data['Icon'].get('name', {})
            if isinstance(name_obj, dict):
                lit = name_obj.get('literalString', '')
                if lit and lit not in _VALID_A2UI_ICONS:
                    mapped = _ICON_FALLBACK_MAP.get(lit, 'info')
                    name_obj['literalString'] = mapped
        return {k: _normalize_a2ui_icons_in_data(v) for k, v in data.items()}
    return data

def _heal_a2ui_message_list(messages):
    import json as _json
    try:
        logger.log_text("[healer_input] messages: " + _json.dumps(messages))
    except Exception as _le:
        logger.log_text("[healer_input] failed to log: " + str(_le))
        
    if not isinstance(messages, list):
        return messages
        
    healed_messages = []
    
    # Normalize surfaceId typos and sanitize Divider components.
    # NOTE: Root IDs are intentionally left as the LLM produced them.
    # GE expects the model's original root IDs; renaming them breaks rendering.
    for m in messages:
        if not isinstance(m, dict):
            healed_messages.append(m)
            continue
            
        if 'beginRendering' in m:
            br = m['beginRendering']
            if isinstance(br, dict) and 'surfaceId' in br:
                if br['surfaceId'] == 'welcome-root':
                    br['surfaceId'] = 'welcome-card'
                
        elif 'surfaceUpdate' in m:
            su = m['surfaceUpdate']
            if isinstance(su, dict) and 'surfaceId' in su:
                if su['surfaceId'] == 'welcome-root':
                    su['surfaceId'] = 'welcome-card'
                
                # --- DIVIDER FAILSAFE ---
                # Clean up all Divider properties to strictly {} to prevent speculative property crashes in browser
                comps = su.get('components')
                if comps and isinstance(comps, list):
                    for comp in comps:
                        if isinstance(comp, dict) and 'component' in comp:
                            if isinstance(comp['component'], dict) and 'Divider' in comp['component']:
                                comp['component']['Divider'] = {}
                            # --- ICON NORMALIZATION ---
                            # Map invalid icon names to valid ones to prevent parser crashes
                            if isinstance(comp['component'], dict) and 'Icon' in comp['component']:
                                _icon_data = comp['component']['Icon']
                                if isinstance(_icon_data, dict):
                                    _name_obj = _icon_data.get('name', {})
                                    if isinstance(_name_obj, dict):
                                        _lit = _name_obj.get('literalString', '')
                                        if _lit and _lit not in _VALID_A2UI_ICONS:
                                            _name_obj['literalString'] = _ICON_FALLBACK_MAP.get(_lit, 'info')
                
        healed_messages.append(m)
        
    try:
        logger.log_text("[healer_output] messages: " + _json.dumps(healed_messages))
    except Exception as _le:
        logger.log_text("[healer_output] failed to log: " + str(_le))
        
    return healed_messages

def _is_suggestions_part(part) -> bool:
    try:
        _root = getattr(part, 'root', None)
        if _root and isinstance(_root, a2a_types.DataPart):
            _data = _root.data
            _items = _data if isinstance(_data, list) else [_data]
            for _item in _items:
                if isinstance(_item, dict):
                    for _k in ('beginRendering', 'surfaceUpdate', 'deleteSurface'):
                        if _k in _item and isinstance(_item[_k], dict):
                            # Matches both the bare 'suggestions' id and the
                            # per-turn scoped 'suggestions-<task_id>' (see
                            # _scope_suggestions_surface).
                            if (_item[_k].get('surfaceId') or '').startswith('suggestions'):
                                return True
    except Exception:
        pass
    return False


def _iter_surface_updates(parts):
    # Yields every surfaceUpdate dict found in a list of a2a Parts.
    for _p in parts:
        try:
            _root = getattr(_p, 'root', None)
            if not (_root and isinstance(_root, a2a_types.DataPart)):
                continue
            _data = _root.data
            _items = _data if isinstance(_data, list) else [_data]
            for _item in _items:
                if isinstance(_item, dict) and isinstance(_item.get('surfaceUpdate'), dict):
                    yield _item['surfaceUpdate']
        except Exception:
            continue


def _surface_update_has_button(_su) -> bool:
    for _c in (_su.get('components') or []):
        if isinstance(_c, dict) and isinstance(_c.get('component'), dict) and 'Button' in _c['component']:
            return True
    return False


def _has_populated_suggestions(parts) -> bool:
    # True iff some part carries a surfaceUpdate on a 'suggestions*' surface
    # that actually contains at least one Button (a begin-only suggestions
    # surface, or an update with no Buttons, renders as nothing in GE).
    for _su in _iter_surface_updates(parts):
        if (_su.get('surfaceId') or '').startswith('suggestions') and _surface_update_has_button(_su):
            return True
    return False


def _has_interactive_card(parts) -> bool:
    # True iff some NON-suggestions surface contains Button components.
    # Mirrors the prompt's A2UI CARD INTERACTION EXCEPTION: when a card carries
    # its own control buttons, suggestion chips are intentionally absent and
    # must NOT be re-prompted for.
    for _su in _iter_surface_updates(parts):
        if not (_su.get('surfaceId') or '').startswith('suggestions') and _surface_update_has_button(_su):
            return True
    return False


# --- Per-turn scoping for the always-on 'suggestions' surface ---
# GE/A2UI treats a surfaceId as a conversation-level singleton anchored to the
# message where it was FIRST rendered. The suggestion chip bar reuses a constant
# surfaceId ('suggestions') on every turn, so a later turn's chips would patch
# that singleton in place and render under the PREVIOUS turn's response (and the
# current turn would show none). Rewriting the surfaceId to a per-turn unique id
# forces GE to create a fresh surface anchored to the CURRENT message each turn.
# Scoped here (the single choke point for all A2UI parts) so the model contract
# stays 'suggestions' and no prompt change is needed.
# NOTE: ONLY 'suggestions' is unconditionally scoped here. Other surfaces keep
# their FIRST-render id stable (confirmation-surface is intentionally carried
# across turns and torn down via deleteSurface; welcome-card only renders on
# the first turn); cross-turn REUSE of those ids is handled separately by
# _rescope_reused_surfaces() below (v10.73).
_current_suggestions_suffix = contextvars.ContextVar('suggestions_suffix', default=None)

def _scope_suggestions_surface(msg):
    _suffix = _current_suggestions_suffix.get()
    if not _suffix or not isinstance(msg, dict):
        return msg
    for _k in ('beginRendering', 'surfaceUpdate', 'dataModelUpdate', 'deleteSurface'):
        _v = msg.get(_k)
        if isinstance(_v, dict) and _v.get('surfaceId') == 'suggestions':
            _v['surfaceId'] = 'suggestions-' + _suffix
    return msg


# --- v10.73: cross-turn surfaceId reuse guard (non-suggestions surfaces) ---
# GE anchors a surfaceId to the message where it FIRST rendered (conversation-
# level singleton). The model is prompted to use type-based surfaceIds (e.g.
# 'batch-editor'), so a SECOND card of the same type a few turns later re-emits
# the SAME id: GE then patches the OLD turn's card in place (its content
# visibly changes) and the new turn shows text only (confirmed 2026-06-11,
# demo-hr-outsourcing: a second Batch Editor overwrote the card rendered a few
# turns earlier and its own turn rendered no card). _rescope_replay_parts only
# covers REPLAYED cached parts (G1/H1); this guard covers FRESH model output.
# Rules (deliberately narrow to avoid regressions):
#   - Only a beginRendering that reuses an id first rendered by a PRIOR
#     invocation is renamed (re-anchored to THIS turn). First renders and
#     same-invocation re-begins keep their id; streaming updates within a
#     turn are untouched.
#   - surfaceUpdate / dataModelUpdate / deleteSurface are rewritten to the
#     LATEST incarnation of their surface (identity rewrite when never
#     renamed), so the prompt's confirmation-surface lifecycle (render turn
#     N, deleteSurface turn N+1) keeps working even after a rename, and a
#     patch-only turn that intentionally updates an old card still can.
#   - 'suggestions*' ids are skipped (already per-turn scoped above).
# State is in-memory per session (same minScale=1 scope as the Y1/G1/H1
# caches); the rename is idempotent because already-renamed ids are first
# normalized back to their logical id.
_current_surface_guard = contextvars.ContextVar('surface_guard', default=None)
_session_surface_registry = {}

def _get_surface_registry(_sid):
    _reg = _session_surface_registry.get(_sid)
    if _reg is None:
        _reg = {}
        _session_surface_registry[_sid] = _reg
        if len(_session_surface_registry) > 300:
            for _old in list(_session_surface_registry.keys())[:len(_session_surface_registry) - 300]:
                _session_surface_registry.pop(_old, None)
    return _reg

def _a2ui_components(_v):
    _c = _v.get('components')
    return _c if isinstance(_c, list) else []

def _a2ui_is_full_card_tree(_v):
    # A self-contained card re-render declares its root component (conventionally
    # id 'root'); a partial in-place patch updates specific components and does
    # NOT re-send the root. Used to distinguish "model re-rendered the whole card
    # via surfaceUpdate (forgot beginRendering)" from "legitimate partial patch".
    _ids = [str(_c.get('id')) for _c in _a2ui_components(_v) if isinstance(_c, dict) and _c.get('id')]
    return 'root' in _ids

def _a2ui_root_id(_v):
    _ids = [str(_c.get('id')) for _c in _a2ui_components(_v) if isinstance(_c, dict) and _c.get('id')]
    return 'root' if 'root' in _ids else (_ids[0] if _ids else 'root')

def _rescope_one(msg, _allow_promote=False):
    # Rescope a single A2UI message against the per-session surface registry.
    # Returns a LIST of messages: normally [msg]; when _allow_promote and an
    # ORPHAN cross-turn full-tree surfaceUpdate is detected (a surface owned by a
    # PRIOR invocation, no beginRendering for it this turn, full card tree), it is
    # promoted to [synthetic beginRendering, msg] with a fresh re-anchored id so
    # GE renders it as a NEW card this turn instead of silently patching the old
    # one (which left the new turn blank - the vanishing progress card, v10.85).
    _guard = _current_surface_guard.get()
    if not _guard or not isinstance(msg, dict):
        return [msg]
    try:
        _reg = _guard['registry']
        _task = _guard['task']
        _begun = _guard.setdefault('begun', set())
        for _k in ('beginRendering', 'surfaceUpdate', 'dataModelUpdate', 'deleteSurface'):
            _v = msg.get(_k)
            if not (isinstance(_v, dict) and _v.get('surfaceId')):
                continue
            _sid = str(_v['surfaceId'])
            if _sid.startswith('suggestions'):
                continue
            # The model may echo an already-renamed id back from history;
            # strip guard suffixes so it resolves to the same logical surface
            # (also prevents '-u' suffix chaining across turns).
            _logical = re.sub(r'(-u[0-9a-f]{4,32})+$', '', _sid) or _sid
            _entry = _reg.get(_logical)
            if _k == 'beginRendering':
                if _entry is None:
                    _reg[_logical] = {'current': _sid, 'owner': _task}
                elif _entry.get('owner') == _task:
                    _v['surfaceId'] = _entry['current']
                else:
                    _new = _logical + '-u' + _guard['suffix']
                    _reg[_logical] = {'current': _new, 'owner': _task}
                    _v['surfaceId'] = _new
                    logger.log_text('[surface_rescope] cross-turn beginRendering reuse of ' + _logical + ' -> ' + _new)
                _begun.add(_logical)
            elif (_k == 'surfaceUpdate' and _allow_promote and _entry is not None
                    and _entry.get('owner') != _task and _logical not in _begun
                    and _a2ui_is_full_card_tree(_v)):
                # Orphan cross-turn full-tree re-render with no begin this turn:
                # GE would patch the prior card and render nothing here. Promote.
                _new = _logical + '-u' + _guard['suffix']
                _reg[_logical] = {'current': _new, 'owner': _task}
                _begun.add(_logical)
                _v['surfaceId'] = _new
                _begin = {'beginRendering': {'surfaceId': _new, 'root': _a2ui_root_id(_v)}}
                logger.log_text('[surface_rescope] promoted orphan surfaceUpdate ' + _logical + ' -> begin+update ' + _new)
                return [_begin, msg]
            elif _entry is not None:
                _v['surfaceId'] = _entry['current']
    except Exception:
        pass
    return [msg]

def _rescope_reused_surfaces(msg):
    # Back-compat single-message rescope (no promotion). Returns the (mutated) msg.
    return _rescope_one(msg, _allow_promote=False)[0]


# --- A2UI shape normalization (v11.4) ---
# The model emits three recurring SHAPE malformations that the A2UI schema
# rejects and the GE client cannot render (confirmed live 2026-07-15,
# demo-tech-distributi: the stream parser refused the card, the regex
# fallback then shipped it UNVALIDATED, and GE hung the whole turn on
# permanent "thinking"):
#   (a) stray scalar keys at the component-dict level, sibling of the type
#       key (e.g. {"component": {"Text": {...}, "usageHint": "h2"}});
#   (b) Text missing the text wrapper ({"Text": {"literalString": "X"}})
#       or text given as a bare string;
#   (c) layout props nested INSIDE the children object
#       ({"children": {"explicitList": [...], "distribution": ..., "alignment": ...}}).
# This normalizer repairs all three in place. Verified against the live
# failing card: raw -> schema INVALID, normalized -> schema VALID.
_A2UI_CHILD_PROP_LIFT = {
    'Row': ('distribution', 'alignment'),
    'Column': ('distribution', 'alignment'),
    'List': ('direction', 'alignment'),
}

def _normalize_a2ui_shapes(msg):
    if not isinstance(msg, dict):
        return msg
    _su = msg.get('surfaceUpdate')
    if not isinstance(_su, dict):
        return msg
    for _comp in _su.get('components') or []:
        if not isinstance(_comp, dict):
            continue
        _cd = _comp.get('component')
        if not isinstance(_cd, dict):
            continue
        # (a) stray scalar keys beside the component-type key
        _stray = [_k for _k, _v in list(_cd.items()) if not isinstance(_v, dict)]
        for _k in _stray:
            _v = _cd.pop(_k)
            if _k == 'usageHint' and isinstance(_cd.get('Text'), dict):
                _cd['Text'].setdefault('usageHint', _v)
        for _cname, _spec in _cd.items():
            if not isinstance(_spec, dict):
                continue
            # (b) Text shape repairs
            if _cname == 'Text':
                _tv = _spec.get('text')
                if isinstance(_tv, str):
                    _spec['text'] = {'literalString': _tv}
                if 'literalString' in _spec:
                    if not isinstance(_spec.get('text'), dict):
                        _spec['text'] = {'literalString': str(_spec['literalString'])}
                    _spec.pop('literalString', None)
            # (c) lift layout props out of the children object
            _ch = _spec.get('children')
            if isinstance(_ch, dict):
                _allowed = _A2UI_CHILD_PROP_LIFT.get(_cname, ())
                for _k in [_k for _k in _ch.keys() if _k != 'explicitList']:
                    _v = _ch.pop(_k)
                    if _k in _allowed and _k not in _spec:
                        _spec[_k] = _v
    return msg

def _a2ui_msg_schema_ok(msg):
    """Schema gate for MODEL-authored A2UI (used by create_a2ui_parts).

    The stream parser validates the happy path, but every RECOVERY path
    (regex fallback, untagged safety nets) used to ship whatever it
    extracted, unvalidated - and one schema-invalid card is enough to hang
    the GE client's rendering of the entire turn. After healing, anything
    that STILL fails validation is dropped (the turn keeps its text and
    other surfaces). Only surfaceUpdate carries components; other message
    kinds pass through. Fail-open: if the validation machinery itself
    errors, deliver as before."""
    try:
        if not (isinstance(msg, dict) and isinstance(msg.get('surfaceUpdate'), dict)):
            return True
        _vp = A2uiStreamParser(catalog=a2ui_selected_catalog)
        _vp.process_chunk('<a2ui-json>' + json.dumps([msg]) + '</a2ui-json>')
        return True
    except ValueError as _ve:
        try:
            _sid = str((msg.get('surfaceUpdate') or {}).get('surfaceId', '?'))
            logger.log_text('[a2ui_gate] dropped schema-invalid surfaceUpdate (surface=' + _sid + '): ' + str(_ve)[:200])
        except Exception:
            pass
        return False
    except Exception:
        return True

def _prep_a2ui_msg(msg):
    _shaped = _normalize_a2ui_shapes(msg)
    _healed = _heal_buttons_in_a2ui(_shaped)
    _rewritten = _rewrite_suggestions_a2ui(_healed)
    _rewritten = _scope_suggestions_surface(_rewritten)
    return _rewritten

def _build_a2ui_part(msg):
    try:
        return _original_create_a2ui_part(msg, version='0.8')
    except TypeError:
        # Fallback: SDK removed version param (e.g., PyPI 0.2.1)
        logger.log_text("[a2ui_compat] version param removed, using fallback MIME fix")
        _part = _original_create_a2ui_part(msg)
        # Force GE-compatible MIME type
        try:
            if hasattr(_part, 'root') and hasattr(_part.root, 'inline_data') and _part.root.inline_data:
                _part.root.inline_data.mime_type = 'application/json+a2ui'
            elif hasattr(_part, 'root') and hasattr(_part.root, 'data_part') and _part.root.data_part:
                _part.root.data_part.mime_type = 'application/json+a2ui'
        except Exception:
            pass
        return _part

def _diag_a2ui(msg, _tag):
    # TEMP DIAGNOSTIC (v10.92): surface dangling child refs / empty tab content in
    # model-authored A2UI. Remove once the empty-card-body bug is pinned.
    try:
        if not isinstance(msg, dict):
            return
        su = msg.get("surfaceUpdate")
        if not isinstance(su, dict):
            return
        _sid = su.get("surfaceId")
        _comps = su.get("components") or []
        _defined = set()
        _refs = set()
        _has_tabs = False
        _empty_lists = []
        for _c in _comps:
            if not isinstance(_c, dict):
                continue
            _cid = _c.get("id")
            if isinstance(_cid, str):
                _defined.add(_cid)
            _comp = _c.get("component") or {}
            if not isinstance(_comp, dict):
                continue
            for _name, _spec in _comp.items():
                if _name == "Tabs":
                    _has_tabs = True
                if not isinstance(_spec, dict):
                    continue
                _child = _spec.get("child")
                if isinstance(_child, str):
                    _refs.add(_child)
                _children = _spec.get("children")
                if isinstance(_children, dict):
                    _el = _children.get("explicitList")
                    if isinstance(_el, list):
                        if len(_el) == 0:
                            _empty_lists.append(_cid)
                        for _r in _el:
                            if isinstance(_r, str):
                                _refs.add(_r)
                _items = _spec.get("tabItems")
                if isinstance(_items, list):
                    for _it in _items:
                        if isinstance(_it, dict) and isinstance(_it.get("child"), str):
                            _refs.add(_it.get("child"))
        _dangling = sorted(_refs - _defined)
        print("[a2ui_diag] " + str(_tag) + " surface=" + str(_sid)
              + " tabs=" + str(_has_tabs) + " defined=" + str(len(_defined))
              + " refs=" + str(len(_refs)) + " DANGLING=" + json.dumps(_dangling)
              + " empty_lists=" + json.dumps(_empty_lists))
        if _dangling or _has_tabs or _empty_lists:
            print("[a2ui_diag] FULL surface=" + str(_sid) + " json=" + json.dumps(msg)[:12000])
    except Exception as _e:
        print("[a2ui_diag] error " + str(_e))

def create_a2ui_part(msg):
    # Single-part entry (no orphan-surfaceUpdate promotion) - back-compat.
    _diag_a2ui(msg, "single")
    return _build_a2ui_part(_rescope_reused_surfaces(_prep_a2ui_msg(msg)))

def create_a2ui_parts(msg):
    # List-returning entry (v10.85): may return [begin, update] when an orphan
    # cross-turn full-tree surfaceUpdate is promoted to a fresh card so it renders
    # this turn. Use this for MODEL-authored A2UI in the stream / drain / salvage
    # paths. Server-authored begin+update pairs are unaffected (the begin marks
    # the surface begun, so its update never promotes).
    _diag_a2ui(msg, "list")
    _prepped = _prep_a2ui_msg(msg)
    # v11.4: never ship a schema-invalid card - one poison surfaceUpdate hangs
    # the GE client's rendering of the whole turn. Empty list is safe for every
    # caller (they all .extend()).
    if not _a2ui_msg_schema_ok(_prepped):
        return []
    return [_build_a2ui_part(_m) for _m in _rescope_one(_prepped, _allow_promote=True)]

from adk_agent.app.agent import app as adk_app, background_agent, INLINE_TOOL_DEADLINE, INLINE_IMAGE_DEADLINE
import adk_agent.app.tools as _agent_tools
import adk_agent.app.part_converters as part_converters

# CRITICAL: Disable OpenTelemetry HTTPX instrumentation to prevent it from colliding
# with our custom httpx monkeypatch (which injects MCP auth tokens) and causing a deadlock.
os.environ["OTEL_PYTHON_DISABLED_INSTRUMENTATIONS"] = "httpx"

# Feedback model (from ASP app_utils/typing.py — inlined to remove ASP dependency)
import uuid
from typing import Literal
from pydantic import BaseModel, Field
class Feedback(BaseModel):
    """Represents feedback for a conversation."""
    score: int | float
    text: str | None = ""
    log_type: Literal["feedback"] = "feedback"
    service_name: Literal["adk-agent"] = "adk-agent"
    user_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
_, project_id = google.auth.default()
logging_client = google_cloud_logging.Client()
logger = logging_client.logger(__name__)

# =============================================================================
# PRE-FLIGHT GATE (v10.93): deterministic server-side Analysis Plan card.
# Prompt-only gating failed 3x (v10.89/91/92): the model starts working /
# transfers instead of rendering the card. So the SERVER classifies a fresh
# user message with a lightweight model and, when it is a heavy multi-step
# analysis, renders the Analysis Plan card itself and short-circuits the turn
# BEFORE the agent runs. The user then picks inline / background / adjust.
# Fail-open everywhere: any error => no card => the agent runs normally.
# =============================================================================
# Pre-browse delegation-note fragment (used inside the Managed-Agent-guarded
# briefing-press handler; empty when Computer Use is off).
_MA_PREBROWSE_EXCEPTION = (
    'EXCEPTION - PRE-BROWSE: if the brief mentions web browsing or names a '
    'specific site / page / URL to consult (or needs data only interactive '
    'browsing can obtain), run the COMPUTER USE browse sequence first and '
    'delegate immediately after, in this same turn. '
) if os.environ.get("ENABLE_COMPUTER_USE") == "1" else ""

# Pre-browse planner override fragment: only meaningful when BOTH the Managed
# Agent and Computer Use are enabled (spliced inside _MA_PLANNER_OVERRIDE).
_MA_CU_BROWSER_EXCLUSION = (
    "EXCLUSION - INTERACTIVE BROWSER OPERATION IS NOT AUTONOMOUS: when the PRIMARY goal is "
    "to OPERATE a website interactively - go to a specific site and click / type / fill "
    "forms / work a portal, or a live look-up the user wants to WATCH in the browser - the "
    "assistant handles it NATIVELY with its own real browser (Computer Use); the autonomous "
    "agent has NO interactive browser. Such a request is NOT signal (a) - classify it by the "
    "remaining rules (usually QUICK or OTHER). It becomes AUTONOMOUS only when the browsing "
    "is merely one input to a bigger job that ALSO carries signal (b), (c), or (d). "
) if os.environ.get("ENABLE_COMPUTER_USE") == "1" else ""

_MA_PLANNER_OVERRIDE = (
    "OVERRIDE - AUTONOMOUS CATEGORY (checked BEFORE the ANALYSIS rule): set category "
    "to 'AUTONOMOUS' when the message requires ANY of the following, regardless of how "
    "much data analysis it also contains: (a) researching CURRENT or EXTERNAL information "
    "from the live web / internet (news, trends, competitors, market prices, regulations, "
    "reading external reports); "
    "(b) producing a downloadable FILE deliverable - a presentation / slide deck / pptx / "
    "Google Slides, a document / docx / Google Docs, a PDF, a spreadsheet file, or a "
    "standalone web page file; "
    "(c) writing and executing custom code, building a prototype, or iterative file "
    "processing; "
    "(d) acting on the user's Google Workspace - saving a file to Google Drive, creating "
    "a Gmail draft or email, posting to a Google Chat space, or creating Calendar events. "
    "IMPORTANT: even ONE of these signals makes the message AUTONOMOUS, no matter how "
    "analytical the rest is. Example: 'read the latest market trend report, combine it "
    "with our data, create a strategy deck as Google Slides in my Drive, draft a summary "
    "email, and post the link to our Chat space' is AUTONOMOUS (web research + file + "
    "Drive + Gmail + Chat), NOT ANALYSIS. Such requests are handled by a dedicated "
    "autonomous agent and must NOT get the ANALYSIS card. "
    "EXCLUSION - INTERACTIVE DASHBOARDS ARE NOT AUTONOMOUS: a request for an interactive "
    "dashboard / explorable page over the internal data that the user opens in the browser "
    "(KPI cards, trends, drill-down views, risk lists) is handled NATIVELY by the assistant, "
    "which builds and hosts it itself. Such a request is NOT signal (b) or (c) - classify it "
    "by the remaining rules (usually ANALYSIS or QUICK) unless the message ALSO contains a "
    "genuine autonomous signal (live web research, a downloadable office/PDF file, a Workspace "
    "action, or a computed what-if SIMULATOR whose model coefficients must be derived by code). "
    + _MA_CU_BROWSER_EXCLUSION +
    "FOR AUTONOMOUS, return these ADDITIONAL keys instead of the analysis fields: "
    "card_title (a SHORT card heading of 3 to 6 words, e.g. the localized form of "
    "'Autonomous task - quick check'. This is a HEADING, NOT a restatement of the "
    "request - never put a full sentence here); "
    "goal (ONE sentence restating what the user wants achieved); "
    "deliverable (one line describing what will be produced, e.g. a slide deck saved to Drive plus a draft email); "
    "missing (an array of 0 to 3 objects {question, suggestion, options} listing ONLY information gaps that "
    "would MATERIALLY change the autonomous run's output - e.g. deliverable format unclear, target "
    "audience unknown, time range / scope unspecified, or a Workspace action without a named recipient "
    "or Chat space. Questions MUST stay at the BUSINESS level (audience, scope, emphasis, time range, "
    "recipients). NEVER ask technical or implementation questions - which platform, BI product, tool, "
    "library, tech stack, hosting, or data-connection method to use, or which internal system holds the "
    "data. The agent decides all implementation details itself; a question naming products like "
    "'Tableau or Power BI?' would ruin the business demo. "
    "question is short; suggestion is your best concrete default answer the user can keep "
    "or edit; options is OPTIONAL - include it ONLY when the answer naturally reduces to a few clear "
    "mutually exclusive choices, as an array of 2 to 4 SHORT choice strings (one of them should match "
    "the suggestion); omit options when free text is more appropriate. If the "
    "request is already specific enough, return an EMPTY missing array - do not invent questions); "
    "briefing_intro (one sentence like: before I start working autonomously, please confirm a few details); "
    "label_start (button label meaning: confirm and start the autonomous task); "
    "label_asis (button label meaning: start as-is without these details). "
) if os.environ.get("ENABLE_MANAGED_AGENT") == "1" else ""

PREFLIGHT_CLASSIFIER_PROMPT = (
    "You are a fast routing classifier for a data-analytics assistant. "
    "Work in two steps. "
    "STEP 1 (LANGUAGE - do this first): detect the natural language the USER MESSAGE "
    "is written in (for example English, French, German, Japanese, Spanish). Put its "
    "English name in the 'language' field. This is the ONLY language signal - ignore "
    "the business domain, place names, and any other text; judge solely by the words "
    "the user actually typed. "
    "EXCEPTION: when a PREVIOUS USER MESSAGE block is provided below AND the USER "
    "MESSAGE looks like a machine-generated command rather than natural human text "
    "(a fixed template phrase, e.g. an imperative English one-liner referencing a "
    "task/ticket id or tool-like action), use the language of the PREVIOUS USER "
    "MESSAGE for STEP 1 instead - the human is conversing in THAT language and the "
    "command text came from a button, not from their keyboard. "
    "STEP 2 (CLASSIFY): decide whether the message is a request for a HEAVY MULTI-STEP "
    "DATA ANALYSIS - several database queries plus synthesis such as correlation, "
    "sensitivity, forecasting, anomaly investigation, cross-source comparison, "
    "ranking-with-reasoning, or strategic recommendation, the kind that takes a few "
    "minutes - versus a quick lookup, an overview/dashboard snapshot, a single "
    "aggregate, a greeting, an edit, or a control action. "
    "Return ONLY a JSON object with these keys: "
    "language (English name of the detected user-message language); "
    "category (one of 'ANALYSIS', 'QUICK', 'OTHER'); "
    "title (short card title); intro (one sentence describing the planned analysis); "
    "data (one line: which data it will use); method (one line: the analytical method); "
    "output (one line: what the result will contain); estimate (rough time, e.g. '~1-3 min'); "
    "steps (an ORDERED array of 3 to 5 objects, each {title: a short imperative step name, "
    "detail: one short line describing what that step does - its data, method, and output}, "
    "breaking the analysis into sequential stages the user can read top to bottom); "
    "label_title (a short card title); "
    "label_inline, label_background, label_adjust, label_field. "
    "These four are FIXED action labels - translate their MEANING into the user's "
    "language and do NOT replace them with names of analysis types, sub-options, or "
    "variations: label_inline = 'Run this analysis now' (run it inline); "
    "label_background = 'Run this analysis in the background'; "
    "label_adjust = 'Edit the request and re-propose'; label_field = a short label "
    "for the editable request box (e.g. the localized form of 'Adjust the request'). "
    "Each label may start with a fitting emoji. "
    "Set category to 'ANALYSIS' ONLY for the heavy multi-step case; otherwise 'QUICK' or 'OTHER'. "
    + _MA_PLANNER_OVERRIDE +
    "ABSOLUTE LANGUAGE RULE: EVERY human-readable string (title, intro, data, method, "
    "output, estimate, every step title and detail, and every label) MUST be written in EXACTLY the language from "
    "STEP 1. If the user wrote in English, write every string in English; never answer "
    "an English message in French, German, or any other language. Do not translate the "
    "user's words into another language. "
    "For non-ANALYSIS messages you may leave the descriptive fields empty."
)

def _extract_user_text(run_args):
    # Returns the user's INTENT text. A button / chip press arrives as a text part
    # whose body is a userAction JSON ({"userAction":{"sourceComponentId":...,
    # "context":{"text":"..."}}}) - we must unwrap it to its context text, NOT feed
    # the raw JSON to the gate (otherwise "Run Inline: ..." is never recognized and
    # the gate re-cards forever). Typed messages are returned as-is.
    try:
        _nm = run_args.get("new_message") if isinstance(run_args, dict) else None
        if _nm is None:
            return ""
        # A button/chip press carries TWO text parts: a generic display filler
        # ("User action triggered.") AND the userAction JSON. We must return ONLY
        # the userAction's context.text - concatenating the filler would break the
        # "Run Inline:" passthrough check and pollute the scope (it accreted
        # "User action triggered. Run Inline: ..." every round). userAction wins.
        _ua_text = None
        _typed = []
        for _p in (getattr(_nm, "parts", None) or []):
            _t = getattr(_p, "text", None)
            if not _t:
                continue
            if "userAction" in _t:
                try:
                    _ua = json.loads(_t).get("userAction", {}) or {}
                    _ctx = _ua.get("context", {}) or {}
                    _ctext = _ctx.get("text")
                    if isinstance(_ctext, str) and _ctext.strip():
                        _ua_text = _ctext.strip()
                except Exception:
                    pass
                continue
            _typed.append(_t)
        if _ua_text is not None:
            return _ua_text
        return (" ".join(_typed)).strip()
    except Exception:
        return ""

def _is_preflight_passthrough(text):
    # Messages that must reach the agent unchanged (already a user choice).
    _l = (text or "").lstrip().lower()
    return _l.startswith("run inline:") or _l.startswith("run in background:")

def _last_typed_user_text(session):
    # v11.6: latest HUMAN-TYPED user text from session history, used as a
    # language reference for the pre-flight classifier. Skips chip presses
    # (userAction JSON + their "User action triggered." filler) and the
    # auto-generated SYSTEM NOTE parts appended to user messages.
    try:
        for _ev in reversed(getattr(session, "events", None) or []):
            if getattr(_ev, "author", "") != "user":
                continue
            _content = getattr(_ev, "content", None)
            for _p in (getattr(_content, "parts", None) or []):
                _t = getattr(_p, "text", None)
                if not _t or not _t.strip():
                    continue
                if "userAction" in _t or _t.strip() == "User action triggered.":
                    continue
                if _t.lstrip().startswith("SYSTEM NOTE"):
                    continue
                return _t.strip()[:200]
    except Exception:
        pass
    return ""

def _is_preflight_confirmed_press(run_args):
    # True only when the press came from the Analysis Plan card's OWN inline
    # button, which carries context {"pf": "1"}. Such a press is the user's
    # explicit, already-confirmed inline choice, so the gate must let it run
    # (re-carding it would loop). A plain "Run Inline:" drill-down chip has NO
    # pf marker, so it is re-classified and may be carded if it is heavy (v10.96).
    try:
        _nm = run_args.get("new_message") if isinstance(run_args, dict) else None
        if _nm is None:
            return False
        for _p in (getattr(_nm, "parts", None) or []):
            _t = getattr(_p, "text", None)
            if _t and "userAction" in _t:
                try:
                    _ua = json.loads(_t).get("userAction", {}) or {}
                    if str((_ua.get("context", {}) or {}).get("pf", "")) == "1":
                        return True
                except Exception:
                    pass
    except Exception:
        return False
    return False

async def _classify_for_preflight(text, prev_user_text=""):
    # v11.6: prev_user_text is a short sample of the last HUMAN-TYPED message,
    # passed as a language reference so fixed-English chip sendTexts do not
    # flip the card language mid-conversation (see STEP 1 EXCEPTION).
    try:
        from google.genai import client as _genai_client
        _loc = os.environ.get("GOOGLE_CLOUD_LOCATION", "global")
        _client = _genai_client.Client(
            vertexai=True, location=_loc, project=project_id,
            http_options={"api_version": "v1"},
        )
        _model = os.environ.get("AGENT_MODEL_LITE", "gemini-3.6-flash")
        _prompt = PREFLIGHT_CLASSIFIER_PROMPT + chr(10) + chr(10)
        if prev_user_text:
            _prompt = (_prompt + "PREVIOUS USER MESSAGE (language reference only - NOT the request):"
                       + chr(10) + prev_user_text[:200] + chr(10) + chr(10))
        _prompt = _prompt + "USER MESSAGE:" + chr(10) + text
        _res = await asyncio.wait_for(
            asyncio.to_thread(
                _client.models.generate_content,
                model=_model,
                contents=[genai_types.Content(role="user", parts=[genai_types.Part.from_text(text=_prompt)])],
                config=genai_types.GenerateContentConfig(response_mime_type="application/json", temperature=0),
            ),
            timeout=12,
        )
        _raw = (getattr(_res, "text", None) or "").strip()
        if not _raw:
            return None
        _obj = json.loads(_raw)
        return _obj if isinstance(_obj, dict) else None
    except Exception as _e:
        logger.log_text("[preflight_gate] classifier skipped (fail-open): " + str(_e)[:200])
        return None

def _build_preflight_card_parts(plan, scope_text):
    try:
        def _g(_k, _d):
            _v = plan.get(_k)
            return _v if (isinstance(_v, str) and _v.strip()) else _d
        _title = _g("label_title", _g("title", "Analysis plan"))
        _intro = _g("intro", "I will run a multi-step analysis.")
        _estimate = _g("estimate", "")
        # Render the plan as a vertical, NUMBERED step timeline (Deep-Research
        # style) when the classifier returned a 'steps' array; otherwise fall
        # back to the original single data | method | output line. Components are
        # keyed by id, so build the column's child list dynamically (v10.96).
        _raw_steps = plan.get("steps")
        _steps = []
        if isinstance(_raw_steps, list):
            for _s in _raw_steps:
                if isinstance(_s, dict):
                    _stitle = _s.get("title")
                    if isinstance(_stitle, str) and _stitle.strip():
                        _sdetail = _s.get("detail")
                        _sdetail = _sdetail.strip() if (isinstance(_sdetail, str) and _sdetail.strip()) else ""
                        _steps.append((_stitle.strip(), _sdetail))
        _steps = _steps[:6]
        _clock = chr(0x1F552)
        _children = ["title", "intro"]
        _comps = [
            {"id": "root", "component": {"Card": {"child": "col"}}},
            {"id": "title", "component": {"Text": {"text": {"literalString": _title}, "usageHint": "h2"}}},
            {"id": "intro", "component": {"Text": {"text": {"literalString": _intro}, "usageHint": "body"}}},
        ]
        if _steps:
            for _i in range(len(_steps)):
                _stitle, _sdetail = _steps[_i]
                _rid = "step" + str(_i)
                _mid = _rid + "_status"
                _bid = _rid + "_body"
                _tid = _rid + "_title"
                _did = _rid + "_detail"
                _keycap = (chr(0x31 + _i) + chr(0xFE0F) + chr(0x20E3)) if _i < 9 else (str(_i + 1) + ".")
                _marker = _keycap + " " + _clock
                _body_children = [_tid] + ([_did] if _sdetail else [])
                _children.append(_rid)
                _comps.append({"id": _rid, "component": {"Row": {"children": {"explicitList": [_mid, _bid]}, "distribution": "start", "alignment": "start"}}})
                _comps.append({"id": _mid, "component": {"Text": {"text": {"literalString": _marker}, "usageHint": "body"}}})
                _comps.append({"id": _bid, "component": {"Column": {"children": {"explicitList": _body_children}, "distribution": "start", "alignment": "stretch"}}})
                _comps.append({"id": _tid, "component": {"Text": {"text": {"literalString": _stitle}, "usageHint": "body"}}})
                if _sdetail:
                    _comps.append({"id": _did, "component": {"Text": {"text": {"literalString": _sdetail}, "usageHint": "caption"}}})
            if _estimate:
                _children.append("eta")
                _comps.append({"id": "eta", "component": {"Text": {"text": {"literalString": chr(0x23F1) + " " + _estimate}, "usageHint": "caption"}}})
        else:
            _why_bits = [b for b in [_g("data", ""), _g("method", ""), _g("output", ""), _estimate] if b]
            _why = " | ".join(_why_bits) if _why_bits else "This may take a few minutes."
            _children.append("why")
            _comps.append({"id": "why", "component": {"Text": {"text": {"literalString": _why}, "usageHint": "caption"}}})
        _children.extend(["scopeField", "actions"])
        _comps.append({"id": "col", "component": {"Column": {"children": {"explicitList": _children}, "distribution": "start", "alignment": "stretch"}}})
        _comps.append({"id": "scopeField", "component": {"TextField": {"label": {"literalString": _g("label_field", "Adjust scope")}, "text": {"path": "/form/scope"}, "textFieldType": "longText"}}})
        _comps.append({"id": "actions", "component": {"Row": {"children": {"explicitList": ["bInline", "bBg", "bRefine"]}, "distribution": "spaceEvenly", "alignment": "center"}}})
        _comps.append({"id": "bInline", "component": {"Button": {"child": "bInlineL", "primary": True, "action": {"name": "sendText", "context": [{"key": "text", "value": {"literalString": "Run Inline: " + scope_text}}, {"key": "pf", "value": {"literalString": "1"}}]}}}})
        _comps.append({"id": "bInlineL", "component": {"Text": {"text": {"literalString": _g("label_inline", "Run inline now")}, "usageHint": "body"}}})
        _comps.append({"id": "bBg", "component": {"Button": {"child": "bBgL", "action": {"name": "sendText", "context": [{"key": "text", "value": {"literalString": "Run in Background: " + scope_text}}]}}}})
        _comps.append({"id": "bBgL", "component": {"Text": {"text": {"literalString": _g("label_background", "Run in background")}, "usageHint": "body"}}})
        _comps.append({"id": "bRefine", "component": {"Button": {"child": "bRefineL", "action": {"name": "sendText", "context": [{"key": "text", "value": {"path": "/form/scope"}}]}}}})
        _comps.append({"id": "bRefineL", "component": {"Text": {"text": {"literalString": _g("label_adjust", "Adjust & re-propose")}, "usageHint": "body"}}})
        _card = [
            {"beginRendering": {"surfaceId": "analysis-plan", "root": "root"}},
            {"dataModelUpdate": {"surfaceId": "analysis-plan", "path": "/form", "contents": [{"key": "scope", "valueString": scope_text}]}},
            {"surfaceUpdate": {"surfaceId": "analysis-plan", "components": _comps}},
        ]
        _parts = []
        for _m in _card:
            _parts.extend(create_a2ui_parts(_m))
        return _parts
    except Exception as _e:
        logger.log_text("[preflight_gate] card build failed (fail-open): " + str(_e)[:200])
        return None
if os.environ.get("ENABLE_MANAGED_AGENT") == "1":

    def _is_autonomous_confirmed_press(run_args):
        # True when the press came from the Autonomous Briefing card's buttons,
        # which carry context {"ra": "1"} - same mechanism as the Analysis
        # card's pf marker.
        try:
            _nm = run_args.get("new_message") if isinstance(run_args, dict) else None
            if _nm is None:
                return False
            for _p in (getattr(_nm, "parts", None) or []):
                _t = getattr(_p, "text", None)
                if _t and "userAction" in _t:
                    try:
                        _ua = json.loads(_t).get("userAction", {}) or {}
                        if str((_ua.get("context", {}) or {}).get("ra", "")) == "1":
                            return True
                    except Exception:
                        pass
        except Exception:
            return False
        return False

    def _build_autonomous_briefing_card_parts(plan, scope_text):
        """Autonomous Task Briefing card v2: shown BEFORE delegation when the
        classifier found material information gaps (plan['missing']). Each gap
        gets its OWN input - a one-line TextField pre-filled with the suggested
        default, or chips when the classifier supplied discrete options. A2UI
        buttons cannot concatenate strings, but a press delivers EVERY context
        key server-side with path references already resolved to data-model
        values, so Start sends the original scope (literal) plus q<i>/a<i>/s<i>
        keys and the server composes the final brief deterministically in the
        ra-press SYSTEM NOTE."""
        try:
            def _g(_k, _d):
                _v = plan.get(_k)
                return _v if (isinstance(_v, str) and _v.strip()) else _d
            _missing = plan.get("missing")
            if not isinstance(_missing, list):
                return None
            _qs = []
            for _mq in _missing[:3]:
                if isinstance(_mq, dict):
                    _q = _mq.get("question")
                    if isinstance(_q, str) and _q.strip():
                        _s = _mq.get("suggestion")
                        _s = _s.strip() if isinstance(_s, str) and _s.strip() else ""
                        _opts = []
                        _oraw = _mq.get("options")
                        if isinstance(_oraw, list):
                            for _o in _oraw:
                                if isinstance(_o, str) and _o.strip():
                                    _opts.append(_o.strip())
                        _opts = _opts[:4] if len(_opts) >= 2 else []
                        _qs.append((_q.strip(), _s, _opts))
            if not _qs:
                return None
            # card_title is a SHORT heading; goal (a full sentence) is demoted to a
            # body line. Truncate defensively in case the classifier omitted
            # card_title and the goal fallback is long - a sentence rendered as h2
            # dominated the whole card in live tests.
            _title = _g("card_title", _g("goal", scope_text))
            if len(_title) > 80:
                _title = _title[:79] + chr(0x2026)
            _goal = _g("goal", "")
            _deliv = _g("deliverable", "")
            _intro = _g("briefing_intro", "Before the autonomous run starts, please confirm a few details.")
            _intro_line = (chr(0x1F4E6) + " " + _deliv + " - " + _intro) if _deliv else _intro
            _comps = []
            _children = ["title"]
            _comps.append({"id": "root", "component": {"Card": {"child": "col"}}})
            _comps.append({"id": "title", "component": {"Text": {"text": {"literalString": chr(0x1F6F0) + chr(0xFE0F) + " " + _title}, "usageHint": "h2"}}})
            if _goal and _goal != _title:
                _children.append("goal")
                _comps.append({"id": "goal", "component": {"Text": {"text": {"literalString": _goal}, "usageHint": "body"}}})
            _children.append("intro")
            _comps.append({"id": "intro", "component": {"Text": {"text": {"literalString": _intro_line}, "usageHint": "caption"}}})
            _dm = []
            _start_ctx = [{"key": "text", "value": {"literalString": scope_text}}, {"key": "ra", "value": {"literalString": "1"}}]
            for _qi in range(len(_qs)):
                _q, _s, _opts = _qs[_qi]
                _ak = "a" + str(_qi)
                _fid = "f" + str(_qi)
                if _opts:
                    # Chips answer: question as a body line, choices as single-select
                    # chips bound to /form/a<i>. No pre-selection (the chip data-model
                    # shape is client-managed); an untouched question falls back to
                    # its suggestion server-side via the s<i> context key.
                    _qid = "q" + str(_qi)
                    _children.append(_qid)
                    _comps.append({"id": _qid, "component": {"Text": {"text": {"literalString": _q}, "usageHint": "body"}}})
                    _oitems = []
                    for _o in _opts:
                        _oitems.append({"label": {"literalString": _o}, "value": _o})
                    _children.append(_fid)
                    _comps.append({"id": _fid, "component": {"MultipleChoice": {"selections": {"path": "/form/" + _ak}, "options": _oitems, "maxAllowedSelections": 1, "variant": "chips"}}})
                else:
                    # Free-text answer: the question itself is the field label, the
                    # suggestion is pre-filled so the user only edits what differs.
                    _children.append(_fid)
                    _comps.append({"id": _fid, "component": {"TextField": {"label": {"literalString": _q}, "text": {"path": "/form/" + _ak}}}})
                    if _s:
                        _dm.append({"key": _ak, "valueString": _s})
                _start_ctx.append({"key": "q" + str(_qi), "value": {"literalString": _q}})
                _start_ctx.append({"key": _ak, "value": {"path": "/form/" + _ak}})
                if _s:
                    _start_ctx.append({"key": "s" + str(_qi), "value": {"literalString": _s}})
            _children.extend(["sep", "actions"])
            _comps.append({"id": "sep", "component": {"Divider": {}}})
            _comps.append({"id": "col", "component": {"Column": {"children": {"explicitList": _children}, "distribution": "start", "alignment": "stretch"}}})
            _comps.append({"id": "actions", "component": {"Row": {"children": {"explicitList": ["bStart", "bAsis"]}, "distribution": "spaceEvenly", "alignment": "center"}}})
            _comps.append({"id": "bStart", "component": {"Button": {"child": "bStartL", "primary": True, "action": {"name": "sendText", "context": _start_ctx}}}})
            _comps.append({"id": "bStartL", "component": {"Text": {"text": {"literalString": chr(0x1F680) + " " + _g("label_start", "Confirm & start autonomous task")}, "usageHint": "body"}}})
            _comps.append({"id": "bAsis", "component": {"Button": {"child": "bAsisL", "action": {"name": "sendText", "context": [{"key": "text", "value": {"literalString": scope_text}}, {"key": "ra", "value": {"literalString": "1"}}]}}}})
            _comps.append({"id": "bAsisL", "component": {"Text": {"text": {"literalString": _g("label_asis", "Start as-is")}, "usageHint": "body"}}})
            _card = [{"beginRendering": {"surfaceId": "autonomous-briefing", "root": "root"}}]
            if _dm:
                _card.append({"dataModelUpdate": {"surfaceId": "autonomous-briefing", "path": "/form", "contents": _dm}})
            _card.append({"surfaceUpdate": {"surfaceId": "autonomous-briefing", "components": _comps}})
            _parts = []
            for _m in _card:
                _parts.extend(create_a2ui_parts(_m))
            return _parts
        except Exception as _e:
            logger.log_text("[autonomous_briefing] card build failed (fail-open): " + str(_e)[:200])
            return None

    def _extract_briefing_answers(run_args):
        # Harvests the q<i>/a<i>/s<i> keys a Start press carried in its userAction
        # context: q<i> is the question (literal), a<i> the user's answer (path
        # reference, resolved client-side at press time), s<i> the classifier's
        # suggested default. Empty answers fall back to the suggestion; chips may
        # deliver the selection as a JSON array string, which is normalized here.
        _pairs = []
        try:
            _nm = run_args.get("new_message") if isinstance(run_args, dict) else None
            if _nm is None:
                return _pairs
            for _p in (getattr(_nm, "parts", None) or []):
                _t = getattr(_p, "text", None)
                if not (_t and "userAction" in _t):
                    continue
                try:
                    _ctx = (json.loads(_t).get("userAction", {}) or {}).get("context", {}) or {}
                except Exception:
                    continue
                for _i in range(3):
                    _q = _ctx.get("q" + str(_i))
                    if not (isinstance(_q, str) and _q.strip()):
                        continue
                    _a = _ctx.get("a" + str(_i))
                    if isinstance(_a, list):
                        _a = ", ".join(str(_x) for _x in _a)
                    if isinstance(_a, str) and _a.strip().startswith("["):
                        try:
                            _al = json.loads(_a)
                            if isinstance(_al, list):
                                _a = ", ".join(str(_x) for _x in _al)
                        except Exception:
                            pass
                    _a = _a.strip() if isinstance(_a, str) else ""
                    if not _a:
                        _s = _ctx.get("s" + str(_i))
                        _a = _s.strip() if isinstance(_s, str) else ""
                    if _a:
                        _pairs.append((_q.strip(), _a))
                if _pairs:
                    break
        except Exception:
            return _pairs
        return _pairs

artifact_service = InMemoryArtifactService()

runner = Runner(
    app=adk_app,
    artifact_service=artifact_service,
    session_service=InMemorySessionService(),
)

# Background task runner — uses Pro model agent for deep reasoning
background_app = App(
    name="background_app",
    root_agent=background_agent,
    plugins=[
        ReflectAndRetryToolPlugin(),
        LoggingPlugin()
    ],
    events_compaction_config=EventsCompactionConfig(
        compaction_interval=20,
        overlap_size=3
    ),
)

background_runner = Runner(
    app=background_app,
    artifact_service=artifact_service,
    session_service=InMemorySessionService(),
)

# =============================================================================
# A2UI SDK — Shared Schema Manager & Catalog (matches agent.py config)
# =============================================================================
a2ui_schema_manager = A2uiSchemaManager(
    version=VERSION_0_8,
    catalogs=[
        BasicCatalog.get_config(
            version=VERSION_0_8,
            examples_path="adk_agent/app/examples/0.8"
        )
    ],
)
a2ui_selected_catalog = a2ui_schema_manager.get_selected_catalog()

def _truncate_response_deep(_obj, _max_chars):
    """Recursively truncate strings exceeding _max_chars in dicts/lists."""
    if isinstance(_obj, str):
        if len(_obj) > _max_chars:
            return _obj[:_max_chars] + "...[TRUNCATED]"
        return _obj
    elif isinstance(_obj, dict):
        return {k: _truncate_response_deep(v, _max_chars) for k, v in _obj.items()}
    elif isinstance(_obj, list):
        return [_truncate_response_deep(item, _max_chars) for item in _obj]
    return _obj

def _heal_session_events(session, force_aggressive=False):
    if not session or not hasattr(session, 'events') or not session.events:
        return
    
    healed_events = []
    prev_content_event = None
    _merge_counts = {}
    _stripped_errors = 0
    _original_count = len(session.events)
    
    for event in session.events:
        # Strip failed/error events (like MALFORMED_FUNCTION_CALL) from history to prevent recovery pollution
        if getattr(event, 'error_code', None):
            _stripped_errors += 1
            continue
            
        if getattr(event, 'content', None) and getattr(event.content, 'role', None):
            role = event.content.role
            if prev_content_event and getattr(prev_content_event, 'content', None) and prev_content_event.content.role == role:
                # Duplicate role detected! Merge parts.
                _merge_counts[role] = _merge_counts.get(role, 0) + 1
                if getattr(event.content, 'parts', None):
                    if not getattr(prev_content_event.content, 'parts', None):
                        prev_content_event.content.parts = []
                    prev_content_event.content.parts.extend(event.content.parts)
                # Skip adding this event to healed_events (it is merged into prev)
                continue
            else:
                prev_content_event = event
        healed_events.append(event)
    
    _total_merges = sum(_merge_counts.values())
    if _total_merges > 0 or _stripped_errors > 0:
        _merge_detail = ", ".join(f"{r}={c}" for r, c in sorted(_merge_counts.items()))
        logger.log_text(
            f"[HEALER] Summary: {_original_count} events -> {len(healed_events)} "
            f"(merged: {_total_merges} [{_merge_detail}], errors_stripped: {_stripped_errors})"
        )

    # =========================================================================
    # Token reduction (v10.62) — keeps the input context under the 1M-token
    # model window. Triggered when ANY of:
    #   - force_aggressive=True (emergency, after a token-overflow ClientError)
    #   - the root model is a lightweight model (flash-lite) — always compact
    #   - the measured context size exceeds the char budget. Heavier models
    #     (3.6-flash / pro) keep FULL context UNTIL near the limit, so normal
    #     large reports are never trimmed — only runaway contexts are.
    # Char-based by design: generated-image bytes are NOT stored in history
    # (generate_image stashes them in session.state), so the real bloat is
    # text — SQL result sets, MCP payloads, multi-turn accumulation.
    # =========================================================================
    _root_model = os.environ.get("AGENT_MODEL_LITE", "gemini-3.6-flash").lower()
    _is_lite = "lite" in _root_model

    def _event_char_size(_ev):
        _content = getattr(_ev, 'content', None)
        if not _content or not getattr(_content, 'parts', None):
            return 0
        _sz = 0
        for _part in _content.parts:
            _t = getattr(_part, 'text', None)
            if isinstance(_t, str):
                _sz += len(_t)
            _fr = getattr(_part, 'function_response', None)
            if _fr and hasattr(_fr, 'response'):
                try:
                    _sz += len(str(_fr.response))
                except Exception:
                    pass
        return _sz
    _ctx_chars = sum(_event_char_size(_ev) for _ev in healed_events)

    # ~1M-token window. JA can be ~1 char/token, so trigger well below 1M chars
    # while staying clear of typical English reports (~4 chars/token). X-C's
    # error-driven salvage is the hard backstop if anything slips past this.
    _CHAR_BUDGET = 1800000
    if force_aggressive or _is_lite or _ctx_chars > _CHAR_BUDGET:
        if force_aggressive:
            _MAX_TOOL_CHARS = 1500
            _MAX_EVENTS = 30
            _mode = "aggressive"
        elif _is_lite:
            _MAX_TOOL_CHARS = 2000
            _MAX_EVENTS = 40
            _mode = "lite"
        else:
            _MAX_TOOL_CHARS = 8000
            _MAX_EVENTS = 60
            _mode = "budget"
        _truncated_parts = 0

        # 1. Truncate large content in event parts
        for _ev in healed_events:
            _content = getattr(_ev, 'content', None)
            if not _content or not getattr(_content, 'parts', None):
                continue
            for _part in _content.parts:
                # Truncate long text parts (e.g. large SQL results as text)
                _text = getattr(_part, 'text', None)
                if isinstance(_text, str) and len(_text) > _MAX_TOOL_CHARS:
                    _part.text = _text[:_MAX_TOOL_CHARS] + chr(10) + "...[TRUNCATED from " + str(len(_text)) + " chars]"
                    _truncated_parts += 1
                # Truncate function response payloads (nested dicts from MCP tools)
                _fr = getattr(_part, 'function_response', None)
                if _fr and hasattr(_fr, 'response') and isinstance(_fr.response, dict):
                    _before = str(_fr.response)
                    if len(_before) > _MAX_TOOL_CHARS:
                        _fr.response = _truncate_response_deep(_fr.response, _MAX_TOOL_CHARS)
                        _truncated_parts += 1

        # 2. Cap event count: keep first 2 (initial context) + most recent events
        _pre_cap = len(healed_events)
        if _pre_cap > _MAX_EVENTS:
            healed_events = healed_events[:2] + healed_events[-(_MAX_EVENTS - 2):]

        if _truncated_parts > 0 or _pre_cap > _MAX_EVENTS:
            logger.log_text(
                "[HEALER] Token reduction (" + _mode + "): ctx_chars=" + str(_ctx_chars)
                + " truncated=" + str(_truncated_parts) + " parts, events "
                + str(_pre_cap) + "->" + str(len(healed_events)) + " (max=" + str(_MAX_EVENTS) + ")"
            )

    session.events = healed_events


# =============================================================================
# Y2 (v10.63): Per-session in-flight serialization.
# Concurrent ADK runs on the SAME InMemorySession corrupt each other: a new
# request calls _heal_session_events (mutating session.events) WHILE a slow
# in-flight invocation (e.g. a ~60s inline deep_analysis) is mid-iteration,
# which silently kills the in-flight run so it never completes. We serialize
# invocations per session_id with an asyncio.Lock so a later request WAITS for
# the in-flight one to finish (and runs on the healed session) instead of
# racing it. Single event loop -> the dict access needs no extra locking.
# Demo services run minScale=1 / concurrency>1, so same-session requests land
# on the same instance, making an in-process lock sufficient.
# =============================================================================
_session_locks = {}
def _get_session_lock(_sid):
    import asyncio as _sl_asyncio
    _lk = _session_locks.get(_sid)
    if _lk is None:
        _lk = _sl_asyncio.Lock()
        _session_locks[_sid] = _lk
    return _lk


# =============================================================================
# G1 (v10.65): Replay cache for duplicate action presses.
# A single A2UI press is delivered as 3-5 identical invocations (multi-fire /
# stream retries). The winner caches its final deliverable here keyed by the
# idempotency key; duplicates re-emit the SAME parts so whichever stream GE
# displays shows the real result instead of an empty "completed" turn. Same
# event loop -> no extra locking; bounded to the most-recent entries.
# =============================================================================
_idem_results = {}
def _store_idem_result(_key, _parts):
    if not _key or not _parts:
        return
    _idem_results[_key] = _parts
    if len(_idem_results) > 300:
        for _old in list(_idem_results.keys())[:len(_idem_results) - 300]:
            _idem_results.pop(_old, None)


def _rescope_replay_parts(_parts, _suffix):
    """Deep-copy replayed parts and re-anchor their A2UI surfaces to THIS task.

    GE anchors a surfaceId to the message where it FIRST rendered
    (conversation-level singleton). Replaying a cached artifact verbatim on a
    different task therefore re-renders NOTHING for its card surfaces: the
    beginRendering/surfaceUpdate just patch the ORIGINAL turn's card in place
    and the replay turn shows text only (confirmed 2026-06-10: a duplicate
    press turn displayed the prior turn's text while its 'flex-form' card
    never appeared). Renaming every surfaceId with a per-replay suffix forces
    GE to create fresh surfaces anchored to the replay turn, so the replayed
    turn visually matches the winner turn. deleteSurface is left untouched:
    it targets the ORIGINAL surface and renaming it would only turn a valid
    teardown into a no-op. Suggestions surfaces are already per-turn scoped
    ('suggestions-<task>'); the extra suffix keeps the 'suggestions' prefix
    that downstream checks rely on.
    """
    _sfx = re.sub(r'[^A-Za-z0-9_-]', '', str(_suffix or ''))[:48]
    if not _sfx or not _parts:
        return _parts
    def _rename(_obj):
        if isinstance(_obj, dict):
            for _k in ('beginRendering', 'surfaceUpdate', 'dataModelUpdate'):
                _v = _obj.get(_k)
                if isinstance(_v, dict) and _v.get('surfaceId'):
                    _v['surfaceId'] = str(_v['surfaceId']) + '-r' + _sfx
        elif isinstance(_obj, list):
            for _it in _obj:
                _rename(_it)
    _out = []
    for _p in _parts:
        try:
            _root = getattr(_p, 'root', None)
            if isinstance(_root, a2a_types.DataPart) and getattr(_root, 'data', None) is not None:
                _cp = _p.model_copy(deep=True)
                _rename(_cp.root.data)
                _out.append(_cp)
            else:
                _out.append(_p)
        except Exception:
            _out.append(_p)
    return _out


# =============================================================================
# H1 (v10.66): Per-session last-deliverable cache for GE "Regenerate".
# GE's "Regenerate response" re-sends the SAME request as a NEW invocation
# (different idempotency key, so G1 replay does not catch it). The model, seeing
# the answer already in history, returns an empty/short response — which the
# terminal else-branch used to emit as a content-replacing final, BLANKING the
# delivered report. We cache the last real deliverable per session keyed by a
# stable message signature; when a turn yields NO new deliverable AND its
# signature matches the cached one (i.e. a re-send/regenerate of the same
# request), we replay the cached parts instead of blanking the turn.
# =============================================================================
_session_last_artifact = {}
def _store_session_artifact(_sid, _sig, _parts):
    if not _sid or not _parts:
        return
    _session_last_artifact[_sid] = (_sig, _parts)
    if len(_session_last_artifact) > 300:
        for _old in list(_session_last_artifact.keys())[:len(_session_last_artifact) - 300]:
            _session_last_artifact.pop(_old, None)

def _msg_signature(_run_args):
    # Stable across a GE regenerate (which keeps the same chip/text but may change
    # the userAction timestamp): key on sourceComponentId + context text, or the
    # typed text. Deliberately ignores surfaceId (carries a per-turn UUID suffix).
    try:
        import json as _sj
        _typed = ''
        for _p in (getattr(_run_args.get('new_message'), 'parts', None) or []):
            _t = getattr(_p, 'text', None)
            if not _t:
                continue
            if 'userAction' in _t:
                try:
                    _ua = _sj.loads(_t).get('userAction', {}) or {}
                    _ctx = _ua.get('context', {}) or {}
                    return 'ua|' + str(_ua.get('sourceComponentId', '')) + '|' + str(_ctx.get('text', ''))
                except Exception:
                    pass
            else:
                _typed = _t
        return 'txt|' + _typed
    except Exception:
        return ''

# =============================================================================
# Inline render deadline (v10.80)
# The GE client stops rendering a streamed turn at roughly 120s; anything the
# agent delivers after that renders as a permanently blank "thinking" state
# (confirmed: a 339s "Run Inline" turn delivered a full report over HTTP 200
# to a client that had stopped listening). Every A2A turn is inline by
# definition (background work goes through /execute_task), so the executor
# enforces two budgets per turn:
#   - INLINE_SOFT_TOOL_BUDGET_S: arms the agent-side tool gate
#     (_inline_tool_budget_gate in agent.py) - past this point tool calls are
#     blocked (and generate_image is blocked outright) so the model must
#     synthesize from data in hand.
#   - INLINE_HARD_DEADLINE_S: the conversion watchdog ends the turn while it
#     still renders by moving the work to a REAL background task (the
#     /execute_task worker, which runs to completion and is retrievable via a
#     "Check Task Status" chip). Applies to BOTH "Run Inline:" chip presses
#     and plain typed analytical requests.
#
# v10.80 fix (was v10.79): the old hard-deadline path showed a "press Continue"
# chip for typed requests and claimed "the work continues in this session". It
# did NOT - aclose() cancels the ADK run, so no final report is ever produced;
# pressing Continue re-ran from scratch -> overran again -> infinite loop
# (confirmed on demo-material-invent-54d97d4d). The continue-chip path is gone:
# every overrun now becomes a real, retrievable background task, the conversion
# is NO LONGER stored under the H1 session-artifact key (which made a re-send
# replay the dead-end message), and incidental generate_image (a 30-40s sink
# that caused most overruns) is blocked inline.
# =============================================================================
# v10.99 (operator preference): do NOT auto-convert an overrunning inline turn to
# a background task. Instead cap inline gathering with a TIGHTER soft budget and,
# once it is hit, force the model to SYNTHESIZE THE REPORT INLINE from the data
# already gathered (partial but immediate) - the user always gets an inline answer.
# Background stays OPT-IN only (the pre-flight card, an explicit chip, or a
# scheduled task).
# Context (still valid, from v10.98): the v10.87 "GE renders silently up to 360s"
# premise was WRONG for real analyses - that probe streamed a constant heartbeat,
# whereas a real heavy analysis has long SILENT gaps (big SQL, generate_image,
# synthesis). Logs (demo-video-archiving, 2026-06-15) show GE re-issues the press
# ~every 60s with no output and can error on very long turns. Capping gathering at
# 180s (was 250s) bounds the turn; generate_image - the biggest single sink - is
# reserved out earlier so the forced synthesis still fits. All env-tunable.
_INLINE_OVERRUN_CONVERT = os.environ.get('INLINE_OVERRUN_CONVERT', '0') == '1'
_INLINE_SOFT_TOOL_BUDGET_S = float(os.environ.get('INLINE_SOFT_TOOL_BUDGET_S', '180'))
_INLINE_HARD_DEADLINE_S = float(os.environ.get('INLINE_HARD_DEADLINE_S', '600'))
# Cutoff for generate_image: the single biggest inline time sink (~30-40s); block
# it well before the soft cutoff so the forced inline synthesis still fits the
# budget. Offer the summary image as a one-click drill-down chip instead.
_INLINE_IMAGE_BUDGET_S = float(os.environ.get('INLINE_IMAGE_BUDGET_S', '150'))
# Control-action context texts that must NEVER be converted into a background
# task (they carry no analysis intent of their own).
_INLINE_CONTROL_PREFIXES = ('continue', 'check progress', 'view full report', 'open operations')
# Internal re-prompt markers (synth/continue/chip salvage) that must not be
# mistaken for a real user request when building background-conversion context.
_INLINE_INTERNAL_MARKERS = ('using ', 'your previous', 'run the full-depth')

def _overrun_bg_prompt(_run_args):
    # Derive a full-depth background-task prompt for a turn that overran the
    # inline render deadline. Handles intent-carrying chips ("Run Inline: X" /
    # "Run in Background: X") and plain typed requests. Returns '' for control
    # actions (Continue / Check progress / View full report) and the bare
    # "User action triggered." sentinel - those must NOT spawn a background task.
    try:
        _parts = getattr(_run_args.get('new_message'), 'parts', None) or []
    except Exception:
        return ''
    for _p in _parts:
        _t = (getattr(_p, 'text', '') or '').strip()
        if not _t:
            continue
        _ctx_text = _t
        if _t.startswith('{'):
            try:
                _obj = json.loads(_t)
                _ctx_text = str((((_obj.get('userAction') or {}).get('context') or {}).get('text') or ''))
            except Exception:
                _ctx_text = ''
        _ctx_text = _ctx_text.strip()
        if not _ctx_text or _ctx_text.lower() == 'user action triggered.':
            continue
        _low = _ctx_text.lower()
        if any(_low.startswith(_cp) for _cp in _INLINE_CONTROL_PREFIXES):
            return ''
        # Strip a leading "Run Inline:" / "Run in Background:" mode prefix.
        for _pfx in ('run inline:', 'run in background:'):
            if _low.startswith(_pfx):
                _ctx_text = _ctx_text[len(_pfx):].strip()
                break
        # Drop a trailing "(Quick first-pass: ...)" clause (ascii or fullwidth).
        for _op in ('(quick first-pass', chr(0xFF08) + 'quick first-pass'):
            _qi = _ctx_text.lower().rfind(_op)
            if _qi != -1:
                _ctx_text = _ctx_text[:_qi].strip()
                break
        if _ctx_text:
            return _ctx_text
    return ''

def _recent_user_texts(_session, _exclude, _limit=2):
    # Pull the last few genuine user-request texts from the session (newest
    # first), skipping chip JSON, control actions, and internal re-prompts.
    # Used to give a converted background task the conversation context a terse
    # follow-up (e.g. "しきい値分析をして") depends on.
    _out = []
    try:
        for _ev in reversed(getattr(_session, 'events', None) or []):
            _c = getattr(_ev, 'content', None)
            if not _c or getattr(_c, 'role', '') != 'user':
                continue
            for _pp in (getattr(_c, 'parts', None) or []):
                _tt = (getattr(_pp, 'text', '') or '').strip()
                if not _tt or _tt.startswith('{') or _tt == 'User action triggered.':
                    continue
                if _tt == _exclude:
                    continue
                _low = _tt.lower()
                if any(_low.startswith(_cp) for _cp in _INLINE_CONTROL_PREFIXES):
                    continue
                if any(_low.startswith(_m) for _m in _INLINE_INTERNAL_MARKERS):
                    continue
                if _tt not in _out:
                    _out.append(_tt)
            if len(_out) >= _limit:
                break
    except Exception:
        pass
    return _out

class AdkAgentToA2AExecutor(A2aAgentExecutor):
    # Note: Concurrent request dedup is handled at the Firestore level
    # in register_background_task (duplicate task_name check) and per-press
    # via the Y1 idempotency guard. Overlapping (non-identical) invocations on
    # one session are serialized by the Y2 per-session lock (see _get_session_lock).
    # The previous _active_contexts guard was removed because context_id
    # is shared across all interactions in a conversation, causing
    # legitimate subsequent requests to be blocked.

    async def _handle_request(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        await self._process_request(context, event_queue)

    async def _process_request(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        runner = await self._resolve_runner()

        # Scope the always-on 'suggestions' surface to THIS turn so its chips
        # render under the current message instead of leaking onto the previous
        # turn's response. context.task_id is unique per A2A task (= per turn);
        # consumed by _scope_suggestions_surface() via create_a2ui_part().
        try:
            _turn_suffix = re.sub(r'[^A-Za-z0-9_-]', '', str(context.task_id or ''))[:64] or uuid.uuid4().hex
            _current_suggestions_suffix.set(_turn_suffix)
        except Exception:
            pass

        run_args = part_converters.convert_a2a_request_to_adk_run_args(context)

        session_id = run_args['session_id']
        user_id = run_args['user_id']

        if os.environ.get("ENABLE_MANAGED_AGENT") == "1":
            # Deterministic completion delivery (v11.0): the state-based
            # {_bg_task_results} injection proved too weak on busy turns - a
            # "Run Inline" press transfers to deep_analysis (whose instruction has
            # no notification block) and a fresh-delegation turn ignores it, while
            # reported_to_user was already flipped, losing the announcement
            # forever (observed live 2026-07-13). So finished tasks are APPENDED
            # to the user's message itself as a system note: maximum salience for
            # whichever agent ends up answering the turn.
            try:
                import builtins as _ma_note_b
                _ma_fs = getattr(_ma_note_b, '_firestore_client', None)
                _ma_demo = os.environ.get('DEMO_ID', '')
                _ma_nm = run_args.get('new_message')
                if _ma_fs and _ma_demo and _ma_nm is not None and getattr(_ma_nm, 'parts', None) is not None:
                    _ma_ndocs = _ma_fs.collection(_ma_demo + '_task_executions').where(
                        'reported_to_user', '==', False).where(
                        'status', 'in', ['completed', 'failed']).limit(3).stream()
                    _ma_notes = []
                    for _ma_nd in _ma_ndocs:
                        _ma_ndd = _ma_nd.to_dict()
                        _ma_full = _ma_ndd.get('result_summary', '') or ''
                        _ma_note = ('Task ticket ' + _ma_ndd.get('task_id', '') + ' status: ' + _ma_ndd.get('status', '')
                                    + '. Result summary (first 400 chars): ' + _ma_full[:400])
                        # The 400-char cut can drop the Drive webViewLink the sandbox put
                        # further down the report, which made the root call the fallback
                        # Drive tool and then claim no file existed (observed 2026-07-14).
                        # Surface every Workspace link from the FULL report deterministically.
                        _ma_links = re.findall(r'https://(?:docs|drive|sheets|slides)[.]google[.]com/[A-Za-z0-9./?=&#%_+:~@-]+', _ma_full)
                        if _ma_links:
                            _ma_note = _ma_note + ' Workspace links found in the full report: ' + ' '.join(_ma_links[:5])
                        # Same salience treatment for GCS deliverable downloads: the signed-URL
                        # markdown links live at the END of the report, far past the 400-char cut.
                        if 'DELIVERABLE DOWNLOADS' in _ma_full:
                            _ma_dl = [_l for _l in _ma_full.split(chr(10)) if _l.strip().startswith('- [')][:5]
                            if _ma_dl:
                                _ma_note = (_ma_note + ' Deliverable download links (present these to the user as '
                                            'markdown links in the announcement; an .html link opens as an interactive '
                                            'page in the browser): ' + ' '.join(_ma_dl))
                        if 'SYSTEM CHECK (auto-generated): no deliverable files' in _ma_full:
                            _ma_note = (_ma_note + ' WARNING: the task uploaded NO deliverable files - any files the '
                                        'summary mentions exist only in the sandbox and were NOT delivered. Tell the '
                                        'user honestly and offer a follow-up autonomous task to upload them (delegate '
                                        'it with deliverables_for_task_id set to this ticket-id so the links attach '
                                        'to this task).')
                        _ma_notes.append(_ma_note)
                        _ma_nd.reference.update({'reported_to_user': True})
                    if _ma_notes:
                        _ma_note_text = ('SYSTEM NOTE (auto-generated; the user did NOT type this): a background task just finished. '
                                         'BEFORE addressing the user message above, announce this result briefly in the user language, '
                                         'and include a suggestion chip labelled with the localized equivalent of View Full Report whose '
                                         'sendText is: Show the full detailed report for task <ticket-id>. Details: ' + ' | '.join(_ma_notes))
                        if (os.environ.get("ENABLE_WORKSPACE_MCP") == "1" or os.environ.get("ENABLE_WORKSPACE_AUTH") == "1"):
                            _ma_note_text = (_ma_note_text
                                             + ' DRIVE HANDLING: if the summary or the Workspace links above show the autonomous '
                                               'agent ALREADY saved the output to Google Drive / Docs / Slides / Sheets, that save '
                                               'is DONE - present it as fact with those links as markdown links and do NOT call '
                                               'save_deliverables_to_drive. Only when the original request asked for Drive but the '
                                               'report confirms no completed Drive save (no Workspace links, or it says the save '
                                               'failed), call save_deliverables_to_drive in this turn. If that tool returns '
                                               'not_found, it only means no staged copies exist - NEVER tell the user the task '
                                               'produced no files; check get_autonomous_task_status for the full report instead. '
                                               'For deliverables NOT yet in Drive, offer a chip labelled with the localized '
                                               'equivalent of Save to Google Drive, whose sendText is: '
                                               'Save the deliverables of task <ticket-id> to Google Drive.')
                        _ma_nm.parts.append(genai_types.Part(text=_ma_note_text))
                        logger.log_text('[managed_agent] appended completion note for ' + str(len(_ma_notes)) + ' task(s) to the user message')

                if (os.environ.get("ENABLE_WORKSPACE_MCP") == "1" or os.environ.get("ENABLE_WORKSPACE_AUTH") == "1"):
                    # Rotating Workspace-token objects (best-effort, throttled to one
                    # refresh per 120s): every user turn carries a FRESH user token,
                    # so we mirror it into autonomous/<task>/.wstoken for each ACTIVE
                    # autonomous task. The sandbox re-fetches it via a pre-signed URL
                    # when its token snapshot expires mid-run. Limit: if the user
                    # never interacts, no fresh token exists anywhere (GE only mints
                    # tokens per request).
                    try:
                        import time as _ma_tt
                        _ma_tok = getattr(_ma_note_b, '_workspace_oauth_token', '')
                        _ma_last_rot = getattr(_ma_note_b, '_ma_token_obj_ts', 0)
                        if _ma_tok and (_ma_tt.time() - _ma_last_rot) > 120:
                            _ma_note_b._ma_token_obj_ts = _ma_tt.time()
                            def _ma_rotate_token_objects(_tok=_ma_tok, _fsc=_ma_fs, _demo=_ma_demo):
                                try:
                                    _bkt = os.environ.get('DASHBOARDS_BUCKET', '').strip()
                                    if not _bkt:
                                        return
                                    from google.cloud import storage as _st
                                    _cl = _st.Client()
                                    _actives = _fsc.collection(_demo + '_task_executions').where(
                                        'status', 'in', ['submitted', 'working']).limit(5).stream()
                                    for _rd in _actives:
                                        _tid = _rd.to_dict().get('task_id', '')
                                        if not _tid:
                                            continue
                                        _dsnap = _fsc.collection(_demo + '_task_definitions').document(_tid).get()
                                        if _dsnap.exists and _dsnap.to_dict().get('task_type') == 'autonomous':
                                            _cl.bucket(_bkt).blob('autonomous/' + _tid + '/.wstoken').upload_from_string(_tok, content_type='text/plain')
                                except Exception:
                                    pass
                            import asyncio as _ma_aio2
                            _ma_aio2.get_running_loop().run_in_executor(None, _ma_rotate_token_objects)
                    except Exception:
                        pass

            except Exception as _ma_note_err:
                logger.log_text('[managed_agent] completion-note injection failed: ' + str(_ma_note_err)[:200])
            if (os.environ.get("ENABLE_WORKSPACE_MCP") == "1" or os.environ.get("ENABLE_WORKSPACE_AUTH") == "1"):

                # Rotating Workspace-token objects for ACTIVE autonomous tasks: the
                # sandbox re-fetches the current user token via a pre-signed URL when
                # its snapshot expires. Refreshed on user turns, throttled to 120s,
                # written off-loop (best-effort).
                try:
                    import time as _ma_tt
                    import builtins as _ma_tb
                    _ma_tok = getattr(_ma_tb, '_workspace_oauth_token', '')
                    _ma_fs2 = getattr(_ma_tb, '_firestore_client', None)
                    _ma_demo2 = os.environ.get('DEMO_ID', '')
                    if _ma_tok and _ma_fs2 and _ma_demo2 and _ma_tt.time() - getattr(_ma_tb, '_ma_token_obj_ts', 0) > 120:
                        _ma_tb._ma_token_obj_ts = _ma_tt.time()
                        def _ma_rotate_token_objects():
                            try:
                                from google.cloud import storage as _st
                                _bkt = os.environ.get('DASHBOARDS_BUCKET', '').strip()
                                if not _bkt:
                                    return
                                _cl = _st.Client()
                                _run = _ma_fs2.collection(_ma_demo2 + '_task_executions').where(
                                    'status', 'in', ['submitted', 'working']).limit(5).stream()
                                for _rd in _run:
                                    _tid = _rd.to_dict().get('task_id', '')
                                    if not _tid:
                                        continue
                                    _dsnap = _ma_fs2.collection(_ma_demo2 + '_task_definitions').document(_tid).get()
                                    if _dsnap.exists and _dsnap.to_dict().get('task_type') == 'autonomous':
                                        _cl.bucket(_bkt).blob('autonomous/' + _tid + '/.wstoken').upload_from_string(_ma_tok, content_type='text/plain')
                            except Exception:
                                pass
                        import asyncio as _ma_aio3
                        _ma_aio3.get_running_loop().run_in_executor(None, _ma_rotate_token_objects)
                except Exception:
                    pass


        # v10.73: arm the cross-turn surfaceId reuse guard for THIS invocation
        # (consumed by _rescope_reused_surfaces() via create_a2ui_part()). The
        # suffix is strictly [0-9a-f] so renamed ids stay normalizable.
        try:
            _sg_suffix = re.sub(r'[^a-f0-9]', '', str(context.task_id or '').lower())[:12]
            if len(_sg_suffix) < 4:
                _sg_suffix = uuid.uuid4().hex[:12]
            _current_surface_guard.set({
                'registry': _get_surface_registry(session_id),
                'task': str(context.task_id or '') or _sg_suffix,
                'suffix': _sg_suffix,
            })
        except Exception:
            pass

        # =============================================================================
        # Y1/G1 (v10.65): Duplicate chip/button-press handling with REPLAY.
        # A single A2UI press arrives as 3-5 identical sendText invocations
        # (multi-fire / GE stream retries) on the same session, all carrying the
        # SAME userAction.timestamp. We serialize on the per-session lock (Y2),
        # then INSIDE the lock claim that timestamp once in Firestore: the first
        # holder is the winner (runs normally and caches its deliverable); later
        # holders are duplicates that REPLAY the winner's cached artifact on their
        # own task, so whichever stream GE shows displays the real result instead
        # of an empty "completed" turn. Serializing the claim inside the lock
        # guarantees the winner runs before any duplicate reads the cache.
        # Typed messages (no userAction timestamp) are never deduped.
        # =============================================================================
        _idem_key_raw = None
        _idem_src = ''
        try:
            import json as _idem_json
            _ua_ts = None
            _ua_surface = ''
            _ua_source = ''
            for _p in (getattr(run_args.get('new_message'), 'parts', None) or []):
                _pt = getattr(_p, 'text', None)
                if not (_pt and 'userAction' in _pt):
                    continue
                try:
                    _ua_obj = _idem_json.loads(_pt).get('userAction', {}) or {}
                except Exception:
                    _ua_obj = {}
                _ua_ts = _ua_obj.get('timestamp')
                _ua_surface = str(_ua_obj.get('surfaceId', ''))
                _ua_source = str(_ua_obj.get('sourceComponentId', ''))
                if _ua_ts:
                    break
            if _ua_ts:
                import hashlib as _idem_hl
                _idem_key_raw = _idem_hl.sha1(
                    (session_id + '|' + _ua_surface + '|' + _ua_source + '|' + str(_ua_ts)).encode('utf-8')
                ).hexdigest()
                _idem_src = _ua_source
        except Exception as _idem_err:
            logger.log_text("[idempotency] key parse skipped (non-fatal): " + str(_idem_err)[:160])

        # Serialize on the session lock (fail OPEN on timeout), then claim/replay/run.
        import asyncio as _y2_asyncio
        _sess_lock = _get_session_lock(session_id)
        _y2_held = False
        try:
            await _y2_asyncio.wait_for(_sess_lock.acquire(), timeout=850)
            _y2_held = True
        except Exception as _y2_err:
            logger.log_text("[session_lock] acquire skipped (non-fatal): " + str(_y2_err)[:120])
        try:
            _winner_key = None
            if _idem_key_raw:
                try:
                    import builtins as _idem_bi
                    from google.api_core import exceptions as _idem_exc
                    _idem_fs = getattr(_idem_bi, '_firestore_client', None)
                    _idem_demo = os.environ.get("DEMO_ID", "")
                    if _idem_fs and _idem_demo:
                        _idem_ref = _idem_fs.collection(_idem_demo + "_action_idempotency").document(_idem_key_raw)
                        _is_dup = False
                        try:
                            _idem_ref.create({
                                'claimed_at': datetime.now(timezone.utc).isoformat(),
                                'session_id': session_id,
                                'source_component_id': _idem_src,
                            })
                        except _idem_exc.AlreadyExists:
                            _is_dup = True
                        if _is_dup:
                            # Winner has already finished (we hold the lock after it);
                            # replay its cached deliverable on THIS duplicate task.
                            # Re-scope surfaceIds so the replayed cards actually
                            # render on this turn (v10.72, see _rescope_replay_parts).
                            _rp_parts = _rescope_replay_parts(
                                _idem_results.get(_idem_key_raw), context.task_id)
                            logger.log_text(
                                "[idempotency] duplicate press -> replay src=" + _idem_src
                                + " key=" + _idem_key_raw[:12] + " parts=" + str(len(_rp_parts) if _rp_parts else 0)
                            )
                            if _rp_parts:
                                await event_queue.enqueue_event(
                                    TaskArtifactUpdateEvent(
                                        task_id=context.task_id,
                                        last_chunk=True,
                                        context_id=context.context_id,
                                        artifact=Artifact(artifact_id=str(uuid.uuid4()), parts=_rp_parts),
                                    )
                                )
                            await event_queue.enqueue_event(
                                TaskStatusUpdateEvent(
                                    task_id=context.task_id,
                                    context_id=context.context_id,
                                    status=TaskStatus(
                                        state=TaskState.completed,
                                        timestamp=datetime.now(timezone.utc).isoformat(),
                                    ),
                                    final=True,
                                )
                            )
                            return
                        else:
                            _winner_key = _idem_key_raw
                except Exception as _claim_err:
                    logger.log_text("[idempotency] claim skipped (non-fatal): " + str(_claim_err)[:160])
            await self._process_request_body(context, event_queue, runner, run_args, session_id, user_id, idem_key=_winner_key)
        finally:
            if _y2_held:
                try:
                    _sess_lock.release()
                except Exception:
                    pass

    async def _process_request_body(
        self,
        context: RequestContext,
        event_queue: EventQueue,
        runner,
        run_args,
        session_id,
        user_id,
        idem_key=None,
    ) -> None:
        session = await runner.session_service.get_session(
            app_name=runner.app_name,
            user_id=user_id,
            session_id=session_id,
        )
        auth_id = os.environ.get("GEMINI_AUTHORIZATION_ID")
        initial_state = {}
        token = None
        
        # Extract token from context.call_context.state['headers']['authorization']
        if hasattr(context, 'call_context') and context.call_context:
            call_context_state = context.call_context.state if hasattr(context.call_context, 'state') else {}
            if isinstance(call_context_state, dict) and 'headers' in call_context_state:
                headers = call_context_state['headers']
                if 'authorization' in headers:
                    auth_header = headers['authorization']
                    if auth_header.startswith("Bearer "):
                        token = auth_header[7:] # Extract token after "Bearer "
            
        # Update the global token holder for Workspace MCP header_provider.
        # Uses builtins to share state across module boundaries.
        if token:
            import builtins
            builtins._workspace_oauth_token = token
            logger.log_text(f"TOKEN SET via builtins._workspace_oauth_token (prefix: {token[:20]}..., len: {len(token)})")
            # v11.6: per-session registry read by header_provider Strategy0.
            # This is the ONLY per-session store that stays fresh: mutating
            # session.state below does NOT persist (see comment there).
            try:
                if not hasattr(builtins, '_ws_session_tokens'):
                    builtins._ws_session_tokens = {}
                _wst = builtins._ws_session_tokens
                _wst.pop(session_id, None)
                _wst[session_id] = token
                while len(_wst) > 50:
                    _wst.pop(next(iter(_wst)))
            except Exception:
                pass

        if token and auth_id:
            initial_state[auth_id] = token
            
        if session is None:
          session = await runner.session_service.create_session(
              app_name=runner.app_name,
              user_id=user_id,
              state=initial_state,
              session_id=session_id,
          )
        else:
          # Update state if token is present in the new request.
          # v11.6 NOTE: this mutation does NOT persist - InMemorySessionService.
          # get_session returns a COPY, so the stored session keeps the
          # CREATE-time token forever (confirmed live 2026-07-16: it went stale
          # after the ~1h rotation and broke Drive saves). Kept only so code
          # reading THIS in-memory copy within the turn sees the fresh value;
          # the durable fresh sources are builtins._workspace_oauth_token and
          # builtins._ws_session_tokens (header_provider Strategies 0/1).
          if token and auth_id:
              session.state[auth_id] = token
          # Clear stale tool results from previous turns to prevent accidental force-injection
          session.state.pop('_last_tool_result', None)
          run_args['session_id'] = session.id

        # Heal the session history before running the agent to prevent MALFORMED_FUNCTION_CALL errors
        # caused by concurrent request race conditions (duplicate roles) or crash-recovery (consecutive user roles).
        _heal_session_events(session)

        # --- PRE-FLIGHT GATE (v10.93): server-rendered Analysis Plan card ---
        # For a FRESH heavy-analysis message (not already a "Run Inline:" /
        # "Run in Background:" choice), classify with a lightweight model and, if
        # it is a real multi-step analysis, render the Analysis Plan card here and
        # finish the turn BEFORE the agent runs. Inline is the recommended button;
        # the user's choice ("Run Inline: ...") then flows through to the agent.
        # The Adjust button resubmits the edited scope, which is re-classified.
        # Fail-open: any miss/error falls through to the normal agent run.
        try:
            _gate_text = _extract_user_text(run_args)
            # v10.96: also gate button/chip-triggered runs. A plain "Run Inline:"
            # drill-down chip used to bypass the card and run synchronously; now it
            # is re-classified and, if it is a heavy multi-step analysis, the card
            # is shown so the user can still choose background. Exceptions that must
            # NOT be carded: a "Run in Background:" press (already the safe choice)
            # and a confirmed inline press from the card's OWN button (pf=1), which
            # would otherwise loop. The scope handed to the classifier/card strips
            # the "Run Inline:" prefix so the card rebuilds clean action text.
            _gate_l = (_gate_text or "").lstrip().lower()
            _gate_is_inline = _gate_l.startswith("run inline:")
            _gate_is_bg = _gate_l.startswith("run in background:")
            _gate_skip = _gate_is_bg or _is_preflight_confirmed_press(run_args)
            # v11.6: fixed-English COMMAND chips (mandated verbatim sendTexts)
            # must go straight to the agent, never to the classifier. Confirmed
            # live 2026-07-16: "Save the deliverables..." was classified as
            # AUTONOMOUS, hijacking the inline save_deliverables_to_drive flow
            # into a sandbox delegation AND rendering the briefing card in
            # English mid-Japanese conversation (the fixed English sendText is
            # the only language signal the classifier sees). The other two
            # command chips waste a classifier LLM call per press the same way.
            _CMD_CHIP_PREFIXES = (
                "save the deliverables of task",
                "show the full detailed report for task",
                "check progress of task",
            )
            if not _gate_skip and any(_gate_l.startswith(_p) for _p in _CMD_CHIP_PREFIXES):
                _gate_skip = True
                logger.log_text("[preflight_gate] command-chip passthrough: " + _gate_l[:80])
            if os.environ.get("ENABLE_MANAGED_AGENT") == "1":
                # Autonomous Briefing card press (context ra=1): skip re-carding
                # and pin the delegation deterministically via a system note.
                if _is_autonomous_confirmed_press(run_args):
                    _gate_skip = True
                    try:
                        _ra_nm = run_args.get('new_message')
                        if _ra_nm is not None and getattr(_ra_nm, 'parts', None) is not None:
                            _ra_pairs = _extract_briefing_answers(run_args)
                            _ra_note = (
                                'SYSTEM NOTE (auto-generated; the user did NOT type this): the task brief in the user '
                                'message above was CONFIRMED via the Autonomous Task Briefing card. ')
                            if _ra_pairs:
                                _ra_note = _ra_note + 'CONFIRMED BRIEFING DETAILS (per-question answers the user confirmed on the card):' + chr(10)
                                for _ra_q, _ra_a in _ra_pairs:
                                    _ra_note = _ra_note + '- ' + _ra_q + ' ' + _ra_a + chr(10)
                                _ra_note = _ra_note + (
                                    'Compose the task_description from the user request above PLUS these confirmed '
                                    'details, then call delegate_autonomous_task as your VERY FIRST action ')
                            else:
                                _ra_note = _ra_note + (
                                    'Call delegate_autonomous_task as your VERY FIRST action with that brief as the '
                                    'task_description ')
                            _ra_note = _ra_note + (
                                '(rewrite it into outcome-only wording if it references internal tool names). '
                                + _MA_PREBROWSE_EXCEPTION +
                                'Do NOT ask any further clarifying questions and do NOT run the analysis inline.')
                            _ra_nm.parts.append(genai_types.Part(text=_ra_note))
                            logger.log_text('[autonomous_briefing] confirmed press - pinned delegation note (' + str(len(_ra_pairs)) + ' answers)')
                    except Exception:
                        pass

            _gate_scope = _gate_text.split(":", 1)[1].strip() if _gate_is_inline else _gate_text

            # v10.97: deterministic short-circuit for an explicit "Run in
            # Background:" press. Register the task HERE (bypassing the agent and
            # the F1 guard via submit_background_task_now) so a STICKY
            # deep_analysis_agent can never receive it, call register_background_task,
            # get F1-blocked by the "complete inline in THIS turn" message, and
            # dead-end into a MALFORMED storm / "Something went wrong". Dup-safe
            # (submit_background_task_now returns already_active); on any failure we
            # emit a retry chip instead of falling through to that dead-end path.
            if _gate_is_bg:
                _bg_scope = _gate_text.split(":", 1)[1].strip() if (":" in _gate_text) else ""
                if _bg_scope:
                    async def _emit_bg_terminal(_t, _chip_specs):
                        _parts = [a2a_types.Part(root=a2a_types.TextPart(text=_t))]
                        _comps = [{'id': 'root', 'component': {'Row': {'children': {'explicitList': ['bg_chip' + str(_i) for _i in range(len(_chip_specs))]}, 'distribution': 'spaceEvenly', 'alignment': 'center'}}}]
                        for _i in range(len(_chip_specs)):
                            _ct, _cl = _chip_specs[_i]
                            _comps.append({'id': 'bg_chip' + str(_i), 'component': {'Button': {'child': 'bg_chip' + str(_i) + 'Lbl', 'action': {'name': 'sendText', 'context': [{'key': 'text', 'value': {'literalString': _ct}}]}}}})
                            _comps.append({'id': 'bg_chip' + str(_i) + 'Lbl', 'component': {'Text': {'text': {'literalString': _cl}, 'usageHint': 'body'}}})
                        for _m in ({'beginRendering': {'surfaceId': 'suggestions', 'root': 'root'}}, {'surfaceUpdate': {'surfaceId': 'suggestions', 'components': _comps}}):
                            _parts.append(create_a2ui_part(_m))
                        await event_queue.enqueue_event(TaskStatusUpdateEvent(task_id=context.task_id, context_id=context.context_id, status=TaskStatus(state=TaskState.working, message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=_parts), timestamp=datetime.now(timezone.utc).isoformat()), final=False))
                        await event_queue.enqueue_event(TaskArtifactUpdateEvent(task_id=context.task_id, last_chunk=True, context_id=context.context_id, artifact=Artifact(artifact_id=str(uuid.uuid4()), parts=_parts)))
                        await event_queue.enqueue_event(TaskStatusUpdateEvent(task_id=context.task_id, status=TaskStatus(state=TaskState.completed, timestamp=datetime.now(timezone.utc).isoformat()), context_id=context.context_id, final=True))
                        if idem_key:
                            _store_idem_result(idem_key, _parts)
                    _bg_name = 'bg_press_' + ''.join(_c for _c in _bg_scope.lower() if _c.isalnum())[:24]
                    _bg_prompt = (
                        "Run the FULL-DEPTH version of the user's request below and deliver a "
                        "complete report. This is a background run with no chat time limit, so do "
                        "the thorough analysis (statistics, charts, recommendations). Ignore any "
                        "inline/quick-pass constraints mentioned in the request." + chr(10) + chr(10)
                        + "REQUEST:" + chr(10) + _bg_scope
                    )
                    try:
                        _bg_reg = await asyncio.to_thread(
                            _agent_tools.submit_background_task_now,
                            _bg_name,
                            'Background task requested by the user via a Run in Background press.',
                            _bg_prompt,
                        )
                    except Exception as _bg_reg_err:
                        _bg_reg = {'status': 'error', 'message': str(_bg_reg_err)[:200]}
                    if _bg_reg.get('status') in ('submitted', 'already_active'):
                        _bg_ticket = str(_bg_reg.get('ticket-id', ''))
                        await _emit_bg_terminal(
                            chr(0x1F680) + " Got it - this analysis is now running as a background task (ticket: "
                            + _bg_ticket + "). It keeps running to completion; press the button below to "
                            "check progress and retrieve the full report.",
                            [("Check progress of task " + _bg_ticket, chr(0x1F4CA) + " Check Task Status")],
                        )
                        logger.log_text("[preflight_gate] Run in Background press -> direct registration (ticket " + _bg_ticket + "), bypassed agent")
                        return
                    await _emit_bg_terminal(
                        chr(0x26A0) + chr(0xFE0F) + " I could not start the background task ("
                        + str(_bg_reg.get('message', 'unknown error'))[:160]
                        + "). Please press the button to try again.",
                        [("Run in Background: " + _bg_scope, chr(0x1F501) + " Try again")],
                    )
                    logger.log_text("[preflight_gate] bg direct-registration failed, emitted retry: " + str(_bg_reg.get('message', ''))[:160])
                    return

            if _gate_scope and not _gate_skip:
                # v11.6: pass the last human-typed message as a language
                # reference so an English chip sendText cannot flip the
                # card language (STEP 1 EXCEPTION in the classifier prompt).
                _plan = await _classify_for_preflight(_gate_scope, _last_typed_user_text(session))
                if isinstance(_plan, dict) and _plan.get("category") == "ANALYSIS":
                    _pf_parts = _build_preflight_card_parts(_plan, _gate_scope)
                    if _pf_parts:
                        await event_queue.enqueue_event(
                            TaskStatusUpdateEvent(
                                task_id=context.task_id,
                                status=TaskStatus(state=TaskState.working, timestamp=datetime.now(timezone.utc).isoformat()),
                                context_id=context.context_id,
                                final=False,
                                metadata={
                                    _get_adk_metadata_key('app_name'): runner.app_name,
                                    _get_adk_metadata_key('user_id'): run_args['user_id'],
                                    _get_adk_metadata_key('session_id'): run_args['session_id'],
                                },
                            )
                        )
                        await event_queue.enqueue_event(
                            TaskArtifactUpdateEvent(
                                task_id=context.task_id,
                                last_chunk=True,
                                context_id=context.context_id,
                                artifact=Artifact(artifact_id=str(uuid.uuid4()), parts=_pf_parts),
                            )
                        )
                        await event_queue.enqueue_event(
                            TaskStatusUpdateEvent(
                                task_id=context.task_id,
                                status=TaskStatus(state=TaskState.completed, timestamp=datetime.now(timezone.utc).isoformat()),
                                context_id=context.context_id,
                                final=True,
                            )
                        )
                        if idem_key:
                            _store_idem_result(idem_key, _pf_parts)
                        logger.log_text("[preflight_gate] rendered analysis-plan card and short-circuited (" + str(len(_pf_parts)) + " parts)")
                        if os.environ.get("ENABLE_MANAGED_AGENT") == "1":
                            return
                    elif isinstance(_plan, dict) and _plan.get("category") == "AUTONOMOUS":
                        # Interactive briefing BEFORE delegation - only when the
                        # classifier found material gaps; otherwise fall through
                        # (zero friction) and the root agent delegates directly.
                        _ab_parts = _build_autonomous_briefing_card_parts(_plan, _gate_scope)
                        if _ab_parts:
                            await event_queue.enqueue_event(
                                TaskStatusUpdateEvent(
                                    task_id=context.task_id,
                                    status=TaskStatus(state=TaskState.working, timestamp=datetime.now(timezone.utc).isoformat()),
                                    context_id=context.context_id,
                                    final=False,
                                    metadata={
                                        _get_adk_metadata_key('app_name'): runner.app_name,
                                        _get_adk_metadata_key('user_id'): run_args['user_id'],
                                        _get_adk_metadata_key('session_id'): run_args['session_id'],
                                    },
                                )
                            )
                            await event_queue.enqueue_event(
                                TaskArtifactUpdateEvent(
                                    task_id=context.task_id,
                                    last_chunk=True,
                                    context_id=context.context_id,
                                    artifact=Artifact(artifact_id=str(uuid.uuid4()), parts=_ab_parts),
                                )
                            )
                            await event_queue.enqueue_event(
                                TaskStatusUpdateEvent(
                                    task_id=context.task_id,
                                    status=TaskStatus(state=TaskState.completed, timestamp=datetime.now(timezone.utc).isoformat()),
                                    context_id=context.context_id,
                                    final=True,
                                )
                            )
                            if idem_key:
                                _store_idem_result(idem_key, _ab_parts)
                            logger.log_text("[autonomous_briefing] rendered briefing card and short-circuited (" + str(len(_ab_parts)) + " parts)")
                        return
        except Exception as _pf_err:
            logger.log_text("[preflight_gate] gate error (fail-open, running agent): " + str(_pf_err)[:200])

        # --- Inline render deadline (v10.79): arm the wall-clock budgets ---
        # The soft tool budget propagates to the agent's before_tool gate via
        # the contextvar (set here, inherited by the run's task context); the
        # hard deadline drives the conversion watchdog created further below.
        _turn_start_mono = time.monotonic()
        try:
            INLINE_TOOL_DEADLINE.set(_turn_start_mono + _INLINE_SOFT_TOOL_BUDGET_S)
            INLINE_IMAGE_DEADLINE.set(_turn_start_mono + _INLINE_IMAGE_BUDGET_S)
        except Exception as _itd_err:
            logger.log_text('[inline_deadline] failed to arm tool budget (non-fatal): ' + str(_itd_err)[:160])
        _overrun_prompt = _overrun_bg_prompt(run_args)

        invocation_context = runner._new_invocation_context(
            session=session,
            new_message=run_args['new_message'],
            run_config=run_args['run_config'],
        )

        await event_queue.enqueue_event(
            TaskStatusUpdateEvent(
                task_id=context.task_id,
                status=TaskStatus(
                    state=TaskState.working,
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
                context_id=context.context_id,
                final=False,
                metadata={
                    _get_adk_metadata_key('app_name'): runner.app_name,
                    _get_adk_metadata_key('user_id'): run_args['user_id'],
                    _get_adk_metadata_key('session_id'): run_args['session_id'],
                },
            )
        )

        task_result_aggregator = part_converters.TaskResultAggregator()

        # =============================================================================
        # A2UI SDK Stream Parser — replaces manual <a2ui-json> tag buffering
        # Provides: incremental JSON healing, component-level yielding,
        #           payload_fixer (trailing comma/smart quotes), schema validation
        # =============================================================================
        stream_parser = A2uiStreamParser(catalog=a2ui_selected_catalog)

        # =============================================================================
        # Artifact Parts Accumulator (Split: text vs media)
        # GE displays: working events → Thinking accordion, artifact → Final response.
        #
        # Strategy: Only the FINAL response text should appear outside thinking.
        # Progress text ("📊 Checking schema...") should stay in thinking only.
        #
        # - artifact_text_parts: Cleared on each function_call → only text from
        #   the LAST model turn (after all tools finish) survives to the artifact.
        # - artifact_media_parts: Images, A2UI cards → never cleared, always in artifact.
        # =============================================================================
        artifact_text_parts = []
        artifact_media_parts = []
        # v11.5: True once ANY real tool result arrived this turn. The stub guard
        # uses this to pick its recovery mode: a stub emitted BEFORE any tool ran
        # (model announced a tool and stalled - confirmed live 2026-07-15, Output=12
        # tokens right after transfer) has NO data to synthesize from, so recovery
        # must RE-EXECUTE with tools allowed instead of forcing a toolless synthesis.
        _turn_had_tool_results = False
        # Running capture of SHORT conversational text the model emitted this turn
        # (incl. text later cleared by a trailing tool call). Used only by the
        # UI-only render guard below to promote a real prior utterance into an
        # otherwise text=0 artifact, which GE refuses to render. Never fabricated.
        _all_model_texts = []
        # True once the adk_request_credential auth flow has produced its user
        # message this turn. The auth texts are short (~74 chars) and final by
        # design - the stub guard and chip re-prompt below must never touch them.
        _auth_flow = False
        # True once a deterministic configuration error (e.g. tool-schema
        # rejection) has produced its final user message. Like _auth_flow, the
        # stub guard / chip re-prompt must not fire extra LLM calls for it --
        # those calls re-send the same broken tool declarations and fail too.
        _fatal_config_error = False


        # =============================================================================
        # Model Name Display — show which model is processing (once per agent)
        # Maps agent name → model string for the thinking accordion header.
        # =============================================================================
        _agent_model_map = {
            'root_agent': os.environ.get("AGENT_MODEL_LITE", "gemini-3.6-flash"),
            'deep_analysis_agent': os.environ.get("AGENT_MODEL", "gemini-3.6-flash"),
        }
        _model_announced = set()  # Track which agents have been announced

        # =============================================================================
        # Graceful Timeout — 800s safety net before Cloud Run's 900s hard limit.
        # Uses a flag checked in the loop to avoid re-indenting 300+ lines.
        # =============================================================================
        _timed_out = False
        async def _timeout_watchdog():
            nonlocal _timed_out
            await asyncio.sleep(800)
            _timed_out = True
        _watchdog_task = asyncio.create_task(_timeout_watchdog())

        # =============================================================================
        # Inline overrun conversion watchdog (v10.80)
        # GE stops rendering the streamed turn at ~120s. At _INLINE_HARD_DEADLINE_S
        # (default 115s, ~5s headroom under the external cutoff) this watchdog
        # ends the turn WHILE IT STILL RENDERS by
        # moving the work to a REAL background task (the /execute_task worker,
        # which runs to completion regardless of the chat) and answering with a
        # "Check Task Status" chip. This applies to BOTH "Run Inline:" chip
        # presses and plain typed analytical requests; the original request is
        # recovered by _overrun_prompt and enriched with recent conversation
        # context so a terse follow-up still resolves its references.
        #
        # Control actions (Continue / Check progress) yield _overrun_prompt == ''
        # and are NEVER converted - the watchdog leaves them to finish naturally.
        # The conversion is cached for true duplicate-press multi-fire (G1) only;
        # it is deliberately NOT stored under the H1 session-artifact key, because
        # an H1 replay of the conversion message on a re-send would loop the user
        # on a dead-end "this moved to background" with no real result. The
        # abandoned in-flight run is closed by the main body at its next event
        # (see the _inline_converted checks below). The watchdog stays armed
        # through the salvage phases so those are wall-clock-bounded too; it is
        # disarmed right before the normal final-artifact emission.
        # =============================================================================
        _inline_converted = False
        _turn_finalizing = False
        async def _inline_overrun_watchdog():
            nonlocal _inline_converted
            # v10.87: auto-conversion to background is OFF by default. GE renders
            # long turns fine, so we let the analysis finish inline instead of
            # converting it (which wasted the user's wait). Re-enable with
            # INLINE_OVERRUN_CONVERT=1. When off, the watchdog is a no-op and the
            # turn completes via the normal final-artifact path.
            if not _INLINE_OVERRUN_CONVERT:
                return
            await asyncio.sleep(_INLINE_HARD_DEADLINE_S)
            if _turn_finalizing or _inline_converted or _timed_out:
                return
            if not _overrun_prompt:
                # Control action (Continue / Check progress) or unclassifiable
                # message: never spawn a background task - let it finish naturally.
                logger.log_text('[inline_deadline] overrun on a non-convertible turn - leaving it to finish naturally')
                return
            _inline_converted = True
            try:
                _conv_elapsed = int(time.monotonic() - _turn_start_mono)
                _ctx_lines = _recent_user_texts(session, _overrun_prompt)
                # NOTE: build newlines with chr(10), never a backslash-n escape.
                # This Python source lives inside a Code.gs JS template literal
                # whose layer turns a backslash-n into a real newline, which
                # would split the string literal and break the container.
                _nl = chr(10)
                _bg_prompt = (
                    "Run the FULL-DEPTH version of the user's request below and deliver a "
                    "complete report. This is a background run with no chat time limit, so "
                    "do the thorough analysis (statistics, charts, recommendations)." + _nl + _nl
                    + "REQUEST:" + _nl + _overrun_prompt
                )
                if _ctx_lines:
                    _bg_prompt += (_nl + _nl + "RECENT CONVERSATION CONTEXT (resolve any "
                                   "references in the request against this):" + _nl + "- "
                                   + (_nl + "- ").join(_ctx_lines))
                _bg_name = 'inline_overrun_' + ''.join(_c for _c in _overrun_prompt.lower() if _c.isalnum())[:24]
                try:
                    _reg = await asyncio.to_thread(
                        _agent_tools.submit_background_task_now,
                        _bg_name,
                        'Auto-converted from an inline run that exceeded the chat rendering time budget.',
                        _bg_prompt,
                    )
                except Exception as _reg_err:
                    _reg = {'status': 'error', 'message': str(_reg_err)[:200]}
                if _reg.get('status') in ('submitted', 'already_active'):
                    _conv_ticket = str(_reg.get('ticket-id', ''))
                    _conv_text = (
                        "⏱️ This analysis needs more time than an inline chat turn can "
                        "display, so I moved it to a background task (ticket: " + _conv_ticket
                        + "). It keeps running to completion - press the button below to "
                        "check progress and retrieve the full report."
                    )
                    _conv_chip_specs = [("Check progress of task " + _conv_ticket, "📊 Check Task Status")]
                else:
                    _conv_text = (
                        "⚠️ This request is taking longer than the chat can display and could "
                        "not be moved to a background task. Please narrow the scope (fewer "
                        "entities, a shorter period, or a single metric) and try again."
                    )
                    _conv_chip_specs = [("Narrow the analysis to a single entity or metric and run it again", "🎯 Narrow scope")]
                _conv_parts = [a2a_types.Part(root=a2a_types.TextPart(text=_conv_text))]
                _chip_components = [
                    {'id': 'root', 'component': {'Row': {'children': {'explicitList': ['ic_chip' + str(_ci) for _ci in range(len(_conv_chip_specs))]}, 'distribution': 'spaceEvenly', 'alignment': 'center'}}},
                ]
                for _ci in range(len(_conv_chip_specs)):
                    _chip_text, _chip_label = _conv_chip_specs[_ci]
                    _chip_components.append({'id': 'ic_chip' + str(_ci), 'component': {'Button': {'child': 'ic_chip' + str(_ci) + 'Lbl', 'action': {'name': 'sendText', 'context': [{'key': 'text', 'value': {'literalString': _chip_text}}]}}}})
                    _chip_components.append({'id': 'ic_chip' + str(_ci) + 'Lbl', 'component': {'Text': {'text': {'literalString': _chip_label}, 'usageHint': 'body'}}})
                for _conv_msg in (
                    {'beginRendering': {'surfaceId': 'suggestions', 'root': 'root'}},
                    {'surfaceUpdate': {'surfaceId': 'suggestions', 'components': _chip_components}},
                ):
                    _conv_parts.append(create_a2ui_part(_conv_msg))
                # Stream text + chips as a WORKING event first (chips that exist
                # only in the final artifact may not render - B-1 pattern), then
                # finalize the turn with the artifact + completed event.
                await event_queue.enqueue_event(TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(
                        state=TaskState.working,
                        message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=_conv_parts),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    final=False,
                ))
                await event_queue.enqueue_event(TaskArtifactUpdateEvent(
                    task_id=context.task_id,
                    last_chunk=True,
                    context_id=context.context_id,
                    artifact=Artifact(artifact_id=str(uuid.uuid4()), parts=_conv_parts),
                ))
                await event_queue.enqueue_event(TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    status=TaskStatus(
                        state=TaskState.completed,
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    context_id=context.context_id,
                    final=True,
                ))
                # G1 duplicate-press replay only. NOT _store_session_artifact:
                # an H1 replay of this message would dead-end a re-send (see note).
                if idem_key:
                    _store_idem_result(idem_key, _conv_parts)
                logger.log_text('[inline_deadline] converted inline turn at ' + str(_conv_elapsed) + 's -> ' + (('background task ' + str(_reg.get('ticket-id', ''))) if _reg.get('status') in ('submitted', 'already_active') else 'narrow-scope fallback'))
            except Exception as _ic_err:
                logger.log_text('[inline_deadline] conversion failed: ' + str(_ic_err)[:300])
        _inline_watchdog_task = asyncio.create_task(_inline_overrun_watchdog())

        # =============================================================================
        # MALFORMED_FUNCTION_CALL Auto-Retry
        # The lite model sometimes fails to generate valid tool calls after errors.
        # Instead of immediately showing an error to the user, retry up to twice
        # with a healed session (multimodal/image turns make MALFORMED more likely,
        # so 1 retry was too thin). run_async can be safely re-invoked on the same
        # session. Each retry is a FULL re-run, so the 800s watchdog bounds latency.
        # =============================================================================
        _max_malformed_retries = 3  # v10.61: was 2 — a touch more stochastic-retry headroom before salvage
        _malformed_retries = 0
        _malformed_should_retry = False

        # =============================================================================
        # LlmCallsLimit Auto-Continue (v10.57)
        # Long, multi-step reports can exhaust RunConfig.max_llm_calls mid-invocation.
        # ADK raises LlmCallsLimitExceededError from inside runner.run_async; if it
        # escapes execute() the task fails with NO artifact (the report is lost),
        # even though the session already holds every gathered tool result. Manually
        # typing "continue" recovers it because a NEW invocation resets the call
        # counter. This wrapper does the same automatically, IN THE SAME TURN: on a
        # limit error it heals the session, resets the stream parser, and re-invokes
        # run_async with a short continuation message, up to _MAX_AUTO_CONTINUES
        # times. The 800s watchdog remains the overall wall-clock safety net.
        # Caught by class name (not import) to stay robust across ADK versions.
        # =============================================================================
        _MAX_AUTO_CONTINUES = 4
        # v10.61: English prompt with an explicit same-language clause so the recovered
        # report follows the conversation's language instead of being forced to Japanese.
        _CONTINUE_MESSAGE = (
            "Using everything you have already gathered and analyzed, finish the "
            "interrupted report to completion. Keep any additional tool calls to the "
            "strict minimum. Write the report in the SAME language you have been using "
            "with the user in this conversation; do not switch languages."
        )

        async def _run_with_auto_continue(initial_args=None):
            nonlocal stream_parser
            _auto_continues = 0
            _cont_args = initial_args if initial_args is not None else run_args
            while True:
                try:
                    async for _ac_event in runner.run_async(**_cont_args):
                        yield _ac_event
                    return  # run_async finished without hitting the call limit
                except Exception as _ac_err:
                    if type(_ac_err).__name__ != 'LlmCallsLimitExceededError':
                        raise  # not our concern — let normal handling take over
                    if _auto_continues >= _MAX_AUTO_CONTINUES or _timed_out:
                        # Budget exhausted / timed out: stop gracefully so the
                        # drain + artifact logic can emit whatever was accumulated
                        # instead of failing the whole task.
                        logger.log_text("LlmCallsLimitExceededError - auto-continue budget exhausted; emitting partial result")
                        return
                    _auto_continues += 1
                    logger.log_text(
                        "LlmCallsLimitExceededError - auto-continuing in-turn ("
                        + str(_auto_continues) + "/" + str(_MAX_AUTO_CONTINUES) + ")"
                    )
                    # Re-fetch + heal the session so the next invocation resumes cleanly.
                    _ac_session = await runner.session_service.get_session(
                        app_name=runner.app_name,
                        user_id=run_args['user_id'],
                        session_id=run_args['session_id'],
                    )
                    if _ac_session is not None:
                        _heal_session_events(_ac_session)
                    # Fresh parser: the interrupted partial stream is discarded; the
                    # final report is produced by the continuation invocation.
                    stream_parser = A2uiStreamParser(catalog=a2ui_selected_catalog)
                    # Keep the user informed (stays inside the Thinking accordion).
                    _ac_msg = "⏳ This is taking a while. Consolidating the results so far and continuing to generate the report… (" + str(_auto_continues) + "/" + str(_MAX_AUTO_CONTINUES) + ")"
                    _ac_evt = TaskStatusUpdateEvent(
                        task_id=context.task_id,
                        context_id=context.context_id,
                        status=TaskStatus(
                            state=TaskState.working,
                            message=Message(
                                message_id=str(uuid.uuid4()),
                                role=Role.agent,
                                parts=[a2a_types.Part(root=a2a_types.TextPart(text=_ac_msg))],
                            ),
                            timestamp=datetime.now(timezone.utc).isoformat(),
                        ),
                        final=False,
                    )
                    task_result_aggregator.process_event(_ac_evt)
                    await event_queue.enqueue_event(_ac_evt)
                    # Re-invoke with a short continuation prompt (fresh call budget).
                    _cont_args = dict(run_args)
                    _cont_args['new_message'] = genai_types.Content(
                        role='user',
                        parts=[genai_types.Part(text=_CONTINUE_MESSAGE)],
                    )
                    continue

        # =============================================================================
        # MALFORMED retry re-entry (v10.58)
        # Wraps _run_with_auto_continue so a MALFORMED_FUNCTION_CALL retry feeds its
        # events back through the SAME main-loop body (with A2uiStreamParser + all
        # SAFETY NETs) instead of a separate simplified pass that dumped raw text
        # (and any A2UI JSON) straight into the artifact. The body sets
        # _malformed_should_retry + continue; we end the current run here, heal the
        # session, reset the parser, and start a fresh run on the same iteration.
        # =============================================================================
        async def _all_events():
            nonlocal stream_parser, _malformed_should_retry
            while True:
                async for _ev in _run_with_auto_continue():
                    yield _ev
                    if _malformed_should_retry:
                        break  # stop consuming the current (failed) run
                if _malformed_should_retry:
                    _malformed_should_retry = False
                    _rs = await runner.session_service.get_session(
                        app_name=runner.app_name,
                        user_id=run_args['user_id'],
                        session_id=run_args['session_id'],
                    )
                    if _rs is not None:
                        _heal_session_events(_rs)
                    stream_parser = A2uiStreamParser(catalog=a2ui_selected_catalog)
                    continue  # re-run on the healed session
                return
        if os.environ.get("ENABLE_MANAGED_AGENT") == "1":

            # --- Managed Agent live progress -> Thinking accordion (v11.0) ---
            # A per-turn poller drains the progress queue that the delegation
            # tool's SSE thread fills (tools.py publishes it on builtins) and
            # re-emits each snippet as a working-state status event - the same
            # shape as the tool-call statuses below, so it renders inside the
            # Thinking accordion in real time while delegate_autonomous_task is
            # still blocking. A generation token retires stale pollers from
            # earlier turns within one poll interval; the poller also exits when
            # the event queue is closed or after a 900s safety cap.
            import builtins as _ma_b
            import asyncio as _ma_aio
            import queue as _ma_q
            _ma_b._ma_poller_gen = getattr(_ma_b, '_ma_poller_gen', 0) + 1
            _ma_my_gen = _ma_b._ma_poller_gen

            async def _ma_progress_poller():
                _pq = getattr(_ma_b, '_ma_progress_queue', None)
                if _pq is None:
                    return
                import time as _ma_t
                _t0 = _ma_t.monotonic()
                while _ma_t.monotonic() - _t0 < 900:
                    if getattr(_ma_b, '_ma_poller_gen', 0) != _ma_my_gen:
                        return
                    _drained = []
                    try:
                        while True:
                            _drained.append(_pq.get_nowait())
                    except _ma_q.Empty:
                        pass
                    except Exception:
                        return
                    # Burst guard: never enqueue more than 3 status events per
                    # tick - back-to-back TaskStatusUpdateEvents have crashed the
                    # GE client's rendering of otherwise-successful turns.
                    if len(_drained) > 3:
                        _drained = [_drained[0], '... (' + str(len(_drained) - 2) + ' more sandbox steps) ...', _drained[-1]]
                    for _pmsg in _drained:
                        try:
                            _pevt = TaskStatusUpdateEvent(
                                task_id=context.task_id,
                                context_id=context.context_id,
                                status=TaskStatus(
                                    state=TaskState.working,
                                    message=Message(
                                        message_id=str(uuid.uuid4()),
                                        role=Role.agent,
                                        parts=[a2a_types.Part(root=a2a_types.TextPart(text='🛰️ Autonomous agent: ' + _pmsg))],
                                    ),
                                    timestamp=datetime.now(timezone.utc).isoformat(),
                                ),
                                final=False,
                            )
                            task_result_aggregator.process_event(_pevt)
                            await event_queue.enqueue_event(_pevt)
                        except Exception:
                            return
                    await _ma_aio.sleep(2)

            try:
                _ma_aio.create_task(_ma_progress_poller())
            except Exception:
                pass

        _events_gen = _all_events()
        async for adk_event in _events_gen:
          if _inline_converted:
              # The deadline watchdog already finalized this turn (conversion
              # text + chips + completed event). Stop consuming and emit nothing
              # further - GE has finished rendering this turn.
              logger.log_text("[inline_deadline] abandoning in-flight inline run after background conversion")
              break
          if _timed_out:
              logger.log_text("⏱️ Agent processing timed out after 800s — sending graceful error to user.")
              timeout_part = a2a_types.Part(root=a2a_types.TextPart(
                  text="⏱️ The analysis timed out due to its complexity. Please try again — the request may succeed on a retry as resources become available."
              ))
              artifact_text_parts.clear()
              artifact_text_parts.append(timeout_part)
              break
          # --- Model name announcement (once per agent) ---
          _evt_agent = getattr(adk_event, 'author', None)
          if _evt_agent and _evt_agent not in _model_announced and _evt_agent in _agent_model_map:
              _model_announced.add(_evt_agent)
              _model_label = _agent_model_map[_evt_agent]
              _model_msg = f"🧠 Model: {_model_label}"
              _model_event = TaskStatusUpdateEvent(
                  task_id=context.task_id,
                  context_id=context.context_id,
                  status=TaskStatus(
                      state=TaskState.working,
                      message=Message(
                          message_id=str(uuid.uuid4()),
                          role=Role.agent,
                          parts=[a2a_types.Part(root=a2a_types.TextPart(text=_model_msg))],
                      ),
                      timestamp=datetime.now(timezone.utc).isoformat(),
                  ),
                  final=False,
              )
              task_result_aggregator.process_event(_model_event)
              await event_queue.enqueue_event(_model_event)

          if hasattr(adk_event, 'error_code') and adk_event.error_code:
              _err_code_str = str(adk_event.error_code)
              # --- Deterministic tool-schema rejection: fail fast (v10.71) ---
              # Vertex rejects the request when a tool declaration cannot be
              # compiled server-side ("Limits exceeded while trying to flatten
              # schema" - e.g. a recursive custom-MCP schema that reached the
              # API raw). EVERY retry and EVERY synth-salvage pass re-sends
              # the same tool declarations, so no amount of retrying can
              # succeed. Surface an explicit, actionable error immediately
              # instead of burning the salvage loop (confirmed 2026-06-10:
              # 4 identical ~4-min retry cycles ended in a GE ServerError).
              # Checked BEFORE the ClientError/X-C branch because the
              # tools.py fast-fail patch demotes this 500 to a ClientError.
              # NOTE: ADK 2.x error events carry only the exception CLASS
              # name in error_code (e.g. "ServerError"); the detail lives in
              # error_message - so match against both.
              _err_full_str = _err_code_str + " " + str(getattr(adk_event, 'error_message', '') or '')
              if ('flatten schema' in _err_full_str
                      or 'Schema is too complex' in _err_full_str):
                  logger.log_text("[schema_error] deterministic tool-schema rejection - failing fast: " + _err_full_str[:200])
                  _schema_err_part = a2a_types.Part(root=a2a_types.TextPart(
                      text="⚠️ The model rejected this agent's tool definitions (a tool schema is too complex - typically a deeply recursive custom MCP tool schema). Retrying cannot fix this. Please redeploy the agent with ADK_DISABLE_JSON_SCHEMA_FOR_FUNC_DECL=1, or remove/simplify the offending MCP tool."
                  ))
                  artifact_text_parts.clear()
                  artifact_text_parts.append(_schema_err_part)
                  _fatal_config_error = True
                  break
              # --- MALFORMED_FUNCTION_CALL / MODEL_RETURNED_NO_CONTENT recovery ---
              # The model sometimes generates invalid tool calls (bad schema,
              # mixed text + function_call). Instead of failing hard, provide
              # a user-friendly retry message so the conversation can continue.
              # v11.15: MODEL_RETURNED_NO_CONTENT (an empty candidate, observed
              # right after large inline code-execution results) is transient in
              # the same way MALFORMED is: the session already holds every tool
              # result, and a healed re-run recovers it. Route both through the
              # SAME retry budget and, when exhausted, the same tool-forbidden
              # synthesis salvage below (previously it fell through the ladder
              # and surfaced as a bare "Error: MODEL_RETURNED_NO_CONTENT").
              if ('MALFORMED_FUNCTION_CALL' in _err_code_str
                      or 'MODEL_RETURNED_NO_CONTENT' in _err_full_str
                      or 'returned no content' in _err_full_str.lower()):
                  # --- Auto-retry: flag for re-run; _all_events() heals + restarts ---
                  # Session healing, parser reset, and the fresh run are handled by
                  # the _all_events() wrapper so the retry's events flow back through
                  # THIS same body (A2uiStreamParser + all SAFETY NETs). Doing a raw
                  # break into a separate simplified loop previously dumped the
                  # post-retry report (incl. A2UI JSON) as raw text.
                  if _malformed_retries < _max_malformed_retries:
                      _malformed_retries += 1
                      logger.log_text("Transient model error (" + _err_code_str[:60] + ") - auto-retrying (" + str(_malformed_retries) + "/" + str(_max_malformed_retries) + ")")
                      _malformed_should_retry = True
                      continue  # _all_events() heals the session and re-runs

                  # --- Max retries exhausted: route to synthesis salvage (v10.61) ---
                  # Do NOT surrender to the user yet. All gathered data is still in the
                  # session; breaking here with artifact_text_parts left EMPTY lets the
                  # tool-forbidden synthesis-recovery loop below run. Because that pass
                  # forbids tool calls it cannot MALFORMED on a tool call, so it salvages
                  # the report in the same turn the vast majority of the time. The B-1
                  # guaranteed fallback (further below) remains the true last resort, so
                  # the user is no longer forced to click "Try Again" repeatedly.
                  logger.log_text("Transient model error (" + _err_code_str[:60] + ") - retries exhausted - routing to tool-forbidden synthesis salvage")
                  break
              # --- X-C (v10.62): input-token overflow / client-error salvage ---
              # A 1M-token context overflow surfaces as a ClientError /
              # INVALID_ARGUMENT ("exceeds the maximum number of tokens"). Do NOT
              # show a bare "Error: ClientError"; aggressively compact the session
              # and fall through to the tool-forbidden synthesis salvage so the
              # user still gets a report (or the B-1 fallback). The synth loop
              # re-heals with the budget compactor, so the retry payload fits.
              if ('exceeds the maximum number of tokens' in _err_code_str
                      or 'INVALID_ARGUMENT' in _err_code_str
                      or 'ClientError' in _err_code_str):
                  logger.log_text("[token_overflow] main run client error - emergency compaction + synthesis salvage: " + _err_code_str[:160])
                  try:
                      _oc_sess = await runner.session_service.get_session(
                          app_name=runner.app_name,
                          user_id=run_args['user_id'],
                          session_id=run_args['session_id'],
                      )
                      if _oc_sess is not None:
                          _heal_session_events(_oc_sess, force_aggressive=True)
                  except Exception as _oc_err:
                      logger.log_text("[token_overflow] emergency compaction failed (non-fatal): " + str(_oc_err)[:160])
                  artifact_text_parts.clear()
                  break
              a2a_event = TaskStatusUpdateEvent(
                      task_id=context.task_id,
                      context_id=context.context_id,
                      status=TaskStatus(
                          state=TaskState.failed,
                          message=Message(
                              role=Role.agent,
                              parts=[a2a_types.Part(root=a2a_types.TextPart(text=f"Error: {adk_event.error_code}"))],
                              message_id=str(uuid.uuid4())
                          ),
                          timestamp=datetime.now(timezone.utc).isoformat(),
                      ),
                      final=True
                  )
              task_result_aggregator.process_event(a2a_event)
              await event_queue.enqueue_event(a2a_event)
              break

          content = getattr(adk_event, 'content', None)
          if content and hasattr(content, 'parts'):
              # Pre-scan: buffer model text when function_call follows (combine into single status)
              _event_has_fc = any(getattr(p, 'function_call', None) for p in content.parts)
              _event_progress_text = ''
              for part in content.parts:
                  if part.text:
                      # --- Detect code execution blocks (AgentEngineSandboxCodeExecutor) ---
                      # This executor uses text-based delimiters instead of executable_code parts.
                      # Detect tool_code / python and tool_output fenced code blocks and emit
                      # status events so they appear in the thinking accordion.
                      import re as _ce_re
                      _ce_fence = chr(96) * 3
                      _ce_code_pattern = _ce_re.compile(_ce_fence + r'(?:tool_code|python)' + chr(92) + 's*' + chr(92) + 'n(.*?)' + _ce_fence, _ce_re.DOTALL)
                      _ce_output_pattern = _ce_re.compile(_ce_fence + r'tool_output' + chr(92) + 's*' + chr(92) + 'n(.*?)' + _ce_fence, _ce_re.DOTALL)
                      _ce_code_matches = _ce_code_pattern.findall(part.text)
                      _ce_output_matches = _ce_output_pattern.findall(part.text)
                      for _ce_code_block in _ce_code_matches:
                          _ce_code_text = chr(10).join(["🐍 Code Execution (Python)", _ce_code_block.strip()])
                          _ce_code_evt = TaskStatusUpdateEvent(
                              task_id=context.task_id,
                              context_id=context.context_id,
                              status=TaskStatus(
                                  state=TaskState.working,
                                  message=Message(
                                      message_id=str(uuid.uuid4()),
                                      role=Role.agent,
                                      parts=[a2a_types.Part(root=a2a_types.TextPart(text=_ce_code_text))],
                                  ),
                                  timestamp=datetime.now(timezone.utc).isoformat(),
                              ),
                              final=False,
                          )
                          task_result_aggregator.process_event(_ce_code_evt)
                          await event_queue.enqueue_event(_ce_code_evt)
                      for _ce_out_block in _ce_output_matches:
                          _ce_out_text = chr(10).join(["✅ Code Execution Result", _ce_out_block.strip()])
                          _ce_out_evt = TaskStatusUpdateEvent(
                              task_id=context.task_id,
                              context_id=context.context_id,
                              status=TaskStatus(
                                  state=TaskState.working,
                                  message=Message(
                                      message_id=str(uuid.uuid4()),
                                      role=Role.agent,
                                      parts=[a2a_types.Part(root=a2a_types.TextPart(text=_ce_out_text))],
                                  ),
                                  timestamp=datetime.now(timezone.utc).isoformat(),
                              ),
                              final=False,
                          )
                          task_result_aggregator.process_event(_ce_out_evt)
                          await event_queue.enqueue_event(_ce_out_evt)
                      # Capture model's progress text for function_call context
                      if _event_has_fc:
                          _event_progress_text = part.text.strip()
                      # SDK handles: tag detection, JSON buffering, healing,
                      # validation, and component-level incremental yielding
                      _fallback_recovered_a2ui = False
                      try:
                          _chunk_text = _sanitize_a2ui_text_icons(part.text) if '<a2ui-json>' in part.text else part.text
                          response_parts = stream_parser.process_chunk(_chunk_text)
                          # Diagnostic: trace what the parser returned
                          _has_a2ui = any(rp.a2ui_json for rp in response_parts)
                          _has_text = any(rp.text for rp in response_parts)
                          if '<a2ui-json>' in part.text or _has_a2ui:
                              logger.log_text(f"[a2ui_diag] process_chunk returned {len(response_parts)} parts, has_a2ui={_has_a2ui}, has_text={_has_text}, input_len={len(part.text)}")
                      except (ValueError, Exception) as parse_err:
                          logger.log_text(f"A2UI stream parse error ({type(parse_err).__name__}): {parse_err}")
                          logger.log_text(f"A2UI parse error text (first 200 chars): {part.text[:200]}")
                          response_parts = []
                          _fallback_recovered_a2ui = False

                          # -------------------------------------------------------
                          # CRITICAL FALLBACK: Extract A2UI JSON via regex when
                          # the stream parser fails (e.g. malformed JSON).
                          # Without this, both text AND A2UI are lost from the
                          # final artifact and trapped inside "thinking".
                          # -------------------------------------------------------
                          import re as _re
                          _a2ui_pattern = _re.compile(r'<a2ui-json>(.*?)</a2ui-json>', _re.DOTALL)
                          _raw = part.text
                          _matches = _a2ui_pattern.findall(_raw)
                          # Strip A2UI blocks from text to get plain text
                          _plain = _a2ui_pattern.sub('', _raw).strip()

                          if _plain:
                              fallback_text_part = a2a_types.Part(root=a2a_types.TextPart(text=_plain))
                              artifact_text_parts.append(fallback_text_part)

                          for _m in _matches:
                              try:
                                  import json as _json
                                  _parsed = _json.loads(_m)
                                  # A2UI JSON is always a list — iterate each dict element
                                  _items = _parsed if isinstance(_parsed, list) else [_parsed]
                                  _items = _heal_a2ui_message_list(_items)
                                  for _item in _items:
                                      if isinstance(_item, dict):
                                          artifact_media_parts.extend(create_a2ui_parts(_item))
                                          _fallback_recovered_a2ui = True
                                  _fb_keys = [list(i.keys())[0] if isinstance(i, dict) and i else '?' for i in _items]
                                  logger.log_text(f"A2UI fallback: recovered {len(_items)} A2UI component(s) via regex, keys={_fb_keys}")
                              except Exception as _je:
                                  logger.log_text(f"A2UI fallback: regex-extracted JSON invalid: {_je}")

                          # Also stream the fallback text to the user immediately
                          _fallback_parts = []
                          if _plain:
                              _fallback_parts.append(fallback_text_part)
                          for _m in _matches:
                              try:
                                  _parsed = _json.loads(_m)
                                  _f_items = _parsed if isinstance(_parsed, list) else [_parsed]
                                  _f_items = _heal_a2ui_message_list(_f_items)
                                  for _f_item in _f_items:
                                      if isinstance(_f_item, dict):
                                          _fallback_parts.extend(create_a2ui_parts(_f_item))
                              except Exception:
                                  pass
                          if not _fallback_parts and _raw:
                              _fallback_parts = [a2a_types.Part(root=a2a_types.TextPart(text=_raw))]
                              artifact_text_parts.append(_fallback_parts[0])
                          if _fallback_parts:
                              a2a_event = TaskStatusUpdateEvent(
                                      task_id=context.task_id,
                                      context_id=context.context_id,
                                      status=TaskStatus(
                                          state=TaskState.working,
                                          message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=_fallback_parts),
                                          timestamp=datetime.now(timezone.utc).isoformat(),
                                      ),
                                      final=False
                                  )
                              task_result_aggregator.process_event(a2a_event)
                              await event_queue.enqueue_event(a2a_event)
                          # Reset parser state to avoid cascading failures
                          try:
                              stream_parser._buffer = ''
                              stream_parser._found_delimiter = False
                          except Exception:
                              pass

                      for rp in response_parts:
                          synthetic_parts = []
                          if rp.text:
                              # Strip stray A2UI tag debris (e.g. a leaked "a2ui-json>"
                              # fragment the stream parser emits as text when the opening
                              # tag splits across chunks) before it reaches the chat (v10.100).
                              _clean_text = _A2UI_TAG_DEBRIS_RE.sub('', rp.text)
                              _trimmed = _clean_text.strip()
                              # Drop a text part that was ONLY tag debris / whitespace so it
                              # does not render as an empty bubble above the card.
                              if not _trimmed:
                                  pass
                              else:
                                  # Robust Failsafe: Block raw Python dict/list repr leaks from reaching the chat
                                  _is_repr = _trimmed.startswith('{') or _trimmed.startswith('[')
                                  if _is_repr and ("'content':" in _trimmed or "'parts':" in _trimmed):
                                      logger.log_text(f"[leak_failsafe] 🛡️ Blocked raw Python response dict leak: {_trimmed[:100]}...")
                                      continue
                                  text_part = a2a_types.Part(root=a2a_types.TextPart(text=_clean_text))
                                  synthetic_parts.append(text_part)
                                  artifact_text_parts.append(text_part)  # ★ Cleared on next function_call
                                  # Keep a copy for the UI-only render guard (short texts only).
                                  if len(_trimmed) <= 2000:
                                      _all_model_texts.append(_trimmed)
                          if rp.a2ui_json:
                              a2ui_messages = rp.a2ui_json if isinstance(rp.a2ui_json, list) else [rp.a2ui_json]
                              a2ui_messages = _heal_a2ui_message_list(a2ui_messages)
                              # Note: "💡 Next Actions" header is injected as text in the final
                              # artifact assembly, not via A2UI (GE suggestions surface ignores
                              # non-Button components).
                              for msg in a2ui_messages:
                                  for ui_part in create_a2ui_parts(msg):
                                      synthetic_parts.append(ui_part)
                                      artifact_media_parts.append(ui_part)  # ★ Never cleared
                          if synthetic_parts:
                              # Skip sending text-only events to Thinking when function_call
                              # follows in the same event — text will be combined into the
                              # function_call status instead for a cohesive display.
                              _skip_text_event = _event_has_fc and not any(rp.a2ui_json for rp in response_parts)
                              if not _skip_text_event:
                                  a2a_event = TaskStatusUpdateEvent(
                                          task_id=context.task_id,
                                          context_id=context.context_id,
                                          status=TaskStatus(
                                              state=TaskState.working,
                                              message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=synthetic_parts),
                                              timestamp=datetime.now(timezone.utc).isoformat(),
                                          ),
                                          final=False
                                      )
                                  task_result_aggregator.process_event(a2a_event)
                                  await event_queue.enqueue_event(a2a_event)

                      # -------------------------------------------------------
                      # POST-SUCCESS SAFETY NET: The A2uiStreamParser may
                      # silently drop A2UI JSON (returns text-only parts even
                      # when input contains <a2ui-json> tags, with empty buffer
                      # afterwards). When this happens, extract A2UI ourselves.
                      # -------------------------------------------------------
                      _parser_found_a2ui = any(rp.a2ui_json for rp in response_parts)
                      if '<a2ui-json>' in part.text and not _parser_found_a2ui and not _fallback_recovered_a2ui:
                          import re as _re
                          import json as _json
                          _a2ui_re = _re.compile(r'<a2ui-json>(.*?)</a2ui-json>', _re.DOTALL)
                          _a2ui_matches = _a2ui_re.findall(part.text)
                          logger.log_text(f"[a2ui_safety_net] Parser missed A2UI! Found {len(_a2ui_matches)} A2UI block(s) via regex in {len(part.text)} chars")
                          
                          # Strip A2UI blocks from the already accumulated text parts to prevent double-rendering
                          if artifact_text_parts:
                              _last_text_part = artifact_text_parts[-1]
                              _lt_root = getattr(_last_text_part, 'root', None)
                              _lt_text = getattr(_lt_root, 'text', '') if _lt_root else ''
                              if _lt_text:
                                  _cleaned_text = _a2ui_re.sub('', _lt_text).strip()
                                  if _cleaned_text:
                                      artifact_text_parts[-1] = a2a_types.Part(root=a2a_types.TextPart(text=_cleaned_text))
                                  else:
                                      artifact_text_parts.pop()

                          _safety_parts = []
                          for _match_str in _a2ui_matches:
                              try:
                                  _parsed_json = _json.loads(_match_str)
                                  # A2UI JSON is always a list — iterate each dict element
                                  _sn_items = _parsed_json if isinstance(_parsed_json, list) else [_parsed_json]
                                  _sn_items = _heal_a2ui_message_list(_sn_items)
                                  for _sn_item in _sn_items:
                                      if isinstance(_sn_item, dict):
                                          for _ui_part in create_a2ui_parts(_sn_item):
                                              _safety_parts.append(_ui_part)
                                              artifact_media_parts.append(_ui_part)
                                  _sn_keys = [list(i.keys())[0] if isinstance(i, dict) and i else '?' for i in _sn_items]
                                  logger.log_text(f"[a2ui_safety_net] Recovered {len(_sn_items)} A2UI component(s) via regex, keys={_sn_keys}")
                              except Exception as _e:
                                  logger.log_text(f"[a2ui_safety_net] Failed to parse regex-extracted JSON: {_e}")
                          if _safety_parts:
                              a2a_event = TaskStatusUpdateEvent(
                                      task_id=context.task_id,
                                      context_id=context.context_id,
                                      status=TaskStatus(
                                          state=TaskState.working,
                                          message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=_safety_parts),
                                          timestamp=datetime.now(timezone.utc).isoformat(),
                                      ),
                                      final=False
                                  )
                              task_result_aggregator.process_event(a2a_event)
                              await event_queue.enqueue_event(a2a_event)

                      # -------------------------------------------------------
                      # SAFETY NET 2 (Robust): Detect untagged A2UI JSON.
                      # Uses json.JSONDecoder().raw_decode() instead of regex
                      # to handle both JSON arrays and individual objects.
                      # This covers models that omit <a2ui-json> tags and/or
                      # JSON array brackets [].
                      # -------------------------------------------------------
                      if not _parser_found_a2ui and '<a2ui-json>' not in part.text:
                          import json as _json2
                          _a2ui_keys = ('"beginRendering"', '"surfaceUpdate"', '"surfaceId"', '"deleteSurface"')
                          if any(k in part.text for k in _a2ui_keys):
                              logger.log_text(f"[a2ui_robust_safety] Scanning untagged A2UI in {len(part.text)} chars")

                              _pos = 0
                              _extracted_spans = []
                              _untagged_parts = []

                              while _pos < len(part.text):
                                  # Find the next potential JSON start character
                                  _start_brace = part.text.find('{', _pos)
                                  _start_bracket = part.text.find('[', _pos)

                                  if _start_brace == -1 and _start_bracket == -1:
                                      break

                                  if _start_bracket == -1:
                                      _start_pos = _start_brace
                                  elif _start_brace == -1:
                                      _start_pos = _start_bracket
                                  else:
                                      _start_pos = min(_start_brace, _start_bracket)

                                  _open_char = part.text[_start_pos]
                                  _close_char = '}' if _open_char == '{' else ']'
                                  
                                  _end_pos = _find_balanced_block(part.text, _start_pos, _open_char, _close_char)
                                  if _end_pos == -1:
                                      _pos = _start_pos + 1
                                      continue
                                      
                                  _sub_str = part.text[_start_pos:_end_pos]
                                  _obj = _parse_loose_json(_sub_str)

                                  if _obj is not None:
                                      # Validate: is this an A2UI component structure?
                                      _is_a2ui = False
                                      if isinstance(_obj, dict):
                                          _is_a2ui = any(k in _obj for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate", "deleteSurface")) or ("id" in _obj and "component" in _obj)
                                      elif isinstance(_obj, list):
                                          _is_a2ui = any(
                                              isinstance(i, dict) and (
                                                  any(k in i for k in ("beginRendering", "surfaceUpdate", "dataModelUpdate", "deleteSurface"))
                                                  or ("id" in i and "component" in i)
                                              ) for i in _obj
                                          )

                                      if _is_a2ui:
                                          _items = _obj if isinstance(_obj, list) else [_obj]
                                          _items = _heal_a2ui_message_list(_items)
                                          for _item in _items:
                                              if isinstance(_item, dict):
                                                  for _ui_p in create_a2ui_parts(_item):
                                                      _untagged_parts.append(_ui_p)
                                                      artifact_media_parts.append(_ui_p)
                                          _extracted_spans.append((_start_pos, _end_pos))
                                          _ut_keys = [list(i.keys())[0] if isinstance(i, dict) and i else '?' for i in _items]
                                          logger.log_text(f"[a2ui_robust_safety] Recovered {len(_items)} component(s), keys={_ut_keys}")
                                          _pos = _end_pos
                                      else:
                                          _pos = _start_pos + 1
                                  else:
                                      _pos = _start_pos + 1

                              # Reconstruct clean text by removing extracted spans
                              if _extracted_spans:
                                  _clean_text = ""
                                  _last_idx = 0
                                  for _s, _e in _extracted_spans:
                                      _clean_text += part.text[_last_idx:_s]
                                      _last_idx = _e
                                  _clean_text += part.text[_last_idx:]
                                  # Clean up empty list items/commas left behind by extraction
                                  import re as _re_clean
                                  _clean_text = _re_clean.sub(r',\s*(?=\s*,)', '', _clean_text)
                                  _clean_text = _re_clean.sub(r'([\[{])\s*,', r'\1', _clean_text)
                                  _clean_text = _re_clean.sub(r',\s*([\]}])', r'\1', _clean_text)
                                  # Collapse multiple empty lines (using chr(10) to avoid backslash-n hazard)
                                  _clean_text = _re_clean.sub(chr(10) + r'\s*' + chr(10), chr(10), _clean_text)
                                  _extracted_text = _clean_text.strip()
                              else:
                                  _extracted_text = part.text

                              # Emit recovered A2UI parts as a working status update
                              if _untagged_parts:
                                  _ut_event = TaskStatusUpdateEvent(
                                      task_id=context.task_id,
                                      context_id=context.context_id,
                                      status=TaskStatus(
                                          state=TaskState.working,
                                          message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=_untagged_parts),
                                          timestamp=datetime.now(timezone.utc).isoformat(),
                                      ),
                                      final=False,
                                  )
                                  task_result_aggregator.process_event(_ut_event)
                                  await event_queue.enqueue_event(_ut_event)
                                  
                              # Emit remaining clean text (if any) and prevent duplication
                              if _extracted_spans:
                                  _clean_text_final = _extracted_text
                                  if _clean_text_final:
                                      # Pop the raw dirty text part that was appended upstream at L10082
                                      if artifact_text_parts:
                                          artifact_text_parts.pop()
                                          
                                      _ct_part = a2a_types.Part(root=a2a_types.TextPart(text=_clean_text_final))
                                      artifact_text_parts.append(_ct_part)
                  else:
                      # Non-text parts (images, function calls) — unchanged
                      synthetic_parts = part_converters.convert_genai_part_to_a2a_parts(part)
                      if synthetic_parts:
                          # ★ Accumulate images for artifact, clear text on tool calls
                          if part.inline_data:
                              artifact_media_parts.extend(synthetic_parts)
                          elif part.function_call:
                              # --- Tool call status (TextPart → Thinking accordion) ---
                              _fc_name = part.function_call.name
                              _fc_args = part.function_call.args or {}
                              if _fc_name.startswith('transfer_to_') or _fc_name == 'transfer_to_agent':
                                  _fc_target = _fc_args.get('agent_name', 'sub-agent')
                                  _fc_status_text = f"🔄 Delegating to {_fc_target}..."
                              elif _fc_name == 'adk_request_credential':
                                  _fc_status_text = None
                              else:
                                  # Extract context from args for detailed status
                                  _fc_detail = ''
                                  if _fc_name in ('execute_sql', 'query', 'run_query', 'execute_query'):
                                      _sql = _fc_args.get('query', _fc_args.get('sql', _fc_args.get('statement', '')))
                                      if _sql:
                                          _fc_detail = _sql.replace(chr(10), ' ')
                                  elif _fc_name == 'generate_image':
                                      _prompt = _fc_args.get('prompt', '')
                                      if _prompt:
                                          _fc_detail = _prompt
                                  else:
                                      # Generic: show all key args
                                      _arg_previews = []
                                      for _k, _v in _fc_args.items():
                                          _arg_previews.append(f"{_k}={str(_v)}")
                                      _fc_detail = ', '.join(_arg_previews)
                                  # Combine: tool name + model's progress text (summary) + technical detail
                                  _fc_lines = [f"🔧 {_fc_name}"]
                                  if _event_progress_text:
                                      _fc_lines.append(_event_progress_text)
                                  if _fc_detail:
                                      _fc_lines.append(_fc_detail)
                                  _fc_status_text = chr(10).join(_fc_lines)
                              if _fc_status_text:
                                  _fc_text_evt = TaskStatusUpdateEvent(
                                      task_id=context.task_id,
                                      context_id=context.context_id,
                                      status=TaskStatus(
                                          state=TaskState.working,
                                          message=Message(
                                              message_id=str(uuid.uuid4()),
                                              role=Role.agent,
                                              parts=[a2a_types.Part(root=a2a_types.TextPart(text=_fc_status_text))],
                                          ),
                                          timestamp=datetime.now(timezone.utc).isoformat(),
                                      ),
                                      final=False,
                                  )
                                  task_result_aggregator.process_event(_fc_text_evt)
                                  await event_queue.enqueue_event(_fc_text_evt)
                              # ★ Special handling: adk_request_credential → show auth URL to user
                              if part.function_call.name == 'adk_request_credential':
                                  fc_args = part.function_call.args or {}
                                  logger.log_text(f"[auth_flow] adk_request_credential detected, args keys: {list(fc_args.keys())}")
                                  # Deep extraction: authConfig.exchangedAuthCredential.oauth2.authUri
                                  auth_url = ''
                                  def _deep_get(obj, *keys, default=''):
                                      cur = obj
                                      for k in keys:
                                          if cur is None:
                                              return default
                                          if isinstance(cur, dict):
                                              cur = cur.get(k)
                                          elif hasattr(cur, k):
                                              cur = getattr(cur, k, None)
                                          else:
                                              return default
                                      return str(cur) if cur else default
                                  auth_url = _deep_get(fc_args, 'authConfig', 'exchangedAuthCredential', 'oauth2', 'authUri')
                                  if not auth_url:
                                      auth_url = _deep_get(fc_args, 'authConfig', 'exchangedAuthCredential', 'oauth2', 'auth_uri')
                                  # Recursive fallback: find any string starting with http in nested structure
                                  if not auth_url:
                                      def _find_url(obj, depth=0):
                                          if depth > 8:
                                              return ''
                                          if isinstance(obj, str) and obj.startswith('http'):
                                              return obj
                                          if isinstance(obj, dict):
                                              for v in obj.values():
                                                  r = _find_url(v, depth + 1)
                                                  if r:
                                                      return r
                                          elif hasattr(obj, '__dict__'):
                                              for v in vars(obj).values():
                                                  r = _find_url(v, depth + 1)
                                                  if r:
                                                      return r
                                          return ''
                                      auth_url = _find_url(fc_args)
                                  logger.log_text(f"[auth_flow] resolved auth_url present: {bool(auth_url)}, url_start: {auth_url[:80] if auth_url else 'N/A'}")
                                  if auth_url:
                                      # Extract service name from auth URL domain
                                      try:
                                          from urllib.parse import urlparse
                                          _domain = urlparse(auth_url).netloc.replace('www.', '').split('.')[0].capitalize()
                                      except Exception:
                                          _domain = "External Service"
                                      auth_text = f"🔐 Authentication required. Please click the link below to authorize access.\n\n[Authorize with {_domain}]({auth_url})\n\nAfter completing authorization, please send your message again."
                                      auth_part = a2a_types.Part(root=a2a_types.TextPart(text=auth_text))
                                      artifact_text_parts.clear()
                                      artifact_text_parts.append(auth_part)
                                      _auth_flow = True
                                      # Send as final response (don't clear)
                                      a2a_event = TaskStatusUpdateEvent(
                                              task_id=context.task_id,
                                              context_id=context.context_id,
                                              status=TaskStatus(
                                                  state=TaskState.working,
                                                  message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=[auth_part]),
                                                  timestamp=datetime.now(timezone.utc).isoformat(),
                                              ),
                                              final=False
                                          )
                                      task_result_aggregator.process_event(a2a_event)
                                      await event_queue.enqueue_event(a2a_event)
                                      continue
                                  else:
                                      # auth_url not found in args — show generic auth-in-progress message
                                      auth_text = "🔐 Authentication is being processed. Please wait a moment and try again."
                                      auth_part = a2a_types.Part(root=a2a_types.TextPart(text=auth_text))
                                      artifact_text_parts.clear()
                                      artifact_text_parts.append(auth_part)
                                      _auth_flow = True
                                      a2a_event = TaskStatusUpdateEvent(
                                              task_id=context.task_id,
                                              context_id=context.context_id,
                                              status=TaskStatus(
                                                  state=TaskState.working,
                                                  message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=[auth_part]),
                                                  timestamp=datetime.now(timezone.utc).isoformat(),
                                              ),
                                              final=False
                                          )
                                      task_result_aggregator.process_event(a2a_event)
                                      await event_queue.enqueue_event(a2a_event)
                                      continue
                              # Tool invocation detected → previous text was just progress.
                              # Note: A2UI blocks from the same event are already captured
                              # in artifact_media_parts by process_chunk() above since text
                              # parts are processed before function_call parts in the loop.
                              #
                              # EXCEPTION: transfer_to_agent is ADK's internal agent-
                              # delegation mechanism, not a real tool call. Text emitted
                              # alongside it (e.g., deep_analysis_agent's full report)
                              # is the actual user-facing analysis, not progress text.
                              # Clearing it here would trap the report in thinking.
                              # EXCEPTION 2: register_background_task - the LLM
                              # often emits the full user confirmation alongside the
                              # function_call. Clearing traps it in thinking.
                              # EXCEPTION 3: generate_image - the model is instructed
                              # to emit the full analysis text in the SAME response as
                              # the generate_image call (TURN SPLITTING rule). Clearing
                              # here silently discards that report, leaving only the
                              # auto-attached image (the "image-only response" bug).
                              # GENERAL RULE: if ADK flagged this model response as the
                              # genuine user-facing response (custom_metadata
                              # "a2a:response", set by inject_image_callback /
                              # a2ui_metadata_callback), its text is deliverable, not
                              # progress — preserve it regardless of which tool was
                              # called. This generalizes the fix beyond images.
                              _is_transfer = part.function_call.name.startswith('transfer_to_') or part.function_call.name == 'transfer_to_agent'
                              _event_is_response = False
                              try:
                                  _cm = getattr(adk_event, 'custom_metadata', None)
                                  if isinstance(_cm, dict) and _cm.get('a2a:response'):
                                      _event_is_response = True
                              except Exception:
                                  _event_is_response = False
                              _preserve = (
                                  _is_transfer
                                  or part.function_call.name in ('register_background_task', 'generate_image')
                                  or _event_is_response
                              )
                              if not _preserve:
                                  artifact_text_parts.clear()
                          elif part.function_response:
                              # --- Tool response status (TextPart → Thinking accordion) ---
                              _fr_name = getattr(part.function_response, 'name', None) or 'tool'
                              _is_transfer = _fr_name.startswith('transfer_to_') or _fr_name == 'transfer_to_agent'
                              if not _is_transfer and _fr_name != 'adk_request_credential':
                                  _turn_had_tool_results = True
                                  _fr_text_evt = TaskStatusUpdateEvent(
                                      task_id=context.task_id,
                                      context_id=context.context_id,
                                      status=TaskStatus(
                                          state=TaskState.working,
                                          message=Message(
                                              message_id=str(uuid.uuid4()),
                                              role=Role.agent,
                                              parts=[a2a_types.Part(root=a2a_types.TextPart(text=f"✅ {_fr_name}"))],
                                          ),
                                          timestamp=datetime.now(timezone.utc).isoformat(),
                                      ),
                                      final=False,
                                  )
                                  task_result_aggregator.process_event(_fr_text_evt)
                                  await event_queue.enqueue_event(_fr_text_evt)
                                  # D-1: heartbeat to fill the silent gap during the
                                  # (non-streamed) model generation that follows the
                                  # last tool. For intermediate tools it is harmlessly
                                  # superseded by the next tool's status.
                                  _hb_evt = TaskStatusUpdateEvent(
                                      task_id=context.task_id,
                                      context_id=context.context_id,
                                      status=TaskStatus(
                                          state=TaskState.working,
                                          message=Message(
                                              message_id=str(uuid.uuid4()),
                                              role=Role.agent,
                                              parts=[a2a_types.Part(root=a2a_types.TextPart(text="📝 Synthesizing the results into the report…"))],
                                          ),
                                          timestamp=datetime.now(timezone.utc).isoformat(),
                                      ),
                                      final=False,
                                  )
                                  task_result_aggregator.process_event(_hb_evt)
                                  await event_queue.enqueue_event(_hb_evt)
                          elif part.executable_code:
                              # --- Code execution: show the code being executed ---
                              _exec_code = getattr(part.executable_code, 'code', '') or ''
                              _exec_lang = getattr(part.executable_code, 'language', 'PYTHON') or 'PYTHON'
                              _ce_lines = [f"🐍 Code Execution ({_exec_lang})"]
                              if _exec_code:
                                  _ce_lines.append(_exec_code.replace(chr(10), chr(10)))
                              _ce_status_text = chr(10).join(_ce_lines)
                              _ce_text_evt = TaskStatusUpdateEvent(
                                  task_id=context.task_id,
                                  context_id=context.context_id,
                                  status=TaskStatus(
                                      state=TaskState.working,
                                      message=Message(
                                          message_id=str(uuid.uuid4()),
                                          role=Role.agent,
                                          parts=[a2a_types.Part(root=a2a_types.TextPart(text=_ce_status_text))],
                                      ),
                                      timestamp=datetime.now(timezone.utc).isoformat(),
                                  ),
                                  final=False,
                              )
                              task_result_aggregator.process_event(_ce_text_evt)
                              await event_queue.enqueue_event(_ce_text_evt)
                              artifact_text_parts.clear()
                          elif part.code_execution_result:
                              _turn_had_tool_results = True
                              # --- Code execution result: show output ---
                              _ce_outcome = getattr(part.code_execution_result, 'outcome', '') or ''
                              _ce_output = getattr(part.code_execution_result, 'output', '') or ''
                              logger.log_text(f"[code_exec] outcome={repr(_ce_outcome)} type={type(_ce_outcome).__name__} output_len={len(_ce_output)}")
                              _ce_icon = "❌" if any(kw in str(_ce_outcome).upper() for kw in ('FAILED', 'ERROR', 'DEADLINE')) else "✅"
                              _cr_lines = [f"{_ce_icon} Code Execution Result"]
                              if _ce_output:
                                  _cr_lines.append(_ce_output)
                              _cr_status_text = chr(10).join(_cr_lines)
                              _cr_text_evt = TaskStatusUpdateEvent(
                                  task_id=context.task_id,
                                  context_id=context.context_id,
                                  status=TaskStatus(
                                      state=TaskState.working,
                                      message=Message(
                                          message_id=str(uuid.uuid4()),
                                          role=Role.agent,
                                          parts=[a2a_types.Part(root=a2a_types.TextPart(text=_cr_status_text))],
                                      ),
                                      timestamp=datetime.now(timezone.utc).isoformat(),
                                  ),
                                  final=False,
                              )
                              task_result_aggregator.process_event(_cr_text_evt)
                              await event_queue.enqueue_event(_cr_text_evt)
                          if not part.inline_data:
                              a2a_event = TaskStatusUpdateEvent(
                                      task_id=context.task_id,
                                      context_id=context.context_id,
                                      status=TaskStatus(
                                          state=TaskState.working,
                                          message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=synthetic_parts),
                                          timestamp=datetime.now(timezone.utc).isoformat(),
                                      ),
                                      final=False
                                  )
                              task_result_aggregator.process_event(a2a_event)
                              await event_queue.enqueue_event(a2a_event)

        # MALFORMED_FUNCTION_CALL retries are handled in-loop by _all_events()
        # above: the body flags _malformed_should_retry + continue, and the wrapper
        # heals the session and re-runs through this same body. No separate retry
        # pass is needed (it previously bypassed the A2UI parser/safety nets).

        # Cancel the timeout watchdog now that the event loop has finished
        _watchdog_task.cancel()

        # Inline overrun conversion (v10.79), exit A: the deadline watchdog
        # already finalized this turn. Close the abandoned in-flight run (frees
        # the LLM call and, with it, the Y2 session lock as soon as possible)
        # and stop here - any further emission would land after GE finalized
        # the turn. NOTE: the inline watchdog is NOT cancelled on the normal
        # path yet; it stays armed so the salvage phases below (synth retry /
        # B-1 / chip re-prompt) are wall-clock-bounded too.
        if _inline_converted:
            try:
                await _events_gen.aclose()
            except Exception as _gen_close_err:
                logger.log_text('[inline_deadline] abandoned-run close error (non-fatal): ' + str(_gen_close_err)[:200])
            try:
                await _inline_watchdog_task  # ensure the conversion emission fully finished
            except Exception:
                pass
            return

        # =============================================================================
        # Drain the A2UI stream parser's internal buffer.
        # A2uiStreamParser does NOT have a flush() method. Instead, after the
        # stream ends we must handle any text remaining in _buffer:
        #   - If _found_delimiter is True, we have an incomplete <a2ui-json> block
        #     (close tag never arrived). Process the raw JSON fragment.
        #   - If _found_delimiter is False, trailing conversational text remains.
        # =============================================================================

        try:
            remaining = getattr(stream_parser, '_buffer', '')
            if remaining:
                if getattr(stream_parser, '_found_delimiter', False):
                    # Incomplete A2UI block — process as if close tag arrived
                    drain_parts = stream_parser.process_chunk('</a2ui-json>')
                else:
                    # Trailing conversational text
                    drain_parts = [ResponsePart(text=remaining)]
                    stream_parser._buffer = ''

                for rp in drain_parts:
                    if rp.text:
                        text_part = a2a_types.Part(root=a2a_types.TextPart(text=rp.text))
                        artifact_text_parts.append(text_part)
                    if rp.a2ui_json:
                        a2ui_messages = rp.a2ui_json if isinstance(rp.a2ui_json, list) else [rp.a2ui_json]
                        a2ui_messages = _heal_a2ui_message_list(a2ui_messages)
                        for msg in a2ui_messages:
                            artifact_media_parts.extend(create_a2ui_parts(msg))
        except Exception as drain_err:
            logger.log_text(f"A2UI stream parser drain error: {drain_err}")

        # =============================================================================
        # Final Artifact — contains ALL accumulated user-facing parts
        # GE displays artifact content OUTSIDE the thinking accordion.
        # Without this, only the last streamed chunk appears as the "final response"
        # and all preceding text is trapped inside thinking.
        # =============================================================================
        # Combine: final response text + all media (images, A2UI)
        # --- Re-order media parts ---
        _normal_media = []
        _suggestion_media = []
        for _mp in artifact_media_parts:
            if _is_suggestions_part(_mp):
                _suggestion_media.append(_mp)
            else:
                _normal_media.append(_mp)

        # Note: '💡 Next Actions' header injection was removed because GE renders
        # text parts ABOVE all media parts, making it impossible to position the
        # header between A2UI cards and suggestion buttons via text injection.
        # Spacing before buttons is now handled inside A2UI component tree by
        # _rewrite_suggestions_a2ui() which inserts a spacer Text component.

        artifact_parts = artifact_text_parts + _normal_media + _suggestion_media

        # --- DIAGNOSTIC: Log final artifact composition ---
        def _part_type_label(p):
            _r = getattr(p, 'root', None)
            if _r is None:
                return 'none'
            if hasattr(_r, 'text'):
                return 'text'
            if hasattr(_r, 'data'):
                _d = _r.data
                if isinstance(_d, dict):
                    for _dk in ('beginRendering', 'surfaceUpdate', 'deleteSurface'):
                        if _dk in _d:
                            return _dk + ':' + str(_d[_dk].get('surfaceId', '?'))
                return 'data'
            if hasattr(_r, 'inline_data'):
                return 'inline_data'
            return 'other'
        _part_labels = [_part_type_label(p) for p in artifact_parts]
        logger.log_text(f"[final_artifact] text={len(artifact_text_parts)} normal_media={len(_normal_media)} suggestion_media={len(_suggestion_media)} total={len(artifact_parts)}")
        logger.log_text(f"[final_artifact_parts] {_part_labels}")

        # =============================================================================
        # Stub guard (v10.70): the model can stall with a degenerate-but-VALID
        # final output - confirmed in logs (Input 175k -> Output 6 tokens, a bare
        # progress line, zero function_calls in the invocation). No error code
        # fires, so no existing salvage triggers, and the stub becomes the whole
        # deliverable (rendered outside thinking; the turn just stops). Detect by
        # deliverable SHAPE - a stub of text with no card/image and no chips -
        # and route through the synthesis recovery below with a neutral
        # completion prompt. Clarifying questions (ending in a question mark)
        # are preserved verbatim; auth and timeout turns are exempt.
        # =============================================================================
        _stub_guard_fired = False
        if (not _normal_media) and (not _suggestion_media) and (not _timed_out) and (not _auth_flow) and (not _fatal_config_error):
            _stub_len = 0
            _stub_tail = ''
            for _sg_p in artifact_text_parts:
                _sg_t = (getattr(getattr(_sg_p, 'root', None), 'text', '') or '').strip()
                if _sg_t:
                    _stub_len += len(_sg_t)
                    _stub_tail = _sg_t[-1]
            if 0 < _stub_len <= 120 and _stub_tail not in ('?', chr(0xFF1F)):
                _stub_guard_fired = True
                logger.log_text("[stub_guard] " + str(_stub_len) + "-char stub deliverable, no card/chips - completion re-prompt")
                artifact_text_parts.clear()
                artifact_parts = []

        # =============================================================================
        # B-2 (v10.59): Synthesis retry when the turn produced NO deliverable.
        # The final report generation can return empty (Content:None) on a bloated
        # context; enforce_result then injects a raw tool dict that leak_failsafe
        # blocks -> total=0 -> the UI hangs on "thinking". Instead of giving up, we
        # re-run the agent with a synthesis-only prompt (no tools), up to N times.
        # _heal_session_events compresses the bloated context (existing mechanism),
        # raising success odds while keeping the model's prior conclusions. This
        # fires ONLY on the empty path; normal successful turns are untouched.
        # =============================================================================
        def _extract_report_parts(_text):
            # Convert a report-shaped text chunk into (text_parts, media_parts),
            # reusing the A2UI stream parser + the untagged/tagged safety nets.
            _tp, _mp = [], []
            _found = False
            _sp = A2uiStreamParser(catalog=a2ui_selected_catalog)
            try:
                _chunk = _sanitize_a2ui_text_icons(_text) if '<a2ui-json>' in _text else _text
                _rps = _sp.process_chunk(_chunk)
            except Exception:
                _rps = []
            for _rp in _rps:
                if _rp.text and _rp.text.strip():
                    _stripped = _rp.text.strip()
                    # Block raw Python dict/list repr leaks (same guard as main loop).
                    if not ((_stripped.startswith('{') or _stripped.startswith('[')) and ("'content':" in _stripped or "'parts':" in _stripped)):
                        _tp.append(a2a_types.Part(root=a2a_types.TextPart(text=_rp.text)))
                if _rp.a2ui_json:
                    _msgs = _rp.a2ui_json if isinstance(_rp.a2ui_json, list) else [_rp.a2ui_json]
                    for _m in _heal_a2ui_message_list(_msgs):
                        _mp.extend(create_a2ui_parts(_m))
                        _found = True
            # Untagged A2UI safety net (model omitted <a2ui-json> tags).
            if not _found and '<a2ui-json>' not in _text and any(_k in _text for _k in ('"beginRendering"', '"surfaceUpdate"', '"deleteSurface"')):
                _pos = 0
                while _pos < len(_text):
                    _sb = _text.find('{', _pos)
                    _sk = _text.find('[', _pos)
                    if _sb == -1 and _sk == -1:
                        break
                    _start = _sb if _sk == -1 else (_sk if _sb == -1 else min(_sb, _sk))
                    _oc = _text[_start]
                    _cc = '}' if _oc == '{' else ']'
                    _end = _find_balanced_block(_text, _start, _oc, _cc)
                    if _end == -1:
                        _pos = _start + 1
                        continue
                    _obj = _parse_loose_json(_text[_start:_end])
                    _ok = False
                    if isinstance(_obj, list):
                        _ok = any(isinstance(_i, dict) and (any(_kk in _i for _kk in ("beginRendering", "surfaceUpdate", "deleteSurface")) or ("id" in _i and "component" in _i)) for _i in _obj)
                    elif isinstance(_obj, dict):
                        _ok = any(_kk in _obj for _kk in ("beginRendering", "surfaceUpdate", "deleteSurface")) or ("id" in _obj and "component" in _obj)
                    if _ok:
                        _items = _obj if isinstance(_obj, list) else [_obj]
                        for _it in _heal_a2ui_message_list(_items):
                            if isinstance(_it, dict):
                                _mp.extend(create_a2ui_parts(_it))
                        _pos = _end
                    else:
                        _pos = _start + 1
            return _tp, _mp

        # v10.61: English prompts + same-language clause (see _CONTINUE_MESSAGE).
        _SYNTH_FULL_MSG = (
            "Using ONLY the results you have already gathered (do NOT make any more "
            "tool calls), produce the final analysis report now, in full. Include the "
            "analytical body text, an A2UI card wrapped in <a2ui-json> tags, and "
            "suggestion chips at the end. Write everything in the SAME language you "
            "have been using with the user in this conversation; do not switch languages."
        )
        _SYNTH_TEXT_MSG = (
            "Using ONLY the results you have already gathered (do NOT make any more "
            "tool calls, and do NOT use A2UI or JSON), produce the final analysis report "
            "now as complete Markdown plain text. Include the key findings, the numbers, "
            "and at least three recommendations. Write everything in the SAME language "
            "you have been using with the user in this conversation; do not switch languages."
        )
        # v10.70: neutral completion prompt for the stub guard. Deliberately does
        # NOT force a report shape - a greeting/confirmation stub should be
        # re-completed as a greeting/confirmation, not inflated into a report.
        _STUB_COMPLETE_MSG = (
            "Your previous reply was an unfinished status line, not a complete "
            "answer. Complete your final response to the user now, using ONLY the "
            "results you have already gathered (do NOT make any more tool calls). "
            "Provide the full answer the user asked for, with A2UI cards where "
            "appropriate and suggestion chips at the end. Write everything in the "
            "SAME language you have been using with the user in this conversation; "
            "do not switch languages."
        )
        # v11.5: recovery prompt for a stub emitted BEFORE any tool ran. The
        # toolless synthesis prompts are useless there (no data was gathered -
        # they either stall again or hallucinate), so this one explicitly
        # re-authorizes tool execution and demands the finished deliverable.
        _STUB_EXECUTE_MSG = (
            "Your previous reply was an unfinished status line and you have NOT "
            "yet gathered any data for the user's request. Resume executing the "
            "request now: call the tools you need (catalog/metadata lookups, SQL "
            "queries), keep the tool calls to the minimum necessary, and then "
            "deliver the COMPLETE final answer in the same turn - the findings as "
            "text, an A2UI card where appropriate, and suggestion chips at the "
            "end. Do NOT stop after a progress line. Write everything in the SAME "
            "language you have been using with the user in this conversation; do "
            "not switch languages."
        )
        # v10.70: chip-only re-prompt for the missing-chips recovery below.
        _SYNTH_CHIPS_MSG = (
            "Your previous response was delivered to the user, but its suggestion "
            "chips were missing. Output ONLY the suggestion chip bar now: a single "
            "<a2ui-json> block using surfaceId 'suggestions', containing BOTH the "
            "beginRendering message AND the surfaceUpdate message with a Row of 3-4 "
            "Buttons whose sendText actions reflect natural next actions in this "
            "conversation. Do NOT repeat the report, do NOT output any other text, "
            "cards, or tool calls. Write the button labels in the SAME language you "
            "have been using with the user."
        )
        _MAX_SYNTH_RETRIES = 3
        _synth_try = 0
        while (not artifact_text_parts) and (not _normal_media) and (not _timed_out) and (not _inline_converted) and _synth_try < _MAX_SYNTH_RETRIES:
            _synth_try += 1
            logger.log_text("[synth_retry] empty deliverable - synthesis retry " + str(_synth_try) + "/" + str(_MAX_SYNTH_RETRIES))
            _hb_msg = "📝 Synthesizing the analysis results into the report… (" + str(_synth_try) + "/" + str(_MAX_SYNTH_RETRIES) + ")"
            _hb_evt = TaskStatusUpdateEvent(
                task_id=context.task_id,
                context_id=context.context_id,
                status=TaskStatus(
                    state=TaskState.working,
                    message=Message(message_id=str(uuid.uuid4()), role=Role.agent, parts=[a2a_types.Part(root=a2a_types.TextPart(text=_hb_msg))]),
                    timestamp=datetime.now(timezone.utc).isoformat(),
                ),
                final=False,
            )
            task_result_aggregator.process_event(_hb_evt)
            await event_queue.enqueue_event(_hb_evt)
            # Heal + compress the bloated context (existing mechanism); reset parser.
            _sr_session = await runner.session_service.get_session(
                app_name=runner.app_name, user_id=run_args['user_id'], session_id=run_args['session_id']
            )
            if _sr_session is not None:
                _heal_session_events(_sr_session)
            stream_parser = A2uiStreamParser(catalog=a2ui_selected_catalog)
            artifact_text_parts.clear()
            artifact_media_parts.clear()
            if _stub_guard_fired and not _turn_had_tool_results and _synth_try < _MAX_SYNTH_RETRIES:
                # No data was gathered before the stall: re-execute WITH tools
                # (a toolless synthesis has nothing to synthesize from). Last
                # retry still falls through to plain-text mode as a final resort.
                _synth_msg = _STUB_EXECUTE_MSG
            elif _stub_guard_fired and _synth_try == 1:
                _synth_msg = _STUB_COMPLETE_MSG
            else:
                _synth_msg = _SYNTH_TEXT_MSG if _synth_try >= _MAX_SYNTH_RETRIES else _SYNTH_FULL_MSG
            _synth_args = dict(run_args)
            _synth_args['new_message'] = genai_types.Content(role='user', parts=[genai_types.Part(text=_synth_msg)])
            try:
                async for _sr_event in _run_with_auto_continue(initial_args=_synth_args):
                    if _timed_out or _inline_converted:
                        break
                    _sr_content = getattr(_sr_event, 'content', None)
                    if not (_sr_content and hasattr(_sr_content, 'parts')):
                        continue
                    for _sr_part in _sr_content.parts:
                        if getattr(_sr_part, 'function_response', None) or getattr(_sr_part, 'code_execution_result', None):
                            # A tool ran during this recovery attempt: later
                            # retries may switch to the toolless synthesis mode.
                            _turn_had_tool_results = True
                        if getattr(_sr_part, 'text', None):
                            _t_parts, _m_parts = _extract_report_parts(_sr_part.text)
                            artifact_text_parts.extend(_t_parts)
                            artifact_media_parts.extend(_m_parts)
            except Exception as _sr_err:
                logger.log_text("[synth_retry] error during synthesis run: " + str(_sr_err))
            # Drain any buffered A2UI left in the synthesis parser.
            try:
                _sr_rem = getattr(stream_parser, '_buffer', '')
                if _sr_rem:
                    if getattr(stream_parser, '_found_delimiter', False):
                        _drain = stream_parser.process_chunk('</a2ui-json>')
                    else:
                        _drain = [ResponsePart(text=_sr_rem)]
                        stream_parser._buffer = ''
                    for _dp in _drain:
                        if _dp.text and _dp.text.strip():
                            artifact_text_parts.append(a2a_types.Part(root=a2a_types.TextPart(text=_dp.text)))
                        if _dp.a2ui_json:
                            _dm = _dp.a2ui_json if isinstance(_dp.a2ui_json, list) else [_dp.a2ui_json]
                            for _dmi in _heal_a2ui_message_list(_dm):
                                artifact_media_parts.extend(create_a2ui_parts(_dmi))
            except Exception:
                pass
            # Recompute media split + artifact_parts after the synthesis pass.
            _normal_media = []
            _suggestion_media = []
            for _mp2 in artifact_media_parts:
                if _is_suggestions_part(_mp2):
                    _suggestion_media.append(_mp2)
                else:
                    _normal_media.append(_mp2)
            artifact_parts = artifact_text_parts + _normal_media + _suggestion_media
            if artifact_parts:
                # v11.5: a recovery attempt that returned ANOTHER stub (short
                # text, no card, no chips) has not recovered anything - the live
                # 2026-07-15 stall produced a second 13-token progress line that
                # the old any-text acceptance shipped as the final answer.
                # Reject it and keep retrying; if every retry stays a stub, the
                # B-1 fallback below gives an honest failure + retry chip
                # instead of a dangling progress line. Clarifying questions
                # (ending in a question mark) are accepted verbatim, mirroring
                # the stub guard itself.
                _rec_text = ""
                for _rp2 in artifact_text_parts:
                    _rec_text = _rec_text + (getattr(getattr(_rp2, 'root', None), 'text', '') or '').strip()
                _rec_tail = _rec_text[-1] if _rec_text else ''
                if ((not _normal_media) and (not _suggestion_media)
                        and len(_rec_text) <= 120 and _rec_tail not in ('?', chr(0xFF1F))):
                    logger.log_text("[synth_retry] retry " + str(_synth_try) + " returned another stub (" + str(len(_rec_text)) + " chars) - rejected, retrying")
                    artifact_text_parts.clear()
                    artifact_media_parts.clear()
                    _normal_media = []
                    _suggestion_media = []
                    artifact_parts = []
                    continue
                logger.log_text("[synth_retry] recovered deliverable on retry " + str(_synth_try) + " (text=" + str(len(artifact_text_parts)) + ", media=" + str(len(artifact_media_parts)) + ")")
                break

        # =============================================================================
        # B-1 (v10.59): Guaranteed fallback. If synthesis retries still produced no
        # deliverable, never end silently -- emit an explicit message + retry chips
        # so the UI shows a real response instead of hanging on "thinking".
        # =============================================================================
        if (not artifact_parts) and (not _inline_converted):
            logger.log_text("[synth_retry] all retries exhausted - emitting explicit fallback message")
            _b1_text = "⚠️ The report could not be generated. The analysis scope may be too large. Please narrow the target period, entities, or metrics and try again."
            _b1_c1_text = "Narrow the analysis to a single entity"
            _b1_c1_label = "🎯 Narrow scope"
            _b1_c2_text = "Generate the report again"
            _b1_c2_label = "🔄 Retry"
            _b1_part = a2a_types.Part(root=a2a_types.TextPart(text=_b1_text))
            artifact_text_parts.clear()
            artifact_text_parts.append(_b1_part)
            _b1_suggestions = [
                { 'beginRendering': { 'surfaceId': 'suggestions', 'root': 'root' } },
                { 'surfaceUpdate': { 'surfaceId': 'suggestions', 'components': [
                    { 'id': 'root', 'component': { 'Row': { 'children': { 'explicitList': ['b1_chip1', 'b1_chip2'] }, 'distribution': 'spaceEvenly', 'alignment': 'center' } } },
                    { 'id': 'b1_chip1', 'component': { 'Button': { 'child': 'b1_chip1Lbl', 'action': { 'name': 'sendText', 'context': [{ 'key': 'text', 'value': { 'literalString': _b1_c1_text } }] } } } },
                    { 'id': 'b1_chip1Lbl', 'component': { 'Text': { 'text': { 'literalString': _b1_c1_label }, 'usageHint': 'body' } } },
                    { 'id': 'b1_chip2', 'component': { 'Button': { 'child': 'b1_chip2Lbl', 'action': { 'name': 'sendText', 'context': [{ 'key': 'text', 'value': { 'literalString': _b1_c2_text } }] } } } },
                    { 'id': 'b1_chip2Lbl', 'component': { 'Text': { 'text': { 'literalString': _b1_c2_label }, 'usageHint': 'body' } } }
                ] } }
            ]
            artifact_media_parts = []
            for _b1_item in _b1_suggestions:
                artifact_media_parts.append(create_a2ui_part(_b1_item))
            _normal_media = []
            _suggestion_media = []
            for _mp3 in artifact_media_parts:
                if _is_suggestions_part(_mp3):
                    _suggestion_media.append(_mp3)
                else:
                    _normal_media.append(_mp3)
            artifact_parts = artifact_text_parts + _normal_media + _suggestion_media
            # Stream the fallback message + chips as a WORKING event so GE renders the
            # suggestions surface from the live stream (chips only in the final artifact
            # may not render). Mirrors the prior MALFORMED-recovery streaming pattern.
            try:
                _b1_evt = TaskStatusUpdateEvent(
                    task_id=context.task_id,
                    context_id=context.context_id,
                    status=TaskStatus(
                        state=TaskState.working,
                        message=Message(
                            message_id=str(uuid.uuid4()),
                            role=Role.agent,
                            parts=[_b1_part] + _suggestion_media,
                        ),
                        timestamp=datetime.now(timezone.utc).isoformat(),
                    ),
                    final=False,
                )
                task_result_aggregator.process_event(_b1_evt)
                await event_queue.enqueue_event(_b1_evt)
            except Exception as _b1_err:
                logger.log_text("[synth_retry] B-1 streaming failed: " + str(_b1_err))
            logger.log_text(f"[final_artifact_after_recovery] text={len(artifact_text_parts)} normal_media={len(_normal_media)} suggestion_media={len(_suggestion_media)} total={len(artifact_parts)}")

        # =============================================================================
        # UI-only render guard (v10.68): GE does NOT render a final artifact that has
        # UI/media parts but ZERO text parts (confirmed in logs: a welcome-card-only
        # turn with text=0 showed a blank turn). The greeting prompt now asks the model
        # to lead with a one-line plain-text greeting, but the lite model may ignore it.
        # As a backstop, if the turn ends UI-only, promote the most recent SHORT
        # conversational text the model emitted this turn (often cleared earlier by a
        # trailing tool call) into the artifact so the turn renders. We NEVER fabricate
        # text (no hardcoded natural language); if nothing reusable was captured we log
        # and leave the turn as-is.
        # =============================================================================
        if (not artifact_text_parts) and (_normal_media or _suggestion_media):
            _promoted = None
            for _cand in reversed(_all_model_texts):
                _c = (_cand or '').strip()
                if _c:
                    _promoted = _c
                    break
            if _promoted:
                artifact_text_parts.append(a2a_types.Part(root=a2a_types.TextPart(text=_promoted)))
                artifact_parts = artifact_text_parts + _normal_media + _suggestion_media
                logger.log_text("[ui_only_guard] promoted prior model text to prevent blank UI-only render (len=" + str(len(_promoted)) + ")")
            else:
                logger.log_text("[ui_only_guard] UI-only artifact (text=0) and no reusable model text captured - turn may render blank")

        # =============================================================================
        # Chip recovery (v10.70): intermittently the model omits the Next Actions
        # chips - either a begin-only 'suggestions' surface with no surfaceUpdate
        # (renders as nothing), or no suggestions block at all (confirmed in logs:
        # a long text-only answer with suggestion_media=0 under degraded context).
        # (a) Drop orphan begin-only suggestion surfaces. (b) If the turn has a
        # substantive deliverable but no populated chips, run ONE chip-only
        # re-prompt and keep ONLY the suggestion parts it returns. Skipped when a
        # card carries its own control buttons (the prompt's A2UI CARD INTERACTION
        # EXCEPTION makes chips intentionally absent there), on auth/timeout
        # turns, and when B-1 already attached its retry chips. Runs BEFORE the
        # G1 idempotency cache and the H1 session artifact store so replays and
        # GE "Regenerate" serve the chip-complete version.
        # =============================================================================
        _chips_ok = _has_populated_suggestions(_suggestion_media)
        if (not _chips_ok) and _suggestion_media:
            _orphan_count = len(_suggestion_media)
            _suggestion_media = []
            artifact_media_parts = [p for p in artifact_media_parts if not _is_suggestions_part(p)]
            artifact_parts = artifact_text_parts + _normal_media + _suggestion_media
            logger.log_text("[chip_reprompt] dropped " + str(_orphan_count) + " orphan suggestion part(s) (no populated surfaceUpdate)")
        if ((not _chips_ok) and (not _timed_out) and (not _auth_flow)
                and (not _fatal_config_error) and (not _inline_converted)
                and (not _has_interactive_card(_normal_media))):
            _cr_text_len = sum(
                len((getattr(getattr(p, 'root', None), 'text', '') or '').strip())
                for p in artifact_text_parts
            )
            if _normal_media or _cr_text_len > 120:
                logger.log_text("[chip_reprompt] substantive deliverable without chips - one chip-only re-prompt")
                _cr_args = dict(run_args)
                _cr_args['new_message'] = genai_types.Content(role='user', parts=[genai_types.Part(text=_SYNTH_CHIPS_MSG)])
                _cr_media = []
                try:
                    async for _cr_event in _run_with_auto_continue(initial_args=_cr_args):
                        if _timed_out or _inline_converted:
                            break
                        _cr_content = getattr(_cr_event, 'content', None)
                        if not (_cr_content and hasattr(_cr_content, 'parts')):
                            continue
                        for _cr_part in _cr_content.parts:
                            if getattr(_cr_part, 'text', None):
                                _cr_tp, _cr_mp = _extract_report_parts(_cr_part.text)
                                _cr_media.extend(_cr_mp)
                except Exception as _cr_err:
                    logger.log_text("[chip_reprompt] error during chip re-prompt: " + str(_cr_err))
                # Keep ONLY suggestion parts - any re-emitted text or cards are
                # discarded so the re-prompt can never duplicate the deliverable.
                _recovered_chips = [p for p in _cr_media if _is_suggestions_part(p)]
                if _has_populated_suggestions(_recovered_chips) and (not _inline_converted):
                    # Stream the chips as a WORKING event so GE renders the
                    # suggestions surface from the live stream (chips only in the
                    # final artifact may not render). Mirrors the B-1 pattern.
                    try:
                        _cr_evt = TaskStatusUpdateEvent(
                            task_id=context.task_id,
                            context_id=context.context_id,
                            status=TaskStatus(
                                state=TaskState.working,
                                message=Message(
                                    message_id=str(uuid.uuid4()),
                                    role=Role.agent,
                                    parts=_recovered_chips,
                                ),
                                timestamp=datetime.now(timezone.utc).isoformat(),
                            ),
                            final=False,
                        )
                        task_result_aggregator.process_event(_cr_evt)
                        await event_queue.enqueue_event(_cr_evt)
                    except Exception as _cr_stream_err:
                        logger.log_text("[chip_reprompt] streaming recovered chips failed: " + str(_cr_stream_err))
                    artifact_media_parts.extend(_recovered_chips)
                    _suggestion_media = list(_recovered_chips)
                    artifact_parts = artifact_text_parts + _normal_media + _suggestion_media
                    logger.log_text("[chip_reprompt] recovered " + str(len(_recovered_chips)) + " suggestion part(s)")
                else:
                    logger.log_text("[chip_reprompt] re-prompt yielded no usable chips - leaving turn as-is")

        # Inline overrun conversion (v10.79), exit B: the deadline watchdog may
        # have fired DURING a salvage phase above. If it converted, it already
        # emitted the final event and cached the replay parts - suppress the
        # normal emission below. Otherwise disarm it now: from here on the real
        # deliverable is being finalized and must not be raced. Single-threaded
        # event loop: no await between the flag check and the cancel, so the
        # watchdog cannot fire in between.
        _turn_finalizing = True
        if _inline_converted:
            try:
                await _inline_watchdog_task  # ensure the conversion emission fully finished
            except Exception:
                pass
            logger.log_text('[inline_deadline] salvage result suppressed - conversion already finalized this turn')
            return
        _inline_watchdog_task.cancel()

        # G1 (v10.65): cache this winner's final deliverable so duplicate presses
        # of the SAME action can replay it instead of rendering an empty turn.
        if idem_key:
            _replay_parts = artifact_parts or (
                task_result_aggregator.task_status_message.parts
                if (task_result_aggregator.task_status_message is not None
                    and task_result_aggregator.task_status_message.parts) else None)
            _store_idem_result(idem_key, _replay_parts)

        # H1 (v10.66): signature of THIS turn's request, used to detect a
        # regenerate/re-send of the same request that produced the last report.
        _cur_sig = _msg_signature(run_args)

        if (
            task_result_aggregator.task_state == TaskState.working
            and artifact_parts
        ):
          _store_session_artifact(session_id, _cur_sig, artifact_parts)
          await event_queue.enqueue_event(
              TaskArtifactUpdateEvent(
                  task_id=context.task_id,
                  last_chunk=True,
                  context_id=context.context_id,
                  artifact=Artifact(
                      artifact_id=str(uuid.uuid4()),
                      parts=artifact_parts,  # ★ Final text + all media
                  ),
              )
          )
          await event_queue.enqueue_event(
              TaskStatusUpdateEvent(
                  task_id=context.task_id,
                  status=TaskStatus(
                      state=TaskState.completed,
                      timestamp=datetime.now(timezone.utc).isoformat(),
                  ),
                  context_id=context.context_id,
                  final=True,
              )
          )
        elif (
            task_result_aggregator.task_state == TaskState.working
            and task_result_aggregator.task_status_message is not None
            and task_result_aggregator.task_status_message.parts
        ):
          # Fallback: use last message if no artifact parts accumulated
          _store_session_artifact(session_id, _cur_sig, task_result_aggregator.task_status_message.parts)
          await event_queue.enqueue_event(
              TaskArtifactUpdateEvent(
                  task_id=context.task_id,
                  last_chunk=True,
                  context_id=context.context_id,
                  artifact=Artifact(
                      artifact_id=str(uuid.uuid4()),
                      parts=task_result_aggregator.task_status_message.parts,
                  ),
              )
          )
          await event_queue.enqueue_event(
              TaskStatusUpdateEvent(
                  task_id=context.task_id,
                  status=TaskStatus(
                      state=TaskState.completed,
                      timestamp=datetime.now(timezone.utc).isoformat(),
                  ),
                  context_id=context.context_id,
                  final=True,
              )
          )
        else:
          # H1: the model produced NO new deliverable this turn. If this is a
          # re-send/regenerate of the same request that produced the last report
          # (matching signature), replay that report so GE's "Regenerate" does not
          # blank the turn. Otherwise emit a clean terminal status (never a
          # non-completed state with final=True, which GE treats as incomplete).
          _last = _session_last_artifact.get(session_id)
          if (_last and _last[0] == _cur_sig and _cur_sig
                  and task_result_aggregator.task_state != TaskState.failed):
              logger.log_text("[empty_turn] no new deliverable - replaying last session report (" + str(len(_last[1])) + " parts)")
              await event_queue.enqueue_event(
                  TaskArtifactUpdateEvent(
                      task_id=context.task_id,
                      last_chunk=True,
                      context_id=context.context_id,
                      # Re-scope surfaceIds so replayed cards render on the
                      # regenerated turn (v10.72, see _rescope_replay_parts).
                      artifact=Artifact(artifact_id=str(uuid.uuid4()), parts=_rescope_replay_parts(_last[1], context.task_id)),
                  )
              )
              await event_queue.enqueue_event(
                  TaskStatusUpdateEvent(
                      task_id=context.task_id,
                      status=TaskStatus(
                          state=TaskState.completed,
                          timestamp=datetime.now(timezone.utc).isoformat(),
                      ),
                      context_id=context.context_id,
                      final=True,
                  )
              )
          else:
              _final_state = task_result_aggregator.task_state
              if _final_state == TaskState.working:
                  _final_state = TaskState.completed
              await event_queue.enqueue_event(
                  TaskStatusUpdateEvent(
                      task_id=context.task_id,
                      status=TaskStatus(
                          state=_final_state,
                          timestamp=datetime.now(timezone.utc).isoformat(),
                          message=task_result_aggregator.task_status_message,
                      ),
                      context_id=context.context_id,
                      final=True,
                  )
              )

request_handler = DefaultRequestHandler(
    agent_executor=AdkAgentToA2AExecutor(runner=runner, use_legacy=True), task_store=InMemoryTaskStore()
)

A2A_RPC_PATH = f"/a2a/{adk_app.name}"

def _build_static_agent_card() -> AgentCard:
    """Build a static AgentCard WITHOUT connecting to MCP servers.

    AgentCardBuilder.build() connects to ALL MCP toolsets to discover tools,
    which can hang indefinitely (especially stdio-based custom MCP servers
    like Redmine). This causes A2A routes to never be registered.

    Instead, we create a static AgentCard with a generic skill. MCP tool
    connections happen LAZILY when the first user request invokes a tool —
    this is handled automatically by the ADK runtime.
    """
    from a2a.types import AgentSkill

    # Advertise A2UI capability via SDK extension helper
    a2ui_extension = get_a2ui_agent_extension(
        version="0.8",
        supported_catalog_ids=a2ui_schema_manager.supported_catalog_ids,
    )

    return AgentCard(
        name=adk_app.name,
        description=adk_app.root_agent.description or f"Agent {adk_app.name}",
        url=f"{os.getenv('APP_URL', 'http://0.0.0.0:8000')}{A2A_RPC_PATH}",
        version=os.getenv("AGENT_VERSION", "0.1.0"),
        capabilities=AgentCapabilities(
            streaming=True,
            pushNotifications=True,
            extensions=[a2ui_extension],
        ),
        defaultInputModes=["text/plain"],
        defaultOutputModes=["text/plain", "application/json"],
        skills=[
            AgentSkill(
                id="general",
                name="General Skill",
                description="Handles general queries using BigQuery, Maps, Firestore, and other data sources.",
                tags=[],
            )
        ],
    )

@asynccontextmanager
async def lifespan(app_instance: FastAPI) -> AsyncIterator[None]:
    # CRITICAL: Register A2A routes IMMEDIATELY with a static agent card.
    # Do NOT call AgentCardBuilder.build() — it connects to ALL MCP servers
    # to discover tools, which hangs on slow/broken MCP connections and
    # prevents A2A routes from ever being registered.
    # MCP tool connections happen LAZILY on first user request.
    agent_card = _build_static_agent_card()
    a2a_app = A2AFastAPIApplication(agent_card=agent_card, http_handler=request_handler)
    a2a_app.add_routes_to_app(
        app_instance,
        agent_card_url=f"{A2A_RPC_PATH}{AGENT_CARD_WELL_KNOWN_PATH}",
        rpc_url=A2A_RPC_PATH,
        extended_agent_card_url=f"{A2A_RPC_PATH}{EXTENDED_AGENT_CARD_PATH}",
    )
    # --- Dependency Compatibility Check (read-only, log-only) ---
    try:
        import importlib.metadata as _meta
        import inspect as _insp
        _dep_issues = []
        # A2UI: version parameter must exist for GE compatibility
        _a2ui_sig = _insp.signature(_original_create_a2ui_part)
        if 'version' not in _a2ui_sig.parameters:
            _dep_issues.append("a2ui-agent-sdk: 'version' param missing from create_a2ui_part")
        # ADK: warn on untested major version
        try:
            _adk_v = _meta.version('google-adk')
            if int(_adk_v.split('.')[0]) >= 2:
                _dep_issues.append("google-adk " + _adk_v + ": untested major version")
        except Exception:
            pass
        if _dep_issues:
            for _di in _dep_issues:
                logger.log_text("[dep_check] WARNING " + _di)
        else:
            logger.log_text("[dep_check] All critical dependencies compatible")
    except Exception as _dep_err:
        logger.log_text("[dep_check] check failed: " + str(_dep_err))

    yield

app = FastAPI(
    title="tmp-ref-run",
    description="API for interacting with the Agent tmp-ref-run",
    lifespan=lifespan,
)

# --- Token Extraction Middleware ---
# ADK's A2aAgentExecutor now delegates to an internal ExecutorImpl, making
# _handle_request overrides ineffective. Instead, capture the OAuth token
# at the HTTP middleware level before the request reaches ADK.
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
import builtins

class TokenExtractionMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        token = None
        auth_id = os.environ.get("GEMINI_AUTHORIZATION_ID", "")
        
        # Strategy 1: Authorization header (Gemini Enterprise passes user token here)
        auth_header = request.headers.get("authorization", "")
        if auth_header.startswith("Bearer "):
            token = auth_header[7:]
            logger.log_text(f"MIDDLEWARE: ✅ Token from Authorization header (prefix={token[:25]}..., len={len(token)})")
        
        # Strategy 2: x-authorization header (fallback)
        if not token:
            x_auth = request.headers.get("x-authorization", "")
            if x_auth.startswith("Bearer "):
                token = x_auth[7:]
                logger.log_text(f"MIDDLEWARE: ✅ Token from x-authorization header (prefix={token[:25]}..., len={len(token)})")
        
        # Strategy 3: Parse JSON body for call_context.state.headers.authorization
        if not token and request.url.path.startswith("/a2a/"):
            try:
                body = await request.body()
                if body:
                    import json
                    body_json = json.loads(body)
                    # Try JSON-RPC params.context or direct context
                    ctx = None
                    if 'params' in body_json and isinstance(body_json['params'], dict):
                        ctx = body_json['params'].get('context', {})
                    elif 'context' in body_json:
                        ctx = body_json.get('context', {})
                    
                    if ctx and isinstance(ctx, dict):
                        state = ctx.get('state', {})
                        if isinstance(state, dict):
                            # Check for auth_id key directly
                            if auth_id and auth_id in state:
                                token = state[auth_id]
                                logger.log_text(f"MIDDLEWARE: ✅ Token from body context.state['{auth_id}'] (prefix={str(token)[:25]}..., len={len(str(token))})")
                            # Check for headers.authorization in state
                            elif 'headers' in state and isinstance(state['headers'], dict):
                                h_auth = state['headers'].get('authorization', '')
                                if h_auth.startswith("Bearer "):
                                    token = h_auth[7:]
                                    logger.log_text(f"MIDDLEWARE: ✅ Token from body state.headers.authorization (prefix={token[:25]}..., len={len(token)})")
            except Exception as e:
                logger.log_text(f"MIDDLEWARE: ⚠️ Body parse error: {type(e).__name__}: {e}")
        
        if token:
            builtins._workspace_oauth_token = token
            # Also store in a request-scoped way via state
            request.state.oauth_token = token
        else:
            if request.url.path.startswith("/a2a/"):
                logger.log_text(f"MIDDLEWARE: ❌ No token found in request to {request.url.path}. Headers: {list(request.headers.keys())}")
        
        response = await call_next(request)
        return response

class DisableBufferingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if response.headers.get('content-type') == 'text/event-stream':
            response.headers['X-Accel-Buffering'] = 'no'
            response.headers['Cache-Control'] = 'no-cache, no-transform'
        return response

app.add_middleware(DisableBufferingMiddleware)
app.add_middleware(TokenExtractionMiddleware)

# =============================================================================
# Background Task Worker & Trigger Endpoints (Long-Running Agent Orchestration)
# =============================================================================
import asyncio as _bg_asyncio
from contextlib import nullcontext as _nullcontext

# --- Mitigation #3: Concurrency limit for background tasks ---
_WORKER_SEMAPHORE = _bg_asyncio.Semaphore(2)  # Max 2 concurrent background tasks

# --- Mitigation #4: OpenTelemetry tracing for worker visibility ---
try:
    from opentelemetry import trace as _otel_trace
    _worker_tracer = _otel_trace.get_tracer("background_worker")
except ImportError:
    _worker_tracer = None


def _fs_update_with_retry(_ref, _data, _max_retries=3):
    """Firestore update with exponential backoff for critical state transitions."""
    import time as _time, logging as _rlog
    for _attempt in range(_max_retries):
        try:
            _ref.update(_data)
            return True
        except Exception as _e:
            if _attempt == _max_retries - 1:
                _rlog.getLogger("bg_worker").error("Firestore update FAILED after %d retries: %s", _max_retries, str(_e)[:300])
                return False
            _wait = (2 ** _attempt) + 0.5
            _rlog.getLogger("bg_worker").warning("Firestore retry %d/%d in %.1fs: %s", _attempt + 1, _max_retries, _wait, str(_e)[:200])
            _time.sleep(_wait)


@app.post("/execute_task")
async def execute_task(request: Request):
    """Internal worker endpoint. Reads task config from Firestore,
    runs the agent, writes result back. Fire-and-forget from LRFT.
    Also handles Pub/Sub push messages from Cloud Scheduler."""
    import builtins, traceback as _tb
    import datetime as _dt
    import base64 as _b64, json as _bjson, logging as _wlog
    _wlogger = _wlog.getLogger("bg_worker")

    # Read ids from the QUERY STRING first. The localhost fire-and-forget caller
    # (_fire in submit_background_task_now / run_scheduled_task_now) uses a 0.5s
    # read timeout and disconnects immediately; awaiting request.json() then races
    # into ClientDisconnect and kills the worker before it starts, leaving the task
    # stuck at 'submitted' (v10.98). Query params live on the request line and are
    # always available regardless of when this coroutine is scheduled. The body is
    # only needed for Pub/Sub push (Cloud Scheduler), which carries no query params.
    _qp = request.query_params
    _qp_task = (_qp.get("task_id") or "") if _qp else ""
    _qp_demo = (_qp.get("demo_id") or "") if _qp else ""
    if _qp_task and _qp_demo:
        _body = {"task_id": _qp_task, "demo_id": _qp_demo}
        if str(_qp.get("force_run", "")).lower() in ("1", "true"):
            _body["force_run"] = True
    else:
        try:
            _body = await request.json()
        except Exception as _bjerr:
            _wlogger.error("execute_task: no query ids and body read failed (%s)", type(_bjerr).__name__)
            return {"status": "error", "message": "Missing task id (no query params, body unreadable)"}

    # --- Support both direct calls and Pub/Sub push messages ---
    # Direct call (from LRFT/localhost): {"task_id": "...", "demo_id": "..."}
    # Pub/Sub push (from Cloud Scheduler): {"message": {"data": "base64..."}}
    _msg_id = ""
    _force_run = False
    if "message" in _body and isinstance(_body.get("message"), dict):
        # Each Cloud Scheduler fire publishes a NEW Pub/Sub message with a
        # unique messageId; redeliveries of the SAME fire reuse the same id.
        _msg_id = str(_body["message"].get("messageId", "") or "")
        _msg_data = _body["message"].get("data", "")
        if _msg_data:
            try:
                _decoded = _bjson.loads(_b64.b64decode(_msg_data).decode("utf-8"))
                _task_id = _decoded.get("task_id", "")
                _demo_id = _decoded.get("demo_id", "")
                _wlogger.warning("execute_task: Pub/Sub trigger task_id=%s demo_id=%s msg_id=%s", _task_id, _demo_id, _msg_id)
            except Exception as _parse_err:
                _wlogger.error("execute_task: Failed to parse Pub/Sub data: %s", str(_parse_err))
                _task_id = ""
                _demo_id = ""
        else:
            _task_id = ""
            _demo_id = ""
    else:
        _task_id = _body.get("task_id", "")
        _demo_id = _body.get("demo_id", "")
        # Set by run_scheduled_task_now (manual test run): allow re-running a
        # task whose execution doc already holds a terminal status.
        _force_run = bool(_body.get("force_run"))

    _fs = getattr(builtins, '_firestore_client', None)
    if not _fs or not _task_id or not _demo_id:
        _wlogger.error("execute_task: Missing config (fs=%s, task_id=%s, demo_id=%s)", bool(_fs), repr(_task_id), repr(_demo_id))
        return {"status": "error", "message": "Missing config"}

    _exec_ref = _fs.collection(_demo_id + "_task_executions").document(_task_id)
    _def_ref = _fs.collection(_demo_id + "_task_definitions").document(_task_id)

    _def_doc = _def_ref.get()
    if not _def_doc.exists:
        return {"status": "error", "message": "Definition not found"}
    _def_data = _def_doc.to_dict()
    _task_prompt = _def_data.get("task_prompt", "")
    _task_name = _def_data.get("task_name", "unknown")

    # --- Mitigation #3: Acquire semaphore before execution ---
    async with _WORKER_SEMAPHORE:

        # --- Mitigation #4: Create OTel span for Cloud Trace visibility ---
        _span_ctx = _worker_tracer.start_as_current_span(
            "background_task." + _task_name,
            attributes={"task_id": _task_id, "task_name": _task_name}
        ) if _worker_tracer else _nullcontext()

        with _span_ctx:
            # Ensure execution document exists (scheduled tasks don't pre-create one)
            _exec_snap = _exec_ref.get()
            _current = _exec_snap.to_dict() if _exec_snap.exists else None

            # Same Pub/Sub message redelivered (ack lost, or the run exceeded
            # the ack deadline): this exact fire already ran or is running.
            if _current and _msg_id and _msg_id == _current.get("last_sched_msg_id", ""):
                _wlogger.warning("execute_task: duplicate delivery of msg %s for task %s, skipping", _msg_id, _task_id)
                return {"status": _current.get("status", "unknown"), "task_id": _task_id}

            # A NEW Cloud Scheduler fire (fresh messageId) of a recurring task,
            # or an explicit manual test run (force_run from
            # run_scheduled_task_now), MUST re-run even though the single
            # per-definition execution doc still holds the previous run's
            # terminal status. Without this exception the 2nd+ fire of every
            # recurring scheduled task is skipped forever.
            _is_refire = bool(_msg_id and _def_data.get("task_type") == "scheduled") or _force_run

            # Check if cancelled before starting
            if _current and _current.get("status") == "cancelled" and not _is_refire:
                return {"status": "cancelled", "task_id": _task_id}

            # Idempotency guard: skip if already completed or failed
            # (prevents stray re-posts of the same execution from overwriting status)
            if _current and _current.get("status") in ("completed", "failed") and not _is_refire:
                _wlogger.warning("execute_task: task %s already %s, skipping re-execution", _task_id, _current.get("status"))
                return {"status": _current.get("status"), "task_id": _task_id}

            # Scheduled AUTONOMOUS fire (v11.33): delegate to the sandbox
            # agent instead of running the background worker. Each fire
            # creates its own per-run autonomous ticket; the SCHEDULE's
            # execution doc only records fire metadata and stays status
            # 'scheduled', so cancelling it stops future fires via the
            # cancelled guard above.
            if os.environ.get("ENABLE_MANAGED_AGENT") == "1" and _def_data.get("task_type") == "scheduled_autonomous":
                _fire_res = {}
                try:
                    _fire_res = _agent_tools._ma_fire_scheduled_autonomous(_def_data, _msg_id)
                except Exception as _fire_err:
                    _fire_res = {"status": "error", "message": str(_fire_err)[:200]}
                _wlogger.warning("execute_task: scheduled_autonomous %s fire -> %s (ticket=%s)",
                                 _task_id, str(_fire_res.get("status", "")), str(_fire_res.get("ticket-id", "")))
                try:
                    _fire_now = _dt.datetime.now(_dt.timezone.utc)
                    _fire_line = ("[" + _fire_now.strftime("%H:%M:%S") + "] SCHEDULER: fire -> "
                                  + str(_fire_res.get("status", "")) + " ticket "
                                  + str(_fire_res.get("ticket-id", "") or "-") + chr(10))
                    _sched_update = {
                        "status": "scheduled",
                        "last_fired_at": _fire_now.isoformat(),
                        "log_tail": (((_current or {}).get("log_tail", "") or "") + _fire_line)[-1500:],
                    }
                    if _msg_id:
                        _sched_update["last_sched_msg_id"] = _msg_id
                    _exec_ref.set(_sched_update, merge=True)
                except Exception:
                    pass
                return {"status": str(_fire_res.get("status", "error")), "task_id": _task_id,
                        "ticket": str(_fire_res.get("ticket-id", ""))}



            # Update status to working — use set(merge=True) so it works for
            # both pre-existing docs (immediate tasks) and new docs (scheduled tasks)
            _now = _dt.datetime.now(_dt.timezone.utc).isoformat()
            _working_doc = {
                "task_id": _task_id,
                "definition_id": _task_id,
                "status": "working",
                "started_at": _now,
                "progress_pct": 10,
                "log_tail": "",
                "result_summary": "",
                "completed_at": "",
                "reported_to_user": False,
            }
            if _msg_id:
                # Remember the processed fire so a redelivery of the SAME
                # message is skipped while a fresh fire still re-runs.
                _working_doc["last_sched_msg_id"] = _msg_id
            _exec_ref.set(_working_doc, merge=True)
            _wlogger.warning("execute_task: STARTING task=%s name=%s prompt_len=%d prompt_head=%s", _task_id, _task_name, len(_task_prompt), repr(_task_prompt[:200]))

            try:
                # Run agent with task prompt using the background runner (Pro model)
                _runner = background_runner
                _session_id = "task-" + _task_id
                _user_id = "background-worker"
                # Delete existing session if present (scheduled task re-execution safety)
                _existing_session = await _runner.session_service.get_session(
                    app_name=_runner.app_name,
                    user_id=_user_id,
                    session_id=_session_id,
                )
                if _existing_session:
                    await _runner.session_service.delete_session(
                        app_name=_runner.app_name,
                        user_id=_user_id,
                        session_id=_session_id,
                    )
                await _runner.session_service.create_session(
                    app_name=_runner.app_name,
                    user_id=_user_id,
                    session_id=_session_id,
                )
                from google.genai import types as _genai_types

                # The background_agent has execution directives baked into
                # its system prompt — no need for runtime _exec_directive.
                _full_prompt = _task_prompt

                _results = []
                _all_text = []
                _tool_calls = []
                _event_count = 0
                _cancel_check_counter = 0
                _bg_malformed_retries = 0

                # =====================================================================
                # Background resilience — parity with the foreground handler.
                # The worker previously ran run_async raw: a MALFORMED_FUNCTION_CALL or
                # LlmCallsLimit at the synthesis step ended the run with no final text,
                # so result_summary was stored as "No output" even after all data was
                # gathered. This mirrors the proven foreground logic (v10.55-v10.59):
                #   - LlmCallsLimit auto-continue (re-invoke with a continuation message)
                #   - MALFORMED retry + session heal (re-run the whole invocation)
                #   - robust text capture (retain any text part as a fallback)
                #   - synthesis recovery (re-prompt for a text-only report if empty)
                # The happy path (final response has text) is unchanged — every new
                # branch fires ONLY on the error/empty paths.
                # =====================================================================
                _BG_MAX_AUTO_CONTINUES = 4
                _BG_MAX_MALFORMED_RETRIES = 3  # v10.61: was 2 — parity with foreground
                _BG_MAX_SYNTH_RETRIES = 3
                # v10.61: English prompts + same-language clause so the stored report
                # follows the conversation's language instead of being forced to Japanese.
                _BG_CONTINUE_MESSAGE = (
                    "Using everything you have already gathered and analyzed, finish the "
                    "interrupted report to completion. Keep any additional tool calls to the "
                    "strict minimum. Write the report in the SAME language you have been using "
                    "with the user in this conversation; do not switch languages."
                )
                _BG_SYNTH_MESSAGE = (
                    "Using ONLY the results you have already gathered (do NOT make any more "
                    "tool calls, and do NOT use A2UI or JSON), produce the final analysis report "
                    "now as complete Markdown plain text. Include the key findings, the numbers, "
                    "and at least three recommendations. Write everything in the SAME language "
                    "you have been using with the user in this conversation; do not switch languages."
                )

                async def _bg_heal_session():
                    try:
                        _hs = await _runner.session_service.get_session(
                            app_name=_runner.app_name, user_id=_user_id, session_id=_session_id,
                        )
                        if _hs is not None:
                            _heal_session_events(_hs)
                    except Exception as _he:
                        _wlogger.warning("execute_task: session heal failed task=%s err=%s", _task_id, str(_he)[:200])

                async def _bg_run_with_auto_continue(_msg_text):
                    # Re-invoke run_async on LlmCallsLimitExceededError with a healed
                    # session + continuation message, up to _BG_MAX_AUTO_CONTINUES.
                    # Caught by class name (not import) to stay robust across ADK versions.
                    _auto = 0
                    _cur_text = _msg_text
                    while True:
                        try:
                            async for _ev in _runner.run_async(
                                user_id=_user_id,
                                session_id=_session_id,
                                new_message=_genai_types.Content(role="user", parts=[_genai_types.Part(text=_cur_text)]),
                            ):
                                yield _ev
                            return
                        except Exception as _ace:
                            if type(_ace).__name__ != 'LlmCallsLimitExceededError':
                                raise
                            if _auto >= _BG_MAX_AUTO_CONTINUES:
                                _wlogger.warning("execute_task: LlmCallsLimit budget exhausted task=%s — emitting partial", _task_id)
                                return
                            _auto += 1
                            _wlogger.warning("execute_task: LlmCallsLimit auto-continue task=%s (%d/%d)", _task_id, _auto, _BG_MAX_AUTO_CONTINUES)
                            await _bg_heal_session()
                            _cur_text = _BG_CONTINUE_MESSAGE

                async def _bg_events(_msg_text):
                    # Wrap the auto-continue generator with MALFORMED retry: on a
                    # MALFORMED_FUNCTION_CALL event, heal the session and re-run the
                    # whole invocation on the same session (mirrors foreground _all_events).
                    nonlocal _bg_malformed_retries
                    _retry_text = _msg_text
                    while True:
                        _should_retry = False
                        async for _ev in _bg_run_with_auto_continue(_retry_text):
                            _ec = getattr(_ev, 'error_code', None)
                            if _ec and 'MALFORMED_FUNCTION_CALL' in str(_ec) and _bg_malformed_retries < _BG_MAX_MALFORMED_RETRIES:
                                _bg_malformed_retries += 1
                                _wlogger.warning("execute_task: MALFORMED auto-retry task=%s (%d/%d)", _task_id, _bg_malformed_retries, _BG_MAX_MALFORMED_RETRIES)
                                _should_retry = True
                                break
                            yield _ev
                        if _should_retry:
                            await _bg_heal_session()
                            _retry_text = _BG_CONTINUE_MESSAGE
                            continue
                        return

                async def _bg_consume(_gen):
                    # Shared consumption: tool tracking, cancellation, text capture.
                    # Returns True if the task was cancelled mid-run.
                    nonlocal _event_count, _cancel_check_counter
                    async for event in _gen:
                        _event_count += 1

                        # Track tool calls for diagnostics + robust text capture
                        if event.content and event.content.parts:
                            for _ep in event.content.parts:
                                if hasattr(_ep, 'function_call') and _ep.function_call:
                                    _fc_name = _ep.function_call.name if _ep.function_call.name else "unknown"
                                    _tool_calls.append(_fc_name)
                                    _wlogger.warning("execute_task: TOOL_CALL task=%s tool=%s", _task_id, _fc_name)
                                if hasattr(_ep, 'function_response') and _ep.function_response:
                                    _fr_name = _ep.function_response.name if _ep.function_response.name else "unknown"
                                    _wlogger.warning("execute_task: TOOL_RESULT task=%s tool=%s", _task_id, _fr_name)
                                # Robust capture: retain ANY text part as a fallback so a
                                # missing final-response text never silently loses content.
                                if hasattr(_ep, 'text') and _ep.text:
                                    _all_text.append(_ep.text)

                        # Cooperative cancellation check (every 10 events to reduce Firestore reads)
                        _cancel_check_counter += 1
                        if _cancel_check_counter % 10 == 0:
                            try:
                                _check_snap = _exec_ref.get()
                                _check = _check_snap.to_dict() if _check_snap.exists else {}
                                if _check.get("status") == "cancelled":
                                    _wlogger.warning("execute_task: CANCELLED task=%s after %d events", _task_id, _event_count)
                                    return True
                            except Exception:
                                pass  # Check failure should not stop task execution

                        if event.is_final_response() and event.content and event.content.parts:
                            for _p in event.content.parts:
                                if hasattr(_p, 'text') and _p.text:
                                    _results.append(_p.text)
                    return False

                # --- Main run (auto-continue + MALFORMED retry) ---
                if await _bg_consume(_bg_events(_full_prompt)):
                    return {"status": "cancelled", "task_id": _task_id}

                # --- Synthesis recovery: no final-response text was produced (e.g. the
                # synthesis turn hit MALFORMED/limit). The data is already gathered, so
                # re-prompt for a text-only report, healing the bloated context first. ---
                _synth_try = 0
                while (not _results) and _synth_try < _BG_MAX_SYNTH_RETRIES:
                    _synth_try += 1
                    _wlogger.warning("execute_task: synthesis recovery task=%s (%d/%d) — empty final text, re-synthesizing", _task_id, _synth_try, _BG_MAX_SYNTH_RETRIES)
                    await _bg_heal_session()
                    try:
                        if await _bg_consume(_bg_run_with_auto_continue(_BG_SYNTH_MESSAGE)):
                            return {"status": "cancelled", "task_id": _task_id}
                    except Exception as _se:
                        _wlogger.warning("execute_task: synthesis recovery error task=%s err=%s", _task_id, str(_se)[:200])

                # Prefer final-response text; fall back to any captured text; else empty.
                if _results:
                    _result_text = chr(10).join(_results)
                elif _all_text:
                    _wlogger.warning("execute_task: using fallback text capture task=%s (no final-response text)", _task_id)
                    _result_text = chr(10).join(_all_text)
                else:
                    _result_text = "No output"
                # Strip A2UI blocks from result — they are session-specific UI artifacts
                # that become meaningless when stored and replayed later.
                import re as _re_strip
                _result_text = _re_strip.sub(r'<a2ui-json>.*?</a2ui-json>', '', _result_text, flags=_re_strip.DOTALL).strip()
                _completed_at = _dt.datetime.now(_dt.timezone.utc).isoformat()

                # Warn if no tool calls were made — the agent likely just planned/described
                if not _tool_calls:
                    _wlogger.warning("execute_task: NO_TOOL_CALLS task=%s events=%d — agent may not have executed operations", _task_id, _event_count)

                _final_status = "completed"
                # Persist the FULL report (was [:2000], which truncated the deliverable
                # so "View Full Report"/continue could never recover the rest). Cap by
                # BYTES, not chars: JA is ~3 bytes/char in UTF-8, and the whole doc
                # (this field + tool_calls + log_tail) must stay under Firestore's 1 MiB
                # document limit, so leave generous headroom.
                _RESULT_CAP_BYTES = 700000
                _result_bytes = _result_text.encode("utf-8")
                if len(_result_bytes) > _RESULT_CAP_BYTES:
                    _result_summary_store = (
                        _result_bytes[:_RESULT_CAP_BYTES].decode("utf-8", "ignore")
                        + chr(10) + "...[truncated: report exceeded storage limit]"
                    )
                else:
                    _result_summary_store = _result_text
                _fs_update_with_retry(_exec_ref, {
                    "status": _final_status,
                    "progress_pct": 100,
                    "result_summary": _result_summary_store,
                    "completed_at": _completed_at,
                    "reported_to_user": False,
                    "tool_calls": _tool_calls[:50],
                    "event_count": _event_count,
                })
                _wlogger.warning("execute_task: COMPLETED task=%s events=%d tools=%s result_len=%d", _task_id, _event_count, repr(_tool_calls[:10]), len(_result_text))

                # Send A2A push notification if configured
                await _send_push_notification(_fs, _demo_id, _task_id, _final_status, _result_text[:500])

                # Publish to result topic for trigger EP notification
                try:
                    from google.cloud import pubsub_v1
                    import json as _pjson
                    _publisher = pubsub_v1.PublisherClient()
                    _project = os.environ.get("GOOGLE_CLOUD_PROJECT", "")
                    _topic = "projects/" + _project + "/topics/" + _demo_id + "-task-results"
                    _publisher.publish(_topic, _pjson.dumps({"task_id": _task_id, "demo_id": _demo_id, "status": _final_status}).encode("utf-8"))
                except Exception:
                    pass

                return {"status": _final_status, "task_id": _task_id}

            except Exception as _e:
                _wlogger.error("execute_task: FAILED task=%s error=%s", _task_id, str(_e)[:500])
                _fs_update_with_retry(_exec_ref, {
                    "status": "failed",
                    "log_tail": str(_e)[:500],
                    "completed_at": _dt.datetime.now(_dt.timezone.utc).isoformat(),
                })
                await _send_push_notification(_fs, _demo_id, _task_id, "failed", str(_e)[:200])
                return {"status": "failed", "error": str(_e)[:200]}


async def _send_push_notification(_fs, _demo_id, _task_id, _status, _message):
    """Sends A2A push notification if client configured a webhook."""
    if not _fs or not _demo_id:
        return
    try:
        _config_ref = _fs.collection(_demo_id + "_task_push_configs").document(_task_id)
        _config_doc = _config_ref.get()
        if not _config_doc.exists:
            return
        _config = _config_doc.to_dict()
        _webhook_url = _config.get("webhook_url", "")
        if not _webhook_url:
            return

        import httpx as _httpx
        import json as _pjson
        _payload = {
            "jsonrpc": "2.0",
            "method": "tasks/pushNotification",
            "params": {
                "taskId": _task_id,
                "status": {"state": _status, "message": _message[:500]},
            },
        }
        async with _httpx.AsyncClient(timeout=10) as _client:
            await _client.post(_webhook_url, json=_payload)
    except Exception:
        pass


# --- Push Notification Configuration Endpoint (A2A Standard) ---
@app.post("/tasks/pushNotification/set")
async def set_push_notification(request: Request):
    """A2A-compliant endpoint for clients to register push notification webhooks."""
    import builtins
    _body = await request.json()
    _params = _body.get("params", {})
    _task_id = _params.get("taskId", "")
    _config = _params.get("pushNotificationConfig", {})
    _webhook_url = _config.get("url", "")

    _fs = getattr(builtins, '_firestore_client', None)
    _demo_id = os.environ.get("DEMO_ID", "")
    if not _fs or not _demo_id or not _task_id:
        return {"jsonrpc": "2.0", "error": {"code": -32602, "message": "Invalid params"}}

    _fs.collection(_demo_id + "_task_push_configs").document(_task_id).set({
        "task_id": _task_id,
        "webhook_url": _webhook_url,
        "authentication": _config.get("authentication", {}),
    })
    return {"jsonrpc": "2.0", "result": {"taskId": _task_id, "status": "configured"}}


@app.post("/feedback")
def collect_feedback(feedback: Feedback) -> dict[str, str]:
    logger.log_struct(feedback.model_dump(), severity="INFO")
    return {"status": "success"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
